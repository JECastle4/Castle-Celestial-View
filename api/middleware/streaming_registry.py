"""Registry for streaming response metadata without polluting response object.

This module provides a WeakKeyDictionary-based registry to track metadata
for StreamingResponse objects without directly attaching attributes to the
response, which violates encapsulation (protected-access pattern).

By using a registry, we:
1. Keep response object clean (no _metrics_* attributes)
2. Avoid protected-access violations
3. Enable automatic cleanup via weak references when response is GC'd
4. Maintain clear separation of concerns (metrics tracking separate from response)

Usage:
    from api.middleware.streaming_registry import streaming_registry, StreamingMetadata

    # Store metadata
    metadata = StreamingMetadata(
        endpoint="/api/v1/events",
        method="GET",
        status_code=200,
        deferred=True,
        pre_route_endpoint="/api/v1/{route}",
        start_time=time.perf_counter()
    )
    streaming_registry.set(response, metadata)

    # Retrieve metadata
    metadata = streaming_registry.get(response)
    if metadata:
        duration = time.perf_counter() - metadata.start_time
        metrics.record_request(metadata.endpoint, metadata.method, metadata.status_code, duration)
"""

from __future__ import annotations

import time
import weakref
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class StreamingMetadata:
    """Metadata for streaming responses requiring deferred metrics recording."""

    endpoint: str
    """Matched route label (e.g., /api/v1/{route})"""

    method: str
    """HTTP method (GET, POST, etc.)"""

    status_code: int
    """HTTP status code"""

    deferred: bool
    """Whether metrics should be recorded after iteration completes"""

    pre_route_endpoint: str
    """Pre-route label for in-progress tracking"""

    start_time: float
    """Time when request started (perf_counter)"""


class StreamingRegistry:
    """WeakKeyDictionary-based registry for streaming response metadata.

    Uses weak references to automatically clean up metadata when responses
    are garbage collected, preventing memory leaks in long-running servers.
    """

    def __init__(self) -> None:
        """Initialize the streaming registry with empty weak key dictionary."""
        # WeakKeyDictionary automatically removes entries when keys are garbage collected
        # This prevents memory leaks from accumulating metadata for responses
        self._metadata: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()

    def set(self, response: object, metadata: StreamingMetadata) -> None:
        """Store metadata for a streaming response.

        Args:
            response: The response object to associate with metadata
            metadata: Metadata to store (endpoint, method, status, start_time, etc.)
        """
        self._metadata[response] = metadata

    def get(self, response: object) -> Optional[StreamingMetadata]:
        """Retrieve metadata for a streaming response.

        Args:
            response: The response object to look up

        Returns:
            StreamingMetadata if found, None if response not in registry or GC'd
        """
        return self._metadata.get(response)

    def clear(self, response: object) -> None:
        """Manually remove metadata for a response.

        Useful for cleanup, though WeakKeyDictionary will auto-cleanup on GC.

        Args:
            response: The response object to remove metadata for
        """
        self._metadata.pop(response, None)

    def __len__(self) -> int:
        """Return number of entries currently in registry."""
        return len(self._metadata)


# Global singleton registry instance
streaming_registry = StreamingRegistry()
