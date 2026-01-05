from __future__ import annotations

from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.settings import settings


class ThemeMiddleware(BaseHTTPMiddleware):
    """
    Cookie-based theme selection.

    - Reads theme from a cookie (default: "theme")
    - Falls back to DEFAULT_THEME
    - Stores result on request.state.theme for templates
    """

    def __init__(self, app):
        super().__init__(app)
        self.default_theme = settings.DEFAULT_THEME
        self.excluded_prefixes = settings.THEME_EXCLUDED_PREFIXES

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        if any(path.startswith(prefix) for prefix in self.excluded_prefixes):
            request.state.theme = self.default_theme
            return await call_next(request)

        request.state.theme = request.cookies.get("theme") or self.default_theme
        return await call_next(request)
