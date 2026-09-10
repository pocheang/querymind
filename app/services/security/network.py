from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from app.core.config import get_settings
from app.domain.text import normalize_string

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address


class OutboundURLValidationError(ValueError):
    """Raised when user-provided outbound base_url is unsafe."""


def _csv_hosts(raw: str) -> list[str]:
    return [x.strip().lower() for x in str(raw or "").split(",") if x.strip()]


def _host_allowlisted(host: str, allowlist: list[str]) -> bool:
    host_lc = normalize_string(host, lowercase=True)
    if not host_lc or not allowlist:
        return False
    for item in allowlist:
        if host_lc == item or host_lc.endswith(f".{item}"):
            return True
    return False


def _parse_ip_literal(host: str) -> IPAddress | None:
    text = str(host or "").strip()
    if not text:
        return None
    # Strip IPv6 zone id if present (e.g. fe80::1%lo0).
    text = text.split("%", 1)[0]
    try:
        return ipaddress.ip_address(text)
    except ValueError:
        return None


def _url_origin(url: str) -> tuple[str, str, int] | None:
    parsed = urlparse(str(url or "").strip())
    scheme = str(parsed.scheme or "").lower()
    host = normalize_string(parsed.hostname, lowercase=True)
    if scheme not in {"http", "https"} or not host:
        return None
    try:
        port = int(parsed.port or (443 if scheme == "https" else 80))
    except ValueError:
        return None
    return scheme, host, port


def _is_blocked_ip(addr: IPAddress) -> bool:
    return bool(
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


def _resolve_host_ips(host: str, port: int, *, enabled: bool) -> list[IPAddress]:
    if not enabled:
        return []
    try:
        rows = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError:
        return []
    resolved: list[ipaddress._BaseAddress] = []
    for row in rows:
        sockaddr = row[4]
        if not sockaddr:
            continue
        ip_text = str(sockaddr[0] or "").strip()
        if not ip_text:
            continue
        parsed = _parse_ip_literal(ip_text)
        if parsed is not None:
            resolved.append(parsed)
    return resolved


def validate_public_http_url(url: str) -> str:
    """Reject outbound HTTP targets that resolve outside the public Internet."""
    normalized = str(url or "").strip()
    parsed = urlparse(normalized)
    scheme = str(parsed.scheme or "").lower()
    if scheme not in {"http", "https"}:
        raise OutboundURLValidationError("outbound URL must use http or https")
    host = normalize_string(parsed.hostname, lowercase=True)
    if not host:
        raise OutboundURLValidationError("outbound URL host is required")
    if host in {"localhost", "localhost.localdomain"}:
        raise OutboundURLValidationError("outbound URL host is blocked by network boundary policy")

    literal_ip = _parse_ip_literal(host)
    if literal_ip is not None and _is_blocked_ip(literal_ip):
        raise OutboundURLValidationError("outbound URL resolves to a blocked address")

    port = int(parsed.port or (443 if scheme == "https" else 80))
    resolved_ips = _resolve_host_ips(host, port, enabled=True)
    if any(_is_blocked_ip(address) for address in resolved_ips):
        raise OutboundURLValidationError("outbound URL DNS resolution includes a blocked address")
    return normalized


def _apply_provider_path_convention(provider_lc: str, path: str, normalized: str) -> str:
    """Anthropic's client appends `/v1` itself; the OpenAI-shaped providers expect
    it already present in `base_url`."""
    if provider_lc == "anthropic" and path == "/v1":
        return normalized[: -len("/v1")]
    if provider_lc in {"openai", "deepseek", "custom"} and path in {"", "/"}:
        return f"{normalized}/v1"
    return normalized


def _already_permitted(provider_lc: str, normalized: str, host: str, settings) -> bool:
    """True when `base_url` may bypass the private/loopback boundary checks below:
    an operator-configured allowlist, the same origin as the deployment's own
    Ollama endpoint, or the blanket `api_base_url_allow_private` escape hatch."""
    allowlist = _csv_hosts(str(getattr(settings, "api_base_url_allowlist", "") or ""))
    if _host_allowlisted(host, allowlist):
        return True
    if provider_lc == "ollama":
        configured_origin = _url_origin(str(getattr(settings, "ollama_base_url", "") or ""))
        if configured_origin is not None and _url_origin(normalized) == configured_origin:
            return True
    return bool(getattr(settings, "api_base_url_allow_private", False))


def _enforce_network_boundary(host: str, parsed, scheme: str, settings) -> None:
    """Raise unless `host` is outside the private/loopback/link-local ranges,
    checking the literal address first and then, if DNS checking is on, every
    address the host resolves to."""
    if host in {"localhost", "localhost.localdomain"}:
        raise OutboundURLValidationError("base_url host is blocked by network boundary policy")

    literal_ip = _parse_ip_literal(host)
    if literal_ip is not None and _is_blocked_ip(literal_ip):
        raise OutboundURLValidationError("base_url resolves to blocked private/loopback/link-local address")

    port = int(parsed.port or (443 if scheme == "https" else 80))
    dns_check = bool(getattr(settings, "api_base_url_dns_check", True))
    resolved_ips = _resolve_host_ips(host, port, enabled=dns_check)
    if any(_is_blocked_ip(x) for x in resolved_ips):
        raise OutboundURLValidationError(
            "base_url DNS resolution includes a blocked private/loopback/link-local address"
        )


def validate_api_base_url_for_provider(base_url: str, *, provider: str) -> str:
    settings = get_settings()
    normalized = str(base_url or "").strip().rstrip("/")
    parsed = urlparse(normalized)
    scheme = str(parsed.scheme or "").lower()
    if scheme not in {"http", "https"}:
        raise OutboundURLValidationError("base_url must use http or https")
    host = normalize_string(parsed.hostname, lowercase=True)
    if not host:
        raise OutboundURLValidationError("base_url host is required")

    provider_lc = normalize_string(provider, lowercase=True)
    path = str(parsed.path or "").rstrip("/")
    normalized = _apply_provider_path_convention(provider_lc, path, normalized)

    if _already_permitted(provider_lc, normalized, host, settings):
        return normalized

    _enforce_network_boundary(host, parsed, scheme, settings)
    return normalized
