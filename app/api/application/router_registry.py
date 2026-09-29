"""Canonical route registration metadata for the FastAPI application.

This module owns only application composition. Route handlers live in the
grouped public/admin/operations/compatibility packages.
"""

from fastapi import FastAPI

from app.api.routes import sessions as sessions_management
from app.api.routes.admin import agent_quality as admin_agent_quality
from app.api.routes.admin import config as admin_config
from app.api.routes.admin import graph_rag as admin_graph_rag
from app.api.routes.admin import language_stats as admin_language_stats
from app.api.routes.admin import ops as admin_ops
from app.api.routes.admin import settings as admin_settings
from app.api.routes.admin import threat_intel as admin_threat_intel
from app.api.routes.admin import users as admin_users
from app.api.routes.admin import web_activity as web_activity_admin
from app.api.routes.operations import agent_health, agent_tracking, analytics, evaluation, health
from app.api.routes.optimization import performance as optimization_performance
from app.api.routes.public import auth, clarification, connectors, documents, memories, orchestration, prompts
from app.api.routes.public import query as advanced_rag
from app.api.routes.public import sessions as public_sessions

API_V1 = "/api/v1"

# Where each router is mounted. Every application endpoint lives under /api/v1;
# the four that do not are infrastructure a load balancer or a browser reaches
# by a fixed name (`/`, `/health`, `/ready`, `/metrics`, all in `health`).
# Routers that already spell out /api/v1/... in their own prefix mount at "".
#
# Order matters in one place: `sessions_management` (tags, facets, search,
# import, /{id}/metadata, /{id}/export) precedes `public_sessions`, whose
# `/{session_id}` would otherwise capture `/tags` and `/facets`.
ROUTER_MOUNTS = (
    (health, ""),
    (auth, API_V1),
    (clarification, ""),
    (connectors, ""),
    (sessions_management, ""),
    (public_sessions, API_V1),
    (memories, ""),
    (documents, API_V1),
    (prompts, API_V1),
    (admin_users, API_V1),
    (admin_ops, API_V1),
    (admin_settings, API_V1),
    (admin_config, API_V1),
    (admin_language_stats, API_V1),
    (admin_agent_quality, ""),
    (agent_tracking, API_V1),
    (agent_health, ""),
    (evaluation, API_V1),
    (advanced_rag, API_V1),
    (analytics, API_V1),
    (admin_graph_rag, API_V1),
    (admin_threat_intel, API_V1),
    (orchestration, ""),
    (web_activity_admin, ""),
    (optimization_performance, API_V1),
)

ROUTER_MODULES = tuple(module for module, _ in ROUTER_MOUNTS)


def register_routers(app: FastAPI) -> None:
    """Register the application's routers, each at its mount point."""
    for route_module, mount in ROUTER_MOUNTS:
        app.include_router(route_module.router, prefix=mount)


__all__ = ["API_V1", "ROUTER_MODULES", "ROUTER_MOUNTS", "register_routers"]
