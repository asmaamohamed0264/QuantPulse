"""
Webhook API endpoints for TradingView integration
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime
import json
from loguru import logger

from app.database import get_db
from app.models.user import User
from app.models.strategy import Strategy
from app.models.execution import Execution, OrderType, OrderSide, ExecutionType
from app.auth import get_client_ip, verify_webhook_ip, rate_limit_check, increment_webhook_counter
from app.services.broker_service import BrokerService
from app.services.trading_service import TradingService

router = APIRouter()

class WebhookPayload(BaseModel):
    """TradingView webhook payload model"""
    # Required fields
    action: str  # "buy" or "sell"
    symbol: str  # e.g., "BTCUSD", "AAPL"
    
    # Optional fields from TradingView
    price: Optional[float] = None
    quantity: Optional[float] = None
    strategy: Optional[str] = None  # Strategy name from TradingView
    exchange: Optional[str] = None
    asset_class: Optional[str] = "crypto"
    
    # Order configuration
    order_type: Optional[str] = "market"  # market, limit
    time_in_force: Optional[str] = "gtc"  # gtc, ioc, fok, day
    
    # Risk management
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    max_slippage: Optional[float] = None
    
    # Position sizing
    position_size_usd: Optional[float] = None
    position_size_percent: Optional[float] = None  # % of account equity
    
    # Test mode
    test_mode: Optional[bool] = False
    
    # Additional metadata
    timestamp: Optional[str] = None
    comment: Optional[str] = None
    
    @validator("action")
    def validate_action(cls, v):
        if v.lower() not in ["buy", "sell", "long", "short", "close"]:
            raise ValueError("Action must be 'buy', 'sell', 'long', 'short', or 'close'")
        return v.lower()
    
    @validator("order_type")
    def validate_order_type(cls, v):
        if v and v.lower() not in ["market", "limit"]:
            raise ValueError("Order type must be 'market' or 'limit'")
        return v.lower() if v else "market"
    
    @validator("symbol")
    def validate_symbol(cls, v):
        return v.upper().strip()


def get_strategy_by_uuid(strategy_uuid: str, db: Session) -> Strategy:
    """Get strategy by UUID and verify it's active"""
    strategy = db.query(Strategy).filter(Strategy.uuid == strategy_uuid).first()
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    return strategy


def verify_webhook_security(request: Request, strategy: Strategy, db: Session) -> User:
    """Verify webhook security (IP whitelist, rate limits, etc.)"""
    user = strategy.user
    
    # Check IP whitelist
    if not verify_webhook_ip(request, user):
        client_ip = get_client_ip(request)
        logger.warning(f"Webhook rejected: IP {client_ip} not whitelisted for user {user.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="IP address not whitelisted"
        )
    
    # Check rate limits
    if not rate_limit_check(user, db):
        logger.warning(f"Webhook rejected: Rate limit exceeded for user {user.username}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    # Check if strategy can trade
    if not strategy.can_trade():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Strategy is not active or broker account is disabled"
        )
    
    # Check subscription limits
    if user.subscription:
        user.subscription.reset_daily_usage_if_needed()
        if not user.subscription.can_send_alert():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Daily alert limit exceeded"
            )
    
    return user


async def process_webhook_background(
    strategy_id: int,
    execution_id: int,
    db: Session
):
    """Background task to process webhook execution"""
    try:
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        execution = db.query(Execution).filter(Execution.id == execution_id).first()
        
        if not strategy or not execution:
            logger.error(f"Strategy or execution not found: {strategy_id}, {execution_id}")
            return
        
        # Initialize trading service
        trading_service = TradingService(strategy.broker_account)
        
        # Execute the trade
        result = await trading_service.execute_order(execution)
        
        if result:
            logger.info(f"Webhook execution successful: {execution.symbol} {execution.order_side.value}")
            # Update strategy performance
            if result.get("realized_pnl"):
                is_winning = result["realized_pnl"] > 0
                strategy.update_performance(result["realized_pnl"], is_winning)
                db.commit()
        else:
            logger.error(f"Webhook execution failed: {execution.symbol} {execution.order_side.value}")
            
    except Exception as e:
        logger.error(f"Background webhook processing error: {e}")


