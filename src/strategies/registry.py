"""
Strategy registry for the Zora trading bot.
Maintains a map of available trading strategies.
"""
from typing import Dict, Type
from .base import Strategy
from .simple import SimpleStrategy
from .momentum import MomentumStrategy

# Registry of all available strategies
STRATEGY_REGISTRY: Dict[str, Type[Strategy]] = {
    "SimpleStrategy": SimpleStrategy,
    "MomentumStrategy": MomentumStrategy,
}
