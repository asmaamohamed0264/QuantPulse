"""
Rate limiting middleware for API security
"""
import time
from typing import Dict, Tuple
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict, deque
import asyncio

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with sliding window algorithm
    """
    
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls  # Max calls per period
        self.period = period  # Period in seconds
        self.clients: Dict[str, deque] = defaultdict(deque)
        self.lock = asyncio.Lock()
    
    def get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        # Check for forwarded headers first
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        
        x_real_ip = request.headers.get("x-real-ip")
        if x_real_ip:
            return x_real_ip.strip()
        
        # Fallback to direct connection IP
        if hasattr(request, 'client') and request.client:
            return request.client.host
        return "unknown"
    
    async def dispatch(self, request: Request, call_next):
        """Rate limiting logic"""
        
        # Skip rate limiting for health checks and static files
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"] or \
           request.url.path.startswith("/static"):
            response = await call_next(request)
            return response
        
        client_ip = self.get_client_ip(request)
        current_time = time.time()
        
        async with self.lock:
            # Clean old requests outside the time window
            client_requests = self.clients[client_ip]
            while client_requests and client_requests[0] <= current_time - self.period:
                client_requests.popleft()
            
            # Check if client exceeded rate limit
            if len(client_requests) >= self.calls:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Rate limit exceeded",
                        "limit": self.calls,
                        "period": self.period,
                        "retry_after": int(client_requests[0] + self.period - current_time)
                    }
                )
            
            # Add current request timestamp
            client_requests.append(current_time)
        
        # Process the request
        response = await call_next(request)
        
        # Add rate limiting headers
        remaining = max(0, self.calls - len(self.clients[client_ip]))
        response.headers["X-RateLimit-Limit"] = str(self.calls)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(current_time + self.period))
        
        return response


class WebhookRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Specialized rate limiting for webhook endpoints
    More restrictive limits for webhook paths
    """
    
    def __init__(self, app, webhook_calls: int = 50, period: int = 60):
        super().__init__(app)
        self.webhook_calls = webhook_calls
        self.period = period
        self.clients: Dict[str, deque] = defaultdict(deque)
        self.lock = asyncio.Lock()
    
    def get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        
        x_real_ip = request.headers.get("x-real-ip")
        if x_real_ip:
            return x_real_ip.strip()
        
        if hasattr(request, 'client') and request.client:
            return request.client.host
        return "unknown"
    
    async def dispatch(self, request: Request, call_next):
        """Webhook-specific rate limiting"""
        
        # Apply only to webhook endpoints
        if not request.url.path.startswith("/api/v1/webhooks"):
            response = await call_next(request)
            return response
        
        client_ip = self.get_client_ip(request)
        current_time = time.time()
        
        async with self.lock:
            # Clean old requests
            client_requests = self.clients[client_ip]
            while client_requests and client_requests[0] <= current_time - self.period:
                client_requests.popleft()
            
            # Check webhook rate limit
            if len(client_requests) >= self.webhook_calls:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Webhook rate limit exceeded",
                        "limit": self.webhook_calls,
                        "period": self.period,
                        "retry_after": int(client_requests[0] + self.period - current_time),
                        "message": "Too many webhook requests. Please check your TradingView alert frequency."
                    }
                )
            
            client_requests.append(current_time)
        
        response = await call_next(request)
        
        # Add webhook-specific headers
        remaining = max(0, self.webhook_calls - len(self.clients[client_ip]))
        response.headers["X-Webhook-RateLimit-Limit"] = str(self.webhook_calls)
        response.headers["X-Webhook-RateLimit-Remaining"] = str(remaining)
        
        return response