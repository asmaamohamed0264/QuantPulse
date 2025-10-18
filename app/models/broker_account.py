"""
BrokerAccount Model - Broker integration management
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class BrokerType(str, enum.Enum):
    ALPACA = "alpaca"
    INTERACTIVE_BROKERS = "interactive_brokers"
    TD_AMERITRADE = "td_ameritrade"
    BINANCE = "binance"
    COINBASE = "coinbase"
    MT4 = "mt4"
    MT5 = "mt5"


class BrokerAccount(Base):
    __tablename__ = "broker_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Account information
    name = Column(String, nullable=False)  # User-friendly name (e.g., "Main Trading Account")
    broker_type = Column(Enum(BrokerType), nullable=False)
    
    # API credentials (encrypted)
    api_key = Column(Text, nullable=False)  # Encrypted API key
    api_secret = Column(Text, nullable=False)  # Encrypted API secret
    api_passphrase = Column(Text, nullable=True)  # For some brokers (e.g., Coinbase Pro)
    
    # Connection settings
    is_paper_trading = Column(Boolean, default=True)  # Paper/live trading mode
    base_url = Column(String, nullable=True)  # Custom API endpoint if needed
    
    # Account status
    is_active = Column(Boolean, default=True)
    is_connected = Column(Boolean, default=False)  # Last connection status
    last_connection_test = Column(DateTime(timezone=True), nullable=True)
    connection_error = Column(Text, nullable=True)  # Last connection error message
    
    # Account balance tracking
    last_balance_check = Column(DateTime(timezone=True), nullable=True)
    cash_balance = Column(Float, default=0.0)
    total_equity = Column(Float, default=0.0)
    buying_power = Column(Float, default=0.0)
    
    # Trading limits
    max_daily_loss = Column(Float, nullable=True)  # Maximum daily loss in USD
    daily_loss_today = Column(Float, default=0.0)
    last_loss_reset = Column(DateTime(timezone=True), server_default=func.now())
    
    # PDT (Pattern Day Trading) tracking
    day_trades_count = Column(Integer, default=0)  # For accounts under $25k
    last_day_trade_reset = Column(DateTime(timezone=True), server_default=func.now())
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="broker_accounts")
    strategies = relationship("Strategy", back_populates="broker_account")
    executions = relationship("Execution", back_populates="broker_account")

    def can_trade(self) -> bool:
        """Check if account can execute trades"""
        if not self.is_active or not self.is_connected:
            return False
        
        # Check daily loss limit
        if self.max_daily_loss and self.daily_loss_today >= self.max_daily_loss:
            return False
            
        return True

    def can_day_trade(self) -> bool:
        """Check if account can execute day trades (PDT rule)"""
        # Accounts with >$25k equity can day trade freely
        if self.total_equity >= 25000:
            return True
            
        # Accounts under $25k are limited to 3 day trades in 5 business days
        return self.day_trades_count < 3

    def update_balance(self, cash: float, equity: float, buying_power: float):
        """Update account balance information"""
        self.cash_balance = cash
        self.total_equity = equity
        self.buying_power = buying_power
        self.last_balance_check = func.now()

    def add_daily_loss(self, loss_amount: float):
        """Add to daily loss tracking"""
        if loss_amount > 0:  # Only track actual losses
            self.daily_loss_today += loss_amount

    def reset_daily_counters_if_needed(self):
        """Reset daily counters if a new day has started"""
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        
        # Reset daily loss
        if self.last_loss_reset and (now - self.last_loss_reset.replace(tzinfo=None)) >= timedelta(days=1):
            self.daily_loss_today = 0.0
            self.last_loss_reset = now
        
        # Reset day trades count (5 business days)
        if self.last_day_trade_reset and (now - self.last_day_trade_reset.replace(tzinfo=None)) >= timedelta(days=5):
            self.day_trades_count = 0
            self.last_day_trade_reset = now

    def get_display_name(self) -> str:
        """Get user-friendly display name"""
        mode = "Paper" if self.is_paper_trading else "Live"
        return f"{self.name} ({self.broker_type.value.title()}) - {mode}"

    def is_crypto_broker(self) -> bool:
        """Check if this is a crypto-focused broker"""
        return self.broker_type in [BrokerType.BINANCE, BrokerType.COINBASE]

    def is_stock_broker(self) -> bool:
        """Check if this is a stock/forex broker"""
        return self.broker_type in [BrokerType.ALPACA, BrokerType.INTERACTIVE_BROKERS, BrokerType.TD_AMERITRADE]

    def is_mt_broker(self) -> bool:
        """Check if this is an MT4/MT5 broker"""
        return self.broker_type in [BrokerType.MT4, BrokerType.MT5]

    def __repr__(self):
        return f"<BrokerAccount {self.name} - {self.broker_type.value}>"