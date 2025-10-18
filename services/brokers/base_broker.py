"""
Base Broker Interface
Abstract base class defining the interface that all brokers must implement
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class AssetClass(Enum):
    STOCKS = "stocks"
    CRYPTO = "crypto"
    FOREX = "forex"
    OPTIONS = "options"
    FUTURES = "futures"


@dataclass
class Position:
    symbol: str
    quantity: float
    side: OrderSide
    market_value: float
    unrealized_pnl: float
    avg_entry_price: float
    asset_class: AssetClass


@dataclass
class OrderResult:
    order_id: str
    symbol: str
    quantity: float
    side: OrderSide
    order_type: OrderType
    status: OrderStatus
    filled_price: Optional[float] = None
    filled_quantity: Optional[float] = None
    timestamp: Optional[datetime] = None
    broker_response: Optional[Dict[str, Any]] = None


@dataclass
class AccountInfo:
    account_id: str
    cash_balance: float
    buying_power: float
    total_portfolio_value: float
    currency: str = "USD"
    day_trades_remaining: Optional[int] = None


class BaseBroker(ABC):
    """Abstract base class for all broker implementations"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.is_connected = False
        self.account_info: Optional[AccountInfo] = None
    
    @property
    @abstractmethod
    def broker_name(self) -> str:
        """Return the broker name"""
        pass
    
    @property
    @abstractmethod
    def supported_asset_classes(self) -> List[AssetClass]:
        """Return list of supported asset classes"""
        pass
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Connect to the broker API
        Returns True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Disconnect from the broker API
        Returns True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_account_info(self) -> AccountInfo:
        """
        Get account information
        Returns AccountInfo object with current account details
        """
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """
        Get all current positions
        Returns list of Position objects
        """
        pass
    
    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        quantity: float,
        side: OrderSide,
        order_type: OrderType,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "day",
        **kwargs
    ) -> OrderResult:
        """
        Place a trading order
        
        Args:
            symbol: Trading symbol (e.g., "AAPL", "BTCUSD")
            quantity: Order quantity
            side: Order side (buy/sell)
            order_type: Order type (market/limit/stop/stop_limit)
            limit_price: Limit price for limit orders
            stop_price: Stop price for stop orders
            time_in_force: Time in force ("day", "gtc", etc.)
            **kwargs: Additional broker-specific parameters
            
        Returns:
            OrderResult object with order details
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an existing order
        
        Args:
            order_id: The order ID to cancel
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str) -> OrderResult:
        """
        Get the status of an order
        
        Args:
            order_id: The order ID to check
            
        Returns:
            OrderResult object with current order status
        """
        pass
    
    @abstractmethod
    async def validate_symbol(self, symbol: str) -> bool:
        """
        Validate if a trading symbol is supported
        
        Args:
            symbol: Trading symbol to validate
            
        Returns:
            True if symbol is valid and tradeable, False otherwise
        """
        pass
    
    async def health_check(self) -> bool:
        """
        Perform a health check on the broker connection
        Returns True if broker is healthy and ready to trade
        """
        if not self.is_connected:
            return False
        
        try:
            account_info = await self.get_account_info()
            return account_info is not None
        except Exception:
            return False
    
    def __str__(self) -> str:
        return f"{self.broker_name} ({'Connected' if self.is_connected else 'Disconnected'})"