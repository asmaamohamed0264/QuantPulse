"""
QuantPulse Configuration Settings
"""
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import validator


class Settings(BaseSettings):
    # App settings
    app_name: str = "QuantPulse"
    debug: bool = False
    version: str = "1.0.0"
    
    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    allowed_ips: List[str] = []
    
    # Database
    database_url: str = "postgresql://quantpulse:password@localhost/quantpulse"
    database_url_async: Optional[str] = None
    
    @validator("database_url_async", pre=True)
    def assemble_async_db_connection(cls, v: Optional[str], values: dict) -> str:
        if isinstance(v, str):
            return v
        return values.get("database_url", "").replace("postgresql://", "postgresql+asyncpg://")
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # Alpaca Trading
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_paper: bool = True
    alpaca_base_url: str = "https://paper-api.alpaca.markets"
    
    # Stripe
    stripe_publishable_key: str = ""
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    
    # Subscription Plans
    basic_plan_price_id: str = ""
    plus_plan_price_id: str = ""
    ultra_plan_price_id: str = ""
    
    # Rate Limiting
    webhook_rate_limit: int = 100  # requests per hour
    
    # CORS
    cors_origins: str = "https://quantpulse.qub3.uk,https://www.quantpulse.qub3.uk"
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "quantpulse.log"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore unknown environment variables


# Global settings instance
settings = Settings()