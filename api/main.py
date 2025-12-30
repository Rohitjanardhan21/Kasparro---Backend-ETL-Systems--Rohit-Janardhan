"""FastAPI application for the Kasparro ETL system."""

from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import time
import uuid
import structlog

from core.database import get_db, check_db_connection
from core.logging import setup_logging, RequestLogger
from core.config import get_settings
from .endpoints import data, health, stats, etl
from .middleware import (
    add_request_id_middleware, 
    add_logging_middleware,
    add_security_headers_middleware,
    add_cors_middleware,
    add_input_validation_middleware,
    add_timeout_middleware
)
from api.middleware.rate_limiter import add_rate_limiting_middleware
from api.middleware.cache import add_cache_middleware

# Setup logging
setup_logging()
logger = structlog.get_logger(__name__)
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="Kasparro ETL API",
    description="Production-grade ETL system for cryptocurrency data",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware with secure settings
add_cors_middleware(app)

# Add response caching middleware (5 minute cache)
add_cache_middleware(app, cache_ttl=300)

# Add timeout middleware (20 second timeout for better reliability)
add_timeout_middleware(app, timeout_seconds=20)

# Add security headers middleware
add_security_headers_middleware(app)

# Add input validation middleware
add_input_validation_middleware(app)

# Add rate limiting middleware (100 requests per minute)
add_rate_limiting_middleware(app, max_requests=100, window_seconds=60)

# Add custom middleware
add_request_id_middleware(app)
add_logging_middleware(app)

# Include routers with v1 prefix
app.include_router(data.router, prefix="/api/v1")
app.include_router(health.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")
app.include_router(etl.router, prefix="/api/v1")

# Include routers at root level for backward compatibility
app.include_router(data.router)
app.include_router(health.router)
app.include_router(stats.router)
app.include_router(etl.router)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Kasparro ETL API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health"
    }

# Legacy endpoints (for backward compatibility)
@app.get("/data")
async def get_data_legacy(
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=1000),
    source: Optional[str] = Query(None),
    coin_id: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    request: Request = None
):
    """Legacy data endpoint (redirects to /api/v1/data)."""
    return await data.get_data(page, limit, source, coin_id, symbol, db, request)

@app.get("/health")
async def get_health_legacy(db: Session = Depends(get_db)):
    """Legacy health endpoint (redirects to /api/v1/health)."""
    return await health.get_health(db)

@app.get("/stats")
async def get_stats_legacy(db: Session = Depends(get_db)):
    """Legacy stats endpoint (redirects to /api/v1/stats)."""
    return await stats.get_stats(db)

# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("Starting Kasparro ETL API")
    
    # Check database connection
    if not check_db_connection():
        logger.error("Database connection failed during startup")
        raise Exception("Database connection failed")
    
    logger.info("Kasparro ETL API started successfully")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Shutting down Kasparro ETL API")

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower()
    )