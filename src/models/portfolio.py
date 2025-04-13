"""
Portfolio management for the Zora trading bot
Tracks user holdings and provides methods to manage them
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from tabulate import tabulate
from colorama import Fore, Style

from .coin import Coin

logger = logging.getLogger(__name__)

@dataclass
class Holding:
    """Represents a user's holding of a specific token"""
    coin: Coin
    amount: float
    avg_purchase_price: float = 0.0
    last_updated: datetime = None
    
    @property
    def current_value(self) -> float:
        """Calculate the current value of this holding"""
        return self.amount * self.coin.current_price
    
    @property
    def purchase_value(self) -> float:
        """Calculate the purchase value of this holding"""
        return self.amount * self.avg_purchase_price
    
    @property
    def profit_loss(self) -> float:
        """Calculate the profit/loss of this holding"""
        return self.current_value - self.purchase_value
    
    @property
    def profit_loss_percent(self) -> float:
        """Calculate the profit/loss percentage of this holding"""
        if self.purchase_value == 0:
            return 0
        return (self.profit_loss / self.purchase_value) * 100
    
    def to_dict(self) -> Dict:
        """Convert holding to dict for serialization"""
        return {
            "coin_id": self.coin.id,
            "coin_symbol": self.coin.symbol,
            "amount": self.amount,
            "avg_purchase_price": self.avg_purchase_price,
            "current_value": self.current_value,
            "profit_loss": self.profit_loss,
            "profit_loss_percent": self.profit_loss_percent,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None
        }


class Portfolio:
    """Manages a user's portfolio of token holdings"""
    
    def __init__(self, wallet_address: str):
        self.wallet_address = wallet_address
        self.holdings: Dict[str, Holding] = {}  # coin_id -> Holding
        self.total_value: float = 0
        self.last_updated: Optional[datetime] = None
    
    def add_holding(self, coin: Any, amount: float, avg_purchase_price: float = 0.0) -> None:
        """
        Add or update a holding in the portfolio
        
        Args:
            coin: The coin object
            amount: Amount of tokens to add
            avg_purchase_price: Average purchase price per token
        """
        coin_id = getattr(coin, 'id', str(coin))
        
        if coin_id in self.holdings:
            # Update existing holding
            existing_holding = self.holdings[coin_id]
            
            # Calculate new average purchase price if adding more
            if amount > existing_holding.amount:
                # Only recalculate if we're adding more tokens
                new_total_cost = (existing_holding.amount * existing_holding.avg_purchase_price) + (amount * avg_purchase_price)
                new_total_amount = existing_holding.amount + amount
                new_avg_price = new_total_cost / new_total_amount
                
                # Update the holding
                self.holdings[coin_id] = Holding(
                    coin=coin,
                    amount=new_total_amount,
                    avg_purchase_price=new_avg_price
                )
            else:
                # Just update the amount (for existing positions)
                self.holdings[coin_id] = Holding(
                    coin=coin,
                    amount=amount,
                    avg_purchase_price=existing_holding.avg_purchase_price if existing_holding.avg_purchase_price > 0 else avg_purchase_price
                )
        else:
            # Add new holding
            self.holdings[coin_id] = Holding(
                coin=coin,
                amount=amount,
                avg_purchase_price=avg_purchase_price
            )
        self._update_total_value()
    
    def remove_holding(self, coin: Any, amount: float = None, sale_price: float = 0.0) -> None:
        """
        Remove or reduce a holding in the portfolio
        
        Args:
            coin: The coin object to remove
            amount: Amount to remove (if None, removes entire holding)
            sale_price: The price at which the tokens were sold
        """
        coin_id = getattr(coin, 'id', str(coin))
        
        if coin_id not in self.holdings:
            return
            
        existing_holding = self.holdings[coin_id]
        
        if amount is None or amount >= existing_holding.amount:
            # Remove the entire holding
            del self.holdings[coin_id]
        else:
            # Reduce the holding
            new_amount = existing_holding.amount - amount
            self.holdings[coin_id] = Holding(
                coin=existing_holding.coin,
                amount=new_amount,
                avg_purchase_price=existing_holding.avg_purchase_price
            )
        self._update_total_value()
            
    def update_holding_amount(self, coin_id: str, new_amount: float) -> None:
        """
        Update the amount of a specific holding
        
        Args:
            coin_id: ID of the coin to update
            new_amount: New amount of the holding
        """
        if coin_id in self.holdings:
            holding = self.holdings[coin_id]
            self.holdings[coin_id] = Holding(
                coin=holding.coin,
                amount=new_amount,
                avg_purchase_price=holding.avg_purchase_price
            )
        self._update_total_value()
    
    def get_holding(self, coin_id: str) -> Optional[Holding]:
        """Get a specific holding by coin ID"""
        return self.holdings.get(coin_id)
    
    def get_all_holdings(self) -> List[Holding]:
        """Get all holdings in the portfolio"""
        return list(self.holdings.values())
    
    def _update_total_value(self) -> None:
        """Update the total value of the portfolio"""
        self.total_value = sum(h.current_value for h in self.holdings.values())
        self.last_updated = datetime.now()
    
    def to_dict(self) -> Dict:
        """Convert portfolio to dict for serialization"""
        return {
            "wallet_address": self.wallet_address,
            "total_value": self.total_value,
            "holdings": [h.to_dict() for h in self.holdings.values()],
            "last_updated": self.last_updated.isoformat() if self.last_updated else None
        }
    
    def display_as_table(self) -> str:
        """Get portfolio as a formatted table string"""
        if not self.holdings:
            return "No holdings found in portfolio"
            
        # Sort holdings by value in descending order
        sorted_holdings = sorted(
            self.holdings.values(), 
            key=lambda h: h.current_value,
            reverse=True
        )
        
        # Create table data
        headers = [
            "Token", "Symbol", "Amount", "Value (USD)", "Price (USD)", "Change"
        ]
        
        rows = []
        for holding in sorted_holdings:
            # Calculate profit/loss color
            if holding.profit_loss_percent > 0:
                pnl_color = Fore.GREEN
            elif holding.profit_loss_percent < 0:
                pnl_color = Fore.RED
            else:
                pnl_color = Style.RESET_ALL
                
            # Format profit/loss text with color
            if holding.profit_loss_percent != 0:
                pnl_text = f"{pnl_color}{holding.profit_loss_percent:.2f}%{Style.RESET_ALL}"
            else:
                pnl_text = "0.00%"
                
            rows.append([
                holding.coin.name,
                holding.coin.symbol,
                f"{holding.amount:.4f}",
                f"${holding.current_value:.2f}",
                f"${holding.coin.current_price:.2f}",
                pnl_text
            ])
            
        # Add total row
        rows.append([
            "TOTAL", "", "", f"${self.total_value:.2f}", "", ""
        ])
        
        # Format the table
        table = tabulate(
            rows,
            headers=headers,
            tablefmt="pretty",
            stralign="right",
            numalign="right"
        )
        
        return f"\n{table}\n"
        
    def get_table(self) -> str:
        """Alias for display_as_table method"""
        return self.display_as_table()
        
    def get_total_value(self) -> float:
        """Get the total value of the portfolio"""
        return self.total_value
