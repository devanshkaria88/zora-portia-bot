"""
Technical analysis utility functions
"""
import numpy as np
from typing import Tuple

def calculate_rsi(prices: list, period: int = 14) -> np.ndarray:
    """
    Calculate Relative Strength Index
    
    Args:
        prices: List of price values
        period: RSI calculation period
        
    Returns:
        NumPy array of RSI values
    """
    if len(prices) <= period:
        return np.array([])
    
    # Convert to numpy array
    price_array = np.array(prices)
    
    # Calculate price changes
    deltas = np.diff(price_array)
    
    # Initialize arrays
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    rs = up / down if down != 0 else float('inf')
    rsi = np.zeros_like(price_array)
    rsi[:period] = 100. - 100. / (1. + rs)
    
    # Calculate RSI
    for i in range(period, len(price_array)):
        delta = deltas[i-1]
        
        if delta > 0:
            upval = delta
            downval = 0.
        else:
            upval = 0.
            downval = -delta
            
        up = (up * (period - 1) + upval) / period
        down = (down * (period - 1) + downval) / period
        
        rs = up / down if down != 0 else float('inf')
        rsi[i] = 100. - 100. / (1. + rs)
    
    return rsi

def calculate_macd(
    prices: list, 
    fast_period: int = 12, 
    slow_period: int = 26, 
    signal_period: int = 9
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Calculate MACD (Moving Average Convergence Divergence)
    
    Args:
        prices: List of price values
        fast_period: Fast EMA period
        slow_period: Slow EMA period
        signal_period: Signal line period
        
    Returns:
        Tuple of (MACD line, signal line, histogram)
    """
    if len(prices) <= slow_period + signal_period:
        return np.array([]), np.array([]), np.array([])
    
    # Convert to numpy array
    price_array = np.array(prices)
    
    # Calculate EMAs
    ema_fast = calculate_ema(price_array, fast_period)
    ema_slow = calculate_ema(price_array, slow_period)
    
    # Calculate MACD line
    macd_line = ema_fast - ema_slow
    
    # Calculate signal line
    signal_line = calculate_ema(macd_line, signal_period)
    
    # Calculate histogram
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram

def calculate_ema(values: np.ndarray, period: int) -> np.ndarray:
    """
    Calculate Exponential Moving Average
    
    Args:
        values: NumPy array of values
        period: EMA period
        
    Returns:
        NumPy array of EMA values
    """
    if len(values) < period:
        return np.array([])
    
    # Initialize with SMA
    ema = np.zeros_like(values)
    ema[:period] = np.mean(values[:period])
    
    # Calculate multiplier
    multiplier = 2.0 / (period + 1)
    
    # Calculate EMA
    for i in range(period, len(values)):
        ema[i] = (values[i] - ema[i-1]) * multiplier + ema[i-1]
    
    return ema
