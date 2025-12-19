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
VOICE_MAPPING_KOKORO: dict[VoiceEnum, str] = {
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
    """TTS 引擎封装，支持多种模型"""

    def __init__(self):
        self._model = None
        self._pipeline = None  # Kokoro 专用
        self._whisper_model = None
        self._settings = get_settings()
        self._model_type = self._settings.model_type

    def _ensure_loaded(self):
        """确保模型已加载"""
        if self._model is not None:
            return

        logger.info(f"Loading model ({self._model_type}): {self._settings.mlx_model}")

        if self._model_type == "kokoro":
            self._load_kokoro()
        elif self._model_type == "chatterbox":
            self._load_chatterbox()
        else:
            raise ValueError(f"Unsupported model type: {self._model_type}")

        logger.info("Model loaded successfully")

    def _load_kokoro(self):
        """加载 Kokoro 模型"""
        from mlx_audio.tts.models.kokoro import KokoroPipeline
        from mlx_audio.tts.utils import load_model

        self._model = load_model(self._settings.mlx_model)
        self._pipeline = KokoroPipeline(
            lang_code=self._settings.default_lang,
            model=self._model,
            repo_id=self._settings.mlx_model,
        )

    def _load_chatterbox(self):
        """加载 Chatterbox 模型"""
        from mlx_audio.tts.utils import load_model

        self._model = load_model(self._settings.mlx_model)

    def _generate_audio(self, text: str, voice: VoiceEnum, speed: float) -> tuple[np.ndarray, int]:
        """生成音频数据，返回 (audio_data, sample_rate)"""
        self._ensure_loaded()

        if self._model_type == "kokoro":
            return self._generate_kokoro(text, voice, speed)
        elif self._model_type == "chatterbox":
            return self._generate_chatterbox(text, speed)
        else:
            raise ValueError(f"Unsupported model type: {self._model_type}")

    def _generate_kokoro(self, text: str, voice: VoiceEnum, speed: float) -> tuple[np.ndarray, int]:
        """使用 Kokoro 生成音频"""
        kokoro_voice = VOICE_MAPPING_KOKORO.get(voice, self._settings.default_voice)

        audio_segments = []
        for _, _, audio in self._pipeline(text, voice=kokoro_voice, speed=speed):
            audio_segments.append(audio[0])

        if audio_segments:
            audio_data = np.concatenate(audio_segments)
        else:
            audio_data = np.array([], dtype=np.float32)

        return audio_data, self._settings.default_sample_rate

    def _generate_chatterbox(self, text: str, speed: float) -> tuple[np.ndarray, int]:
        """使用 Chatterbox 生成音频"""
        # Chatterbox 不支持 voice 和 speed 参数，使用默认设置
        audio_segments = []
        for result in self._model.generate(text=text, verbose=False):
            if result.audio is not None:
                audio_segments.append(np.array(result.audio))

        if audio_segments:
            audio_data = np.concatenate(audio_segments)
        else:
            audio_data = np.array([], dtype=np.float32)

        # Chatterbox 输出 24kHz
        return audio_data, 24000

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
        audio_data, sample_rate = self._generate_audio(text, voice, speed)

        audio_bytes = self._convert_format(
            audio_data,
            sample_rate,
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
        audio_data, sample_rate = self._generate_audio(text, voice, speed)

        # 转换为 mp3 并编码为 base64
        audio_bytes = self._convert_format(
            audio_data,
            sample_rate,
            ResponseFormatEnum.mp3,
        )
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

        # 使用 Whisper 进行字符对齐
        alignment = self._align_audio(audio_data, text, sample_rate)

        return audio_base64, alignment

    def _align_audio(self, audio_data: np.ndarray, text: str, sample_rate: int) -> AlignmentInfo | None:
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
            if sample_rate != 16000:
                num_samples = int(len(audio_data) * 16000 / sample_rate)
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
        # Chatterbox 只支持英语
        if self._model_type == "chatterbox":
            return "en"

        lang_map = {
            "a": "en",
            "b": "en",
            "z": "zh",
            "j": "ja",
        }
        return lang_map.get(self._settings.default_lang, "en")

    def _convert_format(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        target_format: ResponseFormatEnum,
    ) -> bytes:
        """转换音频格式"""
        wav_buffer = io.BytesIO()
        sf.write(wav_buffer, audio_data, sample_rate, format="WAV")
        wav_buffer.seek(0)

        if target_format == ResponseFormatEnum.wav:
            return wav_buffer.getvalue()

        if target_format == ResponseFormatEnum.pcm:
            pcm_data = (audio_data * 32767).astype(np.int16)
            return pcm_data.tobytes()

        audio_segment = AudioSegment.from_wav(wav_buffer)
        output_buffer = io.BytesIO()

        format_map = {
            ResponseFormatEnum.mp3: "mp3",
            ResponseFormatEnum.opus: "opus",
            ResponseFormatEnum.aac: "adts",
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
