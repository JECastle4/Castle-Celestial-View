"""Connection observations and ownership of work outliving an HTTP response."""

import asyncio
import logging
import time

import anyio

from api.metrics import get_metrics

logger = logging.getLogger(__name__)


async def disconnected_before_response(receive) -> bool:
    """Peek without waiting, before response completion can synthesize a disconnect.

    A GET may leave its empty request-body message unread. Never drain an
    unbounded body or compete with a streaming response's receive loop.
    """
    for _ in range(2):
        message = {}
        with anyio.CancelScope() as cancel_scope:
            cancel_scope.cancel()
            message = await receive()
        if message.get("type") == "http.disconnect":
            return True
        if message.get("type") != "http.request" or message.get("more_body", False):
            return False
    return False


class BackgroundRequests:
    """Keep detached tasks alive and observe every eventual exception."""

    def __init__(self):
        self.tasks: set[asyncio.Task] = set()

    def track(
        self, task: asyncio.Task, endpoint: str, started_at: float, reason: str | None = "timeout"
    ) -> None:
        """Track an operation whose response deadline has passed."""
        if task in self.tasks:
            return
        metrics = get_metrics()
        if reason:
            metrics.abandoned_work_in_progress.labels(endpoint=endpoint).inc()
        self.tasks.add(task)

        def completed(finished):
            self.tasks.discard(finished)
            if reason:
                metrics.abandoned_work_in_progress.labels(endpoint=endpoint).dec()
            if finished.cancelled():
                return
            if reason:
                metrics.record_abandoned_work(
                    endpoint, reason, time.perf_counter() - started_at
                )
            exception = finished.exception()
            if exception is not None:
                logger.error(
                    "Background request failed on %s",
                    endpoint,
                    exc_info=(type(exception), exception, exception.__traceback__),
                )

        task.add_done_callback(completed)

    async def shutdown(self) -> None:
        """Allow five seconds for completion; cancellation cannot stop running threads."""
        if not self.tasks:
            return
        _, pending = await asyncio.wait(self.tasks, timeout=5.0)
        if pending:
            logger.warning(
                "Shutting down with %d unfinished background requests; "
                "running worker threads cannot be interrupted", len(pending)
            )
            for task in pending:
                task.cancel()
