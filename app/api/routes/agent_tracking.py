import asyncio
import json
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.agent_execution_tracker import (
    AgentExecutionTracker,
    ExecutionTrace,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent-tracking", tags=["agent-tracking"])


class ExecutionStatus(BaseModel):
    execution_id: str
    status: str
    query: str
    step_count: int
    start_time: str
    end_time: Optional[str] = None
    total_duration_ms: Optional[float] = None


@router.get("/stream/{execution_id}")
async def stream_execution(execution_id: str):
    """
    Server-Sent Events (SSE) endpoint for real-time execution tracking.

    Streams agent steps as they complete during execution.
    """
    tracker = AgentExecutionTracker.get_instance()

    async def event_generator():
        last_step_count = 0
        heartbeat_counter = 0
        max_iterations = 600
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            trace = tracker.get_execution_trace(execution_id)

            if not trace:
                yield f"event: error\ndata: {json.dumps({'error': 'Execution not found'})}\n\n"
                break

            if len(trace.steps) > last_step_count:
                for step in trace.steps[last_step_count:]:
                    step_data = step.model_dump(mode='json')
                    yield f"event: agent_step\ndata: {json.dumps(step_data)}\n\n"
                last_step_count = len(trace.steps)

            if trace.status in ['completed', 'failed']:
                trace_data = trace.model_dump(mode='json')
                yield f"event: execution_complete\ndata: {json.dumps(trace_data)}\n\n"
                break

            heartbeat_counter += 1
            if heartbeat_counter >= 30:
                yield f"event: heartbeat\ndata: {json.dumps({'timestamp': trace.start_time.isoformat()})}\n\n"
                heartbeat_counter = 0

            await asyncio.sleep(0.5)

        if iteration >= max_iterations:
            yield f"event: timeout\ndata: {json.dumps({'message': 'Stream timeout'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/trace/{execution_id}", response_model=ExecutionTrace)
async def get_execution_trace(execution_id: str):
    """
    Get the complete execution trace for a given execution ID.
    """
    tracker = AgentExecutionTracker.get_instance()
    trace = tracker.get_execution_trace(execution_id)

    if not trace:
        raise HTTPException(status_code=404, detail="Execution not found")

    return trace


@router.get("/history", response_model=List[ExecutionTrace])
async def get_execution_history(limit: int = 20):
    """
    Get recent execution traces.
    """
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")

    tracker = AgentExecutionTracker.get_instance()
    return tracker.get_recent_executions(limit=limit)


@router.get("/status/{execution_id}", response_model=ExecutionStatus)
async def get_execution_status(execution_id: str):
    """
    Get the current status of an execution.
    """
    tracker = AgentExecutionTracker.get_instance()
    trace = tracker.get_execution_trace(execution_id)

    if not trace:
        raise HTTPException(status_code=404, detail="Execution not found")

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
async def delete_execution_trace(execution_id: str):
    """
    Delete a specific execution trace.
    """
    tracker = AgentExecutionTracker.get_instance()
    trace = tracker.get_execution_trace(execution_id)

    if not trace:
        raise HTTPException(status_code=404, detail="Execution not found")

    with tracker._traces_lock:
        del tracker._traces[execution_id]

    return {"message": "Execution trace deleted", "execution_id": execution_id}


@router.post("/cleanup")
async def cleanup_old_traces():
    """
    Manually trigger cleanup of old execution traces.
    """
    tracker = AgentExecutionTracker.get_instance()
    removed_count = tracker.cleanup_old_traces()

    return {
        "message": f"Cleaned up {removed_count} old execution traces",
        "removed_count": removed_count
    }
