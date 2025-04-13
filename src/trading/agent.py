"""
Trading Agent for Zora Network
Autonomous agent that executes trades based on signals
"""
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from colorama import Fore, Style
import random
import os

from ..api.zora import ZoraClient
from ..models.portfolio import Portfolio, Holding
from ..models.signal import Signal, SignalType
from ..models.coin import Coin
from .zora_trader import ZoraSDKTrader

logger = logging.getLogger(__name__)

class TradingAgent:
    """
    Autonomous trading agent that executes trades based on signals
    """
    
    def __init__(
        self, 
        wallet_address: str, 
        zora_client: ZoraClient,
        auto_trading_enabled: bool = False,
        confidence_threshold: float = 0.75,
        max_trade_amount_usd: float = 100.0,
        max_allocation_percent: float = 20.0,
        min_eth_reserve: float = 0.05,
        simulate: bool = True,
        mock_capital: float = 1000.0,  # Start with $1000 mock capital
        private_key: Optional[str] = None  # For real trading
    ):
        self.wallet_address = wallet_address
        self.zora_client = zora_client
        self.auto_trading_enabled = auto_trading_enabled
        self.confidence_threshold = confidence_threshold
        self.max_trade_amount_usd = max_trade_amount_usd
        self.max_allocation_percent = max_allocation_percent
        self.min_eth_reserve = min_eth_reserve
        self.simulate = simulate
        self.mock_capital = mock_capital  # Mock trading capital
        self.mock_cash_balance = mock_capital  # Available cash for trading
        
        self.portfolio = Portfolio(wallet_address)
        self.trading_history: List[Dict[str, Any]] = []
        self.pending_trades: List[Dict[str, Any]] = []
        self.last_portfolio_update: Optional[datetime] = None
        self.last_price_update: Optional[datetime] = None
        
        # Initialize the trader for executing actual trades when enabled
        self.private_key = private_key or os.environ.get("WALLET_PRIVATE_KEY")
        if not simulate and not self.private_key:
            logger.warning("⚠️ Trading agent initialized without private key. Only simulated trades will be executed.")
            self.simulate = True
            
        # Create the ZoraSDKTrader instance
        self.trader = ZoraSDKTrader(
            zora_client=self.zora_client,
            wallet_address=self.wallet_address,
            private_key=self.private_key,
            slippage_tolerance=0.01  # 1% slippage by default
        )

    async def update_portfolio(self) -> None:
        """
        Update user's portfolio data from the blockchain
        """
        try:
            # Fetch holdings from Zora blockchain
            holdings_data = await self.zora_client.get_user_holdings(self.wallet_address)
            
            if not holdings_data:
                logger.warning(f"⚠️ No holdings found for wallet {self.wallet_address}")
                return
                
            # Create portfolio from holdings data
            for token_address, holding_data in holdings_data.items():
                # Create Coin object
                coin = Coin(
                    id=holding_data["token_address"],
                    address=holding_data["token_address"],
                    symbol=holding_data["symbol"],
                    name=holding_data["name"],
                    creator_address="", # Not needed for holdings
                    current_price=holding_data["price_usd"],
                    volume_24h=0,  # Will be updated later if this coin is tracked
                    price_change_24h=0,  # Will be updated later if this coin is tracked
                    created_at="",  # Not needed for holdings
                    market_cap=0  # Will be updated later if this coin is tracked
                )
                
                # Add to portfolio
                self.portfolio.add_holding(
                    coin=coin,
                    amount=holding_data["balance"],
                    avg_purchase_price=holding_data.get("avg_purchase_price", holding_data["price_usd"] * 0.9)  # Estimate purchase price
                )
                
            self.last_portfolio_update = datetime.now()
            logger.info(f"✨ Updated portfolio for {self.wallet_address} with {len(holdings_data)} tokens")
            
        except Exception as e:
            logger.error(f"❌ Failed to update portfolio: {e}")
            
    def use_demo_portfolio(self) -> None:
        """
        Use a demo portfolio with sample data for testing purposes
        """
        # Clear existing portfolio
        self.portfolio = Portfolio(self.wallet_address)
        
        # Sample token data
        sample_tokens = [
            {
                "address": "0x7ce9c67c8a1d65ce61fc464727cc0f9caabf92b9",
                "symbol": "ZORA",
                "name": "Zora Protocol Token (Demo)",
                "price_usd": 87.45,
                "balance": 3.75,
                "avg_purchase_price": 75.20
            },
            {
                "address": "0x4200000000000000000000000000000000000006",
                "symbol": "WETH",
                "name": "Wrapped Ethereum (Demo)",
                "price_usd": 3870.25,
                "balance": 1.12,
                "avg_purchase_price": 3450.0
            },
            {
                "address": "0x50c5725949a6f0c72e6c4a641f24049a917db0cb",
                "symbol": "DEGEN",
                "name": "Degen Token (Demo)",
                "price_usd": 0.25,
                "balance": 450.0,
                "avg_purchase_price": 0.20
            },
            {
                "address": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
                "symbol": "USDC",
                "name": "USD Coin (Demo)",
                "price_usd": 1.0,
                "balance": 1250.0,
                "avg_purchase_price": 1.0
            }
        ]
        
        # Create demo portfolio
        for token in sample_tokens:
            coin = Coin(
                id=token["address"],
                address=token["address"],
                symbol=token["symbol"],
                name=token["name"],
                creator_address="", 
                current_price=token["price_usd"],
                volume_24h=0,
                price_change_24h=0,
                created_at="",
                market_cap=0
            )
            
            self.portfolio.add_holding(
                coin=coin,
                amount=token["balance"],
                avg_purchase_price=token["avg_purchase_price"]
            )
            
        self.last_portfolio_update = datetime.now()
        logger.info("📊 Using demo portfolio data for simulation")
        
    async def enable_auto_trading(self, enabled: bool = True) -> None:
        """
        Enable or disable automatic trading
        """
        self.auto_trading_enabled = enabled
        status = "enabled" if enabled else "disabled"
        logger.info(f"🤖 Auto-trading {status} - Will execute trades automatically based on signals")
        
        # Show initial account status when enabling auto-trading
        if enabled:
            logger.info(self.display_agent_status())
            
    async def simulate_price_movements(self) -> None:
        """
        Simulate price movements for all tokens in the portfolio to 
        generate realistic trading conditions
        """
        if not self.portfolio or not self.portfolio.holdings:
            return
            
        # Get current time to ensure we don't update too frequently
        current_time = datetime.now()
        
        # Only update every minute at most
        if hasattr(self, 'last_price_update') and (current_time - self.last_price_update).seconds < 60:
            return
            
        # Update prices with some randomized movement
        price_changes = []
        for address, holding in self.portfolio.holdings.items():
            coin = holding.coin
            
            # Skip if not a valid coin
            if not coin or not hasattr(coin, 'current_price'):
                continue
                
            # Start with a small price if we have zero
            if coin.current_price <= 0:
                coin.current_price = 0.0001
                
            # Generate a random price change (-5% to +10%)
            # Slightly bias towards positive to make trading interesting
            change_pct = random.uniform(-0.05, 0.10)
            
            # Apply the change
            old_price = coin.current_price
            new_price = old_price * (1 + change_pct)
            coin.current_price = max(0.00001, new_price)  # Ensure price never goes negative
            
            # Update price change percentage
            coin.price_change_24h = change_pct * 100
            
            # Add some random volume
            if not hasattr(coin, 'volume_24h') or coin.volume_24h <= 0:
                coin.volume_24h = random.uniform(1000, 10000)
            else:
                # Random volume change
                volume_change = random.uniform(0.8, 1.2)
                coin.volume_24h *= volume_change
                
            # Record price change for logging
            price_changes.append({
                'symbol': coin.symbol,
                'old_price': old_price,
                'new_price': coin.current_price,
                'change_pct': change_pct * 100
            })
            
        # Log price changes
        if price_changes:
            logger.info(f"📈 Simulated price movements for {len(price_changes)} tokens")
            for change in price_changes:
                direction = "📈" if change['change_pct'] > 0 else "📉"
                logger.info(f"{direction} {change['symbol']}: ${change['old_price']:.6f} → ${change['new_price']:.6f} ({change['change_pct']:+.2f}%)")
                
        # Update timestamp
        self.last_price_update = current_time
        
    async def evaluate_signals(self, signals: List[Signal]) -> List[Dict[str, Any]]:
        """
        Evaluate signals and decide which trades to execute
        
        Args:
            signals: List of trading signals
            
        Returns:
            List of trade decisions
        """
        if not signals:
            return []
            
        # Filter out signals that don't pass the confidence threshold
        valid_signals = [s for s in signals if s.strength >= self.confidence_threshold]
        
        if not valid_signals:
            logger.debug(f"No signals passed the confidence threshold of {self.confidence_threshold}")
            return []
            
        # Convert signals to trade decisions
        decisions = []
        for signal in valid_signals:
            coin = signal.coin
            
            if not coin:
                continue
                
            # Skip signals without price
            if coin.current_price <= 0:
                continue
                
            # Determine trade amount based on signal type
            if signal.type == SignalType.BUY:
                # Calculate available amount to buy
                available_cash = self.mock_cash_balance
                cash_to_use = min(self.max_trade_amount_usd, available_cash * 0.2)
                
                # Skip if not enough cash
                if cash_to_use <= 0:
                    continue
                    
                # Calculate amount of tokens to buy
                amount = cash_to_use / coin.current_price
                
                # Skip if amount is too small
                if amount <= 0:
                    continue
                    
                decisions.append({
                    "coin": coin,
                    "type": "BUY",
                    "amount": amount,
                    "price": coin.current_price,
                    "signal_strength": signal.strength,
                    "reason": signal.reason
                })
                
            elif signal.type == SignalType.SELL:
                # Get holding for this coin
                holding = self.portfolio.get_holding(coin.address)
                
                if not holding or holding.amount <= 0:
                    continue
                    
                # Calculate amount to sell (half of total if strong signal, 20% if moderate)
                sell_percentage = 0.5 if signal.strength > 0.85 else 0.2
                amount = holding.amount * sell_percentage
                
                # Skip if amount is too small
                if amount <= 0:
                    continue
                    
                decisions.append({
                    "coin": coin,
                    "type": "SELL",
                    "amount": amount,
                    "price": coin.current_price,
                    "signal_strength": signal.strength,
                    "reason": signal.reason
                })
                
        return decisions
        
    async def execute_trade(self, trade_decision: Dict) -> Dict:
        """
        Execute a trade based on a decision
        
        Args:
            trade_decision: The trade decision dictionary
            
        Returns:
            Dict with trade results
        """
        coin = trade_decision.get("coin")
        if not coin:
            logger.error("❌ Cannot execute trade: No coin specified")
            return {"success": False, "error": "No coin specified"}
            
        trade_type = trade_decision.get("type")
        if not trade_type:
            logger.error("❌ Cannot execute trade: No trade type specified")
            return {"success": False, "error": "No trade type specified"}
            
        amount = trade_decision.get("amount", 0)
        max_usd_amount = trade_decision.get("max_usd_amount", self.max_trade_amount_usd)
        
        # Get the coin's current price
        price = getattr(coin, "current_price", 0)
        if not price or price <= 0:
            logger.warning(f"⚠️ Cannot determine price for {coin.symbol}, using estimated price")
            price = trade_decision.get("estimated_price", 1.0)
            
        # Generate a mocked price for simulation if needed
        if self.simulate and not price:
            price = random.uniform(0.1, 100.0)
            logger.info(f"Using simulated price ${price:.4f} for {coin.symbol}")
            
        # Store the portfolio state before the trade
        before_table = str(self.portfolio.get_table())
        before_total = self.portfolio.get_total_value()
        
        try:
            # Generate the signal from the decision
            signal_type = SignalType.BUY if trade_type.upper() == "BUY" else SignalType.SELL
            
            # Determine the trade amount in USD
            trade_value = min(max_usd_amount, amount * price if amount else max_usd_amount)
            
            # If we're simulating, perform a mock trade
            if self.simulate:
                # Simulate the trade in our portfolio
                if trade_type.upper() == "BUY":
                    # Calculate how many coins we can buy with the trade value
                    if price <= 0:
                        logger.error(f"❌ Cannot execute trade: Invalid price ${price}")
                        return {"success": False, "error": "Invalid price"}
                        
                    # Check if we have enough mock cash
                    if trade_value > self.mock_cash_balance:
                        trade_value = self.mock_cash_balance
                        logger.warning(f"⚠️ Reduced trade amount to ${trade_value:.2f} due to insufficient funds")
                        
                    if trade_value <= 0:
                        logger.error("❌ Trade failed: Insufficient funds")
                        return {"success": False, "error": "Insufficient funds"}
                        
                    amount = trade_value / price
                    
                    # Update our mock cash balance
                    self.mock_cash_balance -= trade_value
                    
                    # Add to portfolio
                    self.portfolio.add_holding(
                        coin=coin,
                        amount=amount,
                        avg_purchase_price=price
                    )
                    
                    # Record the trade
                    self.trading_history.append({
                        "timestamp": datetime.now(),
                        "type": "BUY",
                        "coin": coin.symbol,
                        "amount": amount,
                        "price": price,
                        "value": trade_value,
                        "simulated": True
                    })
                    
                    logger.info(f"✅ TRADE: BOUGHT {amount:.4f} {coin.symbol} @ ${price:.4f} | Total: ${trade_value:.2f}")
                    
                elif trade_type.upper() == "SELL":
                    # Check if we have the coin in our portfolio
                    holding = self.portfolio.get_holding(coin.id)
                    if not holding:
                        logger.error(f"❌ Cannot sell {coin.symbol}: Not in portfolio")
                        return {"success": False, "error": f"Cannot sell {coin.symbol}: Not in portfolio"}
                        
                    # Determine how much to sell
                    if amount <= 0 or amount > holding.amount:
                        amount = holding.amount
                        
                    trade_value = amount * price
                    
                    # Update our mock cash balance
                    self.mock_cash_balance += trade_value
                    
                    # Remove from portfolio
                    self.portfolio.remove_holding(
                        coin=coin,
                        amount=amount,
                        sale_price=price
                    )
                    
                    # Record the trade
                    self.trading_history.append({
                        "timestamp": datetime.now(),
                        "type": "SELL",
                        "coin": coin.symbol,
                        "amount": amount,
                        "price": price,
                        "value": trade_value,
                        "simulated": True
                    })
                    
                    logger.info(f"💰 TRADE: SOLD {amount:.4f} {coin.symbol} @ ${price:.4f} | Total: ${trade_value:.2f}")
                
                # Get after portfolio snapshot
                after_table = str(self.portfolio.get_table())
                after_total = self.portfolio.get_total_value()
                
                # If the portfolio value changed, show the updated table
                value_change = after_total - before_total
                if value_change != 0:
                    change_pct = (value_change / before_total) * 100 if before_total > 0 else 0
                    direction = "+" if value_change > 0 else ""
                    
                    # Display updated portfolio after trade
                    logger.info("")  # Empty line for spacing
                    logger.info(f"Portfolio value change: {direction}${value_change:.2f} ({direction}{change_pct:.2f}%)")
                    
                    # Show updated trading account status
                    logger.info(self.display_agent_status())
                
                return {
                    "success": True,
                    "coin": coin,
                    "amount": amount,
                    "price": price,
                    "value": trade_value,
                    "type": trade_type
                }
            else:
                # Execute a real trade using the ZoraSDKTrader
                logger.info(f"🔄 Executing real trade for {coin.symbol}")
                
                # Create a signal from the trade decision
                signal = Signal(
                    type=signal_type,
                    strength=trade_decision.get("confidence", 0.75),
                    reason=trade_decision.get("reason", "Trading signal"),
                    coin=coin,
                    strategy=trade_decision.get("strategy", "TradingAgent")
                )
                
                # Process the signal with the trader
                result = await self.trader.process_trade_signal(signal, trade_value)
                
                if result.get("success"):
                    # Update our portfolio based on the successful trade
                    if trade_type.upper() == "BUY":
                        # Add to portfolio
                        self.portfolio.add_holding(
                            coin=coin,
                            amount=result.get("token_amount", amount),
                            avg_purchase_price=price
                        )
                        
                        logger.info(f"✅ TRADE: BOUGHT {result.get('token_amount', amount):.4f} {coin.symbol} @ ${price:.4f} | Total: ${trade_value:.2f}")
                        
                    elif trade_type.upper() == "SELL":
                        # Remove from portfolio
                        self.portfolio.remove_holding(
                            coin=coin,
                            amount=result.get("token_amount", amount),
                            sale_price=price
                        )
                        
                        logger.info(f"💰 TRADE: SOLD {result.get('token_amount', amount):.4f} {coin.symbol} @ ${price:.4f} | Total: ${trade_value:.2f}")
                    
                    # Record the trade
                    self.trading_history.append({
                        "timestamp": datetime.now(),
                        "type": trade_type.upper(),
                        "coin": coin.symbol,
                        "amount": result.get("token_amount", amount),
                        "price": price,
                        "value": trade_value,
                        "transaction_hash": result.get("transaction_hash"),
                        "simulated": False
                    })
                    
                    # Return the result
                    return {
                        "success": True,
                        "coin": coin,
                        "amount": result.get("token_amount", amount),
                        "price": price,
                        "value": trade_value,
                        "type": trade_type,
                        "transaction_hash": result.get("transaction_hash")
                    }
                else:
                    logger.error(f"❌ Trade failed: {result.get('error', 'Unknown error')}")
                    return {
                        "success": False,
                        "error": result.get("error", "Trade execution failed"),
                        "coin": coin,
                        "type": trade_type
                    }
            
        except Exception as e:
            logger.error(f"Failed to execute trade: {e}")
            return {
                "success": False,
                "coin": coin,
                "error": str(e),
                "type": trade_type
            }
        
    async def execute_trades(self, trade_decisions: List[Dict[str, Any]]) -> None:
        """
        Execute the trades based on decisions
        
        Args:
            trade_decisions: List of trade decisions to execute
        """
        for trade in trade_decisions:
            await self.execute_trade(trade)
        
    def get_trading_history(self) -> List[Dict[str, Any]]:
        """Get the agent's trading history"""
        return self.trading_history
        
    def set_auto_trading(self, enabled: bool) -> None:
        """Enable or disable auto-trading"""
        self.auto_trading_enabled = enabled
        logger.info(f"{'✅' if enabled else '❌'} Auto-trading {'enabled' if enabled else 'disabled'}")
        
    def set_confidence_threshold(self, threshold: float) -> None:
        """Set the confidence threshold for auto-trading"""
        self.confidence_threshold = max(0.0, min(1.0, threshold))
        logger.info(f"✅ Confidence threshold set to {self.confidence_threshold:.2f}")
        
    def set_max_trade_amount(self, amount_usd: float) -> None:
        """Set the maximum trade amount in USD"""
        self.max_trade_amount_usd = max(0.0, amount_usd)
        logger.info(f"✅ Max trade amount set to ${self.max_trade_amount_usd:.2f}")

    def display_agent_status(self) -> str:
        """
        Display the agent's current status including mock capital
        """
        # Calculate total portfolio value 
        portfolio_value = self.portfolio.get_total_value()
        
        # Calculate total account value (portfolio + available cash)
        total_value = portfolio_value + self.mock_cash_balance
        
        # Calculate profit/loss compared to initial capital
        pnl = total_value - self.mock_capital
        pnl_percent = (pnl / self.mock_capital) * 100 if self.mock_capital > 0 else 0
        
        # Format string with colorful output
        if pnl >= 0:
            pnl_color = Fore.GREEN
            pnl_sign = "+"
        else:
            pnl_color = Fore.RED
            pnl_sign = ""
            
        status = f"\n💰 TRADING ACCOUNT STATUS\n"
        status += f"Initial Capital: ${self.mock_capital:.2f}\n"
        status += f"Portfolio Value: ${portfolio_value:.2f}\n"
        status += f"Available Cash: ${self.mock_cash_balance:.2f}\n"
        status += f"Total Value: ${total_value:.2f}\n"
        status += f"P&L: {pnl_color}{pnl_sign}${pnl:.2f} ({pnl_sign}{pnl_percent:.2f}%){Style.RESET_ALL}\n"
        
        return status
