"""The client's address, decided in one place (SEC-02, ARC-01 phase 9).

There were two answers. The rate-limit middleware took the first value of
`X-Forwarded-For` -- which nginx *appends* to, so a client's own header stayed
first, and rotating it bypassed every per-IP limit. The auth routes used
`request.client.host`, which behind nginx is nginx: every user shared one
registration bucket and every audit row named the proxy.

Now the server decides once. uvicorn rewrites `request.client` from the
forwarded headers only when the connection comes from a trusted proxy
(`QUERYMIND_TRUSTED_PROXIES`, checked by `trusted_proxies`), nginx overwrites
`X-Forwarded-For` with the address it saw, and the application reads
`request.client.host` and nothing else.
"""

from __future__ import annotations

import ipaddress
import os

from starlette.requests import Request

UNKNOWN = "unknown"
_DEFAULT_TRUSTED = "127.0.0.1"


def client_ip(request: Request) -> str:
    """The address the server attributes this request to; never a header the client sent."""

    if request.client and request.client.host:
        return request.client.host
    return UNKNOWN


def trusted_proxies(raw: str | None = None) -> list[str]:
    """The peers allowed to set X-Forwarded-For, from QUERYMIND_TRUSTED_PROXIES.

    Read from the process environment because the process manager builds its
    workers before any `Settings` exist. Every entry must parse as an address or
    a network: a typo would otherwise trust nobody, silently, and every limit
    would key on nginx's address again.

    Not `FORWARDED_ALLOW_IPS`, although that is uvicorn's name for this: gunicorn
    reads the same variable at import, as the default for its own setting, and
    refuses a network there -- so a subnet under that name stopped every worker
    from booting (found in the phase 9 container run, not by any unit test).
    """

    value = os.environ.get("QUERYMIND_TRUSTED_PROXIES", _DEFAULT_TRUSTED) if raw is None else raw
    entries = [entry.strip() for entry in value.split(",") if entry.strip()]
    for entry in entries:
        if entry != "*":
            ipaddress.ip_network(entry, strict=False)  # ValueError names the bad entry
    return entries or [_DEFAULT_TRUSTED]
