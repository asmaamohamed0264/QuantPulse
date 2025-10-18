"""
Alpaca Broker Implementation
Implements the BaseBroker interface for Alpaca Markets trading
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, StopOrderRequest, StopLimitOrderRequest
from alpaca.trading.enums import OrderSide as AlpacaOrderSide, OrderType as AlpacaOrderType, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest, CryptoLatestQuoteRequest

from .base_broker import (
    BaseBroker, OrderType, OrderSide, OrderStatus, AssetClass,
    Position, OrderResult, AccountInfo
)

logger = logging.getLogger(__name__)


class AlpacaBroker(BaseBroker):
    """Alpaca broker implementation for automated trading"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        self.api_key = config.get('api_key')
        self.secret_key = config.get('secret_key')
        self.paper = config.get('paper', True)
        
        if not self.api_key or not self.secret_key:
            raise ValueError("Alpaca API key and secret key are required")
        
        # Initialize trading client
        self.client = TradingClient(
            api_key=self.api_key,
            secret_key=self.secret_key,
            paper=self.paper
        )
        
        # Initialize data clients for quotes
        self.stock_data_client = StockHistoricalDataClient(
            api_key=self.api_key,
            secret_key=self.secret_key
        )
        
        self.crypto_data_client = CryptoHistoricalDataClient(
            api_key=self.api_key,
            secret_key=self.secret_key
        )
        
        logger.info(f"Alpaca broker initialized ({'paper' if self.paper else 'live'} trading)")
    
    @property
    def broker_name(self) -> str:
        return "Alpaca"
    
    @property
    def supported_asset_classes(self) -> List[AssetClass]:
        return [AssetClass.STOCKS, AssetClass.CRYPTO]
    
    async def connect(self) -> bool:
        """Connect to Alpaca API"""
        try:
            account = self.client.get_account()
            self.is_connected = True
            self.account_info = await self.get_account_info()
            logger.info(f"Successfully connected to Alpaca API. Account ID: {account.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Alpaca API: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from Alpaca API"""
        self.is_connected = False
        self.account_info = None
        logger.info("Disconnected from Alpaca API")
        return True
    
    async def get_account_info(self) -> AccountInfo:
        """Get account information"""
        try:
            account = self.client.get_account()
            return AccountInfo(
                account_id=str(account.id),
                cash_balance=float(account.cash),
                buying_power=float(account.buying_power),
                total_portfolio_value=float(account.equity),
                currency="USD",
                day_trades_remaining=getattr(account, 'daytrade_buying_power', None)
            )
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            raise
    
    async def get_positions(self) -> List[Position]:
        """Get all current positions"""
        try:
            positions = self.client.get_all_positions()
            position_list = []
            
            for pos in positions:
                qty = float(pos.qty)
                side = OrderSide.BUY if qty > 0 else OrderSide.SELL
                
                # Determine asset class based on symbol or use stocks as default
                asset_class = AssetClass.CRYPTO if self._is_crypto_symbol(pos.symbol) else AssetClass.STOCKS
                
                position_list.append(Position(
                    symbol=pos.symbol,
                    quantity=abs(qty),
                    side=side,
                    market_value=float(pos.market_value),
                    unrealized_pnl=float(pos.unrealized_pnl),
                    avg_entry_price=float(pos.avg_entry_price),
                    asset_class=asset_class
                ))
            
            return position_list
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            raise
    
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
        """Place a trading order"""
        try:
            # Convert to Alpaca enums
            alpaca_side = AlpacaOrderSide.BUY if side == OrderSide.BUY else AlpacaOrderSide.SELL
            
            # Map time in force
            tif_mapping = {
                "day": TimeInForce.DAY,
                "gtc": TimeInForce.GTC,
                "ioc": TimeInForce.IOC,
                "fok": TimeInForce.FOK
            }
            alpaca_tif = tif_mapping.get(time_in_force.lower(), TimeInForce.DAY)
            
            # Create appropriate order request
            if order_type == OrderType.MARKET:
                order_request = MarketOrderRequest(
                    symbol=symbol,
                    qty=quantity,
                    side=alpaca_side,
                    time_in_force=alpaca_tif
                )
            elif order_type == OrderType.LIMIT:
                if not limit_price:
                    raise ValueError("Limit price required for limit orders")
                order_request = LimitOrderRequest(
                    symbol=symbol,
                    qty=quantity,
                    side=alpaca_side,
                    time_in_force=alpaca_tif,
                    limit_price=limit_price
                )
            elif order_type == OrderType.STOP:
                if not stop_price:
                    raise ValueError("Stop price required for stop orders")
                order_request = StopOrderRequest(
                    symbol=symbol,
                    qty=quantity,
                    side=alpaca_side,
                    time_in_force=alpaca_tif,
                    stop_price=stop_price
                )
            elif order_type == OrderType.STOP_LIMIT:
                if not stop_price or not limit_price:
                    raise ValueError("Both stop price and limit price required for stop-limit orders")
                order_request = StopLimitOrderRequest(
                    symbol=symbol,
                    qty=quantity,
                    side=alpaca_side,
                    time_in_force=alpaca_tif,
                    stop_price=stop_price,
                    limit_price=limit_price
                )
            else:
                raise ValueError(f"Unsupported order type: {order_type}")
            
            # Submit order
            logger.info(f"Submitting Alpaca order: {symbol} {side.value} {quantity} {order_type.value}")
            order = self.client.submit_order(order_request)
            
            # Convert status
            status = self._convert_order_status(order.status.value)
            
            # Create result
            result = OrderResult(
                order_id=str(order.id),
                symbol=symbol,
                quantity=quantity,
                side=side,
                order_type=order_type,
                status=status,
                filled_price=float(order.filled_avg_price) if order.filled_avg_price else None,
                filled_quantity=float(order.filled_qty) if order.filled_qty else None,
                timestamp=order.submitted_at,
                broker_response={
                    "alpaca_order_id": str(order.id),
                    "client_order_id": str(order.client_order_id),
                    "submitted_at": str(order.submitted_at),
                    "filled_at": str(order.filled_at) if order.filled_at else None
                }
            )
            
            logger.info(f"Alpaca order submitted successfully: {order.id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to place Alpaca order: {e}")
            raise
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order"""
        try:
            self.client.cancel_order_by_id(order_id)
            logger.info(f"Alpaca order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel Alpaca order {order_id}: {e}")
            return False
    
    async def get_order_status(self, order_id: str) -> OrderResult:
        """Get the status of an order"""
        try:
            order = self.client.get_order_by_id(order_id)
            
            # Convert enums
            side = OrderSide.BUY if order.side == AlpacaOrderSide.BUY else OrderSide.SELL
            order_type = self._convert_order_type(order.order_type.value)
            status = self._convert_order_status(order.status.value)
            
            return OrderResult(
                order_id=str(order.id),
                symbol=order.symbol,
                quantity=float(order.qty),
                side=side,
                order_type=order_type,
                status=status,
                filled_price=float(order.filled_avg_price) if order.filled_avg_price else None,
                filled_quantity=float(order.filled_qty) if order.filled_qty else None,
                timestamp=order.submitted_at,
                broker_response={
                    "alpaca_order_id": str(order.id),
                    "client_order_id": str(order.client_order_id),
                    "submitted_at": str(order.submitted_at),
                    "filled_at": str(order.filled_at) if order.filled_at else None
                }
            )
        except Exception as e:
            logger.error(f"Failed to get Alpaca order status {order_id}: {e}")
            raise
    
    async def validate_symbol(self, symbol: str) -> bool:
        """Validate if a trading symbol is supported"""
        try:
            # Try to get a quote for the symbol
            if self._is_crypto_symbol(symbol):
                request = CryptoLatestQuoteRequest(symbol_or_symbols=[symbol])
                quotes = self.crypto_data_client.get_crypto_latest_quote(request)
            else:
                request = StockLatestQuoteRequest(symbol_or_symbols=[symbol])
                quotes = self.stock_data_client.get_stock_latest_quote(request)
            
            return symbol in quotes and quotes[symbol] is not None
        except Exception as e:
            logger.warning(f"Symbol validation failed for {symbol}: {e}")
            return False
    
    def _is_crypto_symbol(self, symbol: str) -> bool:
        """Check if symbol is a cryptocurrency"""
        crypto_suffixes = ['USD', 'USDT', 'BTC', 'ETH']
        crypto_symbols = ['BTC', 'ETH', 'LTC', 'BCH', 'DOGE', 'ADA', 'DOT', 'UNI', 'LINK']
        
        # Check if it's a common crypto symbol
        if any(symbol.startswith(crypto) for crypto in crypto_symbols):
            return True
        
        # Check if it has crypto-like suffix
        if any(symbol.endswith(suffix) for suffix in crypto_suffixes):
            return True
            
        return False
    
    def _convert_order_status(self, alpaca_status: str) -> OrderStatus:
        """Convert Alpaca order status to our standard format"""
        status_mapping = {
            "new": OrderStatus.PENDING,
            "pending_new": OrderStatus.PENDING,
            "accepted": OrderStatus.PENDING,
            "held": OrderStatus.PENDING,
            "filled": OrderStatus.FILLED,
            "partially_filled": OrderStatus.PARTIALLY_FILLED,
            "cancelled": OrderStatus.CANCELLED,
            "rejected": OrderStatus.REJECTED,
            "expired": OrderStatus.CANCELLED
        }
        return status_mapping.get(alpaca_status.lower(), OrderStatus.PENDING)
    
    def _convert_order_type(self, alpaca_order_type: str) -> OrderType:
        """Convert Alpaca order type to our standard format"""
        type_mapping = {
            "market": OrderType.MARKET,
            "limit": OrderType.LIMIT,
            "stop": OrderType.STOP,
            "stop_limit": OrderType.STOP_LIMIT
        }
        return type_mapping.get(alpaca_order_type.lower(), OrderType.MARKET)