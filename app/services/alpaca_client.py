"""
Alpaca API Client - Trading execution for stocks and crypto
"""
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, OrderType, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest, CryptoLatestQuoteRequest
from typing import Optional, Dict, Any
import asyncio
from loguru import logger

from app.models.broker_account import BrokerAccount, BrokerType
from app.models.execution import Execution, OrderSide as ExecutionOrderSide, OrderStatus
from app.config import settings


class AlpacaClient:
    """Alpaca trading client wrapper"""
    
    def __init__(self, broker_account: BrokerAccount):
        self.broker_account = broker_account
        
        if broker_account.broker_type != BrokerType.ALPACA:
            raise ValueError("BrokerAccount must be Alpaca type")
        
        # Initialize trading client
        self.client = TradingClient(
            api_key=broker_account.api_key,  # Should be decrypted
            secret_key=broker_account.api_secret,  # Should be decrypted
            paper=broker_account.is_paper_trading,
            url_override=broker_account.base_url if broker_account.base_url else None
        )
        
        # Initialize data clients for quotes
        self.stock_data_client = StockHistoricalDataClient(
            api_key=broker_account.api_key,
            secret_key=broker_account.api_secret
        )
        
        self.crypto_data_client = CryptoHistoricalDataClient(
            api_key=broker_account.api_key,
            secret_key=broker_account.api_secret
        )

    async def test_connection(self) -> bool:
        """Test connection to Alpaca API"""
        try:
            account = self.client.get_account()
            logger.info(f"Alpaca connection successful. Account ID: {account.id}")
            return True
        except Exception as e:
            logger.error(f"Alpaca connection failed: {e}")
            return False

    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        try:
            account = self.client.get_account()
            return {
                "account_id": str(account.id),
                "cash": float(account.cash),
                "equity": float(account.equity),
                "buying_power": float(account.buying_power),
                "day_trade_count": account.daytrade_count,
                "status": account.status,
                "pattern_day_trader": account.pattern_day_trader,
                "is_paper": self.broker_account.is_paper_trading
            }
        except Exception as e:
            logger.error(f"Failed to get Alpaca account info: {e}")
            raise

    async def get_positions(self) -> list:
        """Get all open positions"""
        try:
            positions = self.client.get_all_positions()
            return [
                {
                    "symbol": pos.symbol,
                    "quantity": float(pos.qty),
                    "side": "long" if float(pos.qty) > 0 else "short",
                    "market_value": float(pos.market_value),
                    "avg_entry_price": float(pos.avg_entry_price),
                    "unrealized_pnl": float(pos.unrealized_pnl),
                    "unrealized_pnl_percent": float(pos.unrealized_plpc) * 100
                }
                for pos in positions
            ]
        except Exception as e:
            logger.error(f"Failed to get Alpaca positions: {e}")
            raise

    async def get_latest_quote(self, symbol: str, asset_class: str = "stock") -> Dict[str, float]:
        """Get latest quote for a symbol"""
        try:
            if asset_class.lower() in ["crypto", "cryptocurrency"]:
                # Use crypto data client
                request = CryptoLatestQuoteRequest(symbol_or_symbols=[symbol])
                quotes = self.crypto_data_client.get_crypto_latest_quote(request)
                quote = quotes[symbol]
                return {
                    "bid_price": float(quote.bid_price),
                    "ask_price": float(quote.ask_price),
                    "bid_size": float(quote.bid_size),
                    "ask_size": float(quote.ask_size)
                }
            else:
                # Use stock data client
                request = StockLatestQuoteRequest(symbol_or_symbols=[symbol])
                quotes = self.stock_data_client.get_stock_latest_quote(request)
                quote = quotes[symbol]
                return {
                    "bid_price": float(quote.bid_price),
                    "ask_price": float(quote.ask_price),
                    "bid_size": int(quote.bid_size),
                    "ask_size": int(quote.ask_size)
                }
        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            raise

    async def execute_order(self, execution: Execution) -> Optional[Dict[str, Any]]:
        """Execute a trading order"""
        try:
            # Determine order side
            side = OrderSide.BUY if execution.order_side == ExecutionOrderSide.BUY else OrderSide.SELL
            
            # Prepare order request
            if execution.order_type.value == "market":
                order_request = MarketOrderRequest(
                    symbol=execution.symbol,
                    qty=execution.quantity,
                    side=side,
                    time_in_force=TimeInForce.DAY
                )
            else:  # limit order
                if not execution.requested_price:
                    raise ValueError("Limit order requires a price")
                
                order_request = LimitOrderRequest(
                    symbol=execution.symbol,
                    qty=execution.quantity,
                    side=side,
                    time_in_force=TimeInForce.GTC,
                    limit_price=execution.requested_price
                )
            
            # Submit order
            logger.info(f"Submitting Alpaca order: {execution.symbol} {side.value} {execution.quantity}")
            order = self.client.submit_order(order_request)
            
            # Update execution with order details
            execution.broker_order_id = str(order.id)
            execution.client_order_id = str(order.client_order_id)
            
            # Check if order is filled immediately (market orders often are)
            if order.filled_at:
                execution.update_execution_status(
                    OrderStatus.FILLED,
                    filled_qty=float(order.filled_qty),
                    executed_price=float(order.filled_avg_price) if order.filled_avg_price else None
                )
            else:
                execution.update_execution_status(OrderStatus.PENDING)
            
            logger.info(f"Alpaca order submitted successfully: {order.id}")
            
            return {
                "broker_order_id": str(order.id),
                "status": order.status,
                "filled_qty": float(order.filled_qty) if order.filled_qty else 0,
                "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
                "submitted_at": order.submitted_at,
                "filled_at": order.filled_at
            }
            
        except Exception as e:
            logger.error(f"Failed to execute Alpaca order: {e}")
            execution.error_message = str(e)
            execution.update_execution_status(OrderStatus.REJECTED)
            raise

    async def cancel_order(self, broker_order_id: str) -> bool:
        """Cancel an order by ID"""
        try:
            self.client.cancel_order_by_id(broker_order_id)
            logger.info(f"Alpaca order cancelled: {broker_order_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel Alpaca order {broker_order_id}: {e}")
            return False

    async def get_order_status(self, broker_order_id: str) -> Optional[Dict[str, Any]]:
        """Get order status by ID"""
        try:
            order = self.client.get_order_by_id(broker_order_id)
            return {
                "order_id": str(order.id),
                "status": order.status,
                "symbol": order.symbol,
                "qty": float(order.qty),
                "filled_qty": float(order.filled_qty) if order.filled_qty else 0,
                "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
                "submitted_at": order.submitted_at,
                "filled_at": order.filled_at,
                "side": order.side
            }
        except Exception as e:
            logger.error(f"Failed to get Alpaca order status {broker_order_id}: {e}")
            return None

    async def close_position(self, symbol: str) -> bool:
        """Close a position by selling/covering all shares"""
        try:
            positions = self.client.get_all_positions()
            position = next((p for p in positions if p.symbol == symbol), None)
            
            if not position:
                logger.warning(f"No position found for {symbol}")
                return True  # No position to close
            
            # Determine side to close position
            qty = abs(float(position.qty))
            side = OrderSide.SELL if float(position.qty) > 0 else OrderSide.BUY
            
            # Submit market order to close
            close_order = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=side,
                time_in_force=TimeInForce.DAY
            )
            
            order = self.client.submit_order(close_order)
            logger.info(f"Position close order submitted for {symbol}: {order.id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to close position for {symbol}: {e}")
            return False

    async def update_account_balance(self) -> None:
        """Update broker account balance information"""
        try:
            account_info = await self.get_account_info()
            self.broker_account.update_balance(
                cash=account_info["cash"],
                equity=account_info["equity"],
                buying_power=account_info["buying_power"]
            )
            
            # Update day trading count
            self.broker_account.day_trades_count = account_info["day_trade_count"]
            
            logger.info(f"Updated account balance: ${account_info['equity']:.2f}")
            
        except Exception as e:
            logger.error(f"Failed to update account balance: {e}")
            raise