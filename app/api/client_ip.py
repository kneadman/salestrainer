from __future__ import annotations

from ipaddress import ip_address, ip_network

from fastapi import Request


def client_ip_from_request(request: Request, *, trusted_proxy_ips: str | None = None) -> str | None:
    """Return the client IP, trusting forwarded headers only from configured proxies."""
    peer_ip = _direct_peer_ip(request)
    if peer_ip is None:
        return None
    trusted_proxies = _trusted_proxy_ips(request, trusted_proxy_ips)
    if not _is_trusted_proxy(peer_ip, trusted_proxies):
        return peer_ip
    forwarded_ip = _first_forwarded_ip(request.headers.get("x-forwarded-for"))
    if forwarded_ip is not None:
        return forwarded_ip
    real_ip = _valid_ip(request.headers.get("x-real-ip"))
    return real_ip or peer_ip


def _direct_peer_ip(request: Request) -> str | None:
    """Return the immediate peer IP from the ASGI client scope."""
    if request.client is None:
        return None
    return request.client.host


def _trusted_proxy_ips(request: Request, configured: str | None) -> str:
    """Read trusted proxy configuration from the explicit value or app settings."""
    if configured is not None:
        return configured
    settings = getattr(request.app.state, "settings", None)
    return str(getattr(settings, "trusted_proxy_ips", "") or "")


def _is_trusted_proxy(peer_ip: str, trusted_proxy_ips: str) -> bool:
    """Check whether the immediate peer belongs to a trusted proxy IP/network list."""
    try:
        parsed_peer = ip_address(peer_ip.strip())
    except ValueError:
        return False
    for raw_entry in trusted_proxy_ips.split(","):
        entry = raw_entry.strip()
        if not entry:
            continue
        try:
            if parsed_peer in ip_network(entry, strict=False):
                return True
        except ValueError:
            continue
    return False


def _first_forwarded_ip(header_value: str | None) -> str | None:
    """Return the first valid IP from an X-Forwarded-For header."""
    if not header_value:
        return None
    for item in header_value.split(","):
        candidate = _valid_ip(item)
        if candidate is not None:
            return candidate
    return None


def _valid_ip(value: str | None) -> str | None:
    """Normalize a single IP string when it is syntactically valid."""
    if not value:
        return None
    candidate = value.strip()
    try:
        return str(ip_address(candidate))
    except ValueError:
        return None
