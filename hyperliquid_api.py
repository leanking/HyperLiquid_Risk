import requests
import json
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import time
from collections import deque

class HyperliquidAPIError(Exception):
    """Custom exception for Hyperliquid API errors"""
    pass

class HyperliquidAPI:
    def __init__(self):
        self.base_url = "https://api.hyperliquid.xyz"
        self.supported_coins = set()
        self.timeout = 10
        
        # Create session with retry strategy
        self.session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[408, 429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST"]
        )
        
        # Mount the adapter with our retry strategy
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Make HTTP request with retry logic"""
        url = f"{self.base_url}{endpoint}"
        
        # If there are params, convert them to JSON for POST requests
        if method.upper() == 'POST' and 'params' in kwargs:
            kwargs['json'] = kwargs.pop('params')
        
        # Add default timeout if not specified
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout
            
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise HyperliquidAPIError(f"API request failed: {str(e)}")
        except json.JSONDecodeError as e:
            raise HyperliquidAPIError(f"Failed to parse API response: {str(e)}")

    def get_market_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Fetch both market metadata and current market data in a single request
        """
        try:
            data = self._make_request("POST", "/info", json={"type": "metaAndAssetCtxs"})
            
            if not isinstance(data, list) or len(data) < 2:
                raise HyperliquidAPIError("Invalid response format: expected array with 2 elements")
            
            universe = data[0].get('universe', [])
            market_data = data[1]
            
            if not isinstance(universe, list) or not isinstance(market_data, list):
                raise HyperliquidAPIError("Invalid data structure in response")
            
            available_coins = [coin.get('name') for coin in universe if coin.get('name')]
            self.supported_coins = set(available_coins)
            
            result = {}
            for idx, coin_info in enumerate(universe):
                try:
                    if idx >= len(market_data):
                        break
                        
                    coin_name = coin_info['name']
                    market_info = market_data[idx]
                    
                    result[coin_name] = {
                        'name': coin_name,
                        'szDecimals': int(coin_info.get('szDecimals', 0)),
                        'maxLeverage': int(coin_info.get('maxLeverage', 0)),
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
            if not self.supported_coins:
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

    def get_user_fills(self, wallet_address: str) -> List[Dict]:
        """Fetch user's historical fills from Hyperliquid API"""
        try:
            data = self._make_request("POST", "/info", json={
                "type": "userFills",
                "user": wallet_address
            })
            if not isinstance(data, list):
                raise HyperliquidAPIError("Invalid response format: expected array")
            return data
        except Exception as e:
            raise HyperliquidAPIError(f"Failed to fetch user fills: {str(e)}") 