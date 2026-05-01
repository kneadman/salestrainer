from __future__ import annotations

from pathlib import Path


def test_nginx_proxies_api_and_auth_to_backend() -> None:
    config = Path("deploy/nginx/default.conf").read_text(encoding="utf-8")

    assert "location /api/" in config
    assert "location /auth/" in config
    assert config.count("proxy_pass http://backend:8000") >= 2
    assert "try_files $uri $uri/ /index.html" in config
