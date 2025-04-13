#!/usr/bin/env python3
"""
Main entry point to run the Zora trading bot
"""
import asyncio
import logging
import sys
import argparse
import json
import os
from dotenv import load_dotenv
from src.bot import ZoraBot
from src.api.zora import ZoraClient
from src.trading.agent import TradingAgent
from src.strategies.simple import SimpleStrategy
from src.utils.logging import setup_logging, setup_signals_only_logging, setup_quiet_trading_logging

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Zora Network Trading Bot')
    
    # Portfolio and market options
    parser.add_argument('--signals-only', action='store_true', help='Only display signals, do not execute trades')
    parser.add_argument('--wallet', type=str, help='Wallet address to track')
    
    # Trading options
    parser.add_argument('--auto-trade', action='store_true', help='Enable automatic trading')
    parser.add_argument('--max-trade-amount', type=float, default=100.0, help='Maximum trade amount in USD (default: 100)')
    parser.add_argument('--confidence', type=float, default=0.75, help='Confidence threshold for executing trades (0-1, default: 0.75)')
    parser.add_argument('--mock-capital', type=float, default=1000.0, help='Mock capital for simulated trading (default: $1000)')
    
    # Strategy options
    parser.add_argument('--strategies', type=str, default='SimpleStrategy', help='Comma-separated list of trading strategies to use')
    
    # Connection options
    parser.add_argument('--no-websocket', action='store_true', help='Disable WebSocket connection (use polling)')
    
    args = parser.parse_args()
    return args

async def start_bot(bot):
    """Start the bot and keep it running"""
    try:
        # Start the bot
        await bot.start()
        
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received, shutting down...")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        # Always clean up
        await bot.stop()

async def main():
    """Main entry point for the Zora trading bot"""
    # Parse command-line arguments
    args = parse_arguments()
    
    # Set up logging based on mode
    if args.signals_only:
        setup_signals_only_logging(log_file="zora_bot.log")
    else:
        setup_quiet_trading_logging(log_file="zora_bot.log")
    
    logger = logging.getLogger(__name__)
    logger.info("Starting Zora trading bot")
    
    # Parse strategies
    strategies = args.strategies.split(',') if args.strategies else ["SimpleStrategy"]
    
    # Validate wallet address if provided
    if args.auto_trade and not args.wallet:
        logger.error("Auto trading requires a wallet address (use --wallet)")
        return
    
    # Load configuration
    config_path = os.environ.get("CONFIG_PATH", "config.json")
    try:
        with open(config_path, 'r') as file:
            config = json.load(file)
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        logger.info("Using default configuration")
        config = {
            "zora": {
                "rpc_url": "https://rpc.zora.energy/"
            },
            "portia": {
                "api_url": "https://api.portia.ai/v1"
            },
            "max_coins": 50,
            "scan_interval": 120,
            "strategies": {
                "momentum": {
                    "enabled": True
                }
            }
        }
    
    # Check for required RPC URL
    if not config.get('zora', {}).get('rpc_url') and not os.environ.get("ZORA_RPC_URL"):
        logger.error("Zora RPC URL not found in environment or config")
        return
    
    # Initialize components
    zora_client = ZoraClient()
    
    # Generate some simulated market data to ensure we have coins to trade
    from src.models.coin import Coin
    import random
    
    # Create simulated trending coins
    logger.info("Generating simulated market data for trading demonstration...")
    trending_coins = []
    coin_names = [
        "ZoraCoin", "BaseToken", "MemeDAO", "AstroFinance", "MetaverseToken",
        "DeFiYield", "PixelArt", "EcoDAO", "ZoraVerse", "ChainNation"
    ]
    
    # Generate 10 simulated coins with realistic price movements
    for i, name in enumerate(coin_names):
        symbol = "".join([word[0] for word in name.split()])
        address = f"0x{''.join([random.choice('0123456789abcdef') for _ in range(40)])}"
        price = random.uniform(0.5, 100.0)
        
        coin = Coin(
            id=address,
            address=address,
            symbol=symbol,
            name=name,
            creator_address="0x" + "".join([random.choice("0123456789abcdef") for _ in range(40)]),
            current_price=price,
            volume_24h=random.uniform(10000, 1000000),
            price_change_24h=random.uniform(-10, 20),
            created_at="2025-01-01T00:00:00Z",
            market_cap=price * random.uniform(100000, 10000000)
        )
        trending_coins.append(coin)
    
    # Create trading agent
    trading_agent = TradingAgent(
        wallet_address=args.wallet,
        zora_client=zora_client,
        confidence_threshold=args.confidence,  # Minimum confidence to execute a trade
        max_trade_amount_usd=args.max_trade_amount,   # Max trade size in USD
        simulate=True,              # Always simulate trades
        mock_capital=args.mock_capital  # Use the provided mock capital amount
    )
    
    # Create trading strategies
    strategy_list = []
    for strategy in strategies:
        if strategy == "SimpleStrategy":
            strategy_list.append(SimpleStrategy(
                volatility_threshold=0.03,   # 3% price change is significant 
                momentum_threshold=0.02,     # 2% momentum threshold
                volume_threshold=500,        # Minimum volume to consider
                confidence_multiplier=1.0,   # Standard confidence level
                simulate_price_movements=True  # Generate price movements for simulation
            ))
        else:
            logger.error(f"Unknown strategy: {strategy}")
            return
    
    # Create bot instance with parsed options
    bot = ZoraBot(
        use_websocket=not args.no_websocket,
        strategies=strategy_list,
        update_interval=60,
        wallet_address=args.wallet,
        auto_trading=args.auto_trade,
        max_trade_amount=args.max_trade_amount,
        confidence_threshold=args.confidence
    )
    
    # Add the simulated coins to the bot for trading
    for coin in trending_coins:
        bot.coins_by_address[coin.address] = coin
        bot.tracked_coins.add(coin.address)
    
    logger.info(f"Added {len(trending_coins)} simulated coins to the market for trading demonstration")
    
    # Initialize the trading agent with mock capital if auto-trading is enabled
    if args.auto_trade and bot.trading_agent:
        # Set mock capital for simulated trading
        bot.trading_agent.mock_capital = args.mock_capital
        bot.trading_agent.mock_cash_balance = args.mock_capital
        bot.trading_agent.auto_trading_enabled = True
        logger.info(f"💰 Using ${args.mock_capital:.2f} mock capital for simulated trading")
    
    # Start with demo signals if requested
    if args.signals_only:
        # Generate demo signals to demonstrate the colored output
        await generate_demo_signals(bot)
    
    # Start the bot directly
    try:
        # Start the bot
        await bot.start()
        
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received, shutting down...")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        # Always clean up
        await bot.stop()

