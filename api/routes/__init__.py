"""
API route modules organized by domain (bodies, batch, events).
"""
from fastapi import APIRouter
from .bodies import router as bodies_router
from .batch import router as batch_router
from .events import router as events_router


# Combine all sub-routers into a single router
router = APIRouter()
router.include_router(bodies_router)
router.include_router(batch_router)
router.include_router(events_router)


__all__ = ["router"]
