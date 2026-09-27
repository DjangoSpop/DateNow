"""
Main FastAPI application

The database schema is managed by Alembic (`alembic upgrade head`); the app
does not create tables on startup.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routes import auth, users, onboarding, matches, websocket

logger = logging.getLogger("datenow")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    logger.info("Starting DateNow API (environment=%s)", settings.ENVIRONMENT)
    if not settings.ai_enabled:
        logger.warning("GEMINI_API_KEY not set: AI features are disabled")
    yield
    logger.info("Shutting down DateNow API")


_docs_enabled = not settings.is_production

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="AI-Moderated Dating Platform API",
    lifespan=lifespan,
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)

# Configure CORS (config rejects "*" because credentials are allowed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 422 responses keep FastAPI's shape but never echo the submitted value back
# (it may be a password or other personal data that ends up in client logs).
_VALIDATION_ERROR_KEYS = ("loc", "msg", "type")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [{k: e[k] for k in _VALIDATION_ERROR_KEYS if k in e} for e in exc.errors()]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": jsonable_encoder(errors)},
    )


# Include routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(onboarding.router, prefix=settings.API_V1_STR)
app.include_router(matches.router, prefix=settings.API_V1_STR)
app.include_router(websocket.router)  # WebSocket routes (no prefix needed)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to DateNow API",
        "version": "1.0.0",
        "docs": "/docs" if _docs_enabled else None,
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
