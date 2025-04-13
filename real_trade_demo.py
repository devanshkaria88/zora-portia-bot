#!/usr/bin/env python
"""
Zora SDK Trading Integration Demo

This script demonstrates the full integration of Zora SDK for real token trading.
It showcases both simulated and real trading modes with colorful CLI output.
"""
import os
import json
import asyncio
import argparse
import logging
import sys
from datetime import datetime
import colorama
from colorama import Fore, Style

from src.api.zora import ZoraClient
from src.trading.agent import TradingAgent
from src.trading.zora_trader import ZoraSDKTrader
from src.models.signal import Signal, SignalType
from src.models.coin import Coin
from src.models.portfolio import Portfolio

# Set up colorful logging
class ColoredFormatter(logging.Formatter):
    """Custom formatter to add colors to log messages based on level"""
    
    COLORS = {
        'DEBUG': Fore.BLUE,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT
    }
    
    ICONS = {
        'DEBUG': '🔍',
        'INFO': 'ℹ️',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🚨'
    }
    
    def format(self, record):
        # Get the original formatted message
        formatted_msg = super().format(record)
        
        # Add color based on level
        levelname = record.levelname
        color = self.COLORS.get(levelname, '')
        icon = self.ICONS.get(levelname, '')
        
        # Add special formatting for specific message types
        if "TRADE" in formatted_msg:
            icon = "💱"  # Trade icon
        elif "WebSocket" in formatted_msg:
            icon = "🔌"  # WebSocket icon
        elif "block" in formatted_msg.lower():
            icon = "⛓️"  # Blockchain icon
        elif "portfolio" in formatted_msg.lower():
            icon = "💼"  # Portfolio icon
        elif "allowance" in formatted_msg.lower():
            icon = "🔓"  # Allowance icon
        elif "swap" in formatted_msg.lower():
            icon = "🔄"  # Swap icon
        elif "price" in formatted_msg.lower():
            icon = "💰"  # Price icon
            
        return f"{icon} {color}{formatted_msg}{Style.RESET_ALL}"

# Configure colorful logging
def setup_logger():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColoredFormatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s", "%H:%M:%S"))
    
    root_logger.handlers = []  # Remove any existing handlers
    root_logger.addHandler(console_handler)
    
    # Set specific module loggers
    for module in ["src.api.zora", "src.trading.agent", "src.trading.zora_trader"]:
        logging.getLogger(module).setLevel(logging.INFO)

# Parse command line arguments
parser = argparse.ArgumentParser(description='Zora SDK Trading Integration Demo')
parser.add_argument('--wallet', type=str, default="0x53dae6e4b5009c1d5b64bee9cb42118914db7e66", 
                    help='Wallet address to use')
parser.add_argument('--config', type=str, default="config.json",
                    help='Path to configuration file')
parser.add_argument('--simulate', action='store_true', default=True,
                    help='Run in simulation mode (no actual transactions)')
parser.add_argument('--mock-capital', type=float, default=5000.0,
                    help='Amount of mock capital to use for trading')
parser.add_argument('--real', action='store_true',
                    help='Enable real trading (requires private key)')
args = parser.parse_args()

# Sample tokens for demo
SAMPLE_TOKENS = [
    {
        "name": "ZoraCoin",
        "symbol": "ZOR",
        "address": "0x7e07e15d2a87a24492740d16f5bdf58c16db0c4e",
        "price": 45.75,
        "price_change": 8.5
    },
    {
        "name": "BaseToken",
        "symbol": "BASE",
        "address": "0x940915d1f369c41af4c1d6bcc731a4e369c8ebc7",
        "price": 120.32,
        "price_change": -3.2
    },
    {
        "name": "MemeDAO",
        "symbol": "MEME",
        "address": "0x8b5cf5c8225055d6845d18cd4160f8d2b3349367",
        "price": 2.45,
        "price_change": 15.7
    }
]

def load_config(config_path):
    """Load configuration from file or create default"""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Create default config
        return {
            "wallet_address": args.wallet,
            "rpc_url": "https://rpc.zora.energy/",
            "chain_id": 8453,
            "api_key": "",
            "trading": {
                "auto_trade": True,
                "simulated": True,
                "strategy": "simple",
                "mock_capital": args.mock_capital,
                "max_trade_amount": 100.0,
                "confidence_threshold": 0.65
            }
        }

def create_sample_tokens():
    """Create sample token objects for demo"""
    tokens = []
    for token_data in SAMPLE_TOKENS:
        coin = Coin(
            id=token_data["address"],
            address=token_data["address"],
            symbol=token_data["symbol"],
            name=token_data["name"],
            creator_address="0x" + "".join(["0" for _ in range(40)]),
            current_price=token_data["price"],
            price_change_24h=token_data["price_change"],
            volume_24h=1000000,
            created_at=datetime.now().isoformat(),
            market_cap=token_data["price"] * 1000000
        )
        tokens.append(coin)
    return tokens

