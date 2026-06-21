from limits import parse
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

_storage = MemoryStorage()
_strategy = MovingWindowRateLimiter(_storage)
_ip_limit = parse("100/minute")
_key_limit = parse("1000/minute")


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        api_key = request.headers.get("X-Agent-Key")
        if api_key:
            identifier = f"key:{api_key}"
            limit = _key_limit
        else:
            identifier = f"ip:{get_remote_address(request)}"
            limit = _ip_limit

        if not _strategy.hit(limit, identifier):
            return JSONResponse(
                {"detail": "Rate limit exceeded"},
                status_code=429,
                headers={"Retry-After": "60"},
            )
        return await call_next(request)


def reset_limits() -> None:
    _storage.reset()
