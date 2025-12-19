from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # 服务配置
    host: str = "0.0.0.0"
    port: int = 8000

    # API Keys（逗号分隔）
    api_keys: str = ""

    # 并发配置
    max_workers: int = 4

    # MLX-Audio 配置
    mlx_model: str = "prince-canuma/Kokoro-82M"
    default_voice: str = "af_heart"
    default_lang: str = "a"
    default_sample_rate: int = 24000

    @property
    def api_keys_list(self) -> list[str]:
        """解析 API Keys 为列表"""
        if not self.api_keys:
            return []
        return [k.strip() for k in self.api_keys.split(",") if k.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
