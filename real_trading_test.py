#!/usr/bin/env python
"""
Zora SDK Real Trading Test

This script performs a real trading test on the Zora Network using the provided private key.
It will execute a small trade to demonstrate the full trading capabilities.
"""
import os
import json
import asyncio
import logging
import sys
from datetime import datetime
import time
import colorama
from colorama import Fore, Style
from decimal import Decimal
from dotenv import load_dotenv
from web3 import Web3
from web3.exceptions import TransactionNotFound

# Load environment variables from .env file
load_dotenv()

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
        elif "transaction" in formatted_msg.lower():
            icon = "📝"  # Transaction icon
        elif "gas" in formatted_msg.lower():
            icon = "⛽"  # Gas icon
            
        return f"{icon} {color}{formatted_msg}{Style.RESET_ALL}"

# Configure colorful logging
def setup_logger():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColoredFormatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s", "%H:%M:%S"))
    
    root_logger.handlers = []  # Remove any existing handlers
    root_logger.addHandler(console_handler)
    
    # Set specific module loggers to debug for more detailed information
    for module in ["src.api.zora", "src.trading.agent", "src.trading.zora_trader"]:
        logging.getLogger(module).setLevel(logging.INFO)

# Configuration
WALLET_ADDRESS = Web3.to_checksum_address("0x53dae6e4b5009c1d5b64bee9cb42118914db7e66")
PRIVATE_KEY = os.environ.get("WALLET_PRIVATE_KEY")
SMALL_TRADE_AMOUNT_USD = 0.5  # Using a smaller amount for test (0.5 USD)

# Network constants
WETH_ADDRESS = Web3.to_checksum_address("0x4200000000000000000000000000000000000006")  # WETH on Zora
# Updated with a token that definitely exists on Zora Network - "Vanela Gathiya" token
TEST_TOKEN_ADDRESS = Web3.to_checksum_address("0xe5B8A3ed37072683eB8D8E0C6D2B9c4A91807Bc9")

