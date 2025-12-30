"""Simple response caching middleware."""

import json
import time
from typing import Dict, Any, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger(__name__)


class SimpleCache:
    """Simple in-memory cache with TTL."""
    
    def __init__(self, default_ttl: int = 300):  # 5 minutes default
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in self.cache:
            entry = self.cache[key]
            if time.time() < entry['expires']:
                return entry['value']
            else:
                # Remove expired entry
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL."""
        if ttl is None:
            ttl = self.default_ttl
        
        self.cache[key] = {
            'value': value,
            'expires': time.time() + ttl
        }
    
    def clear_expired(self) -> None:
        """Clear expired entries."""
        now = time.time()
        expired_keys = [k for k, v in self.cache.items() if now >= v['expires']]
        for key in expired_keys:
            del self.cache[key]


class CacheMiddleware(BaseHTTPMiddleware):
    """Response caching middleware."""
    
    def __init__(self, app, cache_ttl: int = 300):
        super().__init__(app)
        self.cache = SimpleCache(cache_ttl)
        self.cache_ttl = cache_ttl
    
    def _should_cache(self, request: Request) -> bool:
        """Determine if request should be cached."""
        # Only cache GET requests
        if request.method != "GET":
            return False
        
        # Cache specific endpoints
        cacheable_paths = ["/data", "/stats", "/api/v1/data", "/api/v1/stats"]
        return any(request.url.path.startswith(path) for path in cacheable_paths)
    
    def _get_cache_key(self, request: Request) -> str:
        """Generate cache key for request."""
        # Include path and query parameters in key
        query_string = str(request.query_params)
        return f"{request.url.path}?{query_string}"
    
    async def dispatch(self, request: Request, call_next):
        # Check if request should be cached
        if not self._should_cache(request):
            return await call_next(request)
        
        # Generate cache key
        cache_key = self._get_cache_key(request)
        
        # Try to get from cache
        cached_response = self.cache.get(cache_key)
        if cached_response is not None:
            logger.debug(
                "Cache hit",
                cache_key=cache_key,
                path=request.url.path
            )
            
            # Return cached response
            return Response(
                content=cached_response['content'],
                status_code=cached_response['status_code'],
                headers={
                    **cached_response['headers'],
                    'X-Cache': 'HIT',
                    'X-Cache-Key': cache_key
                },
                media_type=cached_response['media_type']
            )
        
        # Process request
        response = await call_next(request)
        
        # Cache successful responses
        if response.status_code == 200:
            # Read response content
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk
            
            # Store in cache
            cached_data = {
                'content': response_body,
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'media_type': response.media_type
            }
            
            self.cache.set(cache_key, cached_data, self.cache_ttl)
            
            logger.debug(
                "Response cached",
                cache_key=cache_key,
                path=request.url.path,
                ttl=self.cache_ttl
            )
            
            # Create new response with cache headers
            return Response(
                content=response_body,
                status_code=response.status_code,
                headers={
                    **dict(response.headers),
                    'X-Cache': 'MISS',
                    'X-Cache-TTL': str(self.cache_ttl)
                },
                media_type=response.media_type
            )
        
        return response


def add_cache_middleware(app, cache_ttl: int = 300):
    """Add caching middleware to the app."""
    app.add_middleware(CacheMiddleware, cache_ttl=cache_ttl)