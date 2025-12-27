"""Custom middleware for the FastAPI application."""

import time
import uuid
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID to all requests."""
    
    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Add to request state
        request.state.request_id = request_id
        
        # Add to response headers
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests and responses."""
    
    async def dispatch(self, request: Request, call_next):
        # Start timing
        start_time = time.time()
        
        # Get request ID
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Log request
        logger.info(
            "API request started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params),
            client_ip=request.client.host if request.client else "unknown"
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            # Log response
            logger.info(
                "API request completed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                latency_ms=round(latency_ms, 2)
            )
            
            # Add latency to response headers
            response.headers["X-Response-Time"] = f"{latency_ms:.2f}ms"
            
            return response
            
        except Exception as e:
            # Calculate latency for failed requests
            latency_ms = (time.time() - start_time) * 1000
            
            # Log error
            logger.error(
                "API request failed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                latency_ms=round(latency_ms, 2),
                error=str(e)
            )
            
            # Re-raise the exception
            raise


def add_request_id_middleware(app: FastAPI):
    """Add request ID middleware to the app."""
    app.add_middleware(RequestIDMiddleware)


def add_logging_middleware(app: FastAPI):
    """Add logging middleware to the app."""
    app.add_middleware(LoggingMiddleware)