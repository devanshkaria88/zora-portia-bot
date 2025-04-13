"""
Momentum trading strategy implementation
"""
import logging
from typing import Optional, List, Dict, Any

import numpy as np

from .base import Strategy
from ..models.coin import Coin
from ..models.signal import Signal, SignalType
from ..utils.analysis import calculate_rsi, calculate_macd

logger = logging.getLogger(__name__)

class MomentumStrategy(Strategy):
    """
    Momentum trading strategy that identifies coins with strong directional movement.
    Uses technical indicators like RSI, MACD and volume analysis.
    """
    
    def __init__(self, config=None):
        """Initialize the momentum strategy with configuration"""
        super().__init__(config)
        self.name = "Momentum"
        
        # Strategy parameters
        self.rsi_period = self.config.get('rsi_period', 14)
        self.rsi_overbought = self.config.get('rsi_overbought', 70)
        self.rsi_oversold = self.config.get('rsi_oversold', 30)
        self.macd_fast = self.config.get('macd_fast', 12)
        self.macd_slow = self.config.get('macd_slow', 26)
        self.macd_signal = self.config.get('macd_signal', 9)
        self.volume_threshold = self.config.get('volume_threshold', 3.0)  # Multiplier of avg volume
    
    def evaluate(self, coin: Coin) -> Optional[Signal]:
        """
        Evaluate a coin using momentum strategy.
        
        Args:
            coin: Coin data with historical prices
            
        Returns:
            Trading signal if momentum conditions are met
        """
        # Skip if not enough historical data
        if not coin.historical_data or len(coin.historical_data) < self.macd_slow + self.macd_signal:
            return None
        
        # Extract price and volume data from historical data
        prices = [float(item.get('price', 0)) for item in coin.historical_data]
        volumes = [float(item.get('volume', 0)) for item in coin.historical_data]
        
        # Calculate technical indicators
        rsi = calculate_rsi(prices, self.rsi_period)
        macd, macd_signal, macd_hist = calculate_macd(
            prices, 
            self.macd_fast, 
            self.macd_slow, 
            self.macd_signal
        )
        
        # Volume analysis
        avg_volume = np.mean(volumes[:-5]) if len(volumes) > 5 else (volumes[0] if volumes else 0)
        recent_volume = volumes[-1] if volumes else 0
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 0
        
        # Additional creator-specific metrics
        creator_strength = self._calculate_creator_strength(coin)
        
        # Latest indicator values
        current_rsi = rsi[-1] if rsi.size > 0 else 50
        current_macd_hist = macd_hist[-1] if macd_hist.size > 0 else 0
        prev_macd_hist = macd_hist[-2] if macd_hist.size > 1 else 0
        
        # Add AI insights if available
        ai_sentiment_boost = 0
        if coin.ai_sentiment is not None:
            ai_sentiment_boost = (coin.ai_sentiment - 0.5) * 0.2  # Scale to -0.1 to +0.1
        
        # Generate buy signal
        if (current_rsi > 50 and current_rsi < self.rsi_overbought and
                current_macd_hist > 0 and current_macd_hist > prev_macd_hist and
                volume_ratio > self.volume_threshold):
            
            # Calculate signal strength (0.0 to 1.0)
            strength = min(1.0, (
                (current_rsi - 50) / (self.rsi_overbought - 50) * 0.3 +
                (volume_ratio / self.volume_threshold) * 0.3 +
                min(1.0, current_macd_hist / 0.02) * 0.2 +
                creator_strength * 0.1 +
                ai_sentiment_boost + 0.1  # Baseline value
            ))
            
            return Signal(
                type=SignalType.BUY,
                coin=coin,
                strength=strength,
                reason=f"Momentum: RSI={current_rsi:.1f}, MACD Hist={current_macd_hist:.4f}, Volume={volume_ratio:.1f}x avg",
                strategy="Momentum"
            )
        
        # Generate sell signal
        elif (current_rsi < 50 and current_rsi > self.rsi_oversold and
                current_macd_hist < 0 and current_macd_hist < prev_macd_hist):
            
            # Calculate signal strength (0.0 to 1.0)
            strength = min(1.0, (
                (50 - current_rsi) / (50 - self.rsi_oversold) * 0.4 +
                min(1.0, abs(current_macd_hist) / 0.02) * 0.3 +
                (1.0 - creator_strength) * 0.1 - 
                ai_sentiment_boost + 0.2  # Baseline value
            ))
            
            return Signal(
                type=SignalType.SELL,
                coin=coin,
                strength=strength,
                reason=f"Momentum: RSI={current_rsi:.1f}, MACD Hist={current_macd_hist:.4f}, bearish divergence",
                strategy="Momentum"
            )
        
        return None
    
    def _calculate_creator_strength(self, coin: Coin) -> float:
        """
        Calculate creator strength based on metrics.
        
        Args:
            coin: Coin data
            
        Returns:
            Creator strength score (0.0 to 1.0)
        """
        # Default to medium strength if we don't have much data
        base_strength = 0.5
        
        # Factors that can increase or decrease creator strength
        factors = []
        
        # Holder count indicates popularity
        if coin.holder_count is not None:
            # More holders generally means stronger creator
            holder_factor = min(1.0, coin.holder_count / 1000.0)
            factors.append(holder_factor)
        
        # Trade count indicates activity
        if coin.trade_count is not None:
            # More trades indicates higher activity and interest
            trade_factor = min(1.0, coin.trade_count / 500.0)
            factors.append(trade_factor)
        
        # Price change can indicate momentum
        if hasattr(coin, 'price_change_24h'):
            # Positive price change is a good sign, but cap it
            price_factor = min(1.0, (coin.price_change_24h + 50) / 100.0)
            factors.append(price_factor)
        
        # Recent trades show market interest
        if coin.recent_trades:
            # Calculate ratio of buys to total trades
            buy_count = sum(1 for trade in coin.recent_trades if trade.get('type') == 'BUY')
            buy_ratio = buy_count / len(coin.recent_trades) if coin.recent_trades else 0.5
            factors.append(buy_ratio)
        
        # Calculate overall score if we have factors
        if factors:
            return sum(factors) / len(factors)
        
        return base_strength
