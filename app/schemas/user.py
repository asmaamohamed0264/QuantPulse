"""
Pydantic schemas pentru users
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """Roluri utilizatori"""
    USER = "user"
    ADMIN = "admin"
    PREMIUM = "premium"


class SubscriptionTier(str, Enum):
    """Niveluri de abonament"""
    FREE = "free"
    PRO = "pro" 
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class UserBase(BaseModel):
    """Schema de bază pentru user"""
    username: str = Field(..., min_length=3, max_length=50, description="Numele de utilizator")
    email: str = Field(..., description="Adresa de email")
    full_name: Optional[str] = Field(None, max_length=100, description="Numele complet")
    is_active: bool = Field(default=True, description="Utilizator activ")


class UserCreate(UserBase):
    """Schema pentru crearea unui utilizator nou"""
    password: str = Field(..., min_length=8, description="Parola (minim 8 caractere)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "trader123",
                "email": "trader@example.com", 
                "full_name": "John Trader",
                "password": "SecurePassword123!"
            }
        }


class UserRegister(UserCreate):
    """Schema pentru înregistrare utilizator nou (poate include câmpuri suplimentare)"""
    agree_terms: bool = Field(True, description="Acceptarea termenilor și condițiilor")
    newsletter: bool = Field(default=False, description="Abonare newsletter")


class UserLogin(BaseModel):
    """Schema pentru login"""
    username: str = Field(..., description="Username sau email")
    password: str = Field(..., description="Parola")
    remember_me: bool = Field(default=False, description="Ține-mă minte")


class UserUpdate(BaseModel):
    """Schema pentru actualizarea profilului utilizator"""
    email: Optional[str] = None
    full_name: Optional[str] = Field(None, max_length=100)
    timezone: Optional[str] = Field(None, description="Fusul orar al utilizatorului")
    notification_email: Optional[bool] = Field(None, description="Notificări prin email")
    notification_webhook: Optional[bool] = Field(None, description="Notificări prin webhook")


class UserChangePassword(BaseModel):
    """Schema pentru schimbarea parolei"""
    current_password: str = Field(..., description="Parola actuală")
    new_password: str = Field(..., min_length=8, description="Parola nouă (minim 8 caractere)")
    confirm_password: str = Field(..., description="Confirmarea parolei noi")


class UserResponse(UserBase):
    """Schema pentru răspunsul user"""
    id: int
    role: UserRole = UserRole.USER
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    is_verified: bool = False
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    
    # Statistici utilizator
    total_strategies: int = 0
    active_strategies: int = 0
    total_trades: int = 0
    successful_trades: int = 0
    total_profit_loss: float = 0.0
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "username": "trader123",
                "email": "trader@example.com",
                "full_name": "John Trader",
                "role": "user",
                "subscription_tier": "pro",
                "is_active": True,
                "is_verified": True,
                "total_strategies": 5,
                "active_strategies": 3,
                "total_trades": 150,
                "successful_trades": 120,
                "total_profit_loss": 2500.75,
                "created_at": "2024-01-01T09:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "last_login": "2024-01-15T08:15:00Z"
            }
        }


class UserProfile(UserResponse):
    """Schema extinsă pentru profilul utilizatorului"""
    timezone: Optional[str] = None
    notification_email: bool = True
    notification_webhook: bool = False
    webhook_requests_today: int = 0
    last_webhook_reset: Optional[datetime] = None
    allowed_ips: List[str] = []


class Token(BaseModel):
    """Schema pentru token JWT"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600  # în secunde


class TokenData(BaseModel):
    """Datele din token JWT"""
    username: Optional[str] = None
    user_id: Optional[int] = None
    role: Optional[UserRole] = None


class UserStats(BaseModel):
    """Statistici detaliate ale utilizatorului"""
    user_id: int
    total_strategies: int
    active_strategies: int
    inactive_strategies: int
    total_trades: int
    successful_trades: int
    failed_trades: int
    success_rate: float = 0.0
    total_profit_loss: float = 0.0
    average_profit_per_trade: float = 0.0
    best_trade: Optional[float] = None
    worst_trade: Optional[float] = None
    total_volume: float = 0.0
    last_trade_date: Optional[datetime] = None


class UserSettingsUpdate(BaseModel):
    """Schema pentru actualizarea setărilor utilizatorului"""
    timezone: Optional[str] = None
    notification_email: Optional[bool] = None
    notification_webhook: Optional[bool] = None
    risk_tolerance: Optional[str] = Field(None, pattern="^(low|medium|high)$")
    default_position_size: Optional[float] = Field(None, ge=0.01, le=100)
    max_daily_trades: Optional[int] = Field(None, ge=1, le=1000)


class UserSubscription(BaseModel):
    """Informații despre abonament"""
    user_id: int
    tier: SubscriptionTier
    is_active: bool = True
    started_at: datetime
    expires_at: Optional[datetime] = None
    auto_renew: bool = False
    
    # Limite abonament
    max_strategies: int = 1
    max_alerts_per_day: int = 10
    max_brokers: int = 1
    has_advanced_features: bool = False