async def perform_real_trading_test():
    """Perform a real trading test on Zora Network"""
    logger = logging.getLogger("real_test")
    
    # Display header
    print("\n" + "="*80)
    print(f"{Fore.CYAN}ZORA NETWORK REAL TRADING TEST{Style.RESET_ALL}")
    print("="*80 + "\n")
    
    if not PRIVATE_KEY:
        logger.error("Private key not found in environment variables (WALLET_PRIVATE_KEY)")
        logger.error("Cannot perform real trading test without a private key")
        return
    
    logger.info(f"Starting real trading test with wallet: {WALLET_ADDRESS}")
    logger.info(f"Trade amount: ${SMALL_TRADE_AMOUNT_USD:.2f}")
    
    # Initialize Zora client
    logger.info("Initializing Zora client...")
    zora_client = ZoraClient(
        rpc_url=os.environ.get("ZORA_RPC_URL", "https://rpc.zora.energy/"),
        api_key=os.environ.get("ZORA_API_KEY")
    )
    
    # Initialize ZoraSDKTrader directly for more control
    logger.info("Initializing Zora SDK Trader...")
    trader = ZoraSDKTrader(
        wallet_address=WALLET_ADDRESS,
        private_key=PRIVATE_KEY,
        zora_client=zora_client,
        slippage_tolerance=0.02,  # 2% slippage for better chance of success
        gas_limit_multiplier=1.5   # 50% extra gas for safety
    )
    
    # Check ETH balance using web3 directly
    try:
        web3 = zora_client.w3
        wei_balance = web3.eth.get_balance(WALLET_ADDRESS)
        eth_balance = web3.from_wei(wei_balance, 'ether')
        
        # Get ETH price
        eth_price = await zora_client.get_eth_price()
        
        logger.info(f"Wallet ETH balance: {eth_balance:.6f} ETH")
        logger.info(f"ETH price: ${eth_price:.2f}")
        logger.info(f"Wallet value: ${float(eth_balance) * eth_price:.2f}")
        
        if eth_balance < 0.001:
            logger.warning(f"ETH balance is very low ({eth_balance:.6f} ETH). This may not be enough for gas fees.")
            response = input("Continue with low balance? (y/n): ")
            if response.lower() != 'y':
                logger.info("Test aborted by user")
                return
    except Exception as e:
        logger.error(f"Error checking wallet balance: {e}")
        logger.warning("Continuing with test despite balance check failure")
    
    # Create test token
    test_token = Coin(
        address=TEST_TOKEN_ADDRESS,
        symbol="TEST",
        name="Test Token",
        id=TEST_TOKEN_ADDRESS,
        creator_address="0x0000000000000000000000000000000000000000",
        current_price=1.0,  # Placeholder
        volume_24h=1000000,
        market_cap=1000000,
        price_change_24h=0.0,
        created_at=datetime.now().isoformat()
    )
    
    # Create a buy signal
    logger.info("Creating test BUY signal...")
    buy_signal = Signal(
        type=SignalType.BUY,
        coin=test_token,
        strength=0.9,
        reason="Test real trading functionality",
        strategy="RealTradingTest"
    )
    
    # Execute the trade using ZoraSDKTrader
    logger.info(f"Executing BUY trade for ${SMALL_TRADE_AMOUNT_USD} of {test_token.symbol}...")
    
    try:
        # Process the trade signal
        result = await trader.process_trade_signal(buy_signal, SMALL_TRADE_AMOUNT_USD)
        
        if result["success"]:
            logger.info("✅ Trade successfully executed!")
            logger.info(f"Transaction hash: {result.get('transaction_hash', 'Unknown')}")
            logger.info(f"Bought token with ETH amount: {result.get('eth_amount', 0):.6f} ETH")
            
            # Wait for transaction to be confirmed
            if result.get("transaction_hash"):
                logger.info("Waiting for transaction confirmation...")
                tx_hash = result.get("transaction_hash")
                
                # Poll for receipt
                max_attempts = 20
                for attempt in range(max_attempts):
                    try:
                        receipt = await zora_client.w3.eth.get_transaction_receipt(tx_hash)
                        if receipt:
                            status = receipt.get("status")
                            if status == 1:
                                logger.info("✅ Transaction confirmed successfully!")
                                gas_used = receipt.get("gasUsed", 0)
                                gas_price = receipt.get("effectiveGasPrice", 0)
                                tx_fee_wei = gas_used * gas_price
                                tx_fee_eth = web3.from_wei(tx_fee_wei, 'ether')
                                logger.info(f"Gas used: {gas_used}")
                                logger.info(f"Transaction fee: {tx_fee_eth:.6f} ETH (${float(tx_fee_eth) * eth_price:.4f})")
                                break
                            elif status == 0:
                                logger.error("❌ Transaction failed on the blockchain")
                                break
                    except TransactionNotFound:
                        pass  # Transaction not yet mined
                    
                    if attempt < max_attempts - 1:
                        logger.info(f"Waiting for confirmation... (attempt {attempt+1}/{max_attempts})")
                        await asyncio.sleep(5)  # Wait 5 seconds between checks
                else:
                    logger.warning("⚠️ Transaction may still be pending, check explorer for status")
                    logger.info(f"Transaction explorer: https://basescan.org/tx/{tx_hash}")
        else:
            logger.error(f"❌ Trade failed: {result.get('error', 'Unknown error')}")
            if "message" in result:
                logger.error(f"Error message: {result['message']}")
    except Exception as e:
        logger.error(f"Error executing trade: {e}")
    
    logger.info("Real trading test completed!")

if __name__ == "__main__":
    colorama.init(autoreset=True)
    setup_logger()
    
    try:
        asyncio.run(perform_real_trading_test())
    except KeyboardInterrupt:
        print("\nTest stopped by user")
    except Exception as e:
        logging.error(f"Error in test: {e}")
