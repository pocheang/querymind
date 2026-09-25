"""The uvicorn worker gunicorn runs in the backend image (ARC-01 phase 9).

One change from `uvicorn_worker.UvicornWorker`: which peers may set the client
address. gunicorn validates `forwarded_allow_ips` as single IP addresses, but
the peer to trust is the frontend nginx, whose address is whatever Docker hands
out inside the compose network's subnet -- so the setting has to be a network.
uvicorn accepts networks, and this worker hands it `QUERYMIND_TRUSTED_PROXIES`
after gunicorn's own check (see app/api/transport/client_address.py, and why
the variable is not called FORWARDED_ALLOW_IPS).

Imported by gunicorn only, on Linux: `uvicorn_worker` needs `fcntl`.
"""

from __future__ import annotations

from uvicorn_worker import UvicornWorker

from app.api.transport.client_address import trusted_proxies


class QueryMindWorker(UvicornWorker):
    CONFIG_KWARGS = {**UvicornWorker.CONFIG_KWARGS, "forwarded_allow_ips": trusted_proxies(), "proxy_headers": True}
