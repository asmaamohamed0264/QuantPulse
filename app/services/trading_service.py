"""
Trading Service - Main service for executing trades across different brokers
"""
from typing import Optional, Dict, Any
from loguru import logger

from app.models.broker_account import BrokerAccount, BrokerType
from app.models.execution import Execution, OrderStatus
from app.services.alpaca_client import AlpacaClient
from app.services.broker_service import BrokerService


class TradingService:
    """Main trading service that handles execution across different brokers"""
    
    def __init__(self, broker_account: BrokerAccount):
        self.broker_account = broker_account
        self.client = self._get_broker_client()
    
    def _get_broker_client(self):
        """Get the appropriate broker client based on broker type"""
        if self.broker_account.broker_type == BrokerType.ALPACA:
            return AlpacaClient(self.broker_account)
        elif self.broker_account.broker_type == BrokerType.BINANCE:
            # TODO: Implement BinanceClient
            raise NotImplementedError("Binance integration not yet implemented")
        elif self.broker_account.broker_type == BrokerType.INTERACTIVE_BROKERS:
            # TODO: Implement IBClient
            raise NotImplementedError("Interactive Brokers integration not yet implemented")
        else:
            raise ValueError(f"Unsupported broker type: {self.broker_account.broker_type}")
    
    async def test_connection(self) -> bool:
        """Test connection to the broker"""
        try:
            return await self.client.test_connection()
        except Exception as e:
            logger.error(f"Connection test failed for {self.broker_account.name}: {e}")
            return False
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        return await self.client.get_account_info()
    
    async def get_positions(self) -> list:
        """Get all open positions"""
        return await self.client.get_positions()
    
    async def execute_order(self, execution: Execution) -> Optional[Dict[str, Any]]:
        """Execute a trading order"""
        try:
            # Pre-execution checks
            if not await self._pre_execution_checks(execution):
                return None
            
            # Execute the order
            result = await self.client.execute_order(execution)
            
            # Post-execution processing
            if result:
                await self._post_execution_processing(execution, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Order execution failed: {e}")
            execution.error_message = str(e)
            execution.update_execution_status(OrderStatus.REJECTED)
            return None
    
    async def cancel_order(self, broker_order_id: str) -> bool:
        """Cancel an order"""
        return await self.client.cancel_order(broker_order_id)
    
    async def get_order_status(self, broker_order_id: str) -> Optional[Dict[str, Any]]:
        """Get order status"""
        return await self.client.get_order_status(broker_order_id)
    
    async def close_position(self, symbol: str) -> bool:
        """Close a position"""
        return await self.client.close_position(symbol)
    
    async def get_latest_quote(self, symbol: str, asset_class: str = "stock") -> Dict[str, float]:
        """Get latest quote for a symbol"""
        return await self.client.get_latest_quote(symbol, asset_class)
    
    async def _pre_execution_checks(self, execution: Execution) -> bool:
        """Perform pre-execution validation checks"""
        try:
            # Check if broker account can trade
            if not self.broker_account.can_trade():
                execution.error_message = "Broker account cannot trade"
                execution.update_execution_status(OrderStatus.REJECTED)
                return False
            
            # Check day trading limits
            if not self.broker_account.can_day_trade():
                execution.error_message = "Day trading limit exceeded"
                execution.update_execution_status(OrderStatus.REJECTED)
                return False
            
            # Get latest quote for slippage check
            if execution.max_slippage_allowed and execution.max_slippage_allowed > 0:
                try:
                    quote = await self.get_latest_quote(execution.symbol, execution.asset_class)
                    current_price = quote["ask_price"] if execution.order_side.value == "buy" else quote["bid_price"]
                    
                    if execution.requested_price:
                        # Calculate expected slippage
                        expected_slippage = abs(current_price - execution.requested_price) / execution.requested_price
                        
                        if expected_slippage > execution.max_slippage_allowed:
                            execution.error_message = f"Expected slippage {expected_slippage:.4f} exceeds limit {execution.max_slippage_allowed:.4f}"
                            execution.update_execution_status(OrderStatus.REJECTED)
                            return False
                    
                    # Store market price at request time
                    execution.market_price_at_request = current_price
                    
                except Exception as e:
                    logger.warning(f"Could not get quote for slippage check: {e}")
                    # Continue with execution if quote fails
            
            return True
            
        except Exception as e:
            logger.error(f"Pre-execution checks failed: {e}")
            execution.error_message = f"Pre-execution checks failed: {e}"
            execution.update_execution_status(OrderStatus.REJECTED)
            return False
    
    async def _post_execution_processing(self, execution: Execution, result: Dict[str, Any]) -> None:
        """Perform post-execution processing"""
        try:
            # Update broker account balance
            await self.client.update_account_balance()
            
            # Calculate slippage if order was filled
            if execution.status == OrderStatus.FILLED and execution.executed_price:
                execution.slippage = execution.calculate_slippage()
                
                # Log excessive slippage
                if execution.max_slippage_allowed and execution.slippage > execution.max_slippage_allowed:
                    logger.warning(f"Order {execution.id} exceeded slippage limit: {execution.slippage:.4f}")
            
            # Update day trading count if this was a day trade
            if self._is_day_trade(execution):
                self.broker_account.day_trades_count += 1
                logger.info(f"Day trade executed. Count: {self.broker_account.day_trades_count}")
            
            logger.info(f"Post-execution processing completed for order {execution.id}")
            
        except Exception as e:
            logger.error(f"Post-execution processing failed: {e}")
    
    def _is_day_trade(self, execution: Execution) -> bool:
        """Check if this execution constitutes a day trade"""
        # This is a simplified check. In practice, you'd need to check
        # if there was an opposite position opened and closed on the same day
        # For now, assume all trades are day trades if account equity < $25k
        return self.broker_account.total_equity < 25000
    
    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary"""
        try:
            account_info = await self.get_account_info()
            positions = await self.get_positions()
            
            total_unrealized_pnl = sum(pos["unrealized_pnl"] for pos in positions)
            
            return {
                "account_value": account_info["equity"],
                "cash": account_info["cash"],
                "buying_power": account_info["buying_power"],
                "positions_count": len(positions),
                "total_unrealized_pnl": total_unrealized_pnl,
                "day_trade_count": account_info.get("day_trade_count", 0),
                "is_paper": account_info.get("is_paper", True),
                "positions": positions
            }
            
        except Exception as e:
            logger.error(f"Failed to get portfolio summary: {e}")
            raise