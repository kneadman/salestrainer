from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.infrastructure.config import Settings
from app.infrastructure.llm_client import FakeLLMClient
from app.infrastructure.session_repository import InMemorySessionRepository
from app.web import static


def _create_client() -> TestClient:
    app = create_app(
        settings=Settings(auth_cookie_secure=False),
        repository=InMemorySessionRepository(),
        llm_client=FakeLLMClient(),
    )
    return TestClient(app)


def test_frontend_routes_return_graceful_response_when_dist_missing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(static, "FRONTEND_DIST_DIR", tmp_path / "missing-dist")

    client = _create_client()

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    login = client.get("/login")
    assert login.status_code == 404
    assert "Frontend build not found" in login.text

    app_response = client.get("/app")
    assert app_response.status_code == 404
    assert "Frontend build not found" in app_response.text

    auth_response = client.get("/auth/me")
    assert auth_response.status_code == 401


def test_frontend_routes_serve_vite_build_and_assets(monkeypatch, tmp_path: Path) -> None:
    dist_dir = tmp_path / "dist"
    assets_dir = dist_dir / "assets"
    assets_dir.mkdir(parents=True)
    (dist_dir / "index.html").write_text(
        '<!doctype html><html><head><script type="module" src="/assets/app.js"></script></head><body></body></html>',
        encoding="utf-8",
    )
    (assets_dir / "app.js").write_text("console.log('sales trainer');", encoding="utf-8")
    monkeypatch.setattr(static, "FRONTEND_DIST_DIR", dist_dir)

    client = _create_client()

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    for path in ("/", "/login", "/app"):
        response = client.get(path)
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "/assets/app.js" in response.text

    asset = client.get("/assets/app.js")
    assert asset.status_code == 200
    assert "sales trainer" in asset.text
