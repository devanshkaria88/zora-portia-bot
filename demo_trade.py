#!/usr/bin/env python
"""
Demo Trading Script for Zora Network

This script provides a simplified demonstration of the Zora trading bot
with simulated market data and automated trading using mock capital.
"""
import os
import asyncio
import random
import logging
import argparse
from datetime import datetime, timedelta
import colorama
from colorama import Fore, Style
from tabulate import tabulate

# Parse command line arguments
parser = argparse.ArgumentParser(description='Demo Trading Bot for Zora Network')
parser.add_argument('--mock-capital', type=float, default=1000.0, help='Amount of mock capital to start with')
parser.add_argument('--wallet', type=str, default="0x53dae6e4b5009c1d5b64bee9cb42118914db7e66", help='Wallet address to use')
args = parser.parse_args()

# Initialize colorama
colorama.init(autoreset=True)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format=f"%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger('zora.demo')

# Wallet we're tracking
WALLET_ADDRESS = args.wallet

# Your actual tokens from the Zora blockchain
ACTUAL_TOKENS = [
    {
        "name": "Trump Tax!",
        "symbol": "Trump Tax!",
        "address": "0x7ce9c67c8a1d65ce61fc464727cc0f9caabf92b9",
        "balance": 10.0
    },
    {
        "name": "Trump is taxing! Tru-xing",
        "symbol": "Trump is t",
        "address": "0x4200000000000000000000000000000000000006",
        "balance": 10.0
    },
    {
        "name": "Vanela Gathiya, Marchu ne sambharo",
        "symbol": "Vanela Gat",
        "address": "0x50c5725949a6f0c72e6c4a641f24049a917db0cb",
        "balance": 10.0
    }
]

# Simulated market tokens for trading
MARKET_TOKENS = [
    {"name": "ZoraCoin", "symbol": "ZOR"},
    {"name": "BaseToken", "symbol": "BASE"},
    {"name": "MemeDAO", "symbol": "MEME"},
    {"name": "AstroFinance", "symbol": "ASTRO"},
    {"name": "MetaverseToken", "symbol": "MVT"},
    {"name": "DeFiYield", "symbol": "DEFI"},
    {"name": "PixelArt", "symbol": "PIXEL"},
    {"name": "EcoDAO", "symbol": "ECO"},
    {"name": "ZoraVerse", "symbol": "ZVERSE"},
    {"name": "ChainNation", "symbol": "CHAIN"}
]

class Coin:
    """Simple coin class for demonstration"""
    def __init__(self, name, symbol, address=None, price=0.0, volume=0, price_change=0):
        self.name = name
        self.symbol = symbol
        self.address = address or f"0x{''.join([random.choice('0123456789abcdef') for _ in range(40)])}"
        self.current_price = price
        self.volume_24h = volume
        self.price_change_24h = price_change
        self.market_cap = price * random.uniform(100000, 10000000)
        
    def update_price(self):
        """Simulate a price update"""
        # Generate a random price change (-8% to +10%)
        change_pct = random.uniform(-0.08, 0.10)
        old_price = self.current_price
        self.current_price = max(0.00001, old_price * (1 + change_pct))
        self.price_change_24h = change_pct * 100
        return old_price, change_pct

