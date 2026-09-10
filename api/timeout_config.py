"""
Request timeout configuration and endpoint cost classification.

Endpoints are classified by computational cost (cheap/medium/expensive)
to enable fair timeout adjustment under load. Timeouts scale based on
observed system performance (p95 request duration).
"""

# Endpoint cost tier classification (for adaptive timeout calculation)
# Paths must match what the middleware receives: full paths with /api/v1 prefix
ENDPOINT_COSTS = {
    # Cheap: lightweight responses, typically <100ms
    '/api/v1/health': 'cheap',
    '/metrics': 'cheap',  # Not under /api/v1 (separate metrics_router)

    # Medium: simple position/phase queries, typically 0.5-2s
    '/api/v1/day-of-week': 'medium',
    '/api/v1/sun-position': 'medium',
    '/api/v1/moon-position': 'medium',
    '/api/v1/mercury-position': 'medium',
    '/api/v1/venus-position': 'medium',
    '/api/v1/mars-position': 'medium',
    '/api/v1/jupiter-position': 'medium',
    '/api/v1/saturn-position': 'medium',
    '/api/v1/uranus-position': 'medium',
    '/api/v1/neptune-position': 'medium',
    '/api/v1/moon-phase': 'medium',

    # Expensive: batch/event processing, typically 5-30s
    '/api/v1/batch-earth-observations': 'expensive',
    '/api/v1/batch-earth-observations-stream': 'expensive',
    '/api/v1/astronomical-events': 'expensive',
    '/api/v1/astronomical-events-stream': 'expensive',
    '/api/v1/contact-times': 'expensive',
}

# Base timeouts (before adaptive scaling based on system performance)
# These are starting points; actual timeouts adjust based on observed p95
BASE_TIMEOUTS = {
    'cheap': 3,        # 3 seconds for quick endpoints
    'medium': 15,      # 15 seconds for standard queries
    'expensive': 120,  # 2 minutes for batch/event operations
}

# Hard limit (absolute maximum timeout regardless of system state)
# This prevents any single request from running indefinitely
HARD_LIMIT_SECONDS = 300  # 5 minutes

# Percentile configuration for adaptive timeout calculation
PERCENTILE_TO_TRACK = 0.95  # p95 (95th percentile)
PERCENTILE_CACHE_TTL_SECONDS = 5  # Recalculate p95 every 5 seconds
SLIDING_WINDOW_SECONDS = 300  # Track last 5 minutes of request times

# Adaptive timeout scaling factors
# Based on ratio of observed p95 to base timeout
TIMEOUT_MULTIPLIERS = {
    # If p95 < base * 0.5: system is fast, be generous
    'generous': 2.0,
    # If base * 0.5 <= p95 < base * 0.8: system healthy, use base
    'normal': 1.0,
    # If p95 >= base * 0.8: system degraded, tighten
    'degraded': 0.7,
}


def get_endpoint_cost(endpoint: str) -> str:
    """
    Get the cost tier for an endpoint.
    
    Args:
        endpoint: Full request path including API prefix (e.g., '/api/v1/batch-earth-observations').
                 Falls back to 'medium' tier if endpoint is not in the cost map.
    
    Returns:
        'cheap', 'medium', or 'expensive' tier (defaults to 'medium' if unknown)
    
    Note:
        Paths must match the full mounted route path with prefix. All endpoints
        registered with 'router' are mounted with prefix '/api/v1' by:
            app.include_router(router, prefix="/api/v1")
        
        Example paths:
            - '/api/v1/batch-earth-observations' → expensive (120s base timeout)
            - '/api/v1/moon-position' → medium (15s base timeout)
            - 'unknown' → medium (15s base timeout, for unmatched routes)
    """
    return ENDPOINT_COSTS.get(endpoint, 'medium')


def get_base_timeout(cost: str) -> int:
    """
    Get the base timeout for a cost tier.
    
    Args:
        cost: 'cheap', 'medium', or 'expensive'
    
    Returns:
        Base timeout in seconds
    """
    return BASE_TIMEOUTS.get(cost, BASE_TIMEOUTS['medium'])
