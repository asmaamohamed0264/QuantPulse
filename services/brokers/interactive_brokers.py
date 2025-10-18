"""
Interactive Brokers Implementation
Implements the BaseBroker interface for Interactive Brokers trading via TWS API
"""

import asyncio
import logging
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from decimal import Decimal

try:
    from ibapi.client import EClient
    from ibapi.wrapper import EWrapper
    from ibapi.contract import Contract
    from ibapi.order import Order
    from ibapi.common import OrderId, TickerId
    from ibapi.execution import Execution
    from ibapi.commission_report import CommissionReport
    IBAPI_AVAILABLE = True
except ImportError:
    IBAPI_AVAILABLE = False

from .base_broker import (
    BaseBroker, OrderType, OrderSide, OrderStatus, AssetClass,
    Position, OrderResult, AccountInfo
)

logger = logging.getLogger(__name__)


class IBApiWrapper(EWrapper):
    """Interactive Brokers API Wrapper for handling callbacks"""
    
    def __init__(self, broker_instance):
        EWrapper.__init__(self)
        self.broker = broker_instance
        self.next_order_id = 1
        self.account_info = {}
        self.positions = {}
        self.orders = {}
        self.executions = {}
        self.error_messages = {}
        
    def nextValidId(self, orderId: OrderId):
        """Callback for next valid order ID"""
        self.next_order_id = orderId
        logger.info(f"Next valid order ID: {orderId}")
        
    def accountSummary(self, reqId: int, account: str, tag: str, value: str, currency: str):
        """Callback for account summary"""
        if account not in self.account_info:
            self.account_info[account] = {}
        self.account_info[account][tag] = value
        
    def position(self, account: str, contract: Contract, position: float, avgCost: float):
        """Callback for position updates"""
        key = f"{account}_{contract.symbol}"
        self.positions[key] = {
            'account': account,
            'symbol': contract.symbol,
            'position': position,
            'avgCost': avgCost,
            'contract': contract
        }
        
    def orderStatus(self, orderId: OrderId, status: str, filled: float, remaining: float,
                   avgFillPrice: float, permId: int, parentId: int, lastFillPrice: float,
                   clientId: int, whyHeld: str, mktCapPrice: float):
        """Callback for order status updates"""
        self.orders[orderId] = {
            'orderId': orderId,
            'status': status,
            'filled': filled,
            'remaining': remaining,
            'avgFillPrice': avgFillPrice,
            'lastFillPrice': lastFillPrice
        }
        
    def execDetails(self, reqId: int, contract: Contract, execution: Execution):
        """Callback for execution details"""
        self.executions[execution.execId] = {
            'contract': contract,
            'execution': execution
        }
        
    def error(self, reqId: TickerId, errorCode: int, errorString: str):
        """Error callback"""
        logger.error(f"IB API Error {errorCode}: {errorString}")
        self.error_messages[reqId] = f"{errorCode}: {errorString}"


class IBApiClient(EClient):
    """Interactive Brokers API Client"""
    
    def __init__(self, wrapper):
        EClient.__init__(self, wrapper)


