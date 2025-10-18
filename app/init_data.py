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
            price=29.00,
            billing_cycle="monthly",
            max_alerts_per_day=50,
            max_strategies=3,
            max_broker_accounts=1,
            features=[
                "Up to 50 alerts per day",
                "3 trading strategies",
                "1 broker account",
                "Basic support",
                "Standard execution speed"
            ],
            trial_days=7,
            is_active=True
        ),
        SubscriptionPlan(
            name="Plus Plan",
            plan_type=PlanType.PLUS,
            price=79.00,
            billing_cycle="monthly",
            max_alerts_per_day=200,
            max_strategies=10,
            max_broker_accounts=3,
            features=[
                "Up to 200 alerts per day",
                "10 trading strategies",
                "3 broker accounts",
                "Priority support",
                "Fast execution speed",
                "Advanced analytics",
                "Risk management tools"
            ],
            trial_days=14,
            is_active=True,
            is_popular=True
        ),
        SubscriptionPlan(
            name="Ultra Plan",
            plan_type=PlanType.ULTRA,
            price=199.00,
            billing_cycle="monthly",
            max_alerts_per_day=1000,
            max_strategies=50,
            max_broker_accounts=10,
            features=[
                "Up to 1000 alerts per day",
                "Unlimited strategies",
                "10 broker accounts",
                "24/7 premium support",
                "Ultra-fast execution",
                "Advanced analytics & reporting",
                "Custom risk management",
                "Portfolio optimization",
                "API access",
                "White-label options"
            ],
            trial_days=30,
            is_active=True,
            is_enterprise=True
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