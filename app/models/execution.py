"""
Execution Model - Trade execution tracking
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class OrderType(str, enum.Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ExecutionType(str, enum.Enum):
    WEBHOOK = "webhook"  # Trade triggered by TradingView webhook
    MANUAL = "manual"    # Manual trade execution
    STOP_LOSS = "stop_loss"  # Automatic stop loss
    TAKE_PROFIT = "take_profit"  # Automatic take profit


class Execution(Base):
    __tablename__ = "executions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    broker_account_id = Column(Integer, ForeignKey("broker_accounts.id"), nullable=False)
    
    # Order identification
    broker_order_id = Column(String, nullable=True)  # Order ID from broker
    client_order_id = Column(String, nullable=True)   # Our internal order ID
    
    # Instrument
    symbol = Column(String, nullable=False)  # e.g., "BTCUSD", "AAPL", "EUR/USD"
    asset_class = Column(String, nullable=True)  # "crypto", "stock", "forex", etc.
    
    # Order details
    order_type = Column(Enum(OrderType), nullable=False)
    order_side = Column(Enum(OrderSide), nullable=False)
    execution_type = Column(Enum(ExecutionType), default=ExecutionType.WEBHOOK)
    
    # Quantities and prices
    quantity = Column(Float, nullable=False)  # Number of shares/contracts/coins
    requested_price = Column(Float, nullable=True)  # Price requested (for limit orders)
    executed_price = Column(Float, nullable=True)   # Actual execution price
    
    # Execution status
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    filled_quantity = Column(Float, default=0.0)
    remaining_quantity = Column(Float, default=0.0)
    
    # Financial details
    notional_value = Column(Float, nullable=True)  # Total value of trade (quantity × price)
    commission = Column(Float, default=0.0)        # Broker commission/fees
    slippage = Column(Float, default=0.0)          # Price slippage amount
    realized_pnl = Column(Float, default=0.0)      # Realized profit/loss
    
    # Risk management
    stop_loss_price = Column(Float, nullable=True)
    take_profit_price = Column(Float, nullable=True)
    max_slippage_allowed = Column(Float, nullable=True)
    
    # TradingView webhook data
    webhook_payload = Column(Text, nullable=True)  # Original webhook JSON payload
    webhook_timestamp = Column(DateTime(timezone=True), nullable=True)
    
    # Execution timing
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    executed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Test mode tracking
    is_test_execution = Column(Boolean, default=False)
    
    # Market conditions at execution time
    market_price_at_request = Column(Float, nullable=True)
    market_volatility = Column(Float, nullable=True)  # If available
    
    # Performance tracking
    is_winning_trade = Column(Boolean, nullable=True)  # Determined after position is closed
    holding_period_minutes = Column(Integer, nullable=True)  # How long position was held
    
    # Relationships
    user = relationship("User", back_populates="executions")
    strategy = relationship("Strategy", back_populates="executions")
    broker_account = relationship("BrokerAccount", back_populates="executions")

    def calculate_slippage(self) -> float:
        """Calculate slippage between requested and executed price"""
        if not self.requested_price or not self.executed_price:
            return 0.0
        
        if self.order_side == OrderSide.BUY:
            # For buy orders, positive slippage means we paid more than expected
            return (self.executed_price - self.requested_price) / self.requested_price
        else:
            # For sell orders, positive slippage means we received less than expected
            return (self.requested_price - self.executed_price) / self.requested_price

    def calculate_total_cost(self) -> float:
        """Calculate total cost including commission"""
        if not self.executed_price or not self.filled_quantity:
            return 0.0
        
        base_cost = self.executed_price * self.filled_quantity
        return base_cost + self.commission

    def update_execution_status(self, status: OrderStatus, filled_qty: float = None, 
                              executed_price: float = None, commission: float = None):
        """Update execution status with fill information"""
        self.status = status
        
        if filled_qty is not None:
            self.filled_quantity = filled_qty
            self.remaining_quantity = max(0, self.quantity - filled_qty)
        
        if executed_price is not None:
            self.executed_price = executed_price
            self.slippage = self.calculate_slippage()
            
        if commission is not None:
            self.commission = commission
        
        if status in [OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED]:
            self.executed_at = func.now()
            if self.executed_price:
                self.notional_value = self.executed_price * self.filled_quantity

    def is_profitable(self) -> bool:
        """Check if this trade was profitable"""
        return self.realized_pnl > 0 if self.realized_pnl else False

    def get_execution_summary(self) -> dict:
        """Get a summary of this execution"""
        return {
            "symbol": self.symbol,
            "side": self.order_side.value,
            "quantity": self.quantity,
            "filled_quantity": self.filled_quantity,
            "status": self.status.value,
            "requested_price": self.requested_price,
            "executed_price": self.executed_price,
            "slippage": self.slippage,
            "commission": self.commission,
            "realized_pnl": self.realized_pnl,
            "total_cost": self.calculate_total_cost(),
            "execution_type": self.execution_type.value,
            "is_test": self.is_test_execution
        }

    def __repr__(self):
        return f"<Execution {self.symbol} {self.order_side.value} {self.quantity} @ {self.executed_price}>"