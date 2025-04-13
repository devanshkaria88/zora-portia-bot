"""
Portia AI client for enhanced trading analysis
"""
import aiohttp
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class PortiaClient:
    """Client for interacting with Portia AI API"""
    
    def __init__(self, api_key: str, api_url: str):
        """
        Initialize the Portia AI client.
        
        Args:
            api_key: API key for authentication
            api_url: Base URL for the Portia AI API
        """
        self.api_key = api_key
        self.api_url = api_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def analyze_coins(self, coin_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Submit coin data to Portia AI for enhanced analysis.
        
        Args:
            coin_data: List of coin data to analyze
            
        Returns:
            List of enriched coin data with AI insights
        """
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_url}/analyze/coins",
                headers=self.headers,
                json={"coins": coin_data}
            ) as response:
                if response.status != 200:
                    logger.error(f"Portia AI analysis failed: {await response.text()}")
                    # Return original data without enrichment on failure
                    return [{} for _ in coin_data]
                
                data = await response.json()
                return data.get("results", [])
    
    async def log_signal(self, signal_data: Dict[str, Any]) -> bool:
        """
        Log a trading signal to Portia AI for tracking and improvement.
        
        Args:
            signal_data: Trading signal data
            
        Returns:
            True if successfully logged, False otherwise
        """
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_url}/log/signal",
                headers=self.headers,
                json=signal_data
            ) as response:
                if response.status != 200:
                    logger.error(f"Failed to log signal to Portia: {await response.text()}")
                    return False
                
                return True
    
    async def get_market_intelligence(self) -> Dict[str, Any]:
        """
        Get overall market intelligence from Portia AI.
        
        Returns:
            Dictionary with market intelligence data
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.api_url}/market/intelligence",
                headers=self.headers
            ) as response:
                if response.status != 200:
                    logger.error(f"Failed to get market intelligence: {await response.text()}")
                    return {}
                
                data = await response.json()
                return data.get("intelligence", {})
