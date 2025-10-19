"""
Enhanced Broker Accounts API - Implementation of missing functionality
"""
from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.broker_account import BrokerAccount, BrokerType
from app.auth import get_current_user_optional
from app.brokers import get_broker_client
from loguru import logger

router = APIRouter()


@router.post("/test", response_model=dict)
async def test_broker_connection(
    request: Request,
    user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Test broker connection before creating account"""
    try:
        # Check if user is authenticated
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Get data from request body
        data = await request.json()
        
        # Validate required fields
        if not data.get("broker_type") or not data.get("api_key") or not data.get("secret_key"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required fields: broker_type, api_key, secret_key"
            )
        
        # Validate broker type
        try:
            broker_type_enum = BrokerType(data["broker_type"].lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid broker type. Supported: alpaca, interactive_brokers"
            )
        
        # Test connection with broker
        broker_client = get_broker_client(
            broker_type_enum, 
            data["api_key"], 
            data["secret_key"], 
            data.get("paper_trading", True)
        )
        
        # Test the connection
        account_info = broker_client.get_account()
        
        return {
            "success": True,
            "message": "Connection successful",
            "account_info": {
                "account_number": account_info.get("account_number"),
                "cash": account_info.get("cash", 0),
                "buying_power": account_info.get("buying_power", 0),
                "portfolio_value": account_info.get("portfolio_value", 0)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Broker connection test failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Connection failed: {str(e)}"
        )


@router.post("/", response_model=dict)
async def create_broker_account(
    request: Request,
    name: str = Form(...),
    broker_type: str = Form(...),  # "alpaca" or "interactive_brokers"
    api_key: str = Form(...),
    api_secret: str = Form(...),
    is_paper_trading: bool = Form(True),
    user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Create new broker account connection"""
    
    # Validate broker type
    try:
        broker_type_enum = BrokerType(broker_type.lower())
    except ValueError:
        if request.headers.get("accept") == "application/json":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid broker type. Supported: alpaca, interactive_brokers"
            )
        return RedirectResponse(
            url="/brokers?error=Invalid broker type",
            status_code=302
        )
    
    try:
        # Test connection with broker
        broker_client = get_broker_client(broker_type_enum, api_key, api_secret, is_paper_trading)
        account_info = broker_client.get_account()
        
        # Create broker account
        broker_account = BrokerAccount(
            user_id=user.id,
            name=name,
            broker_type=broker_type_enum,
            api_key=api_key,
            api_secret=api_secret,
            is_paper_trading=is_paper_trading,
            is_connected=True,
            is_active=True,
            account_number=account_info.get("account_number"),
            cash_balance=float(account_info.get("cash", 0)),
            buying_power=float(account_info.get("buying_power", 0)),
            total_equity=float(account_info.get("portfolio_value", 0))
        )
        
        db.add(broker_account)
        db.commit()
        db.refresh(broker_account)
        
        if request.headers.get("accept") == "application/json":
            return {
                "success": True,
                "message": "Broker account connected successfully",
                "broker_id": broker_account.id
            }
        
        return RedirectResponse(url="/brokers?success=Broker connected", status_code=302)
        
    except Exception as e:
        if request.headers.get("accept") == "application/json":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to connect to broker: {str(e)}"
            )
        
        return RedirectResponse(
            url="/brokers?error=Failed to connect broker",
            status_code=302
        )


@router.put("/{broker_id}", response_model=dict)
async def update_broker_account(
    broker_id: int,
    request: Request,
    name: str = Form(None),
    api_key: str = Form(None),
    api_secret: str = Form(None),
    is_active: bool = Form(None),
    user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Update broker account settings"""
    
    broker_account = db.query(BrokerAccount).filter(
        BrokerAccount.id == broker_id,
        BrokerAccount.user_id == user.id
    ).first()
    
    if not broker_account:
        if request.headers.get("accept") == "application/json":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Broker account not found"
            )
        return RedirectResponse(
            url="/brokers?error=Broker account not found",
            status_code=302
        )
    
    try:
        # Update fields if provided
        if name is not None:
            broker_account.name = name
        if api_key is not None:
            broker_account.api_key = api_key
        if api_secret is not None:
            broker_account.api_secret = api_secret
        if is_active is not None:
            broker_account.is_active = is_active
        
        # Test connection if credentials changed
        if api_key is not None or api_secret is not None:
            try:
                broker_client = get_broker_client(
                    broker_account.broker_type,
                    broker_account.api_key,
                    broker_account.api_secret,
                    broker_account.is_paper_trading
                )
                account_info = broker_client.get_account()
                broker_account.is_connected = True
                
                # Update account info
                broker_account.cash_balance = float(account_info.get("cash", 0))
                broker_account.buying_power = float(account_info.get("buying_power", 0))
                broker_account.total_equity = float(account_info.get("portfolio_value", 0))
                
            except Exception as e:
                broker_account.is_connected = False
        
        broker_account.updated_at = datetime.utcnow()
        db.commit()
        
        if request.headers.get("accept") == "application/json":
            return {
                "success": True,
                "message": "Broker account updated successfully"
            }
        
        return RedirectResponse(url="/brokers?success=Broker updated", status_code=302)
        
    except Exception as e:
        if request.headers.get("accept") == "application/json":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update broker account"
            )
        
        return RedirectResponse(
            url="/brokers?error=Failed to update broker",
            status_code=302
        )


@router.delete("/{broker_id}", response_model=dict)
async def delete_broker_account(
    broker_id: int,
    user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Delete broker account"""
    
    broker_account = db.query(BrokerAccount).filter(
        BrokerAccount.id == broker_id,
        BrokerAccount.user_id == user.id
    ).first()
    
    if not broker_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Broker account not found"
        )
    
    try:
        # Check if broker is used by any strategies
        from app.models.strategy import Strategy
        strategies_count = db.query(Strategy).filter(
            Strategy.broker_account_id == broker_id
        ).count()
        
        if strategies_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete broker account. It's used by {strategies_count} strategy(s)."
            )
        
        db.delete(broker_account)
        db.commit()
        
        return {"success": True, "message": "Broker account deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete broker account"
        )


