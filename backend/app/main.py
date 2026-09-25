"""
Main FastAPI application

The database schema is managed by Alembic: run `alembic upgrade head` before starting the app.
"""
import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.errors import register_exception_handlers
from app.routes import auth, users, matches, websocket

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    logger.info("Starting DateNow API (environment=%s)", settings.ENVIRONMENT)
    cleanup = asyncio.create_task(websocket.session_cleanup_loop(), name="ws-session-cleanup")
    try:
        yield
    finally:
        cleanup.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await cleanup
        logger.info("DateNow API shut down")


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="AI-Moderated Dating Platform API",
    lifespan=lifespan
)

register_exception_handlers(app)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(matches.router, prefix=settings.API_V1_STR)
app.include_router(websocket.router)  # WebSocket routes (no prefix needed)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to DateNow API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "DateNow API",
        "environment": settings.ENVIRONMENT
    }
