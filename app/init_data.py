"""
Database initialization script
Creates default subscription plans and other required data
"""
from sqlalchemy.orm import Session
from app.database import engine, SessionLocal
from app.models.subscription import SubscriptionPlan, PlanType
from loguru import logger


def init_subscription_plans(db: Session):
    """Initialize default subscription plans"""
    
    # Check if plans already exist
    existing_plans = db.query(SubscriptionPlan).count()
    if existing_plans > 0:
        logger.info("Subscription plans already exist, skipping initialization")
        return
    
    # Create default plans
    plans = [
        SubscriptionPlan(
            name="Basic Plan",
            plan_type=PlanType.BASIC,
            price_monthly=29.00,
            max_alerts_per_day=50,
            max_strategies=3,
            supports_crypto=True,
            supports_stocks=False,
            supports_forex=False,
            supports_mt4_mt5=False,
            supports_prop_firms=False,
            trial_days=7,
            is_active=True
        ),
        SubscriptionPlan(
            name="Plus Plan",
            plan_type=PlanType.PLUS,
            price_monthly=79.00,
            max_alerts_per_day=200,
            max_strategies=10,
            supports_crypto=True,
            supports_stocks=True,
            supports_forex=True,
            supports_mt4_mt5=False,
            supports_prop_firms=False,
            trial_days=14,
            is_active=True
        ),
        SubscriptionPlan(
            name="Ultra Plan",
            plan_type=PlanType.ULTRA,
            price_monthly=199.00,
            max_alerts_per_day=1000,
            max_strategies=50,
            supports_crypto=True,
            supports_stocks=True,
            supports_forex=True,
            supports_mt4_mt5=True,
            supports_prop_firms=True,
            trial_days=30,
            is_active=True
        )
    ]
    
    for plan in plans:
        db.add(plan)
    
    db.commit()
    logger.info(f"Created {len(plans)} subscription plans")


def init_database():
    """Initialize database with default data"""
    logger.info("Initializing database with default data...")
    
    db = SessionLocal()
    try:
        init_subscription_plans(db)
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_database()