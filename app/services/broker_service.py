"""
Broker Service - Generic broker interface (placeholder)
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BrokerService(ABC):
    """Abstract base class for broker services"""
    
    @abstractmethod
    async def test_connection(self) -> bool:
        pass
    
    @abstractmethod
    async def get_account_info(self) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def execute_order(self, execution) -> Optional[Dict[str, Any]]:
        pass