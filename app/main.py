"""
QuantPulse - Main FastAPI Application
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from loguru import logger

from app.config import settings
from app.database import create_tables
from app.init_data import init_database
from app.api.v1 import auth, webhooks, strategies, users, subscriptions, broker_accounts
from app.api.v1 import strategies_enhanced
from app.api.v1 import brokers_enhanced
from app.middleware import RateLimitMiddleware, WebhookRateLimitMiddleware, CSRFTokenInjector
from app.utils import migrate_credentials_to_encrypted
from app.database import get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting QuantPulse application...")
    create_tables()
    logger.info("Database tables created/verified")
    init_database()
    logger.info("Database initialized with default data")
    
    # Migrate existing credentials to encrypted format
    if hasattr(settings, 'encryption_key') and settings.encryption_key:
        try:
            db = next(get_db())
            result = migrate_credentials_to_encrypted(db, settings.encryption_key)
            logger.info(f"Credential migration: {result}")
            db.close()
        except Exception as e:
            logger.warning(f"Credential migration failed: {e}")
    
    yield
    # Shutdown
    logger.info("Shutting down QuantPulse application...")


# Create FastAPI app
app = FastAPI(
    title="QuantPulse",
    description="Professional Automated Trading Service for TradingView Webhooks",
    version=settings.version,
    docs_url="/docs",  # Always enable docs for now
    redoc_url="/redoc",  # Always enable redoc for now
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else getattr(settings, 'cors_origins', "https://quantpulse.qub3.uk,https://www.quantpulse.qub3.uk").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security middleware (order matters - apply from outermost to innermost)
if not settings.debug:  # Only in production
    # Rate limiting for general API requests
    app.add_middleware(
        RateLimitMiddleware,
        calls=getattr(settings, 'rate_limit_per_minute', 100),
        period=60
    )
    
    # Specialized rate limiting for webhooks
    app.add_middleware(
        WebhookRateLimitMiddleware,
        webhook_calls=getattr(settings, 'webhook_rate_limit', 50),
        period=60
    )
    
    # CSRF token injection for HTML responses
    app.add_middleware(
        CSRFTokenInjector,
        secret_key=settings.secret_key
    )

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for Docker and monitoring"""
    return {
        "status": "healthy",
        "service": "QuantPulse",
        "version": settings.version
    }

# Root endpoint is now handled by web routes

# Include web routes for frontend (before API routes to handle root)
from app.web import router as web_router
app.include_router(web_router, tags=["web"])

# Include API routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(webhooks.router, prefix="/api/v1", tags=["Webhooks"])
app.include_router(strategies.router, prefix="/api/v1/strategies", tags=["Strategies"])
app.include_router(strategies_enhanced.router, prefix="/api/v1/strategies", tags=["Strategies Enhanced"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(subscriptions.router, prefix="/api/v1/subscriptions", tags=["Subscriptions"])
app.include_router(broker_accounts.router, prefix="/api/v1/broker-accounts", tags=["Broker Accounts"])
app.include_router(brokers_enhanced.router, prefix="/api/v1/broker-accounts", tags=["Broker Accounts Enhanced"])

# Mount static files (if you have a web interface)
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except RuntimeError:
    # Static directory doesn't exist, skip mounting
    pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )