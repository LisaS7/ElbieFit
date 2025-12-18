from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response

from app.settings import settings
from app.utils.db import RateLimitDdbError, rate_limit_hit
from app.utils.log import logger

# ─────────────────────────────────────────
# Config
# ─────────────────────────────────────────


@dataclass(frozen=True)
class LimitConfig:
    read_per_min: int
    write_per_min: int


# ─────────────────────────────────────────
# Middleware
# ─────────────────────────────────────────


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Global rate limiting middleware.

    - Applies baseline limits to all users.
    - Applies stricter limits when a demo session cookie is present.
    - Uses DynamoDB fixed-window counters via rate_limit_hit().
    """

    def __init__(self, app):
        super().__init__(app)

        self.excluded_prefixes = settings.RATE_LIMIT_EXCLUDED_PREFIXES

        self.limits = LimitConfig(
            read_per_min=settings.RATE_LIMIT_READ_PER_MIN,
            write_per_min=settings.RATE_LIMIT_WRITE_PER_MIN,
        )

        self.ttl_seconds = settings.RATE_LIMIT_TTL_SECONDS

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        path = request.url.path

        if self._is_excluded(path):
            return await call_next(request)

        client_id = self._identify_client(request)

        is_write = request.method.upper() not in ("GET", "HEAD", "OPTIONS")
        limit = self.limits.write_per_min if is_write else self.limits.read_per_min

        try:
            allowed, retry_after = rate_limit_hit(
                client_id=client_id,
                limit=limit,
                ttl_seconds=self.ttl_seconds,
            )
        except RateLimitDdbError:
            # Fail open so limiter issues don't break the whole app.
            logger.warning(
                f"Rate limiter storage error; allowing request. Path: {path}. Method: {request.method}",
            )
            return await call_next(request)

        if not allowed:
            logger.info(
                f"Request blocked by rate limiter.\nPath: {path}\nMethod:{request.method}\nRetry after: {retry_after}",
            )
            return PlainTextResponse(
                "Rate limit exceeded. Please try again shortly.",
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)

    # ─────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────

    def _is_excluded(self, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in self.excluded_prefixes)

    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP, preferring X-Forwarded-For.
        """
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()

        if request.client:
            return request.client.host

        return "unknown"

    def _identify_client(self, request: Request) -> str:
        ip = self._get_client_ip(request)
        ua = request.headers.get("user-agent", "unknown")
        ua_hash = str(abs(hash(ua)) % 10_000_000)
        return f"ip:{ip}:ua:{ua_hash}"
