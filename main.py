import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes.audio import init_concurrency, router as audio_router

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    settings = get_settings()
    logger.info(f"Starting server on {settings.host}:{settings.port}")
    logger.info(f"Max workers: {settings.max_workers}")
    logger.info(f"Model: {settings.mlx_model}")

    # 初始化并发控制
    init_concurrency(settings.max_workers)

    yield

    # 清理（如果需要）
    logger.info("Shutting down...")


# 创建 FastAPI 应用
app = FastAPI(
    title="MLX TTS API",
    description="OpenAI 兼容的 TTS 服务，基于 mlx-audio",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(audio_router)


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "MLX TTS API",
        "version": "1.0.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )
