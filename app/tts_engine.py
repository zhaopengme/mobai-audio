import base64
import io
import logging

import numpy as np
import soundfile as sf
from pydub import AudioSegment

from app.config import get_settings
from app.models import AlignmentInfo, ResponseFormatEnum, VoiceEnum

logger = logging.getLogger(__name__)

# OpenAI 声音到 Kokoro 声音的映射
VOICE_MAPPING: dict[VoiceEnum, str] = {
    VoiceEnum.alloy: "af_heart",
    VoiceEnum.echo: "am_adam",
    VoiceEnum.fable: "bf_emma",
    VoiceEnum.onyx: "bm_george",
    VoiceEnum.nova: "af_bella",
    VoiceEnum.shimmer: "af_nicole",
}

# 音频格式的 MIME 类型
CONTENT_TYPE_MAPPING: dict[ResponseFormatEnum, str] = {
    ResponseFormatEnum.mp3: "audio/mpeg",
    ResponseFormatEnum.opus: "audio/opus",
    ResponseFormatEnum.aac: "audio/aac",
    ResponseFormatEnum.flac: "audio/flac",
    ResponseFormatEnum.wav: "audio/wav",
    ResponseFormatEnum.pcm: "audio/pcm",
}


class TTSEngine:
    """TTS 引擎封装"""

    def __init__(self):
        self._pipeline = None
        self._model = None
        self._whisper_model = None
        self._settings = get_settings()

    def _ensure_loaded(self):
        """确保模型已加载"""
        if self._pipeline is not None:
            return

        logger.info(f"Loading model: {self._settings.mlx_model}")

        from mlx_audio.tts.models.kokoro import KokoroPipeline
        from mlx_audio.tts.utils import load_model

        self._model = load_model(self._settings.mlx_model)
        self._pipeline = KokoroPipeline(
            lang_code=self._settings.default_lang,
            model=self._model,
            repo_id=self._settings.mlx_model,
        )
        logger.info("Model loaded successfully")

    def generate(
        self,
        text: str,
        voice: VoiceEnum,
        speed: float = 1.0,
        response_format: ResponseFormatEnum = ResponseFormatEnum.mp3,
    ) -> tuple[bytes, str]:
        """
        生成语音

        Args:
            text: 要转换的文本
            voice: OpenAI 声音选项
            speed: 语速
            response_format: 输出格式

        Returns:
            (音频数据, content_type)
        """
        self._ensure_loaded()

        # 映射声音
        kokoro_voice = VOICE_MAPPING.get(voice, self._settings.default_voice)

        # 生成音频
        audio_segments = []
        for _, _, audio in self._pipeline(text, voice=kokoro_voice, speed=speed):
            audio_segments.append(audio[0])

        # 合并音频片段
        if audio_segments:
            audio_data = np.concatenate(audio_segments)
        else:
            audio_data = np.array([], dtype=np.float32)

        # 转换格式
        audio_bytes = self._convert_format(
            audio_data,
            self._settings.default_sample_rate,
            response_format,
        )

        content_type = CONTENT_TYPE_MAPPING[response_format]
        return audio_bytes, content_type

    def generate_json(
        self,
        text: str,
        voice: VoiceEnum,
        speed: float = 1.0,
    ) -> tuple[str, AlignmentInfo | None]:
        """
        生成语音并返回 base64 编码

        Args:
            text: 要转换的文本
            voice: OpenAI 声音选项
            speed: 语速

        Returns:
            (audio_base64, alignment_or_none)
        """
        self._ensure_loaded()

        # 映射声音
        kokoro_voice = VOICE_MAPPING.get(voice, self._settings.default_voice)

        # 生成音频
        audio_segments = []
        for _, _, audio in self._pipeline(text, voice=kokoro_voice, speed=speed):
            audio_segments.append(audio[0])

        # 合并音频片段
        if audio_segments:
            audio_data = np.concatenate(audio_segments)
        else:
            audio_data = np.array([], dtype=np.float32)

        # 转换为 mp3 并编码为 base64
        audio_bytes = self._convert_format(
            audio_data,
            self._settings.default_sample_rate,
            ResponseFormatEnum.mp3,
        )
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

        # 使用 Whisper 进行字符对齐
        alignment = self._align_audio(audio_data, text)

        return audio_base64, alignment

    def _align_audio(self, audio_data: np.ndarray, text: str) -> AlignmentInfo | None:
        """使用 Whisper 进行强制对齐"""
        if len(audio_data) == 0:
            return None

        try:
            import stable_whisper
            from scipy import signal

            # 懒加载 Whisper 模型
            if self._whisper_model is None:
                logger.info(f"Loading Whisper model: {self._settings.whisper_model}")
                self._whisper_model = stable_whisper.load_model(self._settings.whisper_model)
                logger.info("Whisper model loaded successfully")

            # Whisper 需要 16kHz 采样率，重采样
            if self._settings.default_sample_rate != 16000:
                num_samples = int(len(audio_data) * 16000 / self._settings.default_sample_rate)
                audio_16k = signal.resample(audio_data, num_samples).astype(np.float32)
            else:
                audio_16k = audio_data

            # 强制对齐
            result = self._whisper_model.align(
                audio_16k,
                text,
                language=self._get_whisper_language(),
                original_split=True,
            )

            # 提取字符级时间戳
            characters = []
            start_times = []
            end_times = []

            for segment in result.segments:
                for word in segment.words:
                    # 对每个词的字符进行时间分配
                    word_text = word.word.strip()
                    if not word_text:
                        continue

                    word_duration = word.end - word.start
                    char_duration = word_duration / len(word_text)

                    for i, char in enumerate(word_text):
                        characters.append(char)
                        char_start = word.start + i * char_duration
                        char_end = word.start + (i + 1) * char_duration
                        start_times.append(round(char_start, 3))
                        end_times.append(round(char_end, 3))

            if not characters:
                return None

            return AlignmentInfo(
                characters=characters,
                characterStartTimesSeconds=start_times,
                characterEndTimesSeconds=end_times,
            )

        except Exception as e:
            logger.warning(f"Alignment failed: {e}")
            return None

    def _get_whisper_language(self) -> str:
        """根据 TTS 语言配置返回 Whisper 语言代码"""
        lang_map = {
            "a": "en",  # 美式英语
            "b": "en",  # 英式英语
            "z": "zh",  # 中文
            "j": "ja",  # 日语
        }
        return lang_map.get(self._settings.default_lang, "en")

    def _convert_format(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        target_format: ResponseFormatEnum,
    ) -> bytes:
        """转换音频格式"""
        # 先写入 WAV 到内存
        wav_buffer = io.BytesIO()
        sf.write(wav_buffer, audio_data, sample_rate, format="WAV")
        wav_buffer.seek(0)

        if target_format == ResponseFormatEnum.wav:
            return wav_buffer.getvalue()

        if target_format == ResponseFormatEnum.pcm:
            # PCM: 16-bit signed little-endian
            pcm_data = (audio_data * 32767).astype(np.int16)
            return pcm_data.tobytes()

        # 使用 pydub 转换其他格式
        audio_segment = AudioSegment.from_wav(wav_buffer)
        output_buffer = io.BytesIO()

        format_map = {
            ResponseFormatEnum.mp3: "mp3",
            ResponseFormatEnum.opus: "opus",
            ResponseFormatEnum.aac: "adts",  # AAC in ADTS container
            ResponseFormatEnum.flac: "flac",
        }

        export_format = format_map.get(target_format, "mp3")
        audio_segment.export(output_buffer, format=export_format)
        output_buffer.seek(0)

        return output_buffer.getvalue()


# 全局单例
_engine: TTSEngine | None = None


def get_tts_engine() -> TTSEngine:
    """获取 TTS 引擎单例"""
    global _engine
    if _engine is None:
        _engine = TTSEngine()
    return _engine
