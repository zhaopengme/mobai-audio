from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

security = HTTPBearer(auto_error=False)


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
) -> str:
    """验证 API Key"""
    settings = get_settings()

    # 如果没有配置 API Keys，跳过验证
    if not settings.api_keys_list:
        return ""

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "message": "Missing API key",
                    "type": "invalid_request_error",
                    "code": "missing_api_key",
                }
            },
        )

    api_key = credentials.credentials
    if api_key not in settings.api_keys_list:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "message": "Invalid API key",
                    "type": "invalid_request_error",
                    "code": "invalid_api_key",
                }
            },
        )

    return api_key
