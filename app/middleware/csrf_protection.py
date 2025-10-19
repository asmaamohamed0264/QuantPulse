"""
CSRF Protection middleware for web forms
"""
import secrets
import time
from typing import Dict, Optional
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import hashlib
import hmac

class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection middleware for web forms
    """
    
    def __init__(self, app, secret_key: str, cookie_name: str = "csrf_token", 
                 header_name: str = "X-CSRFToken", token_lifetime: int = 3600):
        super().__init__(app)
        self.secret_key = secret_key.encode()
        self.cookie_name = cookie_name
        self.header_name = header_name
        self.token_lifetime = token_lifetime
    
    def generate_csrf_token(self) -> str:
        """Generate a CSRF token"""
        timestamp = str(int(time.time()))
        random_part = secrets.token_urlsafe(32)
        message = f"{timestamp}:{random_part}"
        
        # Create HMAC signature
        signature = hmac.new(
            self.secret_key,
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"{message}:{signature}"
    
    def validate_csrf_token(self, token: str) -> bool:
        """Validate CSRF token"""
        try:
            parts = token.split(':')
            if len(parts) != 3:
                return False
            
            timestamp, random_part, signature = parts
            message = f"{timestamp}:{random_part}"
            
            # Verify signature
            expected_signature = hmac.new(
                self.secret_key,
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                return False
            
            # Check if token is expired
            token_time = int(timestamp)
            current_time = int(time.time())
            
            if current_time - token_time > self.token_lifetime:
                return False
            
            return True
            
        except (ValueError, TypeError):
            return False
    
    def should_protect(self, request: Request) -> bool:
        """Determine if request should be CSRF protected"""
        # Protect only POST, PUT, PATCH, DELETE for web forms
        if request.method not in ["POST", "PUT", "PATCH", "DELETE"]:
            return False
        
        # Skip API endpoints (they use JWT authentication)
        if request.url.path.startswith("/api/"):
            return False
        
        # Skip health checks and static files
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"] or \
           request.url.path.startswith("/static"):
            return False
        
        # Protect web form endpoints
        protected_paths = [
            "/auth/login",
            "/auth/register", 
            "/auth/logout",
            "/profile/update",
            "/strategies/create",
            "/strategies/update",
            "/brokers/connect",
            "/brokers/disconnect"
        ]
        
        return any(request.url.path.startswith(path) for path in protected_paths)
    
    async def dispatch(self, request: Request, call_next):
        """CSRF protection logic"""
        
        if not self.should_protect(request):
            response = await call_next(request)
            return response
        
        # Get token from header or form data
        csrf_token = request.headers.get(self.header_name)
        
        if not csrf_token:
            # Try to get from form data for POST requests
            if request.method == "POST":
                try:
                    form_data = await request.form()
                    csrf_token = form_data.get("csrf_token")
                except:
                    pass
        
        # Validate CSRF token
        if not csrf_token or not self.validate_csrf_token(csrf_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "CSRF token validation failed",
                    "message": "Invalid or missing CSRF token"
                }
            )
        
        response = await call_next(request)
        return response


def get_csrf_token(request: Request, secret_key: str) -> str:
    """
    Utility function to generate CSRF token for templates
    """
    middleware = CSRFProtectionMiddleware(None, secret_key)
    return middleware.generate_csrf_token()


class CSRFTokenInjector(BaseHTTPMiddleware):
    """
    Middleware to inject CSRF tokens into HTML responses
    """
    
    def __init__(self, app, secret_key: str):
        super().__init__(app)
        self.secret_key = secret_key
    
    async def dispatch(self, request: Request, call_next):
        """Inject CSRF token into HTML responses"""
        response = await call_next(request)
        
        # Only inject for HTML responses
        if "text/html" in response.headers.get("content-type", ""):
            # Generate CSRF token
            csrf_token = get_csrf_token(request, self.secret_key)
            
            # Set CSRF token cookie
            response.set_cookie(
                "csrf_token",
                csrf_token,
                httponly=False,  # Allow JavaScript access
                secure=True,     # HTTPS only in production
                samesite="strict"
            )
            
            # Add token to response headers for JavaScript access
            response.headers["X-CSRFToken"] = csrf_token
        
        return response