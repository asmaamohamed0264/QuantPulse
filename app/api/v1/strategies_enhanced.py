"""
Enhanced Strategies API - Implementation of missing functionality
"""
from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid

from app.database import get_db
from app.models.user import User
from app.models.strategy import Strategy, StrategyStatus
from app.models.broker_account import BrokerAccount
from app.auth import get_current_user
from app.schemas.strategy import StrategyCreate, StrategyUpdate, StrategyResponse

router = APIRouter()


@router.post("/", response_model=dict)
async def create_strategy(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    symbol_list: str = Form(...),  # Comma-separated symbols
    broker_account_id: int = Form(...),
    risk_per_trade: float = Form(1.0),
    max_trades_per_day: int = Form(10),
    trading_hours_start: str = Form("09:30"),
    trading_hours_end: str = Form("16:00"),
    is_active: bool = Form(True),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new trading strategy"""
    
    # Validate broker account belongs to user
    broker_account = db.query(BrokerAccount).filter(
        BrokerAccount.id == broker_account_id,
        BrokerAccount.user_id == user.id
    ).first()
    
    if not broker_account:
        if request.headers.get("accept") == "application/json":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Broker account not found"
            )
        return RedirectResponse(
            url="/strategies?error=Broker account not found",
            status_code=302
        )
    
    # Process symbol list
    symbols = [s.strip().upper() for s in symbol_list.split(",") if s.strip()]
    
    try:
        # Create strategy
        strategy = Strategy(
            uuid=str(uuid.uuid4()),
            user_id=user.id,
            name=name,
            description=description,
            symbol_list=",".join(symbols),
            broker_account_id=broker_account_id,
            status=StrategyStatus.ACTIVE if is_active else StrategyStatus.PAUSED,
            risk_per_trade=risk_per_trade,
            max_trades_per_day=max_trades_per_day,
            trading_hours_start=trading_hours_start,
            trading_hours_end=trading_hours_end
        )
        
        db.add(strategy)
        db.commit()
        db.refresh(strategy)
        
        if request.headers.get("accept") == "application/json":
            return {
                "success": True,
                "message": "Strategy created successfully",
                "strategy_id": strategy.id
            }
        
        return RedirectResponse(url="/strategies?success=Strategy created", status_code=302)
        
    except Exception as e:
        if request.headers.get("accept") == "application/json":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create strategy"
            )
        
        return RedirectResponse(
            url="/strategies?error=Failed to create strategy",
            status_code=302
        )


@router.put("/{strategy_id}", response_model=dict)
async def update_strategy(
    strategy_id: int,
    request: Request,
    name: str = Form(None),
    description: str = Form(None),
    symbol_list: str = Form(None),
    broker_account_id: int = Form(None),
    risk_per_trade: float = Form(None),
    max_trades_per_day: int = Form(None),
    trading_hours_start: str = Form(None),
    trading_hours_end: str = Form(None),
    is_active: bool = Form(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update trading strategy"""
    
    strategy = db.query(Strategy).filter(
        Strategy.id == strategy_id,
        Strategy.user_id == user.id
    ).first()
    
    if not strategy:
        if request.headers.get("accept") == "application/json":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )
        return RedirectResponse(
            url="/strategies?error=Strategy not found",
            status_code=302
        )
    
    try:
        # Update fields if provided
        if name is not None:
            strategy.name = name
        if description is not None:
            strategy.description = description
        if symbol_list is not None:
            symbols = [s.strip().upper() for s in symbol_list.split(",") if s.strip()]
            strategy.symbol_list = ",".join(symbols)
        if broker_account_id is not None:
            # Validate broker account
            broker_account = db.query(BrokerAccount).filter(
                BrokerAccount.id == broker_account_id,
                BrokerAccount.user_id == user.id
            ).first()
            if broker_account:
                strategy.broker_account_id = broker_account_id
        if risk_per_trade is not None:
            strategy.risk_per_trade = risk_per_trade
        if max_trades_per_day is not None:
            strategy.max_trades_per_day = max_trades_per_day
        if trading_hours_start is not None:
            strategy.trading_hours_start = trading_hours_start
        if trading_hours_end is not None:
            strategy.trading_hours_end = trading_hours_end
        if is_active is not None:
            strategy.status = StrategyStatus.ACTIVE if is_active else StrategyStatus.PAUSED
        
        strategy.updated_at = datetime.utcnow()
        db.commit()
        
        if request.headers.get("accept") == "application/json":
            return {
                "success": True,
                "message": "Strategy updated successfully"
            }
        
        return RedirectResponse(url="/strategies?success=Strategy updated", status_code=302)
        
    except Exception as e:
        if request.headers.get("accept") == "application/json":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update strategy"
            )
        
        return RedirectResponse(
            url="/strategies?error=Failed to update strategy",
            status_code=302
        )


@router.delete("/{strategy_id}", response_model=dict)
async def delete_strategy(
    strategy_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete trading strategy"""
    
    strategy = db.query(Strategy).filter(
        Strategy.id == strategy_id,
        Strategy.user_id == user.id
    ).first()
    
    if not strategy:
        if request.headers.get("accept") == "application/json":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "Strategy not found"}
        )
    
    try:
        db.delete(strategy)
        db.commit()
        
        return {"success": True, "message": "Strategy deleted successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete strategy"
        )


@router.post("/{strategy_id}/toggle", response_model=dict)
async def toggle_strategy(
    strategy_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toggle strategy active/inactive status"""
    
    strategy = db.query(Strategy).filter(
        Strategy.id == strategy_id,
        Strategy.user_id == user.id
    ).first()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    # Toggle status
    if strategy.status == StrategyStatus.ACTIVE:
        strategy.status = StrategyStatus.PAUSED
        message = "Strategy paused"
    else:
        strategy.status = StrategyStatus.ACTIVE
        message = "Strategy activated"
    
    strategy.updated_at = datetime.utcnow()
    db.commit()
    
    return {
        "success": True,
        "message": message,
        "status": strategy.status.value
    }


@router.get("/{strategy_id}/performance", response_model=dict)
async def get_strategy_performance(
    strategy_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get strategy performance metrics"""
    
    strategy = db.query(Strategy).filter(
        Strategy.id == strategy_id,
        Strategy.user_id == user.id
    ).first()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    # Calculate performance metrics
    performance = {
        "total_trades": strategy.total_trades,
        "winning_trades": strategy.winning_trades,
        "losing_trades": strategy.losing_trades,
        "win_rate": strategy.get_win_rate(),
        "total_pnl": strategy.total_pnl,
        "avg_win": strategy.avg_win,
        "avg_loss": strategy.avg_loss,
        "profit_factor": strategy.get_profit_factor(),
        "sharpe_ratio": strategy.get_sharpe_ratio(),
        "max_drawdown": strategy.max_drawdown,
        "trades_today": strategy.trades_today,
        "last_trade_at": strategy.last_trade_at
    }
    
    return {
        "success": True,
        "strategy_name": strategy.name,
        "performance": performance
    }