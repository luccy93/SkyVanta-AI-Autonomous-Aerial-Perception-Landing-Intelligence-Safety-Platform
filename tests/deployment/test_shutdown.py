"""Unit tests for ShutdownCoordinator and graceful lifecycle termination."""

import asyncio
import pytest

from skyvanta.deployment.reliability.shutdown import (
    ShutdownCoordinator,
    ShutdownResult,
)


@pytest.mark.asyncio
async def test_shutdown_coordinator_nominal():
    """Verifies that ShutdownCoordinator executes cleanup handlers and cancels tasks."""
    coordinator = ShutdownCoordinator(default_timeout_sec=5.0)

    handler_called = False
    async_handler_called = False

    def sync_cleanup():
        nonlocal handler_called
        handler_called = True

    async def async_cleanup():
        nonlocal async_handler_called
        async_handler_called = True

    coordinator.register_handler(sync_cleanup)
    coordinator.register_handler(async_cleanup)

    # Register background task
    async def background_worker():
        while True:
            await asyncio.sleep(0.1)

    task = asyncio.create_task(background_worker())
    coordinator.register_task(task)

    assert not task.done()
    assert not coordinator.is_shutting_down

    result = await coordinator.initiate_shutdown(timeout_sec=2.0)

    assert result.success is True
    assert result.handlers_executed == 2
    assert result.tasks_cancelled == 1
    assert handler_called is True
    assert async_handler_called is True
    assert task.done()
    assert coordinator.is_shutting_down is True
    assert coordinator.is_shutdown_complete is True


@pytest.mark.asyncio
async def test_shutdown_coordinator_idempotency():
    """Verifies that calling initiate_shutdown multiple times is safe and returns cached result."""
    coordinator = ShutdownCoordinator()
    call_count = 0

    def cleanup():
        nonlocal call_count
        call_count += 1

    coordinator.register_handler(cleanup)

    res1 = await coordinator.initiate_shutdown(timeout_sec=1.0)
    assert res1.success is True
    assert call_count == 1

    # Second call must be idempotent
    res2 = await coordinator.initiate_shutdown(timeout_sec=1.0)
    assert res2.success is True
    assert call_count == 1  # Handler not re-executed


@pytest.mark.asyncio
async def test_shutdown_coordinator_handler_exception_resilience():
    """Verifies that exceptions in cleanup handlers are captured without crashing shutdown."""
    coordinator = ShutdownCoordinator()

    def faulty_handler():
        raise RuntimeError("Simulated resource release failure")

    coordinator.register_handler(faulty_handler)

    result = await coordinator.initiate_shutdown(timeout_sec=1.0)
    assert result.success is False
    assert len(result.errors) == 1
    assert "Simulated resource release failure" in result.errors[0]
    assert coordinator.is_shutdown_complete is True