@router.post("/{broker_id}/test-connection", response_model=dict)
async def test_broker_connection(
    broker_id: int,
    user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Test broker account connection"""
    
    broker_account = db.query(BrokerAccount).filter(
        BrokerAccount.id == broker_id,
        BrokerAccount.user_id == user.id
    ).first()
    
    if not broker_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Broker account not found"
        )
    
    try:
        # Test connection
        broker_client = get_broker_client(
            broker_account.broker_type,
            broker_account.api_key,
            broker_account.api_secret,
            broker_account.is_paper_trading
        )
        account_info = broker_client.get_account()
        
        # Update connection status and account info
        broker_account.is_connected = True
        broker_account.cash_balance = float(account_info.get("cash", 0))
        broker_account.buying_power = float(account_info.get("buying_power", 0))
        broker_account.total_equity = float(account_info.get("portfolio_value", 0))
        broker_account.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "success": True,
            "message": "Connection successful",
            "account_info": {
                "account_number": account_info.get("account_number"),
                "cash_balance": broker_account.cash_balance,
                "buying_power": broker_account.buying_power,
                "total_equity": broker_account.total_equity
            }
        }
        
    except Exception as e:
        # Update connection status
        broker_account.is_connected = False
        broker_account.updated_at = datetime.utcnow()
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Connection failed: {str(e)}"
        )


@router.post("/{broker_id}/sync", response_model=dict)
async def sync_broker_account(
    broker_id: int,
    user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Sync broker account data"""
    
    broker_account = db.query(BrokerAccount).filter(
        BrokerAccount.id == broker_id,
        BrokerAccount.user_id == user.id
    ).first()
    
    if not broker_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Broker account not found"
        )
    
    if not broker_account.is_connected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Broker account is not connected"
        )
    
    try:
        # Sync account data
        broker_client = get_broker_client(
            broker_account.broker_type,
            broker_account.api_key,
            broker_account.api_secret,
            broker_account.is_paper_trading
        )
        
        account_info = broker_client.get_account()
        positions = broker_client.get_positions()
        
        # Update account info
        broker_account.cash_balance = float(account_info.get("cash", 0))
        broker_account.buying_power = float(account_info.get("buying_power", 0))
        broker_account.total_equity = float(account_info.get("portfolio_value", 0))
        broker_account.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "success": True,
            "message": "Account data synchronized",
            "account_data": {
                "cash_balance": broker_account.cash_balance,
                "buying_power": broker_account.buying_power,
                "total_equity": broker_account.total_equity,
                "positions_count": len(positions) if positions else 0
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}"
        )


@router.get("/{broker_id}/positions", response_model=dict)
async def get_broker_positions(
    broker_id: int,
    user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Get current positions for broker account"""
    
    broker_account = db.query(BrokerAccount).filter(
        BrokerAccount.id == broker_id,
        BrokerAccount.user_id == user.id
    ).first()
    
    if not broker_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Broker account not found"
        )
    
    if not broker_account.is_connected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Broker account is not connected"
        )
    
    try:
        broker_client = get_broker_client(
            broker_account.broker_type,
            broker_account.api_key,
            broker_account.api_secret,
            broker_account.is_paper_trading
        )
        
        positions = broker_client.get_positions()
        
        return {
            "success": True,
            "broker_name": broker_account.name,
            "positions": positions or []
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get positions: {str(e)}"
        )