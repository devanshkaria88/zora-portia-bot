"""
Configuration handling for Zora trading bot
"""
import os
import json
import logging
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

def load_config() -> Dict[str, Any]:
    """
    Load bot configuration from environment and config files
    
    Returns:
        Dictionary with configuration parameters
    """
    # Default configuration
    config = {
        "zora": {
            "api_key": os.environ.get("ZORA_API_KEY", ""),
            "api_url": os.environ.get("ZORA_API_URL", "https://api.zora.co/v1"),
            "websocket_url": os.environ.get("ZORA_WS_URL", "wss://api.zora.co/ws/v1")
        },
        "portia": {
            "api_key": os.environ.get("PORTIA_API_KEY", ""),
            "api_url": os.environ.get("PORTIA_API_URL", "https://api.portia.ai/v1")
        },
        "max_coins": 100,
        "scan_interval": 60,  # seconds
        "fetch_historical": True,
        "historical_timeframe": "1d",
        "historical_limit": 30,
        "max_signals_per_run": 5,
        "min_signal_strength": 0.7,
        "strategies": {
            "momentum": {
                "enabled": True,
                "rsi_period": 14,
                "rsi_overbought": 70,
                "rsi_oversold": 30,
                "macd_fast": 12,
                "macd_slow": 26,
                "macd_signal": 9,
                "volume_threshold": 3.0
            }
        }
    }
    
    # Try to load from config file
    config_path = os.environ.get("CONFIG_PATH", "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                file_config = json.load(f)
                # Merge configurations
                _deep_update(config, file_config)
            logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.error(f"Failed to load config file: {e}")
    
    return config

def _deep_update(target: Dict, source: Dict) -> Dict:
    """
    Recursively update a nested dictionary
    """
    for key, value in source.items():
        if isinstance(value, dict) and key in target and isinstance(target[key], dict):
            _deep_update(target[key], value)
        else:
            target[key] = value
    return target
