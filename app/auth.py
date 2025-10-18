"""
Authentication and security utilities
"""
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.user import User
import ipaddress


# JWT Security
security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = verify_token(credentials.credentials)
    if payload is None:
        raise credentials_exception
    
    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user"
        )
    
    return user


def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Get current user if authenticated, otherwise return None"""
    try:
        # Try to get token from cookie first
        token = request.cookies.get("access_token")
        if token and token.startswith("Bearer "):
            token = token[7:]  # Remove 'Bearer ' prefix
        
        # If no cookie token, try Authorization header
        if not token:
            authorization = request.headers.get("authorization")
            if authorization and authorization.startswith("Bearer "):
                token = authorization[7:]
        
        if not token:
            return None
            
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        email: str = payload.get("sub")
        if email is None:
            return None
            
        user = db.query(User).filter(User.email == email).first()
        return user if user and user.is_active else None
        
    except (JWTError, AttributeError):
        return None

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def get_current_superuser(current_user: User = Depends(get_current_user)) -> User:
    """Get current superuser"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

def get_client_ip(request: Request) -> str:
    """Extract client IP address from request"""
    # Check for forwarded headers first
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        # Take the first IP in the chain
        return x_forwarded_for.split(",")[0].strip()
    
    x_real_ip = request.headers.get("x-real-ip")
    if x_real_ip:
        return x_real_ip.strip()
    
    # Fallback to direct connection IP
    return request.client.host

def is_ip_whitelisted(ip: str, allowed_ips: List[str]) -> bool:
    """Check if IP is in whitelist"""
    if not allowed_ips:
        return True  # No whitelist means allow all
    
    # Default allowed IPs (localhost, TradingView IPs)
    default_allowed = [
        "127.0.0.1",
        "::1",
        "localhost",
        # TradingView webhook IPs (add actual IPs here)
        "52.89.214.238",
        "34.212.75.30",
        "54.218.53.128",
        "52.32.178.7"
    ]
    
    all_allowed_ips = set(default_allowed + allowed_ips)
    
    try:
        client_ip = ipaddress.ip_address(ip)
        
        for allowed_ip in all_allowed_ips:
            try:
                # Handle CIDR notation
                if "/" in allowed_ip:
                    network = ipaddress.ip_network(allowed_ip, strict=False)
                    if client_ip in network:
                        return True
                else:
                    # Handle individual IP
                    if client_ip == ipaddress.ip_address(allowed_ip):
                        return True
            except ValueError:
                # Skip invalid IP addresses
                continue
        
        return False
        
    except ValueError:
        # Invalid IP address format
        return False

def verify_webhook_ip(request: Request, user: User) -> bool:
    """Verify that webhook request comes from allowed IP"""
    client_ip = get_client_ip(request)
    user_allowed_ips = user.get_allowed_ips()
    
    # Combine global settings with user-specific IPs
    all_allowed_ips = settings.allowed_ips + user_allowed_ips
    
    return is_ip_whitelisted(client_ip, all_allowed_ips)

def rate_limit_check(user: User, db: Session) -> bool:
    """Check if user has exceeded webhook rate limits"""
    # Reset counter if it's a new day
    now = datetime.utcnow()
    if user.last_webhook_reset:
        time_diff = now - user.last_webhook_reset.replace(tzinfo=None)
        if time_diff.days >= 1:
            user.webhook_requests_today = 0
            user.last_webhook_reset = now
            db.commit()
    
    # Check subscription limits
    if user.subscription and user.subscription.is_active():
        max_alerts = user.subscription.plan.max_alerts_per_day
        return user.webhook_requests_today < max_alerts
    
    # Default limit for users without subscription
    return user.webhook_requests_today < settings.webhook_rate_limit

def increment_webhook_counter(user: User, db: Session):
    """Increment user's webhook request counter"""
    user.webhook_requests_today += 1
    db.commit()

# Strategy UUID validation
def verify_strategy_access(strategy_uuid: str, user: User, db: Session):
    """Verify that user owns the strategy with given UUID"""
    from app.models.strategy import Strategy
    
    strategy = db.query(Strategy).filter(
        Strategy.uuid == strategy_uuid,
        Strategy.user_id == user.id
    ).first()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    if not strategy.can_trade():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Strategy is not active or broker account is disabled"
        )
    
    return strategy