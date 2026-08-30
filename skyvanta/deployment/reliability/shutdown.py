"""Graceful shutdown coordinator, resource draining, and idempotent termination handling."""

import asyncio
import inspect
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from skyvanta.deployment.observability.events import EventType, event_logger

logger = logging.getLogger("skyvanta.reliability.shutdown")


class ShutdownResult(BaseModel):
    """Result model containing shutdown execution diagnostics."""

    success: bool = Field(
        description="Whether shutdown completed cleanly within the timeout.",
    )
    tasks_cancelled: int = Field(
        default=0,
        description="Number of active asynchronous tasks terminated.",
    )
    handlers_executed: int = Field(
        default=0,
        description="Number of registered cleanup handlers executed.",
    )
    duration_ms: float = Field(
        default=0.0,
        description="Total duration in milliseconds for shutdown sequence.",
    )
    errors: List[str] = Field(
        default_factory=list,
        description="List of exceptions encountered during shutdown handler execution.",
    )


class ShutdownCoordinator:
    """Coordinates idempotent, graceful termination of active simulation and WebSocket tasks."""

    def __init__(self, default_timeout_sec: float = 10.0):
        self._default_timeout_sec = default_timeout_sec
        self._is_shutting_down = False
        self._is_shutdown_complete = False
        self._last_result: Optional[ShutdownResult] = None
        self._tracked_tasks: Set[asyncio.Task] = set()
        self._cleanup_handlers: List[Callable[[], Any]] = []

    @property
    def is_shutting_down(self) -> bool:
        """Indicates whether a shutdown sequence is currently in progress or complete."""
        return self._is_shutting_down

    @property
    def is_shutdown_complete(self) -> bool:
        """Indicates whether shutdown sequence has completed."""
        return self._is_shutdown_complete

    def register_task(self, task: asyncio.Task) -> None:
        """Registers a background asyncio task to be cleanly cancelled during shutdown."""
        if not task.done():
            self._tracked_tasks.add(task)
            task.add_done_callback(lambda t: self._tracked_tasks.discard(t))

    def register_handler(self, handler: Callable[[], Any]) -> None:
        """Registers a synchronous or asynchronous cleanup callable."""
        if handler not in self._cleanup_handlers:
            self._cleanup_handlers.append(handler)

    async def initiate_shutdown(
        self,
        timeout_sec: Optional[float] = None,
        environment: str = "production",
    ) -> ShutdownResult:
        """Executes the graceful shutdown workflow.

        Steps:
        1. Set shutting_down flag to reject new incoming traffic.
        2. Execute registered cleanup handlers (e.g. flushing telemetry, closing connections).
        3. Cancel and await any tracked asynchronous simulation or WebSocket tasks.
        4. Flush structured event logger.
        5. Mark complete and return metrics.

        Idempotency:
        - If shutdown has already completed, returns the cached result without repeating.
        """
        if self._is_shutdown_complete and self._last_result is not None:
            logger.debug("Shutdown already completed; returning cached result.")
            return self._last_result

        start_time = time.perf_counter()
        timeout = timeout_sec if timeout_sec is not None else self._default_timeout_sec
        self._is_shutting_down = True
        errors: List[str] = []
        handlers_count = 0
        tasks_cancelled_count = 0

        logger.info("Initiating graceful shutdown sequence (Timeout: %.1fs)...", timeout)

        # 1. Emit structured shutdown event
        try:
            event_logger.emit(
                event_type=EventType.SERVICE_SHUTDOWN,
                message="Graceful shutdown sequence initiated",
                severity="INFO",
                details={"timeout_sec": timeout},
                environment=environment,
            )
        except Exception as e:
            errors.append(f"Event logger shutdown notification failed: {e}")

        # 2. Run registered cleanup handlers
        for handler in self._cleanup_handlers:
            try:
                if inspect.iscoroutinefunction(handler):
                    await asyncio.wait_for(handler(), timeout=max(1.0, timeout / 2.0))
                else:
                    handler()
                handlers_count += 1
            except Exception as e:
                logger.warning("Error in cleanup handler %s: %s", getattr(handler, "__name__", str(handler)), e)
                errors.append(f"Cleanup handler error: {e}")

        # 3. Cancel tracked background tasks
        active_tasks = [t for t in self._tracked_tasks if not t.done()]
        tasks_cancelled_count = len(active_tasks)

        if active_tasks:
            logger.info("Cancelling %d active background tasks...", len(active_tasks))
            for task in active_tasks:
                task.cancel()

            try:
                await asyncio.wait_for(
                    asyncio.gather(*active_tasks, return_exceptions=True),
                    timeout=max(1.0, timeout / 2.0),
                )
            except asyncio.TimeoutError:
                logger.warning("Timed out waiting for background tasks to cancel.")
                errors.append("Timeout waiting for background tasks cancellation.")
            except Exception as e:
                logger.warning("Exception during task cancellation: %s", e)
                errors.append(f"Task cancellation error: {e}")

        self._tracked_tasks.clear()

        # 4. Flush event logger
        try:
            event_logger.flush()
        except Exception:
            pass

        self._is_shutdown_complete = True
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        success = len(errors) == 0

        result = ShutdownResult(
            success=success,
            tasks_cancelled=tasks_cancelled_count,
            handlers_executed=handlers_count,
            duration_ms=round(elapsed_ms, 2),
            errors=errors,
        )
        self._last_result = result
        logger.info("Graceful shutdown completed in %.2fms (Success: %s).", elapsed_ms, success)
        return result

    def reset(self) -> None:
        """Resets coordinator state (primarily used in testing environments)."""
        self._is_shutting_down = False
        self._is_shutdown_complete = False
        self._last_result = None
        self._tracked_tasks.clear()
        self._cleanup_handlers.clear()


# Global singleton instance
shutdown_coordinator = ShutdownCoordinator()
