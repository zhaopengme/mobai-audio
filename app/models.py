from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class VoiceEnum(str, Enum):
    """OpenAI 兼容的声音选项"""

    alloy = "alloy"
    echo = "echo"
    fable = "fable"
    onyx = "onyx"
    nova = "nova"
    shimmer = "shimmer"


class ResponseFormatEnum(str, Enum):
    """支持的音频格式"""

    mp3 = "mp3"
    opus = "opus"
    aac = "aac"
    flac = "flac"
    wav = "wav"
    pcm = "pcm"
    json = "json"


class SpeechRequest(BaseModel):
    """TTS 请求模型"""

    model: str = Field(
        default="tts-1",
        description="模型名称（接收但使用后台配置）",
    )
    input: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        description="要转换为语音的文本",
    )
    voice: VoiceEnum = Field(
        default=VoiceEnum.alloy,
        description="声音选择",
    )
    response_format: ResponseFormatEnum = Field(
        default=ResponseFormatEnum.mp3,
        description="音频输出格式",
    )
    speed: float = Field(
        default=1.0,
        ge=0.25,
        le=4.0,
        description="语速 (0.25-4.0)",
    )


class ModelInfo(BaseModel):
    """模型信息"""

    id: str
    object: Literal["model"] = "model"
    created: int
    owned_by: str


class ModelsResponse(BaseModel):
    """模型列表响应"""

    object: Literal["list"] = "list"
    data: list[ModelInfo]


class ErrorDetail(BaseModel):
    """错误详情"""

    message: str
    type: str
    code: str | None = None


class ErrorResponse(BaseModel):
    """错误响应"""

    error: ErrorDetail


class AlignmentInfo(BaseModel):
    """字符对齐信息"""

    characters: list[str]
    characterStartTimesSeconds: list[float]
    characterEndTimesSeconds: list[float]


class SpeechJsonResponse(BaseModel):
    """JSON 格式的语音响应"""

    audio_base64: str
    alignment: AlignmentInfo | None = None
