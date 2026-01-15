from __future__ import annotations

from fastapi import FastAPI, Request
from starlette.testclient import TestClient

from app.middleware.theme import ThemeMiddleware
from app.settings import settings


def _make_app() -> FastAPI:
    app = FastAPI()

    @app.get("/echo-theme")
    def echo_theme(request: Request) -> dict[str, str]:
        return {"theme": request.state.theme}

    @app.get("/static/echo-theme")
    def echo_theme_static(request: Request) -> dict[str, str]:
        return {"theme": request.state.theme}

    return app


def _make_client(monkeypatch) -> TestClient:
    monkeypatch.setattr(settings, "DEFAULT_THEME", "prehistoric")
    monkeypatch.setattr(settings, "THEME_EXCLUDED_PREFIXES", ["/static", "/healthz"])

    app = _make_app()
    app.add_middleware(ThemeMiddleware)
    return TestClient(app)


def test_theme_middleware_excluded_prefix_forces_default_theme(monkeypatch) -> None:
    client = _make_client(monkeypatch)

    # Even if cookie is set, excluded paths should force default
    client.cookies.set("theme", "apothecary")

    response = client.get("/static/echo-theme")

    assert response.status_code == 200
    assert response.json() == {"theme": "prehistoric"}


def test_theme_middleware_non_excluded_uses_cookie_theme(monkeypatch) -> None:
    client = _make_client(monkeypatch)

    client.cookies.set("theme", "apothecary")
    response = client.get("/echo-theme")

    assert response.status_code == 200
    assert response.json() == {"theme": "apothecary"}


def test_theme_middleware_non_excluded_no_cookie_falls_back_to_default(
    monkeypatch,
) -> None:
    client = _make_client(monkeypatch)

    response = client.get("/echo-theme")

    assert response.status_code == 200
    assert response.json() == {"theme": "prehistoric"}
