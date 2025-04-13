"""
Base strategy interface for Zora trading bot
"""
from abc import ABC, abstractmethod
from typing import Optional

from ..models.coin import Coin
from ..models.signal import Signal

class Strategy(ABC):
    """Base class for all trading strategies"""
    
    def __init__(self, config=None):
        """
        Initialize the strategy.
        
        Args:
            config: Strategy-specific configuration
        """
        self.config = config or {}
        self.name = "BaseStrategy"
    
    @abstractmethod
    def evaluate(self, coin: Coin) -> Optional[Signal]:
        """
        Evaluate a coin and generate a trading signal if appropriate.
        
        Args:
            coin: Coin data to evaluate
            
        Returns:
            A Signal object if a trading opportunity is identified, None otherwise
        """
        pass