async def demo_trading_agent():
    """Demonstrate the Trading Agent with Zora SDK integration"""
    logger = logging.getLogger("demo")
    logger.info(f"Starting Zora SDK Trading Demo")
    
    # Load configuration
    config = load_config(args.config)
    
    # Override with command line args
    wallet_address = args.wallet or config.get("wallet_address")
    mock_capital = args.mock_capital or config.get("trading", {}).get("mock_capital", 5000.0)
    simulate = not args.real and config.get("trading", {}).get("simulated", True)
    
    logger.info(f"Using wallet: {wallet_address}")
    logger.info(f"Mock capital: ${mock_capital:.2f}")
    logger.info(f"Trading mode: {'SIMULATED' if simulate else 'REAL'}")
    
    # Get private key if real trading
    private_key = None
    if not simulate:
        private_key = os.environ.get("WALLET_PRIVATE_KEY")
        if not private_key:
            logger.error("🔒 Private key not found but real trading requested. Set WALLET_PRIVATE_KEY environment variable.")
            logger.warning("⚠️ Falling back to simulation mode")
            simulate = True
    
    # Create Zora client
    zora_client = ZoraClient(
        rpc_url=config.get("rpc_url"),
        api_key=config.get("api_key")
    )
    
    # Initialize trading agent
    agent = TradingAgent(
        wallet_address=wallet_address,
        zora_client=zora_client,
        auto_trading_enabled=True,
        confidence_threshold=config.get("trading", {}).get("confidence_threshold", 0.65),
        max_trade_amount_usd=config.get("trading", {}).get("max_trade_amount", 100.0),
        simulate=simulate,
        mock_capital=mock_capital,
        private_key=private_key
    )
    
    # Display header
    print("\n" + "="*80)
    print(f"{Fore.CYAN}ZORA NETWORK TRADING DEMO WITH SDK INTEGRATION{Style.RESET_ALL}")
    print("="*80 + "\n")
    
    # Initialize portfolio and add a token
    logger.info("Initializing portfolio...")
    await agent.update_portfolio()
    
    # Show initial portfolio status
    logger.info("📊 Initial trading account status")
    print(agent.display_agent_status())
    
    # Create sample tokens
    sample_tokens = create_sample_tokens()
    
    # Generate and execute sample trades
    logger.info("🔍 Generating sample trading signals...")
    
    # Add tokens to portfolio
    for token in sample_tokens:
        # Add a small amount of each token to portfolio
        agent.portfolio.add_holding(
            coin=token,
            amount=10.0,
            avg_purchase_price=token.current_price * 0.95  # Slight profit
        )
    
    # Update mock cash balance
    agent.mock_cash_balance -= 1000  # Assume the tokens cost $1000
    
    # Show portfolio status after adding tokens
    logger.info("📊 Portfolio after adding sample tokens")
    print(agent.portfolio.display_as_table())
    print(agent.display_agent_status())
    
    # Generate buy and sell signals
    logger.info("⚡ Generating trading signals...")
    signals = []
    
    # Buy signal for first token if price change is positive
    if sample_tokens[0].price_change_24h > 0:
        buy_signal = Signal(
            type=SignalType.BUY,
            strength=0.85,
            reason=f"Strong momentum: +{sample_tokens[0].price_change_24h:.2f}%",
            coin=sample_tokens[0],
            strategy="DemoStrategy"
        )
        signals.append(buy_signal)
    
    # Sell signal for another token if price change is negative
    for token in sample_tokens:
        if token.price_change_24h < 0:
            sell_signal = Signal(
                type=SignalType.SELL,
                strength=0.80,
                reason=f"Negative momentum: {token.price_change_24h:.2f}%",
                coin=token,
                strategy="DemoStrategy"
            )
            signals.append(sell_signal)
            break
    
    # Process signals
    if signals:
        logger.info(f"📊 Processing {len(signals)} trading signals")
        trade_decisions = await agent.evaluate_signals(signals)
        
        if trade_decisions:
            logger.info(f"📝 Executing {len(trade_decisions)} trades")
            for decision in trade_decisions:
                result = await agent.execute_trade(decision)
                if result["success"]:
                    logger.info(f"✅ Trade executed: {result['type']} {result.get('amount', 0):.4f} {result['coin'].symbol} @ ${result.get('price', 0):.2f}")
                    if not simulate and result.get("transaction_hash"):
                        logger.info(f"🔗 Transaction hash: {result['transaction_hash']}")
                else:
                    logger.error(f"🛑 Trade failed: {result.get('error', 'Unknown error')}")
        else:
            logger.info("🤔 No trade decisions generated from signals")
    else:
        logger.info("🤷 No trading signals generated")
    
    # Show final portfolio status
    logger.info("📊 Final portfolio status")
    print(agent.portfolio.display_as_table())
    print(agent.display_agent_status())
    
    # Show trading history
    if agent.trading_history:
        logger.info("📜 Trading history")
        for i, trade in enumerate(agent.trading_history, 1):
            trade_color = Fore.GREEN if trade["type"] == "BUY" else Fore.RED
            logger.info(f"{i}. {trade_color}{trade['type']}{Style.RESET_ALL} {trade['amount']:.4f} {trade['coin']} @ ${trade['price']:.2f} (${trade['value']:.2f})")
    
    logger.info("Demo completed! 🎉")

if __name__ == "__main__":
    colorama.init(autoreset=True)
    setup_logger()
    try:
        asyncio.run(demo_trading_agent())
    except KeyboardInterrupt:
        print("\nDemo stopped by user")
    except Exception as e:
        logging.error(f"Error in demo: {e}")
