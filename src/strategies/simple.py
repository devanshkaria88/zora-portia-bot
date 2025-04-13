"""
Simple trading strategy implementation for Zora tokens.
Uses basic market indicators without requiring complex historical data.
"""

import logging
from typing import Dict, Any, Optional
import random
import asyncio
from datetime import datetime

from ..models.coin import Coin
from ..models.signal import Signal, SignalType

logger = logging.getLogger(__name__)

class SimpleStrategy:
    """
    A simple trading strategy using basic technical indicators
    """
    
    def __init__(
        self,
        volatility_threshold: float = 0.05,
        momentum_threshold: float = 0.03,
        volume_threshold: float = 1000,
        confidence_multiplier: float = 1.0,
        simulate_price_movements: bool = True  # Add simulation for demo purposes
    ):
        self.volatility_threshold = volatility_threshold
        self.momentum_threshold = momentum_threshold
        self.volume_threshold = volume_threshold
        self.confidence_multiplier = confidence_multiplier
        self.simulate_price_movements = simulate_price_movements
        self.last_price_updates = {}  # Track last update for each coin
        
    async def generate_signals(self, coins: list[Coin]) -> list[Signal]:
        """
        Generate trading signals for a list of coins
        
        Args:
            coins: List of coins to analyze
            
        Returns:
            List of generated signals
        """
        signals = []
        
        for coin in coins:
            if not coin or not hasattr(coin, 'address'):
                continue
                
            # If we're simulating, update the coin's price and stats
            if self.simulate_price_movements:
                await self._simulate_price_movement(coin)
                
            # Skip coins with no price
            if coin.current_price <= 0:
                continue
                
            # Calculate volatility and momentum
            volatility = abs(coin.price_change_24h) if hasattr(coin, 'price_change_24h') else 0
            momentum = self._calculate_momentum(coin)
            volume = coin.volume_24h if hasattr(coin, 'volume_24h') else 0
            
            # Calculate base signal strength
            signal_strength = self._calculate_signal_strength(volatility, momentum, volume)
            
            # Apply confidence multiplier
            signal_strength *= self.confidence_multiplier
            
            # Cap strength at 0.95 to avoid automatic certainty
            signal_strength = min(0.95, signal_strength)
            
            # Decide signal type based on momentum direction
            signal_type = SignalType.HOLD
            reason = ""
            
            if signal_strength >= 0.6:  # Only generate BUY/SELL if confident enough
                if momentum > self.momentum_threshold:
                    signal_type = SignalType.BUY
                    reason = f"Strong positive momentum ({momentum:.2%}) with volatility: {volatility:.2%}"
                elif momentum < -self.momentum_threshold:
                    signal_type = SignalType.SELL
                    reason = f"Negative momentum ({momentum:.2%}) with volatility: {volatility:.2%}"
                else:
                    reason = f"Moderate momentum ({momentum:.2%}) - holding position"
            else:
                reason = f"Weak signal - insufficient data to make decision"
                
            # Only add non-HOLD signals or strong hold signals
            if signal_type != SignalType.HOLD or signal_strength > 0.8:
                signals.append(Signal(
                    type=signal_type,
                    strength=signal_strength,
                    coin=coin,
                    reason=reason,
                    strategy="SimpleStrategy"
                ))
                
        return signals
    
    async def _simulate_price_movement(self, coin: Coin) -> None:
        """
        Simulate price movement for a coin to generate more realistic signals
        for demonstration purposes
        
        Args:
            coin: The coin to update
        """
        # If this is a new coin, initialize
        if coin.address not in self.last_price_updates:
            self.last_price_updates[coin.address] = {
                'time': datetime.now(),
                'price': coin.current_price if coin.current_price > 0 else 0.00001,
                'direction': random.choice([-1, 1]),
                'trend_duration': random.randint(3, 10)
            }
            return
            
        # Get last update data
        last_update = self.last_price_updates[coin.address]
        time_diff = (datetime.now() - last_update['time']).total_seconds()
        
        # Only update every ~20 seconds
        if time_diff < 20:
            return
            
        # Determine if we should change trend direction
        trend_duration = last_update.get('trend_duration', 5)
        direction = last_update.get('direction', 1)
        
        # 20% chance to change direction on each update, or force change after trend_duration
        if random.random() < 0.2 or time_diff > trend_duration * 60:
            direction *= -1
            trend_duration = random.randint(3, 10)  # 3 to 10 minutes
            
        # Calculate price movement (0.5% to 5% change)
        base_volatility = random.uniform(0.005, 0.05) 
        price_change_pct = base_volatility * direction
        
        # Higher volatility for newer/smaller tokens
        if not coin.market_cap or coin.market_cap < 1000000:
            price_change_pct *= 3
            
        # For the first few updates, ensure some movement up to make trades interesting
        if len(self.last_price_updates) < 5 and random.random() < 0.7:
            price_change_pct = abs(price_change_pct)
            
        # Get current price or set a minimum if zero
        current_price = coin.current_price if coin.current_price > 0 else 0.00001
        
        # Calculate new price
        new_price = current_price * (1 + price_change_pct)
        
        # Update coin data
        coin.current_price = max(0.00001, new_price)  # Prevent zero/negative prices
        coin.price_change_24h = price_change_pct * 100
        
        # Update volume (random increase/decrease)
        if hasattr(coin, 'volume_24h'):
            volume_change = random.uniform(0.85, 1.15)
            coin.volume_24h = max(10, coin.volume_24h * volume_change) if coin.volume_24h else 1000
            
        # Update market cap based on new price
        if hasattr(coin, 'market_cap'):
            # Estimate total supply
            total_supply = coin.market_cap / last_update['price'] if last_update['price'] > 0 else 100000
            coin.market_cap = total_supply * new_price
            
        # Update last update data
        self.last_price_updates[coin.address] = {
            'time': datetime.now(),
            'price': new_price,
            'direction': direction,
            'trend_duration': trend_duration
        }
        
    def _calculate_momentum(self, coin: Coin) -> float:
        """
        Calculate momentum for a coin
        
        Args:
            coin: The coin to calculate momentum for
            
        Returns:
            Momentum value as a float
        """
        # If no price change data is available, use a randomized small value
        if not hasattr(coin, 'price_change_24h') or coin.price_change_24h == 0:
            if self.simulate_price_movements:
                return random.uniform(-0.02, 0.02)
            return 0
            
        # Convert percentage to decimal
        return coin.price_change_24h / 100
        
    def _calculate_signal_strength(self, volatility: float, momentum: float, volume: float) -> float:
        """
        Calculate signal strength based on volatility, momentum, and volume
        
        Args:
            volatility: Price volatility as a decimal (e.g., 0.05 for 5%)
            momentum: Price momentum as a decimal
            volume: 24h trading volume
            
        Returns:
            Signal strength as a float between 0 and 1
        """
        # Normalize inputs
        norm_volatility = min(1.0, volatility / (self.volatility_threshold * 2))
        norm_momentum = min(1.0, abs(momentum) / (self.momentum_threshold * 2))
        norm_volume = min(1.0, volume / (self.volume_threshold * 2))
        
        # For very low volume, reduce signal strength
        if volume < self.volume_threshold / 10:
            volume_factor = 0.5
        else:
            volume_factor = 1.0
            
        # Calculate combined strength
        strength = (norm_volatility * 0.3 + norm_momentum * 0.5 + norm_volume * 0.2) * volume_factor
        
        # Add some randomization for simulation purposes
        if self.simulate_price_movements:
            strength += random.uniform(-0.1, 0.1)
            
        # Ensure within 0-1 range
        return max(0.1, min(0.95, strength))