class Portfolio:
    """Simple portfolio class for demonstration"""
    def __init__(self, wallet_address, cash_balance=1000.0):
        self.wallet_address = wallet_address
        self.holdings = {}
        self.cash_balance = cash_balance
        self.initial_capital = cash_balance
        self.trade_history = []
        
    def add_coin(self, coin, amount=0):
        """Add a coin to the portfolio"""
        self.holdings[coin.address] = {
            "coin": coin,
            "amount": amount,
            "avg_price": coin.current_price
        }
    
    def buy(self, coin, amount, price):
        """Buy a coin"""
        cost = amount * price
        if cost > self.cash_balance:
            logger.warning(f"❌ TRADE FAILED: Not enough funds to buy {amount} {coin.symbol}. Available: ${self.cash_balance:.2f}, Required: ${cost:.2f}")
            return False
            
        # Subtract from cash balance
        self.cash_balance -= cost
        
        # Add to holdings
        if coin.address in self.holdings:
            # Calculate new average price
            holding = self.holdings[coin.address]
            total_amount = holding["amount"] + amount
            total_cost = (holding["amount"] * holding["avg_price"]) + cost
            holding["amount"] = total_amount
            holding["avg_price"] = total_cost / total_amount
        else:
            self.holdings[coin.address] = {
                "coin": coin,
                "amount": amount,
                "avg_price": price
            }
            
        # Record the trade
        self.trade_history.append({
            "time": datetime.now(),
            "type": "BUY",
            "coin": coin.name,
            "symbol": coin.symbol,
            "amount": amount,
            "price": price,
            "value": cost
        })
        
        logger.info(f"✅ TRADE: BOUGHT {amount:.4f} {coin.symbol} @ ${price:.4f} | Total: ${cost:.2f}")
        return True
        
    def sell(self, coin, amount, price):
        """Sell a coin"""
        if coin.address not in self.holdings:
            logger.warning(f"❌ TRADE FAILED: You don't own any {coin.symbol}")
            return False
            
        holding = self.holdings[coin.address]
        if holding["amount"] < amount:
            logger.warning(f"❌ TRADE FAILED: Not enough {coin.symbol} to sell. Available: {holding['amount']:.4f}, Requested: {amount:.4f}")
            return False
            
        # Calculate proceeds
        proceeds = amount * price
        
        # Add to cash balance
        self.cash_balance += proceeds
        
        # Remove from holdings
        holding["amount"] -= amount
        if holding["amount"] <= 0.000001:
            # Remove altogether if essentially zero
            del self.holdings[coin.address]
        
        # Record the trade
        self.trade_history.append({
            "time": datetime.now(),
            "type": "SELL",
            "coin": coin.name,
            "symbol": coin.symbol,
            "amount": amount,
            "price": price,
            "value": proceeds
        })
        
        logger.info(f"💰 TRADE: SOLD {amount:.4f} {coin.symbol} @ ${price:.4f} | Total: ${proceeds:.2f}")
        return True
        
    def get_total_value(self):
        """Calculate total portfolio value"""
        holdings_value = sum(holding["amount"] * holding["coin"].current_price for holding in self.holdings.values())
        return holdings_value + self.cash_balance
        
    def get_performance(self):
        """Calculate portfolio performance"""
        total_value = self.get_total_value()
        profit_loss = total_value - self.initial_capital
        return {
            "initial_capital": self.initial_capital,
            "holdings_value": sum(holding["amount"] * holding["coin"].current_price for holding in self.holdings.values()),
            "cash_balance": self.cash_balance,
            "total_value": total_value,
            "profit_loss": profit_loss,
            "profit_loss_percent": (profit_loss / self.initial_capital) * 100 if self.initial_capital > 0 else 0
        }
        
    def display_portfolio(self):
        """Display portfolio as a formatted table"""
        if not self.holdings:
            logger.info("\n💼 PORTFOLIO IS EMPTY\n")
            return
            
        table_data = []
        for holding in self.holdings.values():
            coin = holding["coin"]
            amount = holding["amount"]
            value = amount * coin.current_price
            pnl = (coin.current_price - holding["avg_price"]) / holding["avg_price"] * 100
            
            table_data.append([
                coin.name,
                coin.symbol,
                f"{amount:.4f}",
                f"${value:.2f}",
                f"${coin.current_price:.4f}",
                f"{coin.price_change_24h:.2f}%"
            ])
            
        # Add total row
        total_value = sum(holding["amount"] * holding["coin"].current_price for holding in self.holdings.values())
        table_data.append([
            "TOTAL",
            "",
            "",
            f"${total_value:.2f}",
            "",
            ""
        ])
        
        # Format and display the table
        headers = ["Token", "Symbol", "Amount", "Value (USD)", "Price (USD)", "Change"]
        table = tabulate(table_data, headers=headers, tablefmt="grid")
        
        logger.info(f"\n💼 PORTFOLIO FOR {self.wallet_address[:8]}...{self.wallet_address[-4:]}\n\n{table}\n")
        
    def display_status(self):
        """Display trading account status"""
        perf = self.get_performance()
        
        # Format PnL with color
        pnl = perf["profit_loss"]
        pnl_percent = perf["profit_loss_percent"]
        
        if pnl >= 0:
            pnl_color = Fore.GREEN
            pnl_sign = "+"
        else:
            pnl_color = Fore.RED
            pnl_sign = ""
            
        status = f"\n💰 TRADING ACCOUNT STATUS\n"
        status += f"Initial Capital: ${perf['initial_capital']:.2f}\n"
        status += f"Portfolio Value: ${perf['holdings_value']:.2f}\n"
        status += f"Available Cash: ${perf['cash_balance']:.2f}\n"
        status += f"Total Value: ${perf['total_value']:.2f}\n"
        status += f"P&L: {pnl_color}{pnl_sign}${pnl:.2f} ({pnl_sign}{pnl_percent:.2f}%){Style.RESET_ALL}\n"
        
        logger.info(status)
        
    def display_trade_history(self):
        """Display trade history"""
        if not self.trade_history:
            logger.info("\n📜 NO TRADE HISTORY\n")
            return
            
        table_data = []
        for trade in self.trade_history[-10:]:  # Show last 10 trades
            trade_type = trade["type"]
            color = Fore.GREEN if trade_type == "BUY" else Fore.RED
            
            table_data.append([
                trade["time"].strftime("%H:%M:%S"),
                f"{color}{trade_type}{Style.RESET_ALL}",
                trade["symbol"],
                f"{trade['amount']:.4f}",
                f"${trade['price']:.4f}",
                f"${trade['value']:.2f}"
            ])
            
        # Format and display the table
        headers = ["Time", "Type", "Symbol", "Amount", "Price", "Value"]
        table = tabulate(table_data, headers=headers, tablefmt="grid")
        
        logger.info(f"\n📜 RECENT TRADES\n\n{table}\n")

