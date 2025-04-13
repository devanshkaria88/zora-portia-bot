"""
Data models for Zora coins
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class Creator:
    """Represents a creator of a Zora coin"""
    address: str
    username: Optional[str] = None
    display_name: Optional[str] = None
    profile_image_url: Optional[str] = None

@dataclass
class Coin:
    """Represents a Zora coin with its market data"""
    id: str
    address: str
    symbol: str
    name: str
    creator_address: str
    current_price: float
    volume_24h: float
    price_change_24h: float
    created_at: str
    supply: Optional[float] = None
    market_cap: Optional[float] = None
    
    # Additional data that may be populated
    historical_data: List[Dict[str, Any]] = field(default_factory=list)
    recent_trades: List[Dict[str, Any]] = field(default_factory=list)
    creator: Optional[Creator] = None
    
    # Metrics
    holder_count: Optional[int] = None
    trade_count: Optional[int] = None
    
    # AI-enriched data (from Portia)
    ai_sentiment: Optional[float] = None
    growth_potential: Optional[float] = None
    risk_score: Optional[float] = None
    market_cycle: Optional[str] = None
    price_prediction: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'Coin':
        """
        Create a Coin object from Zora API response.
        
        Args:
            data: Coin data from API
            
        Returns:
            Initialized Coin object
        """
        creator = None
        if 'creator' in data and data['creator']:
            creator = Creator(
                address=data['creator'].get('address', ''),
                username=data['creator'].get('username'),
                display_name=data['creator'].get('displayName'),
                profile_image_url=data['creator'].get('profileImageUrl')
            )
        
        holder_count = None
        if 'holders' in data and data['holders']:
            holder_count = data['holders'].get('total')
            
        trade_count = None
        if 'trades' in data and data['trades']:
            trade_count = data['trades'].get('total')
        
        return cls(
            id=data.get('id', ''),
            address=data.get('address', ''),
            symbol=data.get('symbol', ''),
            name=data.get('name', ''),
            creator_address=data.get('creatorAddress', ''),
            current_price=float(data.get('currentPrice', 0)),
            volume_24h=float(data.get('volumeLast24h', 0)),
            price_change_24h=float(data.get('priceChangePercentage24h', 0)),
            created_at=data.get('createdAt', ''),
            supply=float(data.get('supply', 0)) if data.get('supply') is not None else None,
            market_cap=float(data.get('marketCap', 0)) if data.get('marketCap') is not None else None,
            creator=creator,
            holder_count=holder_count,
            trade_count=trade_count
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API calls"""
        return {
            "id": self.id,
            "address": self.address,
            "symbol": self.symbol,
            "name": self.name,
            "creator_address": self.creator_address,
            "current_price": self.current_price,
            "volume_24h": self.volume_24h,
            "price_change_24h": self.price_change_24h,
            "created_at": self.created_at,
            "supply": self.supply,
            "market_cap": self.market_cap,
            "creator": {
                "address": self.creator.address,
                "username": self.creator.username,
                "display_name": self.creator.display_name
            } if self.creator else None,
            "holder_count": self.holder_count,
            "trade_count": self.trade_count,
            # Don't include historical data to keep payload size manageable
            # AI-enriched data
            "ai_sentiment": self.ai_sentiment,
            "growth_potential": self.growth_potential,
            "risk_score": self.risk_score,
            "market_cycle": self.market_cycle
        }
