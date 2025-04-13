"""
Trading strategies for Zora trading bot.
Contains different strategies for identifying trading opportunities.
"""

from .base import Strategy
from .simple import SimpleStrategy
from .momentum import MomentumStrategy
from .registry import STRATEGY_REGISTRY
