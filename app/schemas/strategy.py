from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class StrategyStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"
    STOPPED = "stopped"

class StrategyType(str, Enum):
    SCALPING = "scalping"
    SWING = "swing"
    DAY_TRADING = "day_trading"
    POSITION = "position"
    ARBITRAGE = "arbitrage"
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM = "momentum"
    CUSTOM = "custom"

class RiskManagement(BaseModel):
    max_position_size: float = Field(..., gt=0, description="Maximum position size per trade")
    stop_loss_percentage: Optional[float] = Field(None, ge=0, le=100, description="Stop loss percentage")
    take_profit_percentage: Optional[float] = Field(None, ge=0, description="Take profit percentage")
    max_daily_loss: Optional[float] = Field(None, gt=0, description="Maximum daily loss limit")
    risk_per_trade: float = Field(default=2.0, ge=0.1, le=10.0, description="Risk percentage per trade")

class TradingParameters(BaseModel):
    symbols: List[str] = Field(..., min_items=1, description="List of trading symbols")
    timeframe: str = Field(default="1m", description="Trading timeframe")
    indicators: Dict[str, Any] = Field(default_factory=dict, description="Technical indicators configuration")
    entry_conditions: Dict[str, Any] = Field(default_factory=dict, description="Entry signal conditions")
    exit_conditions: Dict[str, Any] = Field(default_factory=dict, description="Exit signal conditions")
    max_open_positions: int = Field(default=5, ge=1, description="Maximum number of open positions")

class BacktestResults(BaseModel):
    total_return: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    profit_factor: Optional[float] = None
    total_trades: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class StrategyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Strategy name")
    description: Optional[str] = Field(None, max_length=500, description="Strategy description")
    strategy_type: StrategyType = Field(..., description="Type of trading strategy")
    status: StrategyStatus = Field(default=StrategyStatus.INACTIVE, description="Strategy status")
    risk_management: RiskManagement = Field(..., description="Risk management parameters")
    trading_parameters: TradingParameters = Field(..., description="Trading parameters")
    
class StrategyCreate(StrategyBase):
    """Schema for creating a new strategy"""
    pass

class StrategyUpdate(BaseModel):
    """Schema for updating an existing strategy"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    strategy_type: Optional[StrategyType] = None
    status: Optional[StrategyStatus] = None
    risk_management: Optional[RiskManagement] = None
    trading_parameters: Optional[TradingParameters] = None

class StrategyResponse(StrategyBase):
    """Schema for strategy response"""
    id: int = Field(..., description="Strategy unique identifier")
    user_id: int = Field(..., description="User ID who owns the strategy")
    created_at: datetime = Field(..., description="Strategy creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    is_active: bool = Field(default=False, description="Whether strategy is currently active")
    backtest_results: Optional[BacktestResults] = Field(None, description="Backtesting results")
    
    class Config:
        from_attributes = True

class StrategyList(BaseModel):
    """Schema for listing strategies"""
    strategies: List[StrategyResponse]
    total: int
    page: int
    size: int

class StrategyExecutionLog(BaseModel):
    """Schema for strategy execution logs"""
    id: int
    strategy_id: int
    timestamp: datetime
    action: str
    symbol: str
    quantity: float
    price: float
    result: str
    profit_loss: Optional[float] = None
    
    class Config:
        from_attributes = True

# Performance metrics schemas
class PerformanceMetrics(BaseModel):
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_profit_loss: float = 0.0
    average_profit_per_trade: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    calmar_ratio: Optional[float] = None

class StrategyPerformanceResponse(BaseModel):
    strategy_id: int
    strategy_name: str
    performance_metrics: PerformanceMetrics
    period_start: datetime
    period_end: datetime
    
    class Config:
        from_attributes = True