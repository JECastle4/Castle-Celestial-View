"""
Limiter protocol and factory for dependency injection.

Defines the interface that all limiter implementations must follow,
enabling dependency injection and testing without conditional imports.
"""

from typing import Protocol, Any, Callable


class LimiterInterface(Protocol):
    """Protocol defining the limiter interface.
    
    Any limiter implementation (real or mock) must implement these methods.
    This enables type-safe dependency injection without conditional imports.
    """

    def is_enabled(self) -> bool:
        """Check whether rate limiting is active.

        Returns:
            True if rate limiting is enforced, False otherwise.
        """
        ...  # pylint: disable=unnecessary-ellipsis

    def get_stats(self) -> dict[str, Any]:
        """Get rate limiter statistics.

        Returns:
            Dictionary containing limiter statistics (format depends on backend).
        """
        ...  # pylint: disable=unnecessary-ellipsis

    def __call__(self, key: str) -> Callable:
        """Return a rate limit decorator for the given key.

        Args:
            key: Rate limit key (e.g., "20/minute")

        Returns:
            Decorator function that enforces the rate limit.
        """
        ...  # pylint: disable=unnecessary-ellipsis
