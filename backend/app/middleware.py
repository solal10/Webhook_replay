from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "PATCH"]:
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > 1_048_576:  # 1 MiB
                raise HTTPException(status_code=413, detail="Payload too large")
        return await call_next(request)
