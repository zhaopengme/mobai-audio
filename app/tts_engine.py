import io
import logging
from typing import Generator

import numpy as np
import soundfile as sf
from pydub import AudioSegment

from app.config import get_settings
from app.models import ResponseFormatEnum, VoiceEnum

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
