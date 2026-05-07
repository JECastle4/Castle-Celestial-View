"""
Main FastAPI application for Astronomy API
"""
import os
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
from api.i18n import set_request_locale, SUPPORTED_LOCALES

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Astronomy API",
    description="API for astronomical calculations including day of week, sun/moon positions, and more",
    version="0.1.0"
)

# Configure CORS with environment-specific settings
# For production, set ALLOWED_ORIGINS environment variable to comma-separated list of domains
# Example: ALLOWED_ORIGINS="https://yourdomain.com,https://www.yourdomain.com"
allowed_origins = [
    origin.strip() 
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"  # Default for local development
    ).split(",")
    if origin.strip()  # Filter out empty strings
]

# Validate CORS origins in production
if os.getenv("ALLOWED_ORIGINS"):
    # Check for insecure HTTP origins
    http_origins = [origin for origin in allowed_origins if origin.startswith("http://")]
    if http_origins:
        logger.warning(
            "⚠️ SECURITY WARNING: CORS configured with insecure HTTP origins: %s. "
            "Use HTTPS for production deployments.",
            http_origins
        )

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,  # No authentication required
    allow_methods=["GET", "POST"],  # Only methods used by the API
    allow_headers=["Content-Type", "Accept", "Accept-Language"],
)


@app.middleware("http")
async def locale_middleware(request: Request, call_next):
    """Read Accept-Language header and set the request-scoped locale.

    Priority:
    1. Accept-Language header (used by POST requests)
    2. ?lang= query parameter (fallback for SSE/EventSource which can't set headers)

    Falls back to 'en' for any unsupported locale.
    """
    accept_language = request.headers.get("accept-language", "")
    lang_param = request.query_params.get("lang", "")

    raw = accept_language or lang_param or "en"
    first_tag = raw.split(",")[0].split(";")[0].strip().lower()
    # Try exact match, then language prefix (e.g. 'en-us' → 'en')
    if first_tag in SUPPORTED_LOCALES:
        locale = first_tag
    else:
        prefix = first_tag.split("-")[0]
        locale = prefix if prefix in SUPPORTED_LOCALES else 'en'
    set_request_locale(locale)
    return await call_next(request)


# Include the routes
app.include_router(router, prefix="/api/v1", tags=["astronomy"])


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Astronomy API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "ok"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
