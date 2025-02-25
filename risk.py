from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import numpy as np

class Side(Enum):
    LONG = "LONG"
    SHORT = "SHORT"

@dataclass
class Position:
    symbol: str
    side: Side
    size: float
    entry_price: float
    leverage: float
    liquidation_price: Optional[float] = None
    unrealized_pnl: float = 0.0

class RiskManager:
    def __init__(self, 
                 account_equity: float,
                 max_position_size_usd: float = 100000,
                 max_leverage: float = 10,
                 max_drawdown_pct: float = 15,
                 max_position_pct: float = 20):
        """
        Initialize the risk manager with account parameters and risk limits
        
        Args:
            account_equity: Total account equity in USD
            max_position_size_usd: Maximum position size in USD
            max_leverage: Maximum allowed leverage
            max_drawdown_pct: Maximum allowed drawdown percentage
            max_position_pct: Maximum single position size as % of equity
        """
        self.account_equity = account_equity
        self.max_position_size_usd = max_position_size_usd
        self.max_leverage = max_leverage
        self.max_drawdown_pct = max_drawdown_pct
        self.max_position_pct = max_position_pct
        self.positions: List[Position] = []

    def add_position(self, position: Position) -> bool:
        """Add a new position and check if it meets risk parameters"""
        if self._validate_position(position):
            self.positions.append(position)
            return True
        return False

    def _validate_position(self, position: Position) -> bool:
        """Validate if a new position meets risk parameters"""
        # Check leverage limits
        if position.leverage > self.max_leverage:
            return False

        # Check position size limits
        position_value = position.size * position.entry_price
        if position_value > self.max_position_size_usd:
            return False

        # Check position size as percentage of equity
        position_pct = (position_value / self.account_equity) * 100
        if position_pct > self.max_position_pct:
            return False

        return True

    def calculate_portfolio_metrics(self) -> Dict:
        """Calculate overall portfolio risk metrics"""
        total_position_value = 0
        total_exposure = 0
        unrealized_pnl = 0

        for position in self.positions:
            position_value = position.size * position.entry_price
            total_position_value += position_value
            total_exposure += position_value * position.leverage
            unrealized_pnl += position.unrealized_pnl

        portfolio_leverage = total_exposure / self.account_equity if self.account_equity > 0 else 0

        return {
            "total_position_value": total_position_value,
            "total_exposure": total_exposure,
            "portfolio_leverage": portfolio_leverage,
            "unrealized_pnl": unrealized_pnl,
            "equity_usage_pct": (total_position_value / self.account_equity) * 100
        }

    def calculate_position_risk(self, position: Position, current_price: float) -> Dict:
        """Calculate risk metrics for a specific position"""
        position_value = position.size * position.entry_price
        current_value = position.size * current_price
        
        # Calculate unrealized PnL
        if position.side == Side.LONG:
            unrealized_pnl = current_value - position_value
        else:
            unrealized_pnl = position_value - current_value

        # Calculate ROE (Return on Equity)
        roe = (unrealized_pnl / (position_value / position.leverage)) * 100

        # Calculate distance to liquidation
        distance_to_liq = 0
        if position.liquidation_price:
            if position.side == Side.LONG:
                distance_to_liq = ((current_price - position.liquidation_price) / current_price) * 100
            else:
                distance_to_liq = ((position.liquidation_price - current_price) / current_price) * 100

        return {
            "position_value": position_value,
            "unrealized_pnl": unrealized_pnl,
            "roe": roe,
            "distance_to_liquidation": distance_to_liq,
            "equity_usage_pct": (position_value / self.account_equity) * 100
        }

    def check_drawdown(self, initial_equity: float) -> Dict:
        """Check current drawdown against maximum allowed drawdown"""
        current_equity = self.account_equity + sum(p.unrealized_pnl for p in self.positions)
        drawdown_pct = ((initial_equity - current_equity) / initial_equity) * 100
        
        return {
            "current_drawdown_pct": drawdown_pct,
            "max_drawdown_warning": drawdown_pct > self.max_drawdown_pct,
            "remaining_drawdown": self.max_drawdown_pct - drawdown_pct
        }

    def get_position_correlation(self, positions: List[Position]) -> float:
        """Calculate correlation between position returns (if historical data available)"""
        # This would require historical price data implementation
        pass

    def suggest_position_size(self, price: float, leverage: float) -> float:
        """Suggest a position size based on current portfolio risk"""
        available_equity = self.account_equity * (self.max_position_pct / 100)
        suggested_size = (available_equity * leverage) / price
        return min(suggested_size, self.max_position_size_usd / price)
