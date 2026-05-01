from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST_DIR = REPOSITORY_ROOT / "frontend" / "dist"
SPA_ROUTES = ("/", "/login", "/app")


def mount_frontend(app: FastAPI) -> None:
    """Serve the Vite production build when it is available."""
    dist_dir = FRONTEND_DIST_DIR
    index_html = dist_dir / "index.html"
    assets_dir = dist_dir / "assets"

    if dist_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir, check_dir=False), name="frontend-assets")

    async def serve_index() -> Response:
        if index_html.is_file():
            return FileResponse(index_html, media_type="text/html")
        return PlainTextResponse(
            "Frontend build not found. Run `cd frontend && npm install && npm run build`.",
            status_code=404,
        )

    for route in SPA_ROUTES:
        app.get(route, include_in_schema=False)(serve_index)
