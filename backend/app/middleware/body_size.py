from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to limit request body size to 1 MiB."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.headers.get("content-length"):
            if int(request.headers["content-length"]) > 1_048_576:  # 1 MiB
                raise HTTPException(413, "Payload too large")
        return await call_next(request)
