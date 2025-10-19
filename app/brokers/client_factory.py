"""
Broker Client Factory

Creates appropriate broker client instances based on broker type.
"""
from typing import Union
from app.models.broker_account import BrokerType
from app.services.alpaca_client import AlpacaClient


class MockInteractiveBrokersClient:
    """Mock Interactive Brokers client for development"""
    
    def __init__(self, api_key: str, api_secret: str, is_paper: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.is_paper = is_paper
    
    def get_account(self):
        """Mock account info"""
        return {
            "account_number": "TEST_IB_123456",
            "cash": 50000.0,
            "buying_power": 100000.0,
            "portfolio_value": 75000.0
        }
    
    def place_order(self, symbol: str, action: str, quantity: int):
        """Mock order placement"""
        return {
            "order_id": "IB_TEST_ORDER_123",
            "status": "SUBMITTED",
            "symbol": symbol,
            "action": action,
            "quantity": quantity
        }
    
    def get_positions(self):
        """Mock positions"""
        return []


def get_broker_client(broker_type: BrokerType, api_key: str, api_secret: str, is_paper: bool = True):
    """
    Factory function to create broker clients based on broker type
    
    Args:
        broker_type: The type of broker (Alpaca, Interactive Brokers, etc.)
        api_key: API key for broker authentication
        api_secret: API secret for broker authentication
        is_paper: Whether to use paper trading (default: True)
    
    Returns:
        Broker client instance
    
    Raises:
        ValueError: If broker type is not supported
    """
    if broker_type == BrokerType.ALPACA:
        # Create a simple mock object for AlpacaClient
        class MockBrokerAccount:
            def __init__(self, broker_type, api_key, api_secret, is_paper_trading):
                self.broker_type = broker_type
                self.api_key = api_key
                self.api_secret = api_secret
                self.is_paper_trading = is_paper_trading
        
        mock_broker_account = MockBrokerAccount(
            broker_type=BrokerType.ALPACA,
            api_key=api_key,
            api_secret=api_secret,
            is_paper_trading=is_paper
        )
        return AlpacaClient(mock_broker_account)
    elif broker_type == BrokerType.INTERACTIVE_BROKERS:
        # For now, return mock client - implement real IB client later
        return MockInteractiveBrokersClient(api_key, api_secret, is_paper)
    else:
        raise ValueError(f"Unsupported broker type: {broker_type}")