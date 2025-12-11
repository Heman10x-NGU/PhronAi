"""
PHRONAI Rate Limiting Middleware

Simple in-memory rate limiting for API protection.
Limits requests per user per time window.

Resume Point: Implemented request throttling at 10 req/min per user
to prevent API cost explosion while maintaining UX.
"""

import time
import logging
from collections import defaultdict
from typing import Callable
from django.http import JsonResponse

logger = logging.getLogger(__name__)

# Configuration
RATE_LIMIT_REQUESTS = 10  # Max requests
RATE_LIMIT_WINDOW = 60  # Per 60 seconds (1 minute)
RATE_LIMIT_CLEANUP_INTERVAL = 300  # Clean old entries every 5 minutes


class RateLimitMiddleware:
    """
    Rate limiting middleware that tracks requests per user.
    
    Uses a sliding window approach with in-memory storage.
    For production scaling, this should use Redis.
    """
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
        # Structure: {user_key: [timestamp1, timestamp2, ...]}
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._last_cleanup = time.time()
    
    def __call__(self, request):
        # Skip rate limiting for static files and health checks
        if request.path.startswith('/static/') or request.path == '/health/':
            return self.get_response(request)
        
        # Get user identifier (IP for anonymous, user_id if authenticated)
        user_key = self._get_user_key(request)
        
        # Check and update rate limit
        now = time.time()
        is_limited, remaining, reset_in = self._check_rate_limit(user_key, now)
        
        if is_limited:
            logger.warning(f"Rate limit exceeded for {user_key}")
            return JsonResponse({
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Try again in {int(reset_in)} seconds.",
                "retry_after": int(reset_in),
            }, status=429)
        
        # Process request
        response = self.get_response(request)
        
        # Add rate limit headers
        response['X-RateLimit-Limit'] = str(RATE_LIMIT_REQUESTS)
        response['X-RateLimit-Remaining'] = str(remaining)
        response['X-RateLimit-Reset'] = str(int(now + reset_in))
        
        # Periodic cleanup
        if now - self._last_cleanup > RATE_LIMIT_CLEANUP_INTERVAL:
            self._cleanup_old_entries(now)
        
        return response
    
    def _get_user_key(self, request) -> str:
        """Extract user identifier from request."""
        # Try to get authenticated user
        if hasattr(request, 'user') and request.user.is_authenticated:
            return f"user:{request.user.id}"
        
        # Fall back to IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        
        return f"ip:{ip}"
    
    def _check_rate_limit(self, user_key: str, now: float) -> tuple[bool, int, float]:
        """
        Check if user is rate limited.
        
        Returns: (is_limited, remaining_requests, seconds_until_reset)
        """
        window_start = now - RATE_LIMIT_WINDOW
        
        # Filter to only requests within the window
        recent_requests = [ts for ts in self._requests[user_key] if ts > window_start]
        self._requests[user_key] = recent_requests
        
        # Add current request
        recent_requests.append(now)
        self._requests[user_key] = recent_requests
        
        request_count = len(recent_requests)
        remaining = max(0, RATE_LIMIT_REQUESTS - request_count)
        
        # Calculate reset time (when oldest request expires from window)
        if recent_requests:
            reset_in = max(0, recent_requests[0] + RATE_LIMIT_WINDOW - now)
        else:
            reset_in = RATE_LIMIT_WINDOW
        
        is_limited = request_count > RATE_LIMIT_REQUESTS
        
        return is_limited, remaining, reset_in
    
    def _cleanup_old_entries(self, now: float) -> None:
        """Remove old entries to prevent memory leak."""
        window_start = now - RATE_LIMIT_WINDOW
        
        keys_to_remove = []
        for user_key, timestamps in self._requests.items():
            # Filter old timestamps
            valid_timestamps = [ts for ts in timestamps if ts > window_start]
            if valid_timestamps:
                self._requests[user_key] = valid_timestamps
            else:
                keys_to_remove.append(user_key)
        
        for key in keys_to_remove:
            del self._requests[key]
        
        self._last_cleanup = now
        if keys_to_remove:
            logger.debug(f"Cleaned up {len(keys_to_remove)} expired rate limit entries")
