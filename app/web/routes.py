"""
Web Routes for QuantPulse Frontend
Serves HTML templates and handles web-based authentication
"""

from fastapi import APIRouter, Depends, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
import json
from datetime import datetime, timedelta

from app.database import get_db
from app.models.user import User
from app.models.strategy import Strategy
from app.models.broker_account import BrokerAccount
from app.models.subscription import Subscription, SubscriptionPlan, PlanType
from app.auth import get_current_user_optional, create_access_token
from app.config import settings

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_user_context(user: Optional[User]) -> dict:
    """Get common user context for templates"""
    if not user:
        return {"user": None}
    
    context = {
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "subscription_plan": None,
            "trial_days_remaining": None,
            "alert_limit": None
        }
    }
    
    # Add subscription info
    if user.subscription:
        context["user"]["subscription_plan"] = user.subscription.plan.plan_type.value
        if user.subscription.trial_end:
            days_remaining = (user.subscription.trial_end.replace(tzinfo=None) - datetime.utcnow()).days
            context["user"]["trial_days_remaining"] = max(0, days_remaining)
        context["user"]["alert_limit"] = user.subscription.plan.max_alerts_per_day
    
    return context


@router.get("/", response_class=HTMLResponse)
async def homepage(request: Request, user: Optional[User] = Depends(get_current_user_optional)):
    """Homepage with pricing and features"""
    context = get_user_context(user)
    context["request"] = request
    return templates.TemplateResponse("index.html", context)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, user: Optional[User] = Depends(get_current_user_optional)):
    """Login page"""
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    return templates.TemplateResponse("login.html", {"request": request, "user": None})


@router.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    remember: bool = Form(False),
    db: Session = Depends(get_db)
):
    """Handle login form submission"""
    from loguru import logger
    logger.info(f"Login attempt for email: {email}")
    
    user = db.query(User).filter(User.email == email).first()
    logger.info(f"User found: {user is not None}")
    
    if not user or not user.check_password(password):
        error_context = {
            "request": request,
            "user": None,
            "error": "Invalid email or password"
        }
        return templates.TemplateResponse("login.html", error_context, status_code=400)
    
    if not user.is_active:
        error_context = {
            "request": request,
            "user": None,
            "error": "Account is deactivated"
        }
        return templates.TemplateResponse("login.html", error_context, status_code=400)
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(days=30) if remember else timedelta(minutes=settings.access_token_expire_minutes)
    )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Redirect to dashboard with token in cookie
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=2592000 if remember else 1800,  # 30 days or 30 minutes
        secure=not settings.debug
    )
    
    return response


@router.get("/test-db")
async def test_database(db: Session = Depends(get_db)):
    """Test database connection and user count"""
    try:
        user_count = db.query(User).count()
        plan_count = db.query(SubscriptionPlan).count()
        return {
            "status": "success",
            "user_count": user_count,
            "plan_count": plan_count,
            "message": "Database connection working"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Database error: {str(e)}"
        }


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, user: Optional[User] = Depends(get_current_user_optional)):
    """Registration page"""
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    return templates.TemplateResponse("register.html", {"request": request, "user": None})