class TradingBot:
    """Simple trading bot for demonstration"""
    def __init__(self, wallet_address, mock_capital=1000.0):
        self.wallet_address = wallet_address
        self.portfolio = Portfolio(wallet_address, mock_capital)
        self.market = {}
        self.running = False
        
    def initialize_market(self):
        """Initialize market with simulated coins"""
        logger.info("Initializing market with simulated trading coins...")
        
        # Add our actual tokens from Zora
        for token in ACTUAL_TOKENS:
            coin = Coin(
                name=token["name"],
                symbol=token["symbol"],
                address=token["address"],
                price=0.0001,  # Start with a very small price
                volume=random.uniform(1000, 10000),
                price_change=0
            )
            self.market[coin.address] = coin
            self.portfolio.add_coin(coin, token["balance"])
            
        # Add market tokens for trading
        for token in MARKET_TOKENS:
            coin = Coin(
                name=token["name"],
                symbol=token["symbol"],
                price=random.uniform(0.5, 100.0),
                volume=random.uniform(10000, 1000000),
                price_change=random.uniform(-10, 20)
            )
            self.market[coin.address] = coin
            
        logger.info(f"✅ Initialized market with {len(self.market)} tokens")
        
    def update_market(self):
        """Update market prices"""
        significant_changes = []
        
        for coin in self.market.values():
            old_price, change_pct = coin.update_price()
            
            # Log significant price changes
            if abs(change_pct) > 0.05:  # 5% or more
                direction = "📈" if change_pct > 0 else "📉"
                significant_changes.append({
                    "symbol": coin.symbol,
                    "name": coin.name,
                    "old_price": old_price,
                    "new_price": coin.current_price,
                    "change_pct": change_pct,
                    "direction": direction
                })
                
        # Log the most significant changes
        if significant_changes:
            significant_changes.sort(key=lambda x: abs(x["change_pct"]), reverse=True)
            for change in significant_changes[:3]:  # Show top 3 most significant
                logger.info(f"{change['direction']} {change['name']} ({change['symbol']}): ${change['old_price']:.4f} → ${change['new_price']:.4f} ({change['change_pct']:.2%})")
                
    def generate_trading_signals(self):
        """Generate trading signals based on price movements"""
        buy_signals = []
        sell_signals = []
        
        # Check for buy signals in market coins (not in portfolio)
        portfolio_addresses = set(self.portfolio.holdings.keys())
        for address, coin in self.market.items():
            if address in portfolio_addresses:
                # Check for sell signals for coins we own
                if coin.price_change_24h < -5:  # Downward trend
                    confidence = min(0.9, abs(coin.price_change_24h) / 20)
                    sell_signals.append({
                        "coin": coin,
                        "confidence": confidence,
                        "reason": f"Negative momentum: {coin.price_change_24h:.2f}% price drop"
                    })
                elif coin.price_change_24h > 15:  # Take profit on strong rally
                    confidence = min(0.9, coin.price_change_24h / 30)
                    sell_signals.append({
                        "coin": coin,
                        "confidence": confidence,
                        "reason": f"Taking profit after {coin.price_change_24h:.2f}% price increase"
                    })
            else:
                # Look for coins with positive momentum to buy
                if coin.price_change_24h > 3:  # More aggressive, lowered from 8% to 3%
                    confidence = min(0.9, coin.price_change_24h / 10)  # Increased confidence
                    buy_signals.append({
                        "coin": coin,
                        "confidence": confidence,
                        "reason": f"Positive momentum: {coin.price_change_24h:.2f}% price increase"
                    })
                    
        # Sort signals by confidence
        buy_signals.sort(key=lambda x: x["confidence"], reverse=True)
        sell_signals.sort(key=lambda x: x["confidence"], reverse=True)
        
        # Return top signals
        return buy_signals[:5], sell_signals[:3]  # Increased from 3 to 5 for buy signals
        
    def execute_trades(self, buy_signals, sell_signals):
        """Execute trades based on signals"""
        # Execute sell signals first to free up capital
        for signal in sell_signals:
            if signal["confidence"] < 0.4:  # Lowered from 0.6 to 0.4
                continue  # Skip low confidence signals
                
            coin = signal["coin"]
            if coin.address in self.portfolio.holdings:
                holding = self.portfolio.holdings[coin.address]
                
                # Decide how much to sell (50% for high confidence, 25% for medium)
                sell_percent = 0.5 if signal["confidence"] > 0.7 else 0.25  # Lowered from 0.8 to 0.7
                amount_to_sell = holding["amount"] * sell_percent
                
                if amount_to_sell > 0:
                    logger.info(f"🔍 SIGNAL: SELL {coin.symbol} - {signal['reason']} (Confidence: {signal['confidence']:.2f})")
                    self.portfolio.sell(coin, amount_to_sell, coin.current_price)
        
        # Then execute buy signals with available cash
        for signal in buy_signals:
            if signal["confidence"] < 0.4:  # Lowered from 0.6 to 0.4
                continue  # Skip low confidence signals
                
            coin = signal["coin"]
            
            # Calculate amount to buy (at most 20% of available cash)
            max_investment = self.portfolio.cash_balance * 0.2
            amount_to_buy = max_investment / coin.current_price
            
            if amount_to_buy > 0:
                logger.info(f"🔍 SIGNAL: BUY {coin.symbol} - {signal['reason']} (Confidence: {signal['confidence']:.2f})")
                self.portfolio.buy(coin, amount_to_buy, coin.current_price)
                
    async def trading_loop(self):
        """Main trading loop"""
        trade_interval = 5  # seconds
        market_update_counter = 0
        
        while self.running:
            try:
                # Update market every iteration
                self.update_market()
                market_update_counter += 1
                
                # Generate and execute trades every 3 market updates (more frequent, was 5)
                if market_update_counter >= 3:
                    buy_signals, sell_signals = self.generate_trading_signals()
                    
                    if buy_signals or sell_signals:
                        signal_count = len(buy_signals) + len(sell_signals)
                        logger.info(f"📊 Generated {signal_count} trading signals")
                        self.execute_trades(buy_signals, sell_signals)
                        
                        # Display portfolio after trades
                        self.portfolio.display_portfolio()
                        self.portfolio.display_status()
                        self.portfolio.display_trade_history()
                        
                    market_update_counter = 0
                
                await asyncio.sleep(trade_interval)
                
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(trade_interval)
                
    async def start(self):
        """Start the trading bot"""
        logger.info(f"Starting Zora automated trading bot demo...")
        logger.info(f"Using wallet: {self.wallet_address}")
        
        # Initialize market
        self.initialize_market()
        
        # Display initial portfolio
        self.portfolio.display_portfolio()
        self.portfolio.display_status()
        
        # Start trading loop
        self.running = True
        await self.trading_loop()
        
    async def stop(self):
        """Stop the trading bot"""
        logger.info("Stopping trading bot...")
        self.running = False
        
        # Display final portfolio and performance
        logger.info("📊 TRADING SUMMARY")
        self.portfolio.display_portfolio()
        self.portfolio.display_status()
        self.portfolio.display_trade_history()

async def main():
    """Main entrypoint"""
    # Create the bot with specified mock capital
    bot = TradingBot(WALLET_ADDRESS, mock_capital=args.mock_capital)
    
    try:
        # Start the bot
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    finally:
        # Stop the bot
        await bot.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
