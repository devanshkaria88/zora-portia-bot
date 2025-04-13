#!/usr/bin/env python
"""
Test Script for Zora SDK Trading Integration

This script demonstrates the Zora SDK trading integration in simulation mode
without executing actual blockchain transactions.
"""
import os
import asyncio
import argparse
import logging
from datetime import datetime
import colorama
from colorama import Fore, Style
from tabulate import tabulate

from src.api.zora import ZoraClient
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
            
        return f"{icon} {color}{formatted_msg}{Style.RESET_ALL}"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Get the root logger and set up our custom formatter
root_logger = logging.getLogger()
for handler in root_logger.handlers:
    if isinstance(handler, logging.StreamHandler):
        handler.setFormatter(ColoredFormatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S"))

logger = logging.getLogger("zora.test")

# Initialize colorama
colorama.init(autoreset=True)

# Parse command line arguments
parser = argparse.ArgumentParser(description='Test Zora SDK Trading Integration')
parser.add_argument('--wallet', type=str, default="0x53dae6e4b5009c1d5b64bee9cb42118914db7e66", 
                    help='Wallet address to use')
parser.add_argument('--simulate', action='store_true', default=True,
                    help='Run in simulation mode (no actual transactions)')
args = parser.parse_args()

# Sample token for testing
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

class MockZoraTrader(ZoraSDKTrader):
    """Mock version of the ZoraSDKTrader that simulates trades without blockchain interaction"""
    
    async def approve_token_spending(self, token_address, amount=2**256 - 1):
        """Mock token approval"""
        logger.info(f"🔄 SIMULATED: Approving token {token_address} for trading")
        return "0xmocked_approval_transaction_hash"
        
    async def get_quote(self, token_in, token_out, amount_in):
        """Mock quote calculation"""
        # Find the tokens in our samples
        token_in_price = 0
        token_out_price = 0
        
        # If token_in is WETH, use 3000 as ETH price
        if token_in.lower() == "0x4200000000000000000000000000000000000006".lower():
            token_in_price = 3000
        else:
            for token in SAMPLE_TOKENS:
                if token["address"].lower() == token_in.lower():
                    token_in_price = token["price"]
                    break
                    
        for token in SAMPLE_TOKENS:
            if token["address"].lower() == token_out.lower():
                token_out_price = token["price"]
                break
                
        # If we couldn't find prices, use defaults
        if token_in_price == 0:
            token_in_price = 1.0
        if token_out_price == 0:
            token_out_price = 1.0
            
        # Calculate exchange rate
        rate = token_in_price / token_out_price
        
        # Calculate output amount
        amount_out = int(amount_in * rate)
        
        logger.info(f"🔍 SIMULATED QUOTE: {amount_in} of {token_in} → {amount_out} of {token_out}")
        
        return rate, [amount_in, amount_out]
        
    async def execute_swap(self, token_in, token_out, amount_in, min_amount_out=None):
        """Mock token swap execution"""
        # Get a simulated quote
        _, amounts = await self.get_quote(token_in, token_out, amount_in)
        
        # Log the simulated trade
        logger.info(f"💱 SIMULATED SWAP: {amount_in} of {token_in} → {amounts[1]} of {token_out}")
        
        # Return simulated results
        return {
            "success": True,
            "transaction_hash": f"0xmocked_swap_tx_{datetime.now().timestamp()}",
            "token_in": token_in,
            "token_out": token_out,
            "amount_in": amount_in,
            "amount_out": amounts[1],
            "gas_used": 150000,
            "effective_gas_price": 20000000000,  # 20 gwei
            "block_number": 12345678
        }
        
    async def swap_eth_for_tokens(self, token_out, eth_amount, min_tokens_out=None):
        """Mock ETH to token swap"""
        # Convert ETH to wei for consistency
        eth_amount_wei = int(eth_amount * 10**18)
        
        # Get a simulated quote
        _, amounts = await self.get_quote("0x4200000000000000000000000000000000000006", token_out, eth_amount_wei)
        
        # Get token information
        token_name = "Unknown Token"
        token_symbol = "???"
        for token in SAMPLE_TOKENS:
            if token["address"].lower() == token_out.lower():
                token_name = token["name"]
                token_symbol = token["symbol"]
                break
                
        # Log the simulated trade
        logger.info(f"💱 SIMULATED BUY: {eth_amount} ETH → {amounts[1] / 10**18:.6f} {token_symbol}")
        
        # Return simulated results
        return {
            "success": True,
            "transaction_hash": f"0xmocked_eth_swap_tx_{datetime.now().timestamp()}",
            "token_in": "ETH",
            "token_out": token_out,
            "amount_in": eth_amount_wei,
            "amount_out": amounts[1],
            "gas_used": 180000,
            "effective_gas_price": 20000000000,  # 20 gwei
            "block_number": 12345678
        }
        
    async def swap_tokens_for_eth(self, token_in, token_amount, min_eth_out=None):
        """Mock token to ETH swap"""
        # Find token information
        token_name = "Unknown Token"
        token_symbol = "???"
        token_decimals = 18
        for token in SAMPLE_TOKENS:
            if token["address"].lower() == token_in.lower():
                token_name = token["name"]
                token_symbol = token["symbol"]
                break
                
        # Convert token amount to wei-equivalent for consistency
        token_amount_wei = int(token_amount * 10**token_decimals)
        
        # Get a simulated quote
        _, amounts = await self.get_quote(token_in, "0x4200000000000000000000000000000000000006", token_amount_wei)
        
        # Log the simulated trade
        logger.info(f"💱 SIMULATED SELL: {token_amount} {token_symbol} → {amounts[1] / 10**18:.6f} ETH")
        
        # Return simulated results
        return {
            "success": True,
            "transaction_hash": f"0xmocked_token_to_eth_tx_{datetime.now().timestamp()}",
            "token_in": token_in,
            "token_out": "ETH",
            "amount_in": token_amount_wei,
            "amount_out": amounts[1],
            "gas_used": 160000,
            "effective_gas_price": 20000000000,  # 20 gwei
            "block_number": 12345678
        }

async def run_demo():
    """Run a demonstration of the Zora SDK trading functionality"""
    logger.info(f"Starting Zora SDK Trading Test")
    logger.info(f"Using wallet: {args.wallet}")
    logger.info(f"Simulation mode: {args.simulate}")
    
    # Create Zora client
    zora_client = ZoraClient()
    
    # Create trading agent
    if args.simulate:
        trader = MockZoraTrader(
            zora_client=zora_client,
            wallet_address=args.wallet,
            private_key="0xmocked_private_key"  # This is a mock key, not real
        )
    else:
        # In a real scenario, you'd get the private key securely
        private_key = os.environ.get("WALLET_PRIVATE_KEY")
        if not private_key:
            logger.error("❌ Private key not found! Set WALLET_PRIVATE_KEY environment variable.")
            return
            
        trader = ZoraSDKTrader(
            zora_client=zora_client,
            wallet_address=args.wallet,
            private_key=private_key
        )
    
    # Create a sample portfolio
    portfolio = Portfolio(args.wallet)
    
    # Display header
    print("\n" + "="*80)
    print(f"{Fore.CYAN}ZORA NETWORK SDK TRADING DEMONSTRATION{Style.RESET_ALL}")
    print("="*80 + "\n")
    
    # Demo 1: Check token allowances
    logger.info("Demo Step 1: Checking token allowances")
    for token in SAMPLE_TOKENS:
        token_address = token["address"]
        logger.info(f"Checking allowance for {token['name']} ({token['symbol']})")
        await trader.approve_token_spending(token_address)
    
    # Demo 2: Get quotes
    logger.info("\nDemo Step 2: Getting swap quotes")
    token1 = SAMPLE_TOKENS[0]["address"]
    token2 = SAMPLE_TOKENS[1]["address"]
    amount = 1000000000000000000  # 1 token with 18 decimals
    
    rate, amounts = await trader.get_quote(token1, token2, amount)
    logger.info(f"Quote: 1 {SAMPLE_TOKENS[0]['symbol']} = {rate:.6f} {SAMPLE_TOKENS[1]['symbol']}")
    logger.info(f"Expected output: {amounts[1] / 10**18:.6f} {SAMPLE_TOKENS[1]['symbol']}")
    
    # Demo 3: Execute trades based on signals
    logger.info("\nDemo Step 3: Processing trade signals")
    
    # Create sample signals
    signals = []
    
    # Buy signal
    buy_coin = Coin(
        id=SAMPLE_TOKENS[0]["address"],
        address=SAMPLE_TOKENS[0]["address"],
        symbol=SAMPLE_TOKENS[0]["symbol"],
        name=SAMPLE_TOKENS[0]["name"],
        creator_address="0x" + "".join(["0" for _ in range(40)]),
        current_price=SAMPLE_TOKENS[0]["price"],
        price_change_24h=SAMPLE_TOKENS[0]["price_change"],
        volume_24h=1000000,
        created_at=datetime.now().isoformat(),
        market_cap=SAMPLE_TOKENS[0]["price"] * 1000000
    )
    buy_signal = Signal(
        coin=buy_coin,
        type=SignalType.BUY,
        strength=0.85,
        reason="Strong upward momentum",
        timestamp=datetime.now(),
        strategy="TestStrategy"
    )
    signals.append(buy_signal)
    
    # Sell signal (if price change is negative)
    if SAMPLE_TOKENS[1]["price_change"] < 0:
        sell_coin = Coin(
            id=SAMPLE_TOKENS[1]["address"],
            address=SAMPLE_TOKENS[1]["address"],
            symbol=SAMPLE_TOKENS[1]["symbol"],
            name=SAMPLE_TOKENS[1]["name"],
            creator_address="0x" + "".join(["0" for _ in range(40)]),
            current_price=SAMPLE_TOKENS[1]["price"],
            price_change_24h=SAMPLE_TOKENS[1]["price_change"],
            volume_24h=1000000,
            created_at=datetime.now().isoformat(),
            market_cap=SAMPLE_TOKENS[1]["price"] * 1000000
        )
        sell_signal = Signal(
            coin=sell_coin,
            type=SignalType.SELL,
            strength=0.78,
            reason="Negative price momentum",
            timestamp=datetime.now(),
            strategy="TestStrategy"
        )
        signals.append(sell_signal)
    
    # Process each signal
    for signal in signals:
        logger.info(f"\nProcessing {signal.type.name} signal for {signal.coin.symbol}")
        logger.info(f"Signal strength: {signal.strength:.2f}")
        logger.info(f"Reason: {signal.reason}")
        
        # Process the signal
        trade_amount = 100.0  # $100 USD
        result = await trader.process_trade_signal(signal, trade_amount)
        
        if result["success"]:
            logger.info(f"✅ Trade executed successfully!")
            logger.info(f"Transaction hash: {result.get('transaction_hash', 'N/A')}")
            
            # Update portfolio (in a real scenario)
            if signal.type == SignalType.BUY:
                # Add to portfolio
                portfolio.add_holding(
                    coin=signal.coin,
                    amount=result.get("eth_amount", 0) * 10,  # Simulated received amount
                    avg_purchase_price=signal.coin.current_price
                )
            elif signal.type == SignalType.SELL:
                # Remove from portfolio
                portfolio.remove_holding(
                    coin=signal.coin,
                    amount=result.get("token_amount", 0),
                    sale_price=signal.coin.current_price
                )
        else:
            logger.error(f"❌ Trade failed: {result.get('error', 'Unknown error')}")
    
    # Display final portfolio
    logger.info("\nUpdated portfolio after trades:")
    print(portfolio.display_as_table())

if __name__ == "__main__":
    try:
        asyncio.run(run_demo())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        logger.error(f"Error in test: {e}")
