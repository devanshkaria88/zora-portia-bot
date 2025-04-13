"""
Tests for the main Zora trading bot class
"""
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from src.bot import ZoraBot
from src.models.coin import Coin
from src.models.signal import Signal, SignalType

class TestZoraBot(unittest.TestCase):
    """Test cases for the ZoraBot class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = {
            "zora": {
                "api_key": "test_api_key",
                "api_url": "https://test.api.zora.co"
            },
            "portia": {
                "api_key": "test_portia_key",
                "api_url": "https://test.api.portia.ai"
            },
            "strategies": {
                "momentum": {
                    "enabled": True
                }
            }
        }
        
    @patch('src.api.zora.ZoraClient')
    @patch('src.api.portia.PortiaClient')
    def test_bot_initialization(self, mock_portia, mock_zora):
        """Test that the bot initializes correctly"""
        bot = ZoraBot(self.config)
        
        # Check API clients are created
        mock_zora.assert_called_once_with(
            api_key=self.config['zora']['api_key'], 
            api_url=self.config['zora']['api_url']
        )
        mock_portia.assert_called_once_with(
            api_key=self.config['portia']['api_key'], 
            api_url=self.config['portia']['api_url']
        )
        
        # Check strategies are initialized
        self.assertEqual(len(bot.strategies), 1)
        
    @patch('src.api.zora.ZoraClient')
    @patch('src.api.portia.PortiaClient')
    @patch('src.strategies.momentum.MomentumStrategy.evaluate')
    async def test_generate_signals(self, mock_evaluate, mock_portia, mock_zora):
        """Test that the bot generates signals correctly"""
        # Setup
        bot = ZoraBot(self.config)
        
        coin = Coin(
            id="test-coin-1",
            symbol="TEST",
            name="Test Coin",
            creator_id="creator-1",
            price=10.0,
            volume_24h=1000.0,
            price_change_24h=5.0,
            created_at="2023-01-01T00:00:00Z"
        )
        
        mock_signal = Signal(
            type=SignalType.BUY,
            coin_id=coin.id,
            price=coin.price,
            strength=0.8,
            reason="Test signal"
        )
        
        # Configure the mock to return our test signal
        mock_evaluate.return_value = mock_signal
        
        # Execute
        signals = bot._generate_signals([coin])
        
        # Assert
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].coin_id, "test-coin-1")
        self.assertEqual(signals[0].type, SignalType.BUY)
        
    @patch('src.api.zora.ZoraClient')
    @patch('src.api.portia.PortiaClient')
    async def test_apply_risk_filters(self, mock_portia, mock_zora):
        """Test that risk filters are applied correctly"""
        # Setup
        bot = ZoraBot(self.config)
        bot.config['min_signal_strength'] = 0.7
        bot.config['max_signals_per_run'] = 2
        
        signals = [
            Signal(type=SignalType.BUY, coin_id="coin1", price=10.0, strength=0.9, reason="Strong signal"),
            Signal(type=SignalType.BUY, coin_id="coin2", price=20.0, strength=0.8, reason="Good signal"),
            Signal(type=SignalType.BUY, coin_id="coin3", price=30.0, strength=0.6, reason="Weak signal"),
            Signal(type=SignalType.SELL, coin_id="coin4", price=40.0, strength=0.75, reason="Medium signal")
        ]
        
        # Execute
        filtered = bot._apply_risk_filters(signals)
        
        # Assert
        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0].coin_id, "coin1")  # Strongest signal
        self.assertEqual(filtered[1].coin_id, "coin2")  # Second strongest
        # coin3 is filtered out (too weak)
        # coin4 is filtered out (exceeds max signals)

# Run the tests
if __name__ == '__main__':
    unittest.main()
