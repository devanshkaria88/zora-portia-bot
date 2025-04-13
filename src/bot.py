"""
ZoraBot - A trading bot for Zora Network that integrates with Portia AI
"""
import asyncio
import logging
import os
import json
import time
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from .api.zora import ZoraClient
from .api.portia import PortiaClient
from .models.coin import Coin
from .models.signal import Signal, SignalType
from .strategies.registry import STRATEGY_REGISTRY
from .trading.agent import TradingAgent

logger = logging.getLogger(__name__)

class ZoraBot:
    """
    Zora trading bot main class
    """
    
    def __init__(
        self,
        use_websocket: bool = True,
        portia_enabled: bool = True,
        strategies: List[str] = None,
        update_interval: int = 60,
        wallet_address: Optional[str] = None,
        auto_trading: bool = False,
        max_trade_amount: float = 100.0,
        confidence_threshold: float = 0.75
    ):
        # Initialize API clients
        self.zora_client = ZoraClient()
        
        # Get Portia credentials from environment
        portia_api_key = os.environ.get("PORTIA_API_KEY")
        portia_api_url = os.environ.get("PORTIA_API_URL", "https://api.portia.ai/v1")
        
        self.portia_client = None
        if portia_enabled and portia_api_key and portia_api_url:
            self.portia_client = PortiaClient(
                api_key=portia_api_key,
                api_url=portia_api_url
            )
            logger.info("Portia AI integration enabled")
        else:
            logger.info("Portia AI integration disabled")
        
        # Bot configuration
        self.use_websocket = use_websocket
        self.portia_enabled = portia_enabled
        self.update_interval = update_interval
        self.wallet_address = wallet_address
        self.auto_trading = auto_trading
        self.realtime_mode = use_websocket
        self.websocket_mode = use_websocket
        self.ws_subscriptions = {}
        self.last_block_time = 0
        self.config = {
            'scan_interval': update_interval,
            'max_coins': 50,
            'use_websockets': use_websocket
        }
        
        # Initialize strategies
        self.strategies = []
        for strategy_name in strategies or ["SimpleStrategy"]:
            if strategy_name in STRATEGY_REGISTRY:
                strategy_class = STRATEGY_REGISTRY[strategy_name]
                self.strategies.append(strategy_class())
        
        # Initialize trading agent if wallet provided
        self.trading_agent = None
        if wallet_address:
            self.trading_agent = TradingAgent(
                wallet_address=wallet_address,
                zora_client=self.zora_client,
                auto_trading_enabled=auto_trading,
                confidence_threshold=confidence_threshold,
                max_trade_amount_usd=max_trade_amount
            )
        
        # Data stores
        self.coins_by_symbol = {}
        self.coins_by_address = {}
        self.tracked_coins = set()
        
        # Runtime state
        self.running = False
        self.last_update = None
        self.last_signals = []
        self.market_data = {}
        self.block_subscription_id = None
    
    def _get_tracked_coins(self) -> Set[str]:
        """Get the set of tracked coin addresses"""
        return self.tracked_coins
    
    async def _process_signals(self, signals: List[Signal]):
        """
        Process trading signals and execute trades if auto-trading is enabled
        
        Args:
            signals: List of trading signals to process
        """
        if not signals:
            return
            
        # Log signals
        for signal in signals:
            self._log_signal(signal)
            
        # If we have a trading agent and auto-trading is enabled, evaluate and execute trades
        if self.trading_agent and self.auto_trading:
            # Send signals to trading agent for evaluation
            trade_decisions = await self.trading_agent.evaluate_signals(signals)
            
            # Track if any trades were executed
            trades_executed = False
            
            # Execute trades
            for trade in trade_decisions:
                result = await self.trading_agent.execute_trade(trade)
                if result.get("success", False):
                    trades_executed = True
            
            # Display updated portfolio if trades were executed
            if trades_executed and self.trading_agent.portfolio:
                table = self.trading_agent.portfolio.get_table()
                wallet = self.wallet_address
                if wallet and len(wallet) > 10:
                    wallet_display = f"{wallet[:8]}...{wallet[-4:]}"
                else:
                    wallet_display = wallet
                    
                logger.info(f"\n💼 PORTFOLIO FOR {wallet_display}\n\n{table}\n")
                
    def _log_signal(self, signal: Signal):
        """Log a trading signal with appropriate formatting"""
        coin = signal.coin
        
        # Color-code based on signal type
        if signal.signal_type == SignalType.BUY:
            icon = "🟢"
            action = "BUY"
        elif signal.signal_type == SignalType.SELL:
            icon = "🔴"
            action = "SELL"
        else:
            icon = "⚪"
            action = "HOLD"
            
        # Format the message
        message = f"{icon} SIGNAL: {action} {coin.symbol} @ ${coin.current_price:.4f} | "
        
        # Add confidence if available
        if hasattr(signal, "confidence") and signal.confidence:
            message += f"Confidence: {signal.confidence:.2f} | "
            
        # Add reasoning if available
        if signal.reasoning:
            message += f"Reason: {signal.reasoning}"
            
        # Log at appropriate level based on signal type
        if signal.signal_type == SignalType.BUY or signal.signal_type == SignalType.SELL:
            logger.info(message)
        else:
            if self.log_hold_signals:
                logger.debug(message)
                
    def _log_trade(self, trade: Dict):
        """Log an executed trade with appropriate formatting"""
        coin = trade.get("coin")
        amount = trade.get("amount", 0)
        price = trade.get("price", 0)
        trade_type = trade.get("type", "UNKNOWN")
        success = trade.get("success", False)
        
        # Format the trade message
        if success:
            if trade_type == "BUY":
                icon = "✅"
                message = f"{icon} TRADE: BOUGHT {amount:.4f} {coin.symbol} @ ${price:.4f} | Total: ${amount * price:.2f}"
            else:
                icon = "💰"
                message = f"{icon} TRADE: SOLD {amount:.4f} {coin.symbol} @ ${price:.4f} | Total: ${amount * price:.2f}"
                
            logger.info(message)
        else:
            # Trade failed
            icon = "❌"
            reason = trade.get("error", "Unknown error")
            message = f"{icon} TRADE FAILED: {trade_type} {coin.symbol} - {reason}"
            logger.error(message)
    
    async def start(self):
        """
        Start the trading bot
        """
        logger.info("Starting Zora trading bot...")
        self.running = True
        
        # Initialize portfolio if we have a trading agent
        if self.trading_agent:
            wallet_display = f"{self.wallet_address[:8]}...{self.wallet_address[-4:]}" if len(self.wallet_address) > 12 else self.wallet_address
            logger.info(f"🔍 Fetching portfolio for wallet: {self.wallet_address}")
            
            # Update portfolio with real holdings from Zora
            await self.trading_agent.update_portfolio()
            
            # Display the portfolio
            if self.trading_agent.portfolio:
                portfolio_table = self.trading_agent.portfolio.get_table()
                if portfolio_table:
                    logger.info(f"\n💼 PORTFOLIO FOR {wallet_display}\n\n{portfolio_table}\n")
                    
                    # Display trading account status
                    logger.info(self.trading_agent.display_agent_status())
                    
                    # Add a note about simulated trades
                    if self.auto_trading:
                        logger.info("📝 NOTE: Trades will be simulated and won't affect your actual wallet holdings.")
                        await self.trading_agent.enable_auto_trading(True)
                else:
                    logger.info(f"No holdings found for wallet {wallet_display}")
        
        await self._init_market_data()
        
        # Set up the event loop
        if self.running:
            # Start the update loops
            asyncio.create_task(self._market_update_loop())
            asyncio.create_task(self._portfolio_update_loop())
            
            # If auto-trading is enabled, start the trading loop
            if self.auto_trading:
                asyncio.create_task(self._trading_loop())
    
    async def _init_market_data(self):
        """
        Initialize market data
        """
        logger.info("Initializing market data...")
        
        try:
            # Get list of tradable coins from Zora API
            tradable_coins = await self.zora_client.get_tradable_coins(limit=50)
            
            if not tradable_coins:
                logger.warning("No coins found to track")
                return
                
            # Reset tracking
            self.tracked_coins = []
            self.coins_by_address = {}
            
            # Add coins to tracking
            for coin in tradable_coins:
                self.tracked_coins.append(coin.address)
                self.coins_by_address[coin.address] = coin
                
            # Set up websocket subscriptions for each coin
            if self.websocket_mode and self.zora_client.ws_connection:
                await self._setup_coin_subscriptions()
                
            logger.info(f"✅ Tracking {len(self.tracked_coins)} coins on Zora")
        except Exception as e:
            logger.error(f"Error initializing market data: {e}")
    
    async def _market_update_loop(self):
        """
        Market update loop
        """
        while self.running:
            try:
                # Process market update
                await self._process_market_update()
                
                # Wait before next update
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error in market update loop: {e}")
                await asyncio.sleep(10)  # Sleep briefly before retrying
    
    async def _process_market_update(self):
        """
        Process market updates and generate signals
        """
        logger.info("Processing market update...")
        
        if not self.tracked_coins:
            await self._init_market_data()
            return
        
        update_count = 0
        updated_coins = []
        
        for address in self.tracked_coins:
            try:
                coin = self.coins_by_address.get(address)
                if not coin:
                    continue
                    
                # Update the coin data
                updated_coin = await self.zora_client.update_coin_data(coin)
                if updated_coin:
                    self.coins_by_address[address] = updated_coin
                    updated_coins.append(updated_coin)
                    update_count += 1
            except Exception as e:
                logger.error(f"Error updating coin {address}: {e}")
        
        if updated_coins:
            logger.info(f"Updated {update_count} coins")
    
    async def _portfolio_update_loop(self):
        """
        Portfolio update loop
        """
        while self.running:
            try:
                # Update portfolio if we have a trading agent
                if self.trading_agent:
                    await self.trading_agent.update_portfolio()
                    
                    # Display portfolio summary
                    portfolio = self.trading_agent.portfolio
                    if portfolio.holdings:
                        table = portfolio.display_as_table()
                        logger.info(f"\n📊 PORTFOLIO UPDATE\n{table}")
                
                # Wait before next update
                await asyncio.sleep(60)  # Update portfolio every minute
            except Exception as e:
                logger.error(f"Error in portfolio update loop: {e}")
                await asyncio.sleep(30)  # Sleep briefly before retrying
    
    async def _trading_loop(self):
        """
        Automated trading loop
        """
        logger.info("🤖 Starting automated trading loop")
        
        while self.running:
            try:
                # Make sure we have market data
                if not self.coins_by_address:
                    await self._init_market_data()
                    await asyncio.sleep(30)  # Wait for data to be initialized
                    continue
                
                # Generate trading signals for ALL coins, not just portfolio coins
                logger.info("⚙️ Analyzing market for trading opportunities...")
                all_signals = []
                
                # First, fetch more coins from Zora if we don't have many
                if len(self.coins_by_address) < 10:
                    logger.info("Fetching additional coins from Zora network...")
                    try:
                        more_coins = await self.zora_client.get_trending_coins(limit=20)
                        for coin in more_coins:
                            if coin.address not in self.coins_by_address:
                                self.coins_by_address[coin.address] = coin
                                self.tracked_coins.add(coin.address)
                        logger.info(f"Now tracking {len(self.coins_by_address)} coins")
                    except Exception as e:
                        logger.error(f"Error fetching trending coins: {e}")
                
                # Update each coin's price data (real or simulated)
                updated_coins = []
                for address, coin in self.coins_by_address.items():
                    try:
                        # Try to get real data first
                        updated = await self.zora_client.update_coin_data(coin)
                        
                        # If no real data, simulate some price movement
                        if not updated or updated.current_price <= 0:
                            # Start with a small price if none exists
                            if coin.current_price <= 0:
                                coin.current_price = 0.001
                                
                            # Simulate a random price movement
                            change_pct = random.uniform(-0.05, 0.10)  # -5% to +10%
                            new_price = coin.current_price * (1 + change_pct)
                            coin.current_price = max(0.0001, new_price)
                            coin.price_change_24h = change_pct * 100
                            
                            # Add volume data if missing
                            if not hasattr(coin, 'volume_24h') or coin.volume_24h <= 0:
                                coin.volume_24h = random.uniform(1000, 100000)
                                
                            updated = coin
                            
                        # Save the updated coin
                        self.coins_by_address[address] = updated
                        updated_coins.append(updated)
                        
                    except Exception as e:
                        logger.error(f"Error updating coin {address}: {e}")
                
                # Generate signals for ALL coins, not just portfolio coins
                logger.info(f"Analyzing {len(updated_coins)} coins for trading signals...")
                for strategy in self.strategies:
                    strategy_signals = await strategy.generate_signals(updated_coins)
                    all_signals.extend(strategy_signals)
                
                if all_signals:
                    logger.info(f"Generated {len(all_signals)} trading signals across {len(updated_coins)} coins")
                    
                    # Filter to valid signals
                    valid_signals = [s for s in all_signals if s.strength >= self.trading_agent.confidence_threshold]
                    
                    if valid_signals:
                        logger.info(f"{len(valid_signals)} signals passed confidence threshold")
                        
                        # Get trade decisions
                        trade_decisions = await self.trading_agent.evaluate_signals(valid_signals)
                        
                        # Execute trades if any
                        if trade_decisions:
                            logger.info(f"💱 Executing {len(trade_decisions)} trades")
                            await self.trading_agent.execute_trades(trade_decisions)
                        else:
                            logger.info("⏸️ No trades to execute at this time")
                    else:
                        logger.info("⏸️ No signals strong enough to trade on")
                else:
                    logger.info("⏸️ No trading signals generated")
                
                # Sleep between trading cycles
                await asyncio.sleep(60)  # Check for trades every minute
                
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(30)  # Sleep briefly before retrying
    
    async def stop(self):
        """Stop the trading bot"""
        logger.info("Stopping Zora trading bot...")
        self.running = False
        
        # Clean up WebSocket subscriptions
        if self.realtime_mode:
            try:
                for sub_id in list(self.ws_subscriptions.keys()):
                    await self.zora_client.ws_unsubscribe(sub_id)
                await self.zora_client.close_websocket()
            except Exception as e:
                logger.error(f"Error cleaning up WebSocket connections: {e}")
