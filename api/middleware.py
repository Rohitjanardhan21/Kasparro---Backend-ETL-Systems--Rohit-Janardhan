"""Custom middleware for the FastAPI application."""

import asyncio
import time
import uuid
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
import structlog

logger = structlog.get_logger(__name__)


class TimeoutMiddleware(BaseHTTPMiddleware):
    """Middleware to prevent request timeouts and hanging connections."""
    
    def __init__(self, app, timeout_seconds: int = 20):
        super().__init__(app)
        self.timeout_seconds = timeout_seconds
    
    async def dispatch(self, request: Request, call_next):
        try:
            # Set timeout for request processing
            response = await asyncio.wait_for(
                call_next(request), 
                timeout=self.timeout_seconds
            )
            return response
        except asyncio.TimeoutError:
            logger.warning(
                "Request timeout",
                path=request.url.path,
                method=request.method,
                timeout_seconds=self.timeout_seconds,
                client_ip=request.client.host if request.client else "unknown"
            )
            return JSONResponse(
                status_code=504,
                content={
                    "detail": "Request timeout. Please try again with smaller parameters.",
                    "timeout_seconds": self.timeout_seconds,
                    "suggestion": "Try reducing the limit parameter or use pagination"
                }
            )
        except Exception as e:
            logger.error(
                "Request processing error",
                path=request.url.path,
                method=request.method,
                error=str(e),
                client_ip=request.client.host if request.client else "unknown"
            )
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "request_id": getattr(request.state, "request_id", "unknown")
                }
            )


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Middleware to validate and sanitize input parameters."""
    
    async def dispatch(self, request: Request, call_next):
        # Check for oversized parameters
        if request.query_params:
            for key, value in request.query_params.items():
                # Limit parameter length to prevent abuse
                if len(str(value)) > 1000:
                    logger.warning(
                        "Oversized parameter detected",
                        parameter=key,
                        length=len(str(value)),
                        client_ip=request.client.host if request.client else "unknown"
                    )
                    raise HTTPException(
                        status_code=400,
                        detail=f"Parameter '{key}' is too long. Maximum length is 1000 characters."
                    )
                
                # Check for potentially malicious patterns
                malicious_patterns = [
                    "script>", "<iframe", "javascript:", "vbscript:",
                    "onload=", "onerror=", "onclick=", "onmouseover="
                ]
                
                value_lower = str(value).lower()
                for pattern in malicious_patterns:
                    if pattern in value_lower:
                        logger.warning(
                            "Potentially malicious input detected",
                            parameter=key,
                            pattern=pattern,
                            client_ip=request.client.host if request.client else "unknown"
                        )
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid characters detected in parameter '{key}'"
                        )
        
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add comprehensive security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "cross-origin"
        
        # Add HSTS for HTTPS (will be ignored on HTTP)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # Add server info hiding
        response.headers["Server"] = "Kasparro-ETL/1.0"
        
        return response


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


def add_timeout_middleware(app: FastAPI, timeout_seconds: int = 25):
    """Add request timeout middleware to the app."""
    app.add_middleware(TimeoutMiddleware, timeout_seconds=timeout_seconds)


def add_input_validation_middleware(app: FastAPI):
    """Add input validation middleware to the app."""
    app.add_middleware(InputValidationMiddleware)


def add_security_headers_middleware(app: FastAPI):
    """Add security headers middleware to the app."""
    app.add_middleware(SecurityHeadersMiddleware)


def add_cors_middleware(app: FastAPI):
    """Add CORS middleware with secure settings."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:8080", "http://98.81.97.104"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Response-Time"]
    )


def add_request_id_middleware(app: FastAPI):
    """Add request ID middleware to the app."""
    app.add_middleware(RequestIDMiddleware)


def add_logging_middleware(app: FastAPI):
    """Add logging middleware to the app."""
    app.add_middleware(LoggingMiddleware)