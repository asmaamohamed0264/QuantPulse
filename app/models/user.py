"""
User Model - Authentication and user management
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from passlib.context import CryptContext
from app.database import Base
import uuid

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # IP whitelist for webhook access (JSON array as string)
    allowed_ips = Column(Text, nullable=True)  # Stored as comma-separated values
    
    # API limits
    webhook_requests_today = Column(Integer, default=0)
    last_webhook_reset = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    strategies = relationship("Strategy", back_populates="user")
    executions = relationship("Execution", back_populates="user")
    broker_accounts = relationship("BrokerAccount", back_populates="user")

    def set_password(self, password: str):
        """Hash and set password"""
        self.hashed_password = pwd_context.hash(password)
    
    def check_password(self, password: str) -> bool:
        """Check if provided password matches the hashed password"""
        return pwd_context.verify(password, self.hashed_password)

    def get_allowed_ips(self) -> list:
        """Get list of allowed IPs"""
        if not self.allowed_ips:
            return []
        return [ip.strip() for ip in self.allowed_ips.split(',') if ip.strip()]

    def add_allowed_ip(self, ip: str):
        """Add IP to whitelist"""
        current_ips = self.get_allowed_ips()
        if ip not in current_ips:
            current_ips.append(ip)
            self.allowed_ips = ','.join(current_ips)

    def remove_allowed_ip(self, ip: str):
        """Remove IP from whitelist"""
        current_ips = self.get_allowed_ips()
        if ip in current_ips:
            current_ips.remove(ip)
            self.allowed_ips = ','.join(current_ips)

    def __repr__(self):
        return f"<User {self.username}>"