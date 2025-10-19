"""
Pydantic schemas pentru brokers
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class BrokerStatus(str, Enum):
    """Status pentru conexiunea cu brokerul"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"  
    CONNECTED = "connected"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class BrokerType(str, Enum):
    """Tipuri de brokeri suportați"""
    ALPACA = "alpaca"
    INTERACTIVE_BROKERS = "interactive_brokers"
    TD_AMERITRADE = "td_ameritrade"
    BINANCE = "binance"
    COINBASE = "coinbase"


class BrokerBase(BaseModel):
    """Schema de bază pentru broker"""
    name: str = Field(..., description="Numele brokerului")
    broker_type: BrokerType = Field(..., description="Tipul brokerului")
    is_paper_trading: bool = Field(default=True, description="Paper trading sau live trading")
    is_active: bool = Field(default=True, description="Broker activ")
    max_positions: int = Field(default=10, ge=1, le=100, description="Numărul maxim de poziții")
    risk_per_trade: float = Field(default=1.0, ge=0.1, le=10.0, description="Riscul per tranzacție (%)")


class BrokerCreate(BrokerBase):
    """Schema pentru crearea unui broker nou"""
    api_key: str = Field(..., description="Cheia API a brokerului")
    api_secret: str = Field(..., description="Secretul API a brokerului")
    base_url: Optional[str] = Field(None, description="URL-ul de bază pentru API")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Alpaca Paper Trading",
                "broker_type": "alpaca",
                "is_paper_trading": True,
                "api_key": "PKGU5Z2MR2QF6CZN3KSHLW3T6Z",
                "api_secret": "9XS54h71XE74Tny73Wqg5PgNZ6rn9YVi",
                "base_url": "https://paper-api.alpaca.markets",
                "max_positions": 5,
                "risk_per_trade": 2.0
            }
        }


class BrokerUpdate(BaseModel):
    """Schema pentru actualizarea unui broker"""
    name: Optional[str] = None
    is_paper_trading: Optional[bool] = None
    is_active: Optional[bool] = None
    max_positions: Optional[int] = Field(None, ge=1, le=100)
    risk_per_trade: Optional[float] = Field(None, ge=0.1, le=10.0)
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    base_url: Optional[str] = None


class BrokerResponse(BrokerBase):
    """Schema pentru răspunsul broker"""
    id: int
    user_id: int
    status: BrokerStatus = BrokerStatus.DISCONNECTED
    last_connection: Optional[datetime] = None
    total_trades: int = 0
    successful_trades: int = 0
    total_profit_loss: float = 0.0
    created_at: datetime
    updated_at: datetime
    
    # Informații suplimentare despre cont
    account_info: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 1,
                "name": "Alpaca Paper Trading",
                "broker_type": "alpaca",
                "is_paper_trading": True,
                "is_active": True,
                "status": "connected",
                "max_positions": 5,
                "risk_per_trade": 2.0,
                "total_trades": 15,
                "successful_trades": 12,
                "total_profit_loss": 245.50,
                "last_connection": "2024-01-15T10:30:00Z",
                "created_at": "2024-01-01T09:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }


class BrokerConnection(BaseModel):
    """Schema pentru testarea conexiunii cu brokerul"""
    broker_id: int
    test_connection: bool = True


class BrokerConnectionResult(BaseModel):
    """Rezultatul testului de conexiune"""
    success: bool
    status: BrokerStatus
    message: str
    account_info: Optional[Dict[str, Any]] = None
    error_details: Optional[str] = None


class BrokerAccountInfo(BaseModel):
    """Informații despre contul brokerului"""
    account_id: str
    buying_power: float
    cash: float
    portfolio_value: float
    day_trade_count: int
    pattern_day_trader: bool
    currency: str = "USD"
    last_updated: datetime


class BrokerPosition(BaseModel):
    """Poziție deschisă la broker"""
    symbol: str
    qty: float
    market_value: float
    cost_basis: float
    unrealized_pl: float
    unrealized_plpc: float
    current_price: float
    side: str  # "long" sau "short"


class BrokerOrder(BaseModel):
    """Comanda la broker"""
    id: str
    symbol: str
    qty: float
    side: str  # "buy" sau "sell"
    order_type: str  # "market", "limit", "stop"
    time_in_force: str  # "day", "gtc", "ioc", "fok"
    status: str
    filled_qty: float = 0
    filled_avg_price: Optional[float] = None
    submitted_at: datetime
    filled_at: Optional[datetime] = None