@router.post("/webhook/{strategy_uuid}")
async def handle_webhook(
    strategy_uuid: str,
    payload: WebhookPayload,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Handle TradingView webhook signals
    
    This endpoint receives webhook signals from TradingView and executes trades
    based on the strategy configuration.
    """
    logger.info(f"Received webhook for strategy: {strategy_uuid}")
    
    # Get strategy and verify access
    strategy = get_strategy_by_uuid(strategy_uuid, db)
    
    # Security checks
    user = verify_webhook_security(request, strategy, db)
    
    # Increment webhook counter
    increment_webhook_counter(user, db)
    if user.subscription:
        user.subscription.increment_alert_usage()
        db.commit()
    
    # Log the webhook payload
    logger.info(f"Webhook payload: {payload.dict()}")
    
    # Validate symbol is allowed for this strategy
    strategy_symbols = strategy.get_symbols()
    if strategy_symbols and payload.symbol not in strategy_symbols:
        logger.warning(f"Symbol {payload.symbol} not allowed for strategy {strategy.name}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Symbol {payload.symbol} not allowed for this strategy"
        )
    
    # Create execution record
    execution = Execution(
        user_id=user.id,
        strategy_id=strategy.id,
        broker_account_id=strategy.broker_account_id,
        symbol=payload.symbol,
        asset_class=payload.asset_class,
        order_type=OrderType.MARKET if payload.order_type == "market" else OrderType.LIMIT,
        order_side=OrderSide.BUY if payload.action in ["buy", "long"] else OrderSide.SELL,
        execution_type=ExecutionType.WEBHOOK,
        quantity=payload.quantity or strategy.default_position_size or 100,
        requested_price=payload.price,
        webhook_payload=json.dumps(payload.dict()),
        webhook_timestamp=datetime.utcnow(),
        stop_loss_price=payload.stop_loss,
        take_profit_price=payload.take_profit,
        max_slippage_allowed=payload.max_slippage or strategy.max_slippage,
        is_test_execution=payload.test_mode or strategy.is_test_mode
    )
    
    # Save execution to database
    db.add(execution)
    db.commit()
    db.refresh(execution)
    
    # If test mode, return immediately
    if execution.is_test_execution:
        logger.info(f"Test mode execution created: {execution.id}")
        return {
            "status": "success",
            "message": "Test execution created",
            "execution_id": execution.id,
            "symbol": payload.symbol,
            "action": payload.action,
            "test_mode": True
        }
    
    # Queue background task for actual execution
    background_tasks.add_task(
        process_webhook_background,
        strategy.id,
        execution.id,
        db
    )
    
    # Update strategy counters
    strategy.trades_today += 1
    strategy.last_trade_at = datetime.utcnow()
    db.commit()
    
    return {
        "status": "success",
        "message": "Webhook received and processing",
        "execution_id": execution.id,
        "symbol": payload.symbol,
        "action": payload.action,
        "test_mode": False
    }


@router.get("/webhook/{strategy_uuid}/status")
async def webhook_status(
    strategy_uuid: str,
    db: Session = Depends(get_db)
):
    """
    Get webhook status and configuration for a strategy
    """
    strategy = get_strategy_by_uuid(strategy_uuid, db)
    
    return {
        "strategy_uuid": strategy_uuid,
        "strategy_name": strategy.name,
        "status": strategy.status.value,
        "is_active": strategy.can_trade(),
        "broker_account": strategy.broker_account.get_display_name(),
        "allowed_symbols": strategy.get_symbols(),
        "trades_today": strategy.trades_today,
        "test_mode": strategy.is_test_mode,
        "webhook_url": f"/api/v1/webhook/{strategy_uuid}",
        "user_limits": {
            "alerts_used_today": strategy.user.subscription.alerts_used_today if strategy.user.subscription else 0,
            "max_alerts_per_day": strategy.user.subscription.plan.max_alerts_per_day if strategy.user.subscription else 100
        } if strategy.user.subscription else None
    }


@router.post("/webhook/{strategy_uuid}/test")
async def test_webhook(
    strategy_uuid: str,
    payload: WebhookPayload,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Test webhook endpoint without executing actual trades
    """
    # Force test mode
    payload.test_mode = True
    
    # Use the main webhook handler
    return await handle_webhook(strategy_uuid, payload, request, BackgroundTasks(), db)