@router.post("/register")
async def register_submit(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    plan: str = Form("plus"),
    terms: bool = Form(False),
    db: Session = Depends(get_db)
):
    """Handle registration form submission"""
    from loguru import logger
    logger.info(f"Registration attempt for email: {email}")
    errors = []
    
    # Validation
    if not terms:
        errors.append("You must agree to the Terms of Service")
    
    if password != confirm_password:
        errors.append("Passwords do not match")
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    # Check if email exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        errors.append("Email address is already registered")
    
    if errors:
        error_context = {
            "request": request,
            "user": None,
            "errors": errors
        }
        return templates.TemplateResponse("register.html", error_context, status_code=400)
    
    try:
        # Create user
        base_username = email.split('@')[0]  # Use email prefix as base username
        username = base_username
        
        # Check if username already exists and make it unique
        counter = 1
        while db.query(User).filter(User.username == username).first():
            username = f"{base_username}{counter}"
            counter += 1
            
        logger.info(f"Creating user with username: {username}")
        
        new_user = User(
            email=email,
            username=username,
            full_name=f"{first_name} {last_name}",
            is_active=True,
            is_verified=False
        )
        new_user.set_password(password)
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        logger.info(f"User created successfully with ID: {new_user.id}")
        
        # Create subscription with trial
        plan_mapping = {
            "basic": PlanType.BASIC,
            "plus": PlanType.PLUS,
            "ultra": PlanType.ULTRA
        }
        
        subscription_plan = db.query(SubscriptionPlan).filter(
            SubscriptionPlan.plan_type == plan_mapping.get(plan, PlanType.PLUS)
        ).first()
        
        if subscription_plan:
            trial_end = datetime.utcnow() + timedelta(days=subscription_plan.trial_days)
            
            subscription = Subscription(
                user_id=new_user.id,
                plan_id=subscription_plan.id,
                trial_start=datetime.utcnow(),
                trial_end=trial_end
            )
            
            db.add(subscription)
            db.commit()
        
        # Auto-login after registration
        access_token = create_access_token(
            data={"sub": new_user.email},
            expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
        )
        
        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie(
            key="access_token",
            value=f"Bearer {access_token}",
            httponly=True,
            max_age=1800,
            secure=not settings.debug
        )
        
        return response
        
    except Exception as e:
        # Log the error for debugging
        from loguru import logger
        logger.error(f"Registration failed: {str(e)}")
        logger.error(f"Registration error details: {type(e).__name__}")
        
        error_context = {
            "request": request,
            "user": None,
            "errors": [f"Registration failed: {str(e)}"]
        }
        return templates.TemplateResponse("register.html", error_context, status_code=500)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user: User = Depends(get_current_user_optional), db: Session = Depends(get_db)):
    """Main dashboard"""
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    # Get user stats
    strategies = db.query(Strategy).filter(Strategy.user_id == user.id).all()
    brokers = db.query(BrokerAccount).filter(BrokerAccount.user_id == user.id).all()
    
    stats = {
        "total_alerts": sum(s.trades_today for s in strategies),
        "successful_trades": sum(s.winning_trades for s in strategies),
        "active_strategies": len([s for s in strategies if s.status.value == "active"]),
        "alerts_today": sum(s.trades_today for s in strategies)
    }
    
    # Recent alerts (mock data for now)
    recent_alerts = []
    
    # Account info
    account = {
        "portfolio_value": sum(b.total_equity for b in brokers) if brokers else 0
    }
    
    # Performance data (mock)
    performance_dates = json.dumps([f"Day {i}" for i in range(1, 8)])
    performance_values = json.dumps([10000 + i * 100 for i in range(7)])
    
    context = get_user_context(user)
    context.update({
        "request": request,
        "stats": stats,
        "recent_alerts": recent_alerts,
        "account": account,
        "brokers": [{"name": b.name, "is_connected": b.is_connected, "account_type": "Paper" if b.is_paper_trading else "Live"} for b in brokers],
        "performance_dates": performance_dates,
        "performance_values": performance_values
    })
    
    return templates.TemplateResponse("dashboard.html", context)


@router.get("/strategies", response_class=HTMLResponse)
async def strategies_page(request: Request, user: User = Depends(get_current_user_optional), db: Session = Depends(get_db)):
    """Strategies management page"""
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    strategies = db.query(Strategy).filter(Strategy.user_id == user.id).all()
    brokers = db.query(BrokerAccount).filter(BrokerAccount.user_id == user.id).all()
    
    stats = {
        "total_strategies": len(strategies),
        "active_strategies": len([s for s in strategies if s.status.value == "active"]),
        "paused_strategies": len([s for s in strategies if s.status.value == "paused"]),
        "total_executions": sum(s.total_trades for s in strategies)
    }
    
    # Format strategies for template
    formatted_strategies = []
    for strategy in strategies:
        formatted_strategies.append({
            "id": strategy.id,
            "name": strategy.name,
            "description": strategy.description,
            "symbols": strategy.get_symbols(),
            "broker_account": {"name": strategy.broker_account.name},
            "is_active": strategy.status.value == "active",
            "alerts_today": strategy.trades_today,
            "success_rate": round(strategy.get_win_rate()),
            "last_alert_at": strategy.last_trade_at
        })
    
    context = get_user_context(user)
    context.update({
        "request": request,
        "strategies": formatted_strategies,
        "stats": stats,
        "user_brokers": [{"id": b.id, "name": b.name, "account_type": "Paper" if b.is_paper_trading else "Live"} for b in brokers]
    })
    
    return templates.TemplateResponse("strategies.html", context)


