"""
Payments API - Stripe Integration
Handles subscription payments, webhooks, and billing
"""
from fastapi import APIRouter, Request, Depends, HTTPException, status, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, Any
import stripe
import hmac
import hashlib
import json
from datetime import datetime, timedelta

from app.database import get_db
from app.models.user import User
from app.models.subscription import Subscription, SubscriptionPlan, PlanType
from app.auth import get_current_user
from app.config import settings
from app.services.stripe_service import StripeService

router = APIRouter()

# Initialize Stripe
stripe_service = StripeService()


@router.post("/create-checkout-session")
async def create_checkout_session(
    plan_type: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create Stripe checkout session for subscription"""
    
    try:
        # Get subscription plan
        plan = db.query(SubscriptionPlan).filter(
            SubscriptionPlan.plan_type == PlanType(plan_type.upper()),
            SubscriptionPlan.is_active == True
        ).first()
        
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription plan not found"
            )
        
        # Create checkout session
        session = stripe_service.create_checkout_session(
            customer_email=current_user.email,
            price_id=plan.stripe_price_id,
            success_url=f"{settings.frontend_url}/subscription?success=true",
            cancel_url=f"{settings.frontend_url}/subscription?canceled=true",
            metadata={
                "user_id": current_user.id,
                "plan_id": plan.id
            }
        )
        
        return {"checkout_url": session.url}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create checkout session: {str(e)}"
        )


@router.post("/create-portal-session")
async def create_portal_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create Stripe customer portal session"""
    
    try:
        # Get user's subscription
        subscription = db.query(Subscription).filter(
            Subscription.user_id == current_user.id,
            Subscription.status.in_(["active", "trialing"])
        ).first()
        
        if not subscription or not subscription.stripe_customer_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found"
            )
        
        # Create portal session
        session = stripe_service.create_customer_portal_session(
            customer_id=subscription.stripe_customer_id,
            return_url=f"{settings.frontend_url}/subscription"
        )
        
        return {"portal_url": session.url}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create portal session: {str(e)}"
        )


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Stripe webhook events"""
    
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        # Verify webhook signature
        if not stripe_service.verify_webhook_signature(payload, sig_header):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook signature"
            )
        
        # Parse event
        event = json.loads(payload)
        
        # Handle different event types
        if event['type'] == 'checkout.session.completed':
            await handle_checkout_completed(event['data']['object'], db)
            
        elif event['type'] == 'customer.subscription.created':
            await handle_subscription_created(event['data']['object'], db)
            
        elif event['type'] == 'customer.subscription.updated':
            await handle_subscription_updated(event['data']['object'], db)
            
        elif event['type'] == 'customer.subscription.deleted':
            await handle_subscription_deleted(event['data']['object'], db)
            
        elif event['type'] == 'invoice.payment_succeeded':
            await handle_payment_succeeded(event['data']['object'], db)
            
        elif event['type'] == 'invoice.payment_failed':
            await handle_payment_failed(event['data']['object'], db)
        
        return {"received": True}
        
    except stripe.error.SignatureVerificationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature"
        )
    except Exception as e:
        # Log error but return 200 to acknowledge receipt
        print(f"Webhook error: {str(e)}")
        return {"received": True, "error": str(e)}


async def handle_checkout_completed(session: Dict[str, Any], db: Session):
    """Handle successful checkout completion"""
    
    metadata = session.get('metadata', {})
    user_id = metadata.get('user_id')
    plan_id = metadata.get('plan_id')
    
    if not user_id or not plan_id:
        return
    
    # Get user and plan
    user = db.query(User).filter(User.id == user_id).first()
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
    
    if not user or not plan:
        return
    
    # Update or create subscription
    subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    
    if subscription:
        # Update existing subscription
        subscription.stripe_customer_id = session['customer']
        subscription.stripe_subscription_id = session['subscription']
        subscription.plan_id = plan_id
        subscription.status = "active"
        subscription.current_period_start = datetime.utcnow()
        subscription.current_period_end = datetime.utcnow() + timedelta(days=30)  # Monthly billing
        subscription.updated_at = datetime.utcnow()
    else:
        # Create new subscription
        subscription = Subscription(
            user_id=user_id,
            plan_id=plan_id,
            stripe_customer_id=session['customer'],
            stripe_subscription_id=session['subscription'],
            status="active",
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30)
        )
        db.add(subscription)
    
    db.commit()


async def handle_subscription_created(subscription: Dict[str, Any], db: Session):
    """Handle subscription creation"""
    
    # Find subscription by Stripe subscription ID
    db_subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == subscription['id']
    ).first()
    
    if db_subscription:
        db_subscription.status = subscription['status']
        db_subscription.current_period_start = datetime.fromtimestamp(subscription['current_period_start'])
        db_subscription.current_period_end = datetime.fromtimestamp(subscription['current_period_end'])
        db_subscription.updated_at = datetime.utcnow()
        db.commit()


async def handle_subscription_updated(subscription: Dict[str, Any], db: Session):
    """Handle subscription updates"""
    
    db_subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == subscription['id']
    ).first()
    
    if db_subscription:
        db_subscription.status = subscription['status']
        db_subscription.current_period_start = datetime.fromtimestamp(subscription['current_period_start'])
        db_subscription.current_period_end = datetime.fromtimestamp(subscription['current_period_end'])
        db_subscription.updated_at = datetime.utcnow()
        db.commit()


async def handle_subscription_deleted(subscription: Dict[str, Any], db: Session):
    """Handle subscription cancellation"""
    
    db_subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == subscription['id']
    ).first()
    
    if db_subscription:
        db_subscription.status = "canceled"
        db_subscription.canceled_at = datetime.utcnow()
        db_subscription.updated_at = datetime.utcnow()
        db.commit()


async def handle_payment_succeeded(invoice: Dict[str, Any], db: Session):
    """Handle successful payment"""
    
    subscription_id = invoice.get('subscription')
    if not subscription_id:
        return
    
    db_subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == subscription_id
    ).first()
    
    if db_subscription:
        # Update subscription to active if payment succeeded
        db_subscription.status = "active"
        db_subscription.updated_at = datetime.utcnow()
        db.commit()
        
        # TODO: Send payment confirmation email


async def handle_payment_failed(invoice: Dict[str, Any], db: Session):
    """Handle failed payment"""
    
    subscription_id = invoice.get('subscription')
    if not subscription_id:
        return
    
    db_subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == subscription_id
    ).first()
    
    if db_subscription:
        # Mark subscription as past due
        db_subscription.status = "past_due"
        db_subscription.updated_at = datetime.utcnow()
        db.commit()
        
        # TODO: Send payment failure notification


@router.get("/plans")
async def get_subscription_plans(db: Session = Depends(get_db)):
    """Get all active subscription plans"""
    
    plans = db.query(SubscriptionPlan).filter(SubscriptionPlan.is_active == True).all()
    
    return {
        "plans": [
            {
                "id": plan.id,
                "name": plan.name,
                "plan_type": plan.plan_type.value,
                "price": float(plan.price),
                "currency": plan.currency,
                "interval": plan.billing_interval,
                "features": plan.features,
                "max_alerts_per_day": plan.max_alerts_per_day,
                "max_strategies": plan.max_strategies,
                "trial_days": plan.trial_days,
                "stripe_price_id": plan.stripe_price_id
            }
            for plan in plans
        ]
    }


@router.get("/subscription")
async def get_user_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's subscription details"""
    
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        return {"subscription": None}
    
    return {
        "subscription": {
            "id": subscription.id,
            "status": subscription.status,
            "plan": {
                "name": subscription.plan.name,
                "plan_type": subscription.plan.plan_type.value,
                "price": float(subscription.plan.price),
                "features": subscription.plan.features
            },
            "current_period_start": subscription.current_period_start,
            "current_period_end": subscription.current_period_end,
            "trial_end": subscription.trial_end,
            "canceled_at": subscription.canceled_at,
            "stripe_customer_id": subscription.stripe_customer_id,
            "stripe_subscription_id": subscription.stripe_subscription_id
        }
    }