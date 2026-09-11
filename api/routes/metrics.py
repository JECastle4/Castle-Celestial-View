"""
Prometheus metrics endpoint.

Exposes `/metrics` in text format for Prometheus scraping.
"""

from fastapi import APIRouter
from starlette.responses import Response
from api.metrics import get_metrics

router = APIRouter()


@router.get('/metrics', tags=['monitoring'])
async def get_metrics_endpoint() -> Response:
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus text exposition format.
    This endpoint is typically scraped by Prometheus every 15-60 seconds.
    
    Response:
        Prometheus text format (text/plain)
    """
    metrics = get_metrics()
    return Response(
        content=metrics.get_metrics_text(),
        media_type='text/plain; version=0.0.4; charset=utf-8',
    )
