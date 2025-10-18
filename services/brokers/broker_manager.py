"""
Broker Manager
Central manager for handling multiple broker connections and routing orders
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from enum import Enum

from .base_broker import BaseBroker, OrderResult, Position, AccountInfo, AssetClass
from .alpaca_broker import AlpacaBroker
from .interactive_brokers import InteractiveBrokersBroker

logger = logging.getLogger(__name__)


class BrokerType(Enum):
    ALPACA = "alpaca"
    INTERACTIVE_BROKERS = "interactive_brokers"


class BrokerManager:
    """
    Manager class for handling multiple broker connections and routing orders
    """
    
    def __init__(self):
        self.brokers: Dict[str, BaseBroker] = {}
        self.default_broker: Optional[str] = None
        self._broker_classes = {
            BrokerType.ALPACA: AlpacaBroker,
            BrokerType.INTERACTIVE_BROKERS: InteractiveBrokersBroker
        }
    
    async def add_broker(self, broker_id: str, broker_type: BrokerType, config: Dict[str, Any]) -> bool:
        """
        Add a new broker connection
        
        Args:
            broker_id: Unique identifier for this broker instance
            broker_type: Type of broker (Alpaca, IB, etc.)
            config: Configuration parameters for the broker
            
        Returns:
            True if broker was added and connected successfully
        """
        try:
            if broker_id in self.brokers:
                logger.warning(f"Broker {broker_id} already exists. Removing old instance.")
                await self.remove_broker(broker_id)
            
            # Get broker class
            broker_class = self._broker_classes.get(broker_type)
            if not broker_class:
                raise ValueError(f"Unsupported broker type: {broker_type}")
            
            # Create broker instance
            broker = broker_class(config)
            
            # Attempt to connect
            if await broker.connect():
                self.brokers[broker_id] = broker
                
                # Set as default if this is the first broker
                if not self.default_broker:
                    self.default_broker = broker_id
                
                logger.info(f"Successfully added broker: {broker_id} ({broker.broker_name})")
                return True
            else:
                logger.error(f"Failed to connect broker: {broker_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to add broker {broker_id}: {e}")
            return False
    
    async def remove_broker(self, broker_id: str) -> bool:
        """Remove a broker connection"""
        try:
            if broker_id not in self.brokers:
                logger.warning(f"Broker {broker_id} not found")
                return False
            
            broker = self.brokers[broker_id]
            await broker.disconnect()
            
            del self.brokers[broker_id]
            
            # Update default broker if needed
            if self.default_broker == broker_id:
                self.default_broker = next(iter(self.brokers.keys())) if self.brokers else None
            
            logger.info(f"Removed broker: {broker_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove broker {broker_id}: {e}")
            return False
    
    def get_broker(self, broker_id: Optional[str] = None) -> Optional[BaseBroker]:
        """
        Get a specific broker or the default broker
        
        Args:
            broker_id: Specific broker ID, or None for default broker
            
        Returns:
            Broker instance or None if not found
        """
        if broker_id is None:
            broker_id = self.default_broker
        
        if broker_id is None:
            return None
        
        return self.brokers.get(broker_id)
    
    def list_brokers(self) -> Dict[str, Dict[str, Any]]:
        """List all connected brokers with their status"""
        broker_list = {}
        
        for broker_id, broker in self.brokers.items():
            broker_list[broker_id] = {
                'name': broker.broker_name,
                'connected': broker.is_connected,
                'supported_assets': [asset.value for asset in broker.supported_asset_classes],
                'is_default': broker_id == self.default_broker
            }
        
        return broker_list
    
    def get_brokers_for_asset_class(self, asset_class: AssetClass) -> List[str]:
        """Get list of broker IDs that support a specific asset class"""
        supporting_brokers = []
        
        for broker_id, broker in self.brokers.items():
            if asset_class in broker.supported_asset_classes and broker.is_connected:
                supporting_brokers.append(broker_id)
        
        return supporting_brokers
    
    async def set_default_broker(self, broker_id: str) -> bool:
        """Set the default broker"""
        if broker_id not in self.brokers:
            logger.error(f"Cannot set default broker: {broker_id} not found")
            return False
        
        self.default_broker = broker_id
        logger.info(f"Set default broker to: {broker_id}")
        return True
    
    async def place_order(
        self,
        symbol: str,
        quantity: float,
        side: str,
        order_type: str,
        broker_id: Optional[str] = None,
        **kwargs
    ) -> OrderResult:
        """
        Place an order using the specified broker or default broker
        
        Args:
            symbol: Trading symbol
            quantity: Order quantity
            side: Order side ('buy' or 'sell')
            order_type: Order type ('market', 'limit', etc.)
            broker_id: Specific broker to use, or None for default
            **kwargs: Additional order parameters
            
        Returns:
            OrderResult object
        """
        broker = self.get_broker(broker_id)
        if not broker:
            raise ValueError(f"Broker not found: {broker_id or 'default'}")
        
        if not broker.is_connected:
            raise RuntimeError(f"Broker {broker_id or 'default'} is not connected")
        
        # Convert string parameters to enums
        from .base_broker import OrderSide, OrderType
        
        order_side = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL
        order_type_enum = OrderType(order_type.lower())
        
        return await broker.place_order(
            symbol=symbol,
            quantity=quantity,
            side=order_side,
            order_type=order_type_enum,
            **kwargs
        )
    
    async def cancel_order(self, order_id: str, broker_id: Optional[str] = None) -> bool:
        """Cancel an order"""
        broker = self.get_broker(broker_id)
        if not broker:
            raise ValueError(f"Broker not found: {broker_id or 'default'}")
        
        return await broker.cancel_order(order_id)
    
    async def get_order_status(self, order_id: str, broker_id: Optional[str] = None) -> OrderResult:
        """Get order status"""
        broker = self.get_broker(broker_id)
        if not broker:
            raise ValueError(f"Broker not found: {broker_id or 'default'}")
        
        return await broker.get_order_status(order_id)
    
    async def get_all_positions(self) -> Dict[str, List[Position]]:
        """Get positions from all connected brokers"""
        all_positions = {}
        
        for broker_id, broker in self.brokers.items():
            if broker.is_connected:
                try:
                    positions = await broker.get_positions()
                    all_positions[broker_id] = positions
                except Exception as e:
                    logger.error(f"Failed to get positions from {broker_id}: {e}")
                    all_positions[broker_id] = []
        
        return all_positions
    
    async def get_all_account_info(self) -> Dict[str, AccountInfo]:
        """Get account information from all connected brokers"""
        all_accounts = {}
        
        for broker_id, broker in self.brokers.items():
            if broker.is_connected:
                try:
                    account_info = await broker.get_account_info()
                    all_accounts[broker_id] = account_info
                except Exception as e:
                    logger.error(f"Failed to get account info from {broker_id}: {e}")
        
        return all_accounts
    
    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on all brokers"""
        health_status = {}
        
        for broker_id, broker in self.brokers.items():
            try:
                health_status[broker_id] = await broker.health_check()
            except Exception as e:
                logger.error(f"Health check failed for {broker_id}: {e}")
                health_status[broker_id] = False
        
        return health_status
    
    async def validate_symbol(self, symbol: str, broker_id: Optional[str] = None) -> bool:
        """Validate symbol with specified broker or all brokers"""
        if broker_id:
            broker = self.get_broker(broker_id)
            if broker and broker.is_connected:
                return await broker.validate_symbol(symbol)
            return False
        
        # Check with all connected brokers
        for broker in self.brokers.values():
            if broker.is_connected:
                try:
                    if await broker.validate_symbol(symbol):
                        return True
                except Exception:
                    continue
        
        return False
    
    async def shutdown(self):
        """Disconnect all brokers and cleanup"""
        logger.info("Shutting down broker manager...")
        
        disconnect_tasks = []
        for broker_id, broker in self.brokers.items():
            if broker.is_connected:
                disconnect_tasks.append(broker.disconnect())
        
        if disconnect_tasks:
            await asyncio.gather(*disconnect_tasks, return_exceptions=True)
        
        self.brokers.clear()
        self.default_broker = None
        
        logger.info("Broker manager shutdown complete")


# Global broker manager instance
broker_manager = BrokerManager()