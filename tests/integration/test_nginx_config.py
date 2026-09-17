from __future__ import annotations

from pathlib import Path
import re


def test_nginx_proxies_api_and_auth_to_backend() -> None:
    config = Path("deploy/nginx/default.conf").read_text(encoding="utf-8")

    assert "location /api/" in config
    assert "location /auth/" in config
    assert config.count("proxy_pass http://backend:8000") >= 2
    assert "try_files $uri $uri/ /index.html" in config


def test_nginx_read_timeout_covers_llm_retries() -> None:
    """POST /api/sessions blocks on persona generation, which may retry once.

    With the nginx default of 60s the client gets a 504 while the backend keeps
    running and still creates the session, leaving the client with no id.
    """
    config = Path("deploy/nginx/default.conf").read_text(encoding="utf-8")

    assert "proxy_read_timeout" in config
    timeout = int(re.search(r"proxy_read_timeout\s+(\d+)s", config).group(1))
    assert timeout >= 120


def test_nginx_trusts_compose_subnet_for_real_client_ip() -> None:
    config = Path("deploy/nginx/default.conf").read_text(encoding="utf-8")

    assert "set_real_ip_from 172.28.0.0/16;" in config
    assert "real_ip_header X-Forwarded-For;" in config


def test_nginx_overwrites_forwarded_for_for_api_and_auth() -> None:
    config = Path("deploy/nginx/default.conf").read_text(encoding="utf-8")

    assert "$proxy_add_x_forwarded_for" not in config
    for location in ("api", "auth"):
        block_match = re.search(rf"location /{location}/ \{{(?P<body>.*?)\n    \}}", config, re.DOTALL)
        assert block_match is not None
        block = block_match.group("body")

        assert "proxy_set_header X-Forwarded-For $remote_addr;" in block
        assert "proxy_set_header X-Real-IP $remote_addr;" in block
        assert "proxy_set_header X-Forwarded-Proto $scheme;" in block
