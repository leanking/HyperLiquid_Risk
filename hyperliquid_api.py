import requests
import json
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

class HyperliquidAPIError(Exception):
    """Custom exception for Hyperliquid API errors"""
    pass

class HyperliquidAPI:
    def __init__(self):
        self.base_url = "https://api.hyperliquid.xyz"
        self.supported_coins = set()
        
    def _make_request(self, endpoint: str, payload: Optional[Dict] = None) -> Dict:
        """
        Make a request to the Hyperliquid API with error handling
        
        Args:
            endpoint (str): API endpoint
            payload (Dict, optional): Request payload
            
        Returns:
            Dict: API response data
            
        Raises:
            HyperliquidAPIError: If the API request fails
        """
        headers = {"Content-Type": "application/json"}
        
        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=10  # Add timeout
            )
            
            # Raise error for bad status codes
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise HyperliquidAPIError(f"API request failed: {str(e)}")
        except json.JSONDecodeError as e:
            raise HyperliquidAPIError(f"Failed to parse API response: {str(e)}")
    
    def get_market_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Fetch both market metadata and current market data in a single request
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary mapping coin symbols to their complete market info
            
        Raises:
            HyperliquidAPIError: If the API request fails or returns invalid data
        """
        endpoint = f"{self.base_url}/info"
        payload = {"type": "metaAndAssetCtxs"}
        
        try:
            data = self._make_request(endpoint, payload)
            
            if not isinstance(data, list) or len(data) < 2:
                raise HyperliquidAPIError("Invalid response format: expected array with 2 elements")
            
            # First element contains universe data
            universe = data[0].get('universe', [])
            # Second element is array of market data
            market_data = data[1]
            
            if not isinstance(universe, list) or not isinstance(market_data, list):
                raise HyperliquidAPIError("Invalid data structure in response")
            
            # Get list of available coins for error messaging
            available_coins = [coin.get('name') for coin in universe if coin.get('name')]
            self.supported_coins = set(available_coins)  # Store supported coins
            
            result = {}
            for idx, coin_info in enumerate(universe):
                try:
                    if idx >= len(market_data):
                        break
                        
                    coin_name = coin_info['name']
                    market_info = market_data[idx]
                    
                    # Combine metadata and market data
                    result[coin_name] = {
                        # Metadata
                        'name': coin_name,
                        'szDecimals': int(coin_info.get('szDecimals', 0)),
                        'maxLeverage': int(coin_info.get('maxLeverage', 0)),
                        # Market data
                        'funding': self._safe_float(market_info.get('funding')),
                        'oraclePx': self._safe_float(market_info.get('oraclePx')),
                        'premium': self._safe_float(market_info.get('premium')),
                        'markPx': self._safe_float(market_info.get('markPx')),
                        'openInterest': self._safe_float(market_info.get('openInterest')),
                        'dayNtlVlm': self._safe_float(market_info.get('dayNtlVlm'))
                    }
                except (KeyError, ValueError) as e:
                    print(f"Warning: Failed to parse market data for {coin_name}: {str(e)}")
                    continue
            
            if not result:
                raise HyperliquidAPIError("No valid market data found in response")
            
            return result
                
        except Exception as e:
            raise HyperliquidAPIError(f"Failed to get market info: {str(e)}")
    
    def get_available_coins(self) -> List[str]:
        """Get list of available coins"""
        try:
            if not self.supported_coins:  # Only fetch if we haven't already
                market_info = self.get_market_info()
            return sorted(list(self.supported_coins))
        except:
            return ["BTC", "ETH"]  # Fallback to common coins if API fails
    
    @staticmethod
    def _safe_float(value: Any) -> float:
        """Safely convert a value to float with validation"""
        try:
            result = float(value)
            if not isinstance(result, (int, float)):
                raise ValueError("Invalid numeric value")
            return result
        except (TypeError, ValueError):
            return 0.0 