#!/usr/bin/env python
"""
Zora Network Autonomous Trading Bot

This script demonstrates the autonomous trading capabilities of the Zora SDK integration.
It will monitor the market and execute trades based on signals without manual intervention.
"""
import os
import json
import asyncio
import logging
import sys
import time
import random
from datetime import datetime, timedelta
import colorama
from colorama import Fore, Style
from dotenv import load_dotenv
from web3 import Web3

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
        elif "signal" in formatted_msg.lower():
            icon = "📈"  # Signal icon
        elif "transaction" in formatted_msg.lower():
            icon = "📝"  # Transaction icon
            
        return f"{icon} {color}{formatted_msg}{Style.RESET_ALL}"

# Configure logging
def setup_logger():
    """Set up colorful logging"""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColoredFormatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s", "%H:%M:%S"))
    
    # Remove any existing handlers
    root_logger.handlers = []
    root_logger.addHandler(console_handler)
    
    # Set specific module loggers
    for module in ["src.api.zora", "src.trading.agent", "src.trading.zora_trader"]:
        logging.getLogger(module).setLevel(logging.INFO)
    
    return logging.getLogger("auto_trader")

# Load environment variables and configuration
load_dotenv()

# Constants and configuration
PRIVATE_KEY = os.environ.get("WALLET_PRIVATE_KEY")
if not PRIVATE_KEY:
    print(f"{Fore.RED}Error: WALLET_PRIVATE_KEY not found in environment variables{Style.RESET_ALL}")
    sys.exit(1)

WALLET_ADDRESS = Web3.to_checksum_address("0x53dae6e4b5009c1d5b64bee9cb42118914db7e66")
ZORA_RPC = os.environ.get("ZORA_RPC_URL", "https://rpc.zora.energy/")
WETH_ADDRESS = Web3.to_checksum_address("0x4200000000000000000000000000000000000006")  # WETH on Zora
USDC_ADDRESS = Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")  # USDC on Base

# Settings
TRADE_INTERVAL = 60  # seconds between market checks 
TRADE_AMOUNT_USD = 0.5  # Very small amount for test trades
MAX_RUNTIME = 1200  # 20 minutes max runtime

# Sample tokens for testing
SAMPLE_TOKENS = [
    {
        "name": "Vanela Gathiya",
        "symbol": "VANELA",
        "address": Web3.to_checksum_address("0xe5B8A3ed37072683eB8D8E0C6D2B9c4A91807Bc9"),
        "price": 0.0002,
        "price_change": 12.5
    },
    {
        "name": "Trump Tax",
        "symbol": "TRUMP",
        "address": Web3.to_checksum_address("0x845ab1a4fa6c9aa5d23aa2f2575eda1b17462e34"),  
        "price": 0.0001,
        "price_change": -5.2
    }
]

class AutonomousTrader:
    """Autonomous trading bot that executes trades based on signals"""
    
    def __init__(self, wallet_address, private_key, trade_amount_usd=1.0):
        self.logger = logging.getLogger("auto_trader")
        self.wallet_address = wallet_address
        self.private_key = private_key
        self.trade_amount_usd = trade_amount_usd
        
        # Initialize API client
        self.logger.info("Initializing Zora client")
        self.zora_client = ZoraClient(
            rpc_url=ZORA_RPC,
            api_key=os.environ.get("ZORA_API_KEY")
        )
        
        # Initialize trading agent
        self.logger.info("Initializing trading agent")
        self.agent = TradingAgent(
            wallet_address=wallet_address,
            zora_client=self.zora_client,
            auto_trading_enabled=True,
            confidence_threshold=0.65,
            max_trade_amount_usd=trade_amount_usd,
            simulate=False,  # Real trading
            mock_capital=5000.0,
            private_key=private_key
        )
        
        self.portfolio = self.agent.portfolio
        self.start_time = datetime.now()
        self.signals_generated = 0
        self.trades_executed = 0
        self.running = False
    
    async def check_balance(self):
        """Check wallet balance and display"""
        try:
            web3 = self.zora_client.w3
            wei_balance = web3.eth.get_balance(self.wallet_address)
            eth_balance = web3.from_wei(wei_balance, 'ether')
            
            # Get ETH price
            eth_price = await self.zora_client.get_eth_price()
            
            self.logger.info(f"Wallet ETH balance: {eth_balance:.6f} ETH")
            self.logger.info(f"ETH price: ${eth_price:.2f}")
            self.logger.info(f"Wallet value: ${float(eth_balance) * eth_price:.2f}")
            
            if eth_balance < 0.0001:
                self.logger.warning(f"ETH balance is very low ({eth_balance:.6f} ETH)")
                return False
            return True
        except Exception as e:
            self.logger.error(f"Error checking wallet balance: {e}")
            return False
    
    async def initialize_portfolio(self):
        """Initialize portfolio with sample tokens"""
        self.logger.info("Initializing portfolio...")
        
        # Get actual tokens from wallet
        await self.agent.update_portfolio()
        
        # If we didn't get any tokens, add the sample tokens
        if len(self.portfolio.holdings) == 0:
            self.logger.info("No tokens found in wallet, adding sample tokens")
            for token_data in SAMPLE_TOKENS:
                coin = Coin(
                    id=token_data["address"],
                    address=token_data["address"],
                    symbol=token_data["symbol"],
                    name=token_data["name"],
                    creator_address="0x0000000000000000000000000000000000000000",
                    current_price=token_data["price"],
                    price_change_24h=token_data["price_change"],
                    volume_24h=1000000,
                    created_at=datetime.now().isoformat(),
                    market_cap=token_data["price"] * 1000000
                )
                # Add a small placeholder amount
                self.portfolio.add_holding(
                    coin=coin,
                    amount=0.01,
                    avg_purchase_price=token_data["price"]
                )
    
    async def generate_trading_signals(self):
        """Generate sample trading signals for demonstration"""
        signals = []
        self.logger.info("Generating trading signals...")
        
        # Get tokens from portfolio
        if len(self.portfolio.holdings) == 0:
            self.logger.warning("No tokens in portfolio to generate signals")
            return signals
        
        tokens = list(self.portfolio.holdings.values())
        
        # Randomly decide to generate a signal (50% chance)
        if random.random() < 0.5:
            # Pick a random token
            token = random.choice(tokens)
            
            # Decide on signal type (buy or sell)
            signal_type = random.choice([SignalType.BUY, SignalType.SELL])
            strength = random.uniform(0.65, 0.95)
            
            signal = Signal(
                type=signal_type,
                coin=token.coin,
                strength=strength,
                reason=f"Automated test signal with {strength:.2f} confidence",
                strategy="AutomatedStrategy"
            )
            
            signals.append(signal)
            signal_type_str = "BUY" if signal_type == SignalType.BUY else "SELL"
            self.logger.info(f"Generated {signal_type_str} signal for {token.coin.symbol} with {strength:.2f} confidence")
        else:
            self.logger.info("No trading signals generated this cycle")
        
        self.signals_generated += len(signals)
        return signals
    
    async def display_status(self):
        """Display bot status"""
        runtime = datetime.now() - self.start_time
        print("\n" + "="*80)
        print(f"{Fore.CYAN}AUTONOMOUS TRADING BOT STATUS{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Runtime: {runtime.total_seconds():.0f} seconds{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Signals Generated: {self.signals_generated}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Trades Executed: {self.trades_executed}{Style.RESET_ALL}")
        print("="*80 + "\n")
        
        # Show portfolio
        print(self.portfolio.display_as_table())
        
        # Show trading performance
        if hasattr(self.agent, 'trading_history') and self.agent.trading_history:
            print("\n" + "-"*80)
            print(f"{Fore.YELLOW}TRADING HISTORY{Style.RESET_ALL}")
            for i, trade in enumerate(self.agent.trading_history, 1):
                trade_color = Fore.GREEN if trade["type"] == "BUY" else Fore.RED
                print(f"{i}. {trade_color}{trade['type']}{Style.RESET_ALL} {trade.get('amount', 0):.6f} {trade.get('coin', {}).get('symbol', '???')} @ ${trade.get('price', 0):.6f}")
            print("-"*80 + "\n")
    
    async def trading_loop(self):
        """Main trading loop"""
        self.logger.info("Starting autonomous trading bot...")
        self.running = True
        self.start_time = datetime.now()
        
        # Initial portfolio setup
        has_funds = await self.check_balance()
        if not has_funds:
            self.logger.warning("Insufficient funds to execute trades")
        
        await self.initialize_portfolio()
        await self.display_status()
        
        # Main trading loop
        while self.running:
            try:
                # Check if we've exceeded max runtime
                if (datetime.now() - self.start_time).total_seconds() > MAX_RUNTIME:
                    self.logger.info(f"Maximum runtime of {MAX_RUNTIME} seconds reached")
                    self.running = False
                    break
                
                self.logger.info(f"Trading cycle started at {datetime.now().strftime('%H:%M:%S')}")
                
                # Generate trading signals
                signals = await self.generate_trading_signals()
                
                if signals:
                    # Evaluate signals and make trade decisions
                    self.logger.info(f"Evaluating {len(signals)} trading signals...")
                    trade_decisions = await self.agent.evaluate_signals(signals)
                    
                    if trade_decisions:
                        self.logger.info(f"Executing {len(trade_decisions)} trades autonomously...")
                        for decision in trade_decisions:
                            # Execute each trade decision
                            result = await self.agent.execute_trade(decision)
                            
                            if result["success"]:
                                self.trades_executed += 1
                                self.logger.info(f"✅ Trade executed: {result['type']} {result.get('amount', 0):.6f} {result['coin'].symbol} @ ${result.get('price', 0):.6f}")
                                if result.get("transaction_hash"):
                                    self.logger.info(f"🔗 Transaction hash: {result['transaction_hash']}")
                            else:
                                self.logger.error(f"❌ Trade failed: {result.get('error', 'Unknown error')}")
                    else:
                        self.logger.info("No trades to execute after evaluating signals")
                
                # Display current status
                await self.display_status()
                
                # Wait for next trading cycle
                next_run = datetime.now() + timedelta(seconds=TRADE_INTERVAL)
                self.logger.info(f"Next trading cycle scheduled for {next_run.strftime('%H:%M:%S')}")
                await asyncio.sleep(TRADE_INTERVAL)
                
            except KeyboardInterrupt:
                self.logger.info("Trading bot stopped by user")
                self.running = False
                break
            except Exception as e:
                self.logger.error(f"Error in trading loop: {e}")
                # Continue despite errors
                await asyncio.sleep(5)
        
        self.logger.info("Trading bot stopped")
    
    async def run(self):
        """Run the autonomous trading bot"""
        try:
            await self.trading_loop()
        except KeyboardInterrupt:
            self.logger.info("Trading bot stopped by user")
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
        finally:
            # Final status display
            self.logger.info("Trading session complete")
            await self.display_status()
            total_runtime = datetime.now() - self.start_time
            self.logger.info(f"Total runtime: {total_runtime.total_seconds():.1f} seconds")
            self.logger.info(f"Signals generated: {self.signals_generated}")
            self.logger.info(f"Trades executed: {self.trades_executed}")

async def main():
    """Main entry point"""
    colorama.init(autoreset=True)
    logger = setup_logger()
    
    if not PRIVATE_KEY:
        logger.error("Private key not found in environment variables")
        return
    
    print("\n" + "="*80)
    print(f"{Fore.MAGENTA}ZORA NETWORK AUTONOMOUS TRADING BOT{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}Powered by Zora SDK with real trading capabilities{Style.RESET_ALL}")
    print("="*80 + "\n")
    
    logger.info(f"Initializing bot for wallet: {WALLET_ADDRESS}")
    logger.info(f"Max trade amount: ${TRADE_AMOUNT_USD}")
    logger.info(f"Trade interval: {TRADE_INTERVAL} seconds")
    logger.info(f"Max runtime: {MAX_RUNTIME} seconds")
    
    # Create and run the autonomous trader
    trader = AutonomousTrader(
        wallet_address=WALLET_ADDRESS,
        private_key=PRIVATE_KEY,
        trade_amount_usd=TRADE_AMOUNT_USD
    )
    
    await trader.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"{Fore.RED}Unexpected error: {e}{Style.RESET_ALL}")