class InteractiveBrokersBroker(BaseBroker):
    """Interactive Brokers broker implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        if not IBAPI_AVAILABLE:
            raise ImportError("Interactive Brokers API (ibapi) is not installed. Install with: pip install ibapi")
        
        super().__init__(config)
        
        self.host = config.get('host', '127.0.0.1')
        self.port = config.get('port', 7497)  # 7497 for TWS paper, 7496 for TWS live
        self.client_id = config.get('client_id', 1)
        self.account_id = config.get('account_id', '')
        
        # Initialize API wrapper and client
        self.wrapper = IBApiWrapper(self)
        self.client = IBApiClient(self.wrapper)
        
        # Threading for API connection
        self.api_thread = None
        self.connection_event = threading.Event()
        
        logger.info(f"Interactive Brokers broker initialized (TWS connection: {self.host}:{self.port})")
    
    @property
    def broker_name(self) -> str:
        return "Interactive Brokers"
    
    @property
    def supported_asset_classes(self) -> List[AssetClass]:
        return [AssetClass.STOCKS, AssetClass.FOREX, AssetClass.OPTIONS, AssetClass.FUTURES]
    
    async def connect(self) -> bool:
        """Connect to Interactive Brokers TWS/Gateway"""
        try:
            # Start API connection in separate thread
            def run_client():
                self.client.connect(self.host, self.port, self.client_id)
                self.client.run()
                
            self.api_thread = threading.Thread(target=run_client, daemon=True)
            self.api_thread.start()
            
            # Wait for connection
            start_time = time.time()
            while not self.client.isConnected() and time.time() - start_time < 10:
                await asyncio.sleep(0.1)
                
            if self.client.isConnected():
                self.is_connected = True
                
                # Request account summary
                self.client.reqAccountSummary(1, "All", "$LEDGER")
                await asyncio.sleep(1)  # Wait for account data
                
                logger.info("Successfully connected to Interactive Brokers TWS")
                return True
            else:
                logger.error("Failed to connect to Interactive Brokers TWS")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to Interactive Brokers: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from Interactive Brokers TWS/Gateway"""
        try:
            if self.client.isConnected():
                self.client.disconnect()
                
            self.is_connected = False
            logger.info("Disconnected from Interactive Brokers TWS")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting from Interactive Brokers: {e}")
            return False
    
    async def get_account_info(self) -> AccountInfo:
        """Get account information"""
        try:
            if not self.account_id and self.wrapper.account_info:
                # Get first available account
                self.account_id = list(self.wrapper.account_info.keys())[0]
            
            account_data = self.wrapper.account_info.get(self.account_id, {})
            
            cash_balance = float(account_data.get('TotalCashValue', 0))
            buying_power = float(account_data.get('BuyingPower', cash_balance))
            net_liquidation = float(account_data.get('NetLiquidation', cash_balance))
            
            return AccountInfo(
                account_id=self.account_id,
                cash_balance=cash_balance,
                buying_power=buying_power,
                total_portfolio_value=net_liquidation,
                currency=account_data.get('Currency', 'USD')
            )
            
        except Exception as e:
            logger.error(f"Error getting IB account info: {e}")
            raise
    
    async def get_positions(self) -> List[Position]:
        """Get all current positions"""
        try:
            # Request positions
            self.client.reqPositions()
            await asyncio.sleep(1)  # Wait for position data
            
            position_list = []
            for key, pos_data in self.wrapper.positions.items():
                if pos_data['position'] == 0:
                    continue  # Skip zero positions
                    
                quantity = abs(pos_data['position'])
                side = OrderSide.BUY if pos_data['position'] > 0 else OrderSide.SELL
                
                # Determine asset class from contract
                asset_class = self._get_asset_class(pos_data['contract'])
                
                position_list.append(Position(
                    symbol=pos_data['symbol'],
                    quantity=quantity,
                    side=side,
                    market_value=0.0,  # Would need separate market data request
                    unrealized_pnl=0.0,  # Would need separate PnL request
                    avg_entry_price=pos_data['avgCost'],
                    asset_class=asset_class
                ))
            
            return position_list
            
        except Exception as e:
            logger.error(f"Error getting IB positions: {e}")
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
            # Create contract
            contract = self._create_contract(symbol, kwargs.get('asset_class', 'stock'))
            
            # Create order
            order = Order()
            order.action = "BUY" if side == OrderSide.BUY else "SELL"
            order.totalQuantity = quantity
            order.orderType = self._convert_order_type(order_type)
            
            # Set prices
            if order_type == OrderType.LIMIT and limit_price:
                order.lmtPrice = limit_price
            elif order_type == OrderType.STOP and stop_price:
                order.auxPrice = stop_price
            elif order_type == OrderType.STOP_LIMIT and limit_price and stop_price:
                order.lmtPrice = limit_price
                order.auxPrice = stop_price
                
            # Set time in force
            tif_mapping = {
                "day": "DAY",
                "gtc": "GTC",
                "ioc": "IOC",
                "fok": "FOK"
            }
            order.tif = tif_mapping.get(time_in_force.lower(), "DAY")
            
            # Get next order ID
            order_id = self.wrapper.next_order_id
            self.wrapper.next_order_id += 1
            
            # Submit order
            logger.info(f"Submitting IB order: {symbol} {side.value} {quantity} {order_type.value}")
            self.client.placeOrder(order_id, contract, order)
            
            # Wait for order acknowledgment
            await asyncio.sleep(1)
            
            # Check order status
            order_status_data = self.wrapper.orders.get(order_id, {})
            status = self._convert_order_status(order_status_data.get('status', 'Submitted'))
            
            result = OrderResult(
                order_id=str(order_id),
                symbol=symbol,
                quantity=quantity,
                side=side,
                order_type=order_type,
                status=status,
                filled_price=order_status_data.get('avgFillPrice') if order_status_data.get('avgFillPrice', 0) > 0 else None,
                filled_quantity=order_status_data.get('filled', 0),
                timestamp=datetime.now(),
                broker_response={
                    "ib_order_id": order_id,
                    "contract": str(contract),
                    "order": str(order)
                }
            )
            
            logger.info(f"IB order submitted successfully: {order_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to place IB order: {e}")
            raise
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order"""
        try:
            self.client.cancelOrder(int(order_id))
            logger.info(f"IB order cancellation requested: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel IB order {order_id}: {e}")
            return False
    
    async def get_order_status(self, order_id: str) -> OrderResult:
        """Get the status of an order"""
        try:
            order_data = self.wrapper.orders.get(int(order_id), {})
            
            if not order_data:
                raise ValueError(f"Order {order_id} not found")
            
            status = self._convert_order_status(order_data.get('status', 'Unknown'))
            
            return OrderResult(
                order_id=order_id,
                symbol="",  # Would need to store this separately
                quantity=0,  # Would need to store this separately
                side=OrderSide.BUY,  # Would need to store this separately
                order_type=OrderType.MARKET,  # Would need to store this separately
                status=status,
                filled_price=order_data.get('avgFillPrice') if order_data.get('avgFillPrice', 0) > 0 else None,
                filled_quantity=order_data.get('filled', 0),
                timestamp=datetime.now(),
                broker_response=order_data
            )
            
        except Exception as e:
            logger.error(f"Failed to get IB order status {order_id}: {e}")
            raise
    
    async def validate_symbol(self, symbol: str) -> bool:
        """Validate if a trading symbol is supported"""
        try:
            # For IB, we'd need to request contract details
            # This is a simplified validation
            return len(symbol) > 0 and symbol.isalpha()
        except Exception as e:
            logger.warning(f"Symbol validation failed for {symbol}: {e}")
            return False
    
    def _create_contract(self, symbol: str, asset_class: str = "stock") -> Contract:
        """Create IB contract from symbol and asset class"""
        contract = Contract()
        contract.symbol = symbol
        
        if asset_class.lower() in ["stock", "equity"]:
            contract.secType = "STK"
            contract.exchange = "SMART"
            contract.currency = "USD"
        elif asset_class.lower() in ["forex", "fx"]:
            contract.secType = "CASH"
            # For forex, symbol should be like "EUR.USD"
            if "." in symbol:
                base, quote = symbol.split(".")
                contract.symbol = base
                contract.currency = quote
            else:
                contract.currency = "USD"
            contract.exchange = "IDEALPRO"
        elif asset_class.lower() == "futures":
            contract.secType = "FUT"
            contract.exchange = "GLOBEX"  # Default exchange for futures
            contract.currency = "USD"
        elif asset_class.lower() == "options":
            contract.secType = "OPT"
            contract.exchange = "SMART"
            contract.currency = "USD"
            # Options would need more parameters (strike, expiry, right)
        
        return contract
    
    def _convert_order_type(self, order_type: OrderType) -> str:
        """Convert our order type to IB order type"""
        mapping = {
            OrderType.MARKET: "MKT",
            OrderType.LIMIT: "LMT",
            OrderType.STOP: "STP",
            OrderType.STOP_LIMIT: "STP LMT"
        }
        return mapping.get(order_type, "MKT")
    
    def _convert_order_status(self, ib_status: str) -> OrderStatus:
        """Convert IB order status to our standard format"""
        status_mapping = {
            "Submitted": OrderStatus.PENDING,
            "Filled": OrderStatus.FILLED,
            "PartiallyFilled": OrderStatus.PARTIALLY_FILLED,
            "Cancelled": OrderStatus.CANCELLED,
            "PendingCancel": OrderStatus.PENDING,
            "ApiCancelled": OrderStatus.CANCELLED,
            "Inactive": OrderStatus.REJECTED
        }
        return status_mapping.get(ib_status, OrderStatus.PENDING)
    
    def _get_asset_class(self, contract: Contract) -> AssetClass:
        """Determine asset class from IB contract"""
        sec_type = contract.secType.upper()
        
        if sec_type == "STK":
            return AssetClass.STOCKS
        elif sec_type == "CASH":
            return AssetClass.FOREX
        elif sec_type == "FUT":
            return AssetClass.FUTURES
        elif sec_type == "OPT":
            return AssetClass.OPTIONS
        else:
            return AssetClass.STOCKS  # Default