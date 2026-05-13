from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI, Request

from app.api.client_ip import client_ip_from_request


def _request(
    *,
    peer_ip: str,
    trusted_proxy_ips: str = "",
    headers: dict[str, str] | None = None,
) -> Request:
    """Build a minimal request with app settings for IP extraction tests."""
    app = FastAPI()
    app.state.settings = SimpleNamespace(trusted_proxy_ips=trusted_proxy_ips)
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "scheme": "http",
            "headers": [(key.lower().encode(), value.encode()) for key, value in (headers or {}).items()],
            "client": (peer_ip, 12345),
            "server": ("testserver", 80),
            "app": app,
        }
    )


def test_client_ip_uses_direct_peer_without_forwarded_headers() -> None:
    request = _request(peer_ip="203.0.113.10")

    assert client_ip_from_request(request) == "203.0.113.10"


def test_client_ip_uses_forwarded_for_only_from_trusted_proxy() -> None:
    request = _request(
        peer_ip="10.0.0.5",
        trusted_proxy_ips="10.0.0.0/8",
        headers={"X-Forwarded-For": "198.51.100.7, 10.0.0.5"},
    )

    assert client_ip_from_request(request) == "198.51.100.7"


def test_client_ip_ignores_spoofed_forwarded_headers_from_untrusted_peer() -> None:
    request = _request(
        peer_ip="203.0.113.10",
        trusted_proxy_ips="10.0.0.0/8",
        headers={"X-Forwarded-For": "198.51.100.7", "X-Real-IP": "198.51.100.8"},
    )

    assert client_ip_from_request(request) == "203.0.113.10"


def test_client_ip_uses_real_ip_from_trusted_proxy_when_forwarded_for_is_invalid() -> None:
    request = _request(
        peer_ip="10.0.0.5",
        trusted_proxy_ips="10.0.0.0/8",
        headers={"X-Forwarded-For": "not-an-ip", "X-Real-IP": "198.51.100.8"},
    )

    assert client_ip_from_request(request) == "198.51.100.8"