async def generate_demo_signals(bot):
    """Generate demo signals to show colored output"""
    from src.models.coin import Coin
    from src.models.signal import Signal, SignalType
    from colorama import Fore, Style
    
    # Create some demo coins
    coins = []
    coin_data = [
        {
            "id": "0x823b92d6a4b2aed4b15675c7917c9f922ea8adad",
            "name": "ZoraUSD Stablecoin",
            "symbol": "ZUSD",
            "current_price": 1.002,
            "price_change_24h": 0.2,
            "volume": 1250000,
            "sentiment": 0.65
        },
        {
            "id": "0x7ce9c67c8a1d65ce61fc464727cc0f9caabf92b9",
            "name": "Zora Ecosystem Token",
            "symbol": "ZORA",
            "current_price": 245.73,
            "price_change_24h": 15.4,
            "volume": 8750000,
            "sentiment": 0.85
        },
        {
            "id": "0x92e52a1a235d9a103d970901066ce910aacefd37",
            "name": "Graphics NFT Collection",
            "symbol": "GFXC",
            "current_price": 32.75,
            "price_change_24h": -8.2,
            "volume": 650000,
            "sentiment": 0.40
        },
        {
            "id": "0x438d9fbea26a7c6c719a4a4ed99b709f27b0df6b",
            "name": "Decentralized Governance",
            "symbol": "DGOV",
            "current_price": 18.93,
            "price_change_24h": -4.1,
            "volume": 475000,
            "sentiment": 0.48
        },
        {
            "id": "0xb1a7e43a9c5f4a6c93d5b6712eadf2c5b3653130",
            "name": "Social Media Platform",
            "symbol": "SOCIAL",
            "current_price": 8.45,
            "price_change_24h": 1.8,
            "volume": 325000,
            "sentiment": 0.62
        }
    ]
    
    for data in coin_data:
        coin = Coin(
            id=data["id"],
            address=data["id"],
            symbol=data["symbol"],
            name=data["name"],
            creator_address="0x0000000000000000000000000000000000000000",
            current_price=data["current_price"],
            volume_24h=data["volume"],
            price_change_24h=data["price_change_24h"],
            created_at="2025-01-01T00:00:00Z",
            market_cap=data["current_price"] * 1000000
        )
        
        # Add AI sentiment for demo
        coin.ai_sentiment = data["sentiment"]
        
        coins.append(coin)
    
    # Create a variety of demo signals
    signals = []
    
    # BUY signals with varying strengths
    signals.append(Signal(
        type=SignalType.BUY,
        coin=coins[1],  # ZORA token
        strength=0.92,
        reason="Strong uptrend with 15.4% gain, high trading volume, extremely bullish pattern",
        strategy="Momentum Strategy"
    ))
    
    signals.append(Signal(
        type=SignalType.BUY,
        coin=coins[4],  # SOCIAL token
        strength=0.76,
        reason="Breaking resistance level, moderate growth with healthy volume",
        strategy="Simple Strategy"
    ))
    
    # SELL signals with varying strengths
    signals.append(Signal(
        type=SignalType.SELL,
        coin=coins[2],  # GFXC token
        strength=0.85,
        reason="Bearish pattern with 8.2% drop, decreasing trading volume, support level broken",
        strategy="Technical Analysis"
    ))
    
    signals.append(Signal(
        type=SignalType.SELL,
        coin=coins[3],  # DGOV token
        strength=0.67,
        reason="Negative momentum, sustained price decline over multiple days",
        strategy="Momentum Strategy"
    ))
    
    # HOLD signal
    signals.append(Signal(
        type=SignalType.HOLD,
        coin=coins[0],  # ZUSD stablecoin
        strength=0.55,
        reason="Stable price with minimal volatility, monitoring for changes",
        strategy="Volatility Strategy"
    ))
    
    # Process the signals to display them with colors
    logger = logging.getLogger(__name__)
    logger.info("🚀 ZORA TRADING BOT - SIGNAL DASHBOARD 🚀")
    logger.info("===========================================")
    await bot._process_signals(signals)
    logger.info("===========================================")

if __name__ == "__main__":
    asyncio.run(main())
