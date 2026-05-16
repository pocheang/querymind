"""API routes for agent flow visualization."""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from typing import Optional
import logging
from app.services.agent_flow_tracker import get_tracker
from app.models.agent_flow import AgentFlowData, AgentFlowSummary, AgentFlowUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent-flow", tags=["agent-flow"])


@router.get("/{session_id}", response_model=AgentFlowData)
async def get_agent_flow(session_id: str):
    """Get agent flow data for a session.

    Args:
        session_id: Session identifier

    Returns:
        AgentFlowData

    Raises:
        HTTPException: If flow not found
    """
    tracker = get_tracker()
    flow = tracker.get_flow(session_id)

    if not flow:
        raise HTTPException(status_code=404, detail=f"Flow not found for session {session_id}")

    return flow


@router.get("/{session_id}/summary", response_model=AgentFlowSummary)
async def get_agent_flow_summary(session_id: str):
    """Get summary statistics for an agent flow.

    Args:
        session_id: Session identifier

    Returns:
        AgentFlowSummary

    Raises:
        HTTPException: If flow not found
    """
    tracker = get_tracker()
    summary = tracker.get_summary(session_id)

    if not summary:
        raise HTTPException(status_code=404, detail=f"Flow not found for session {session_id}")

    return summary


@router.delete("/{session_id}")
async def clear_agent_flow(session_id: str):
    """Clear agent flow data for a session.

    Args:
        session_id: Session identifier

    Returns:
        Success message
    """
    tracker = get_tracker()
    tracker.clear_flow(session_id)

    return {"message": f"Flow cleared for session {session_id}"}


@router.websocket("/ws/{session_id}")
async def agent_flow_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time agent flow updates.

    Args:
        websocket: WebSocket connection
        session_id: Session identifier
    """
    await websocket.accept()
    logger.info(f"WebSocket connected for session {session_id}")

    tracker = get_tracker()

    # Send initial flow data
    flow = tracker.get_flow(session_id)
    if flow:
        await websocket.send_json({
            "type": "flow_init",
            "data": flow.model_dump()
        })

    # Subscribe to updates
    async def send_update(update: AgentFlowUpdate):
        try:
            await websocket.send_json(update.model_dump())
        except Exception as e:
            logger.error(f"Failed to send update via WebSocket: {e}")

    tracker.subscribe(session_id, send_update)

    try:
        # Keep connection alive and listen for client messages
        while True:
            data = await websocket.receive_text()
            # Handle client messages if needed (e.g., ping/pong)
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
    finally:
        tracker.unsubscribe(session_id, send_update)
