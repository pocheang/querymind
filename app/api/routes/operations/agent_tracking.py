import logging
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.api.dependencies import _require_permission, _require_user
from app.api.routes.internal.path_params import ExecutionId
from app.api.transport.errors import bad_request, forbidden, not_found
from app.services.observability.agent_execution_tracker import (
    AgentExecutionTracker,
    ExecutionTrace,
)
from app.services.security.rbac import Permission

logger = logging.getLogger(__name__)

# Per-execution trace inspection (steps, status, history), scoped to the owner.
# One stream exists and it is not here: a run's live events are
# `GET /api/v1/orchestration/executions/{id}/events`. A second, 0.5 s polling
# SSE at `/agent-tracking/stream` saw only this worker's traces and had no
# caller; it was removed with the admin-only duplicate `/agents/trace/{id}`.
router = APIRouter(prefix="/agent-tracking", tags=["agent-tracking"])

_EXECUTION_NOT_FOUND = "Execution not found"


def _verify_trace_ownership(trace: ExecutionTrace, user: dict[str, Any]) -> None:
    """
    Verify that the user has permission to access this trace.

    Regular users can only access their own traces.
    Admins can access all traces.

    Raises:
        HTTPException: If user doesn't have permission to access the trace.
    """
    role = str(user.get("role", "viewer")).lower()
    if role == "admin":
        return

    user_id = str(user.get("user_id", ""))
    trace_user_id = str(trace.user_id or "")

    if user_id != trace_user_id:
        raise forbidden("You do not have permission to access this execution trace")


class ExecutionStatus(BaseModel):
    execution_id: str
    status: str
    query: str
    step_count: int
    start_time: str
    end_time: str | None = None
    total_duration_ms: float | None = None


@router.get("/trace/{execution_id}", response_model=ExecutionTrace)
async def get_execution_trace(
    execution_id: ExecutionId, request: Request, user: dict[str, Any] = Depends(_require_user)
):
    """
    Get the complete execution trace for a given execution ID.
    User can only view their own executions unless they are admin.
    """
    _require_permission(user, Permission.QUERY_RUN, request, "agent-tracking")
    tracker = AgentExecutionTracker.get_instance()
    trace = tracker.get_execution_trace(execution_id)

    if not trace:
        raise not_found(_EXECUTION_NOT_FOUND)

    _verify_trace_ownership(trace, user)
    return trace


@router.get("/history", response_model=list[ExecutionTrace])
async def get_execution_history(request: Request, user: dict[str, Any] = Depends(_require_user), limit: int = 20):
    """
    Get recent execution traces.
    Users see only their own executions; admins see all.
    """
    _require_permission(user, Permission.QUERY_RUN, request, "agent-tracking")
    if limit < 1 or limit > 100:
        raise bad_request("Limit must be between 1 and 100")

    tracker = AgentExecutionTracker.get_instance()
    all_traces = tracker.get_recent_executions(limit=limit * 2)  # Get more to filter

    # Filter by user unless admin
    role = str(user.get("role", "viewer")).lower()
    if role != "admin":
        user_id = str(user.get("user_id", ""))
        # Note: This assumes ExecutionTrace has a user_id field.
        # If not, all users will see all traces. Need to verify the model.
        filtered_traces = [t for t in all_traces if getattr(t, "user_id", None) == user_id]
        return filtered_traces[:limit]

    return all_traces[:limit]


@router.get("/status/{execution_id}", response_model=ExecutionStatus)
async def get_execution_status(
    execution_id: ExecutionId, request: Request, user: dict[str, Any] = Depends(_require_user)
):
    """
    Get the current status of an execution.
    User can only view their own executions unless they are admin.
    """
    _require_permission(user, Permission.QUERY_RUN, request, "agent-tracking")
    tracker = AgentExecutionTracker.get_instance()
    trace = tracker.get_execution_trace(execution_id)

    if not trace:
        raise not_found(_EXECUTION_NOT_FOUND)

    _verify_trace_ownership(trace, user)

    return ExecutionStatus(
        execution_id=trace.execution_id,
        status=trace.status,
        query=trace.query,
        step_count=len(trace.steps),
        start_time=trace.start_time.isoformat(),
        end_time=trace.end_time.isoformat() if trace.end_time else None,
        total_duration_ms=trace.total_duration_ms,
    )


@router.delete("/trace/{execution_id}")
async def delete_execution_trace(
    execution_id: ExecutionId, request: Request, user: dict[str, Any] = Depends(_require_user)
):
    """
    Delete a specific execution trace.
    User can only delete their own executions unless they are admin.
    """
    _require_permission(user, Permission.QUERY_RUN, request, "agent-tracking")
    tracker = AgentExecutionTracker.get_instance()
    trace = tracker.get_execution_trace(execution_id)

    if not trace:
        raise not_found(_EXECUTION_NOT_FOUND)

    _verify_trace_ownership(trace, user)

    with tracker._traces_lock:
        del tracker._traces[execution_id]

    return {"message": "Execution trace deleted", "execution_id": execution_id}


@router.post("/cleanup")
async def cleanup_old_traces(request: Request, user: dict[str, Any] = Depends(_require_user)):
    """
    Manually trigger cleanup of old execution traces - Admin only.
    """
    _require_permission(user, Permission.ADMIN_OPS_MANAGE, request, "admin")
    tracker = AgentExecutionTracker.get_instance()
    removed_count = tracker.cleanup_old_traces()

    return {"message": f"Cleaned up {removed_count} old execution traces", "removed_count": removed_count}
