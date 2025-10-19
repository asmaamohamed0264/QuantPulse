"""
Broker Integration Module

This module provides a unified interface for connecting to different brokers
like Alpaca, Interactive Brokers, etc.
"""

from .client_factory import get_broker_client

__all__ = ['get_broker_client']