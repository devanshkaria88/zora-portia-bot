# Trading Strategies (Continued)

## Price Simulation (Continued)

For testing or demo purposes, strategies can simulate price movements:

```python
async def _simulate_price_movement(self, coin: Coin) -> None:
    """
    Simulate price movement for a coin
    """
    # Get last update data
    last_update = self.last_price_updates.get(coin.address, {
        'time': datetime.now(),
        'price': coin.current_price if coin.current_price > 0 else 0.00001,
        'direction': random.choice([-1, 1]),
        'trend_duration': random.randint(3, 10)
    })
    
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
        
    # Calculate new price
    new_price = coin.current_price * (1 + price_change_pct)
    
    # Update coin data
    coin.current_price = max(0.00001, new_price)  # Prevent zero/negative prices
    coin.price_change_24h = price_change_pct * 100
```

This simulation creates realistic price movements for testing strategy performance without requiring real market data.

## Strategy Implementation Details

### Signal Strength Calculation

Strategies calculate signal strength based on multiple factors:

```python
def _calculate_signal_strength(self, volatility: float, momentum: float, volume: float) -> float:
    """
    Calculate signal strength based on volatility, momentum, and volume
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
        
    # Calculate combined strength (weighted average)
    strength = (norm_volatility * 0.3 + norm_momentum * 0.5 + norm_volume * 0.2) * volume_factor
    
    # Ensure within 0-1 range
    return max(0.1, min(0.95, strength))
```

### Momentum Calculation

```python
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
```

## Strategy Registry

The strategy registry maintains a mapping of strategy names to their implementation classes:

```python
# Registry of available strategies
STRATEGY_REGISTRY = {
    "SimpleStrategy": SimpleStrategy,
    "MomentumStrategy": MomentumStrategy,
    "TrendFollowingStrategy": TrendFollowingStrategy,
    # Add more strategies here
}
```

This allows strategies to be dynamically loaded by name:

```python
strategy_name = "SimpleStrategy"
if strategy_name in STRATEGY_REGISTRY:
    strategy_class = STRATEGY_REGISTRY[strategy_name]
    strategy = strategy_class()
```

## Custom Strategy Development

To create a custom strategy:

1. Create a new file in `src/strategies/`
2. Implement the strategy class with a `generate_signals` method
3. Register the strategy in `src/strategies/registry.py`

Example of a custom strategy:

```python
from ..models.coin import Coin
from ..models.signal import Signal, SignalType

class MyCustomStrategy:
    """
    Custom trading strategy implementation
    """
    
    def __init__(self, my_param: float = 0.05):
        self.my_param = my_param
        
    async def generate_signals(self, coins: list[Coin]) -> list[Signal]:
        """Generate trading signals based on custom logic"""
        signals = []
        
        for coin in coins:
            # Implement custom signal logic here
            if custom_condition:
                signals.append(Signal(
                    type=SignalType.BUY,
                    coin=coin,
                    strength=0.75,
                    reason="Custom buy condition met",
                    strategy="MyCustomStrategy"
                ))
            
        return signals
```

## Strategy Visualization and Logging

The bot includes a colored visualization of signals in the console output:

```
🟢 SIGNAL: BUY ZORA @ $245.73 | Confidence: 0.92 | Reason: Strong uptrend with 15.4% gain, high trading volume, extremely bullish pattern
🔴 SIGNAL: SELL GFXC @ $32.75 | Confidence: 0.85 | Reason: Bearish pattern with 8.2% drop, decreasing trading volume, support level broken
⚪ SIGNAL: HOLD ZUSD @ $1.002 | Confidence: 0.55 | Reason: Stable price with minimal volatility, monitoring for changes
```

## Strategy Performance Metrics

The bot tracks strategy performance through the trading history:

```python
# Get all trades executed from a specific strategy
strategy_trades = [t for t in agent.trading_history if t.get("strategy") == "SimpleStrategy"]

# Calculate performance
strategy_pnl = sum(t["profit_loss"] for t in strategy_trades)
win_rate = len([t for t in strategy_trades if t["profit_loss"] > 0]) / len(strategy_trades)
```

## Multi-Strategy Approach

The bot can run multiple strategies simultaneously:

```python
# Configure multiple strategies
strategies = [
    SimpleStrategy(volatility_threshold=0.03),
    MomentumStrategy(momentum_threshold=0.02)
]

# Collect signals from all strategies
all_signals = []
for strategy in strategies:
    strategy_signals = await strategy.generate_signals(coins)
    all_signals.extend(strategy_signals)
```

## Strategy Optimization

Strategies can be optimized by adjusting their parameters:

1. **Backtesting**: Test strategies against historical data to find optimal parameters
2. **Parameter Tuning**: Adjust thresholds for volatility, momentum, and volume
3. **Environment Adaptation**: Modify strategy behavior based on market conditions

## Future Strategy Development

Potential future strategies include:

1. **AI-Powered Strategy**: Integrate with Portia AI for advanced prediction models
2. **Social Sentiment Strategy**: Consider social media sentiment in trading decisions
3. **Arbitrage Strategy**: Exploit price differences across exchanges
4. **Market Maker Strategy**: Provide liquidity and profit from bid-ask spreads
5. **Swing Trading Strategy**: Capture medium-term price swings

## Strategy Selection Guide

| Strategy | Market Condition | Risk Level | Time Horizon |
|----------|------------------|------------|--------------|
| SimpleStrategy | All markets | Low-Medium | Short-term |
| MomentumStrategy | Trending markets | Medium | Short to Medium |
| VolatilityStrategy | Volatile markets | High | Very Short |
| TrendFollowingStrategy | Strong trends | Medium | Medium-term |

Choose strategies based on your risk tolerance and market conditions.

## Best Practices

1. **Start with Simulation**: Always test strategies in simulation mode first
2. **Diversify Strategies**: Use multiple strategies for different market conditions
3. **Monitor Performance**: Regularly evaluate strategy performance
4. **Adjust Parameters**: Fine-tune strategy parameters based on results
5. **Start Small**: When moving to real trading, start with small amounts
