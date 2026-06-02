import asyncio
import logging
import threading
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


def utcnow():
    return datetime.now(timezone.utc)


class AgentStep(BaseModel):
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
    )

    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str
    start_time: datetime = Field(default_factory=utcnow)
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = None
    decision_rationale: Optional[str] = None
    status: str = "running"
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExecutionTrace(BaseModel):
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
    )

    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query: str
    steps: List[AgentStep] = Field(default_factory=list)
    status: str = "running"
    start_time: datetime = Field(default_factory=utcnow)
    end_time: Optional[datetime] = None
    total_duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentExecutionTracker:
    _instance: Optional["AgentExecutionTracker"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._traces: Dict[str, ExecutionTrace] = {}
        self._traces_lock = threading.RLock()  # Use RLock for reentrant locking
        self._trace_locks: Dict[str, threading.RLock] = defaultdict(threading.RLock)  # Per-trace fine-grained locks
        self._ttl_hours = 1
        self._cleanup_task: Optional[asyncio.Task] = None

    @classmethod
    def get_instance(cls) -> "AgentExecutionTracker":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def start_execution(self, query: str, execution_id: Optional[str] = None) -> str:
        if execution_id is None:
            execution_id = str(uuid.uuid4())

        trace = ExecutionTrace(
            execution_id=execution_id,
            query=query,
            status="running",
        )

        with self._traces_lock:
            self._traces[execution_id] = trace

        logger.info(f"Started execution trace: {execution_id}")
        return execution_id

    def record_agent_step(
        self,
        execution_id: str,
        agent_name: str,
        input_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        step = AgentStep(
            agent_name=agent_name,
            input_data=input_data or {},
            status="running",
        )

        with self._traces_lock:
            if execution_id not in self._traces:
                logger.warning(f"Execution {execution_id} not found, creating new trace")
                self._traces[execution_id] = ExecutionTrace(
                    execution_id=execution_id,
                    query="Unknown",
                )

            self._traces[execution_id].steps.append(step)

        logger.debug(f"Recorded agent step: {agent_name} in {execution_id}")
        return step.step_id

    def complete_agent_step(
        self,
        execution_id: str,
        step_id: str,
        output_data: Optional[Dict[str, Any]] = None,
        decision_rationale: Optional[str] = None,
    ) -> None:
        with self._traces_lock:
            if execution_id not in self._traces:
                logger.warning(f"Execution {execution_id} not found")
                return

            trace = self._traces[execution_id]
            for step in trace.steps:
                if step.step_id == step_id:
                    step.end_time = utcnow()
                    step.duration_ms = (
                        (step.end_time - step.start_time).total_seconds() * 1000
                    )
                    step.output_data = output_data
                    step.decision_rationale = decision_rationale
                    step.status = "completed"
                    logger.debug(f"Completed agent step: {step.agent_name} in {execution_id}")
                    return

            logger.warning(f"Step {step_id} not found in execution {execution_id}")

    def fail_agent_step(
        self,
        execution_id: str,
        step_id: str,
        error: str,
    ) -> None:
        with self._traces_lock:
            if execution_id not in self._traces:
                logger.warning(f"Execution {execution_id} not found")
                return

            trace = self._traces[execution_id]
            for step in trace.steps:
                if step.step_id == step_id:
                    step.end_time = utcnow()
                    step.duration_ms = (
                        (step.end_time - step.start_time).total_seconds() * 1000
                    )
                    step.status = "failed"
                    step.error = error
                    logger.debug(f"Failed agent step: {step.agent_name} in {execution_id}")
                    return

            logger.warning(f"Step {step_id} not found in execution {execution_id}")

    def complete_execution(self, execution_id: str) -> None:
        with self._traces_lock:
            if execution_id not in self._traces:
                logger.warning(f"Execution {execution_id} not found")
                return

            trace = self._traces[execution_id]
            trace.end_time = utcnow()
            trace.total_duration_ms = (
                (trace.end_time - trace.start_time).total_seconds() * 1000
            )
            trace.status = "completed"
            logger.info(f"Completed execution trace: {execution_id}")

    def fail_execution(self, execution_id: str, error: str) -> None:
        with self._traces_lock:
            if execution_id not in self._traces:
                logger.warning(f"Execution {execution_id} not found")
                return

            trace = self._traces[execution_id]
            trace.end_time = utcnow()
            trace.total_duration_ms = (
                (trace.end_time - trace.start_time).total_seconds() * 1000
            )
            trace.status = "failed"
            trace.metadata["error"] = error
            logger.info(f"Failed execution trace: {execution_id}")

    def get_execution_trace(self, execution_id: str) -> Optional[ExecutionTrace]:
        with self._traces_lock:
            return self._traces.get(execution_id)

    def get_recent_executions(self, limit: int = 20) -> List[ExecutionTrace]:
        with self._traces_lock:
            traces = list(self._traces.values())
            traces.sort(key=lambda t: t.start_time, reverse=True)
            return traces[:limit]

    def cleanup_old_traces(self) -> int:
        cutoff_time = utcnow() - timedelta(hours=self._ttl_hours)
        removed_count = 0

        with self._traces_lock:
            execution_ids_to_remove = [
                execution_id
                for execution_id, trace in self._traces.items()
                if trace.start_time < cutoff_time
            ]

            for execution_id in execution_ids_to_remove:
                del self._traces[execution_id]
                removed_count += 1

        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old execution traces")

        return removed_count

    def clear_all_traces(self) -> None:
        with self._traces_lock:
            self._traces.clear()
            # Also clear per-trace locks to prevent memory leak
            self._trace_locks.clear()
        logger.info("Cleared all execution traces")

    async def start_periodic_cleanup(self, interval_seconds: int = 300) -> None:
        """
        Start background cleanup task that periodically removes old traces.

        Args:
            interval_seconds: Cleanup interval in seconds (default: 300 = 5 minutes)
        """
        if self._cleanup_task is not None and not self._cleanup_task.done():
            logger.warning("Cleanup task already running")
            return

        self._cleanup_task = asyncio.create_task(self._cleanup_loop(interval_seconds))
        logger.info(f"Started execution tracker cleanup (interval={interval_seconds}s, ttl={self._ttl_hours}h)")

    async def _cleanup_loop(self, interval_seconds: int) -> None:
        """Background task that periodically cleans old traces."""
        while True:
            try:
                await asyncio.sleep(interval_seconds)
                removed = self.cleanup_old_traces()
                if removed > 0:
                    logger.info(f"Periodic cleanup removed {removed} old execution traces")

                # Also clean up orphaned per-trace locks
                with self._traces_lock:
                    active_ids = set(self._traces.keys())
                    lock_ids = set(self._trace_locks.keys())
                    orphaned = lock_ids - active_ids
                    for orphan_id in orphaned:
                        del self._trace_locks[orphan_id]
                    if orphaned:
                        logger.debug(f"Cleaned up {len(orphaned)} orphaned trace locks")

            except asyncio.CancelledError:
                logger.info("Cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}", exc_info=True)

    async def stop_periodic_cleanup(self) -> None:
        """Stop background cleanup task."""
        if self._cleanup_task is not None and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        self._cleanup_task = None
        logger.info("Stopped execution tracker cleanup")


def track_agent_execution(agent_name: str) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracker = AgentExecutionTracker.get_instance()
            execution_id = kwargs.get("execution_id")

            if not execution_id:
                logger.warning(f"No execution_id provided for {agent_name}, skipping tracking")
                return await func(*args, **kwargs)

            input_data = {
                k: v for k, v in kwargs.items()
                if k != "execution_id" and not k.startswith("_")
            }

            step_id = tracker.record_agent_step(
                execution_id=execution_id,
                agent_name=agent_name,
                input_data=input_data,
            )

            try:
                result = await func(*args, **kwargs)

                output_data = {}
                decision = None

                if isinstance(result, dict):
                    output_data = {k: v for k, v in result.items() if k != "execution_id"}
                    decision = result.get("decision_rationale")
                elif isinstance(result, str):
                    output_data = {"result": result}
                else:
                    output_data = {"result": str(result)}

                tracker.complete_agent_step(
                    execution_id=execution_id,
                    step_id=step_id,
                    output_data=output_data,
                    decision_rationale=decision,
                )

                return result

            except Exception as e:
                tracker.fail_agent_step(
                    execution_id=execution_id,
                    step_id=step_id,
                    error=str(e),
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracker = AgentExecutionTracker.get_instance()
            execution_id = kwargs.get("execution_id")

            if not execution_id:
                logger.warning(f"No execution_id provided for {agent_name}, skipping tracking")
                return func(*args, **kwargs)

            input_data = {
                k: v for k, v in kwargs.items()
                if k != "execution_id" and not k.startswith("_")
            }

            step_id = tracker.record_agent_step(
                execution_id=execution_id,
                agent_name=agent_name,
                input_data=input_data,
            )

            try:
                result = func(*args, **kwargs)

                output_data = {}
                decision = None

                if isinstance(result, dict):
                    output_data = {k: v for k, v in result.items() if k != "execution_id"}
                    decision = result.get("decision_rationale")
                elif isinstance(result, str):
                    output_data = {"result": result}
                else:
                    output_data = {"result": str(result)}

                tracker.complete_agent_step(
                    execution_id=execution_id,
                    step_id=step_id,
                    output_data=output_data,
                    decision_rationale=decision,
                )

                return result

            except Exception as e:
                tracker.fail_agent_step(
                    execution_id=execution_id,
                    step_id=step_id,
                    error=str(e),
                )
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def get_tracker() -> AgentExecutionTracker:
    """Get the singleton instance of AgentExecutionTracker."""
    return AgentExecutionTracker.get_instance()
