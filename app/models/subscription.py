"""
Subscription and SubscriptionPlan Models - Payment and plan management
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class PlanType(str, enum.Enum):
    BASIC = "basic"
    PLUS = "plus"
    ULTRA = "ultra"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # "QuantPulse Basic", "QuantPulse Plus", etc.
    plan_type = Column(Enum(PlanType), nullable=False)
    description = Column(String, nullable=True)
    
    # Pricing
    price_monthly = Column(Float, nullable=False)  # USD
    stripe_price_id = Column(String, nullable=True)  # Stripe price ID
    
    # Limits
    max_strategies = Column(Integer, nullable=False)
    max_alerts_per_day = Column(Integer, nullable=False)
    
    # Features
    supports_crypto = Column(Boolean, default=True)
    supports_stocks = Column(Boolean, default=False)
    supports_forex = Column(Boolean, default=False)
    supports_mt4_mt5 = Column(Boolean, default=False)
    supports_prop_firms = Column(Boolean, default=False)
    
    # Trial
    trial_days = Column(Integer, default=30)
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    subscriptions = relationship("Subscription", back_populates="plan")

    def __repr__(self):
        return f"<SubscriptionPlan {self.name}>"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)  # One subscription per user
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=False)
    
    # Stripe integration
    stripe_subscription_id = Column(String, unique=True, nullable=True)
    stripe_customer_id = Column(String, nullable=True)
    
    # Status
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.TRIALING)
    
    # Billing period
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    
    # Trial
    trial_start = Column(DateTime(timezone=True), nullable=True)
    trial_end = Column(DateTime(timezone=True), nullable=True)
    
    # Usage tracking (daily limits)
    strategies_used_today = Column(Integer, default=0)
    alerts_used_today = Column(Integer, default=0)
    last_usage_reset = Column(DateTime(timezone=True), server_default=func.now())
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    canceled_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="subscription")
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")

    def is_trial_active(self) -> bool:
        """Check if trial period is still active"""
        if not self.trial_end:
            return False
        from datetime import datetime
        return datetime.utcnow() < self.trial_end.replace(tzinfo=None)

    def is_active(self) -> bool:
        """Check if subscription is active"""
        return self.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]

    def can_create_strategy(self) -> bool:
        """Check if user can create more strategies"""
        if not self.is_active():
            return False
        return self.strategies_used_today < self.plan.max_strategies

    def can_send_alert(self) -> bool:
        """Check if user can send more alerts today"""
        if not self.is_active():
            return False
        return self.alerts_used_today < self.plan.max_alerts_per_day

    def increment_strategy_usage(self):
        """Increment strategy usage counter"""
        self.strategies_used_today += 1

    def increment_alert_usage(self):
        """Increment alert usage counter"""
        self.alerts_used_today += 1

    def reset_daily_usage_if_needed(self):
        """Reset daily usage counters if a new day has started"""
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        if self.last_usage_reset and (now - self.last_usage_reset.replace(tzinfo=None)) >= timedelta(days=1):
            self.strategies_used_today = 0
            self.alerts_used_today = 0
            self.last_usage_reset = now

    def __repr__(self):
        return f"<Subscription {self.user.username} - {self.plan.name}>"