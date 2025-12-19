import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from app.auth import verify_api_key
from app.config import get_settings
from app.models import (
    ErrorResponse,
    ModelInfo,
    ModelsResponse,
    SpeechRequest,
)
from app.tts_engine import get_tts_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["audio"])

# 线程池和信号量（在 main.py 中初始化）
_executor: ThreadPoolExecutor | None = None
_semaphore: asyncio.Semaphore | None = None


def init_concurrency(max_workers: int):
    """初始化并发控制"""
    global _executor, _semaphore
    _executor = ThreadPoolExecutor(max_workers=max_workers)
    _semaphore = asyncio.Semaphore(max_workers)


@router.post(
    "/audio/speech",
    responses={
        200: {"content": {"audio/mpeg": {}}},
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def create_speech(
    request: SpeechRequest,
    api_key: str = Depends(verify_api_key),
) -> Response:
    """
    生成语音

    兼容 OpenAI TTS API
    """
    global _executor, _semaphore

    if _executor is None or _semaphore is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"message": "Server not initialized", "type": "server_error"}},
        )

    # 获取信号量，限制并发
    async with _semaphore:
        try:
            loop = asyncio.get_event_loop()
            engine = get_tts_engine()

            # 在线程池中执行 TTS 生成
            audio_bytes, content_type = await loop.run_in_executor(
                _executor,
                engine.generate,
                request.input,
                request.voice,
                request.speed,
                request.response_format,
            )

            return Response(
                content=audio_bytes,
                media_type=content_type,
            )

        except Exception as e:
            logger.exception("TTS generation failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": {
                        "message": str(e),
                        "type": "server_error",
                    }
                },
            )


@router.get("/models", response_model=ModelsResponse)
async def list_models(
    api_key: str = Depends(verify_api_key),
) -> ModelsResponse:
    """
    列出可用模型

    兼容 OpenAI Models API
    """
    settings = get_settings()
    current_time = int(time.time())

    return ModelsResponse(
        data=[
            ModelInfo(
                id="tts-1",
                created=current_time,
                owned_by="local",
            ),
            ModelInfo(
                id="tts-1-hd",
                created=current_time,
                owned_by="local",
            ),
        ]
    )


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}