@router.get("/brokers", response_class=HTMLResponse)
async def brokers_page(request: Request, user: User = Depends(get_current_user_optional), db: Session = Depends(get_db)):
    """Broker accounts page"""
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    brokers = db.query(BrokerAccount).filter(BrokerAccount.user_id == user.id).all()
    
    # Format brokers for template
    formatted_brokers = []
    for broker in brokers:
        formatted_brokers.append({
            "id": broker.id,
            "name": broker.name,
            "broker_type": broker.broker_type.value,
            "is_connected": broker.is_connected,
            "is_paper_trading": broker.is_paper_trading,
            "is_active": broker.is_active,
            "account_balance": broker.cash_balance,
            "buying_power": broker.buying_power,
            "updated_at": broker.updated_at
        })
    
    context = get_user_context(user)
    context.update({
        "request": request,
        "brokers": formatted_brokers
    })
    
    return templates.TemplateResponse("brokers.html", context)


@router.get("/pricing", response_class=HTMLResponse)
async def pricing_page(request: Request, user: Optional[User] = Depends(get_current_user_optional), db: Session = Depends(get_db)):
    """Pricing page with subscription plans"""
    
    # Get all active subscription plans
    plans = db.query(SubscriptionPlan).filter(SubscriptionPlan.is_active == True).all()
    
    context = get_user_context(user)
    context.update({
        "request": request,
        "plans": plans
    })
    
    return templates.TemplateResponse("pricing.html", context)


@router.get("/subscription", response_class=HTMLResponse)
async def subscription_page(request: Request, user: User = Depends(get_current_user_optional), db: Session = Depends(get_db)):
    """User subscription management page"""
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    # Get current subscription
    subscription = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    
    # Get all available plans
    plans = db.query(SubscriptionPlan).filter(SubscriptionPlan.is_active == True).all()
    
    context = get_user_context(user)
    context.update({
        "request": request,
        "subscription": subscription,
        "plans": plans
    })
    
    return templates.TemplateResponse("subscription.html", context)


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, user: User = Depends(get_current_user_optional)):
    """User settings page"""
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    context = get_user_context(user)
    context["request"] = request
    
    return templates.TemplateResponse("settings.html", context)


@router.get("/alerts", response_class=HTMLResponse)
async def alerts_page(request: Request, user: User = Depends(get_current_user_optional), db: Session = Depends(get_db)):
    """Alerts history page"""
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    # Get recent executions/alerts (limit to 50 for performance)
    from app.models.execution import Execution
    recent_executions = db.query(Execution).filter(
        Execution.user_id == user.id
    ).order_by(Execution.created_at.desc()).limit(50).all()
    
    # Format executions for template
    formatted_executions = []
    for execution in recent_executions:
        formatted_executions.append({
            "id": execution.id,
            "strategy_name": execution.strategy.name,
            "symbol": execution.symbol,
            "action": execution.action.value,
            "quantity": execution.quantity,
            "price": execution.price,
            "status": execution.status.value,
            "created_at": execution.created_at,
            "pnl": execution.pnl,
            "broker_name": execution.strategy.broker_account.name
        })
    
    context = get_user_context(user)
    context.update({
        "request": request,
        "executions": formatted_executions
    })
    
    return templates.TemplateResponse("alerts.html", context)


@router.get("/contact", response_class=HTMLResponse)
async def contact_page(request: Request, user: Optional[User] = Depends(get_current_user_optional)):
    """Contact page"""
    context = get_user_context(user)
    context["request"] = request
    return templates.TemplateResponse("contact.html", context)


@router.get("/logout")
async def logout():
    """Logout and clear session"""
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("access_token")
    return response
