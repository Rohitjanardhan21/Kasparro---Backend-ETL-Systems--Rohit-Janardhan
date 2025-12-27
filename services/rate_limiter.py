"""Rate limiting service with exponential backoff."""

import time
from typing import Dict, Optional
from dataclasses import dataclass
from threading import Lock
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests_per_period: int
    period_seconds: int
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0


class RateLimiter:
    """Thread-safe rate limiter with exponential backoff."""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.requests: Dict[str, list] = {}
        self.lock = Lock()
    
    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed under rate limit."""
        with self.lock:
            now = time.time()
            
            # Initialize or clean old requests
            if key not in self.requests:
                self.requests[key] = []
            
            # Remove requests outside the time window
            cutoff = now - self.config.period_seconds
            self.requests[key] = [req_time for req_time in self.requests[key] if req_time > cutoff]
            
            # Check if we're under the limit
            if len(self.requests[key]) < self.config.requests_per_period:
                self.requests[key].append(now)
                return True
            
            return False
    
    def wait_if_needed(self, key: str) -> None:
        """Wait if rate limit is exceeded."""
        if not self.is_allowed(key):
            with self.lock:
                if self.requests[key]:
                    oldest_request = min(self.requests[key])
                    wait_time = self.config.period_seconds - (time.time() - oldest_request)
                    if wait_time > 0:
                        logger.info(f"Rate limit exceeded for {key}, waiting {wait_time:.2f}s")
                        time.sleep(wait_time)
    
    def get_retry_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay."""
        delay = self.config.base_delay * (2 ** attempt)
        return min(delay, self.config.max_delay)


class RetryableError(Exception):
    """Exception that indicates the operation should be retried."""
    pass


def with_retry_and_rate_limit(rate_limiter: RateLimiter, key: str):
    """Decorator for functions that need rate limiting and retry logic."""
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(rate_limiter.config.max_retries + 1):
                try:
                    # Apply rate limiting
                    rate_limiter.wait_if_needed(key)
                    
                    # Execute function
                    return func(*args, **kwargs)
                    
                except RetryableError as e:
                    last_exception = e
                    if attempt < rate_limiter.config.max_retries:
                        delay = rate_limiter.get_retry_delay(attempt)
                        logger.warning(
                            f"Retryable error on attempt {attempt + 1}, retrying in {delay}s",
                            error=str(e)
                        )
                        time.sleep(delay)
                    else:
                        logger.error(f"Max retries exceeded for {key}", error=str(e))
                        raise
                except Exception as e:
                    logger.error(f"Non-retryable error for {key}", error=str(e))
                    raise
            
            # This should never be reached, but just in case
            raise last_exception or Exception("Unknown error in retry logic")
        
        return wrapper
    return decorator