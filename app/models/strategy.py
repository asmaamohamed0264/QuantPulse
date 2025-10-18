"""
Strategy Model - Trading strategy management
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum
import uuid


class StrategyStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


class MarketType(str, enum.Enum):
    CRYPTO = "crypto"
    STOCKS = "stocks"
    FOREX = "forex"
    FUTURES = "futures"
    OPTIONS = "options"


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    broker_account_id = Column(Integer, ForeignKey("broker_accounts.id"), nullable=False)
    
    # Strategy information
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    market_type = Column(Enum(MarketType), nullable=False)
    status = Column(Enum(StrategyStatus), default=StrategyStatus.ACTIVE)
    
    # TradingView webhook configuration
    webhook_url = Column(String, nullable=True)  # Generated webhook URL for this strategy
    webhook_secret = Column(String, nullable=True)  # Optional webhook secret
    
    # Trading settings
    default_position_size = Column(Float, nullable=True)  # Default position size in USD
    max_position_size = Column(Float, nullable=True)  # Maximum position size in USD
    allow_pyramiding = Column(Boolean, default=False)  # Allow position scaling
    max_slippage = Column(Float, default=0.01)  # Maximum allowed slippage (1%)
    
    # Risk management
    stop_loss_percent = Column(Float, nullable=True)  # Stop loss as percentage
    take_profit_percent = Column(Float, nullable=True)  # Take profit as percentage
    max_daily_loss = Column(Float, nullable=True)  # Maximum daily loss in USD
    
    # Active instruments (symbols this strategy trades)
    symbols = Column(Text, nullable=True)  # Comma-separated list of symbols
    
    # Performance tracking
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    total_profit_loss = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    
    # Usage limits
    trades_today = Column(Integer, default=0)
    last_trade_reset = Column(DateTime(timezone=True), server_default=func.now())
    
    # Test mode
    is_test_mode = Column(Boolean, default=False)  # If true, trades are simulated
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_trade_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="strategies")
    broker_account = relationship("BrokerAccount", back_populates="strategies")
    executions = relationship("Execution", back_populates="strategy")

    def get_symbols(self) -> list:
        """Get list of trading symbols"""
        if not self.symbols:
            return []
        return [symbol.strip().upper() for symbol in self.symbols.split(',') if symbol.strip()]

    def add_symbol(self, symbol: str):
        """Add a trading symbol to this strategy"""
        current_symbols = self.get_symbols()
        symbol = symbol.strip().upper()
        if symbol not in current_symbols:
            current_symbols.append(symbol)
            self.symbols = ','.join(current_symbols)

    def remove_symbol(self, symbol: str):
        """Remove a trading symbol from this strategy"""
        current_symbols = self.get_symbols()
        symbol = symbol.strip().upper()
        if symbol in current_symbols:
            current_symbols.remove(symbol)
            self.symbols = ','.join(current_symbols)

    def can_trade(self) -> bool:
        """Check if strategy can execute trades"""
        return self.status == StrategyStatus.ACTIVE and self.broker_account.is_active

    def update_performance(self, profit_loss: float, is_winning: bool):
        """Update strategy performance metrics"""
        self.total_trades += 1
        self.total_profit_loss += profit_loss
        
        if is_winning:
            self.winning_trades += 1

        # Update max drawdown if this is a loss
        if profit_loss < 0 and abs(profit_loss) > self.max_drawdown:
            self.max_drawdown = abs(profit_loss)

    def get_win_rate(self) -> float:
        """Calculate win rate percentage"""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100

    def generate_webhook_url(self, base_url: str) -> str:
        """Generate the webhook URL for this strategy"""
        return f"{base_url}/webhook/{self.uuid}"

    def reset_daily_trades_if_needed(self):
        """Reset daily trade counter if a new day has started"""
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        if self.last_trade_reset and (now - self.last_trade_reset.replace(tzinfo=None)) >= timedelta(days=1):
            self.trades_today = 0
            self.last_trade_reset = now

    def __repr__(self):
        return f"<Strategy {self.name} - {self.user.username}>"