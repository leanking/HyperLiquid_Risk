from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hyperliquid_api import HyperliquidAPI, HyperliquidAPIError
import numpy as np

@dataclass
class HyperliquidPosition:
    coin: str
    side: str  # 'long' or 'short'
    size: float
    leverage: float
    entry_price: float
    liquidation_price: float
    unrealized_pnl: float
    realized_pnl: float  # Add realized PnL
    margin_used: float
    timestamp: datetime

class HyperliquidPositionTracker(HyperliquidAPI):
    def __init__(self):
        super().__init__()
        self.risk_limits = {
            'max_position_size_usd': 100000,  # Maximum position size in USD
            'max_leverage': 50,               # Maximum allowed leverage
            'max_drawdown_pct': 15,          # Maximum drawdown percentage
            'max_position_pct': 20,          # Maximum single position size as % of equity
            'min_distance_to_liq': 10,       # Minimum distance to liquidation (%)
            'max_correlation': 0.7           # Maximum correlation between positions
        }

    def _safe_float(self, value, default=0.0):
        """Safely convert value to float, returning default if conversion fails"""
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def get_user_positions(self, wallet_address: str) -> List[HyperliquidPosition]:
        """
        Fetch all open positions for a given wallet address
        
        Args:
            wallet_address: User's wallet address in hex format
            
        Returns:
            List[HyperliquidPosition]: List of current open positions
        """
        try:
            response = self._make_request(f"{self.base_url}/info", {
                "type": "clearinghouseState",
                "user": wallet_address
            })
            
            # Get current market prices for PnL calculations
            market_info = self.get_market_info()
            positions: List[HyperliquidPosition] = []
            
            # Parse position data from response
            if 'assetPositions' in response:
                for asset_position in response['assetPositions']:
                    try:
                        position_data = asset_position.get('position', {})
                        if not position_data:
                            continue

                        coin = position_data.get('coin', '')
                        
                        # Get size from szi (size information)
                        size = self._safe_float(position_data.get('szi', 0))
                        if size == 0:
                            continue

                        # Determine side based on szi value
                        side = 'short' if size < 0 else 'long'
                        
                        # Get leverage value safely
                        leverage_data = position_data.get('leverage', {})
                        leverage = self._safe_float(leverage_data.get('value', 0)) if isinstance(leverage_data, dict) else 0
                        
                        # Get other position details with safe conversion
                        entry_price = self._safe_float(position_data.get('entryPx'))
                        liquidation_price = self._safe_float(position_data.get('liquidationPx'))
                        margin_used = self._safe_float(position_data.get('marginUsed'))
                        unrealized_pnl = self._safe_float(position_data.get('unrealizedPnl'))
                        realized_pnl = self._safe_float(position_data.get('realizedPnl'))

                        positions.append(HyperliquidPosition(
                            coin=coin,
                            side=side,
                            size=abs(size),
                            leverage=leverage,
                            entry_price=entry_price,
                            liquidation_price=liquidation_price,
                            unrealized_pnl=unrealized_pnl,
                            realized_pnl=realized_pnl,
                            margin_used=margin_used,
                            timestamp=datetime.fromtimestamp(response.get('time', 0) / 1000)
                        ))
                    except Exception as e:
                        print(f"Warning: Failed to parse position for {coin}: {str(e)}")
                        continue
            
            return positions

        except Exception as e:
            raise HyperliquidAPIError(f"Failed to fetch positions: {str(e)}")

    def get_account_summary(self, wallet_address: str) -> Dict:
        """
        Get account summary including total equity, margin usage, and PnL
        
        Args:
            wallet_address: User's wallet address in hex format
            
        Returns:
            Dict: Account summary information
        """
        try:
            response = self._make_request(f"{self.base_url}/info", {
                "type": "clearinghouseState",
                "user": wallet_address
            })
            
            # Get margin summary from response
            margin_summary = response.get('marginSummary', {})
            cross_margin_summary = response.get('crossMarginSummary', {})
            
            # Calculate total unrealized PnL from all positions
            total_unrealized_pnl = 0
            for asset_position in response.get('assetPositions', []):
                if 'position' in asset_position:
                    position = asset_position['position']
                    unrealized_pnl = float(position.get('unrealizedPnl', 0))
                    total_unrealized_pnl += unrealized_pnl

            # Calculate account leverage
            total_ntl_pos = float(margin_summary.get('totalNtlPos', 0))
            total_margin_used = float(margin_summary.get('totalMarginUsed', 0))
            account_leverage = total_ntl_pos / total_margin_used if total_margin_used > 0 else 0
            
            return {
                "total_position_value": total_ntl_pos,
                "total_margin_used": total_margin_used,
                "account_value": float(margin_summary.get('accountValue', 0)),
                "total_raw_usd": float(margin_summary.get('totalRawUsd', 0)),
                "position_count": len(response.get('assetPositions', [])),
                "withdrawable": float(response.get('withdrawable', 0)),
                "total_unrealized_pnl": total_unrealized_pnl,
                "account_leverage": account_leverage
            }
            
        except Exception as e:
            raise HyperliquidAPIError(f"Failed to get account summary: {str(e)}")

    def calculate_risk_metrics(self, positions: List[HyperliquidPosition], account_value: float) -> Dict:
        """Calculate comprehensive risk metrics for all positions"""
        
        if not positions:
            return {"status": "No open positions"}

        # Initialize metrics
        metrics = {
            "position_risks": {},
            "portfolio_risks": {},
            "risk_warnings": []
        }

        total_exposure = 0
        largest_position = 0
        position_exposures = []

        # Calculate individual position metrics
        for pos in positions:
            position_value = pos.size * pos.entry_price
            exposure = position_value * pos.leverage
            total_exposure += exposure
            largest_position = max(largest_position, position_value)
            position_exposures.append(exposure)

            # Calculate distance to liquidation
            dist_to_liq = abs(pos.entry_price - pos.liquidation_price) / pos.entry_price * 100

            # Update position percentage calculation to use margin
            position_pct = (pos.margin_used / account_value) * 100  # Changed from position_value to margin_used

            # Position-specific metrics
            pos_metrics = {
                "position_value_usd": position_value,
                "exposure_usd": exposure,
                "pct_of_account": position_pct,  # This will now show margin-based percentage
                "distance_to_liquidation": dist_to_liq,
                "leverage": pos.leverage,
                "roi": (pos.unrealized_pnl / pos.margin_used) * 100 if pos.margin_used > 0 else 0,
                "risk_score": self._calculate_position_risk_score(pos, dist_to_liq)
            }

            metrics["position_risks"][pos.coin] = pos_metrics

            # Add position-specific warnings
            self._add_position_warnings(metrics["risk_warnings"], pos, pos_metrics)

        # Portfolio-wide metrics
        metrics["portfolio_risks"] = {
            "total_exposure_usd": total_exposure,
            "exposure_to_equity_ratio": total_exposure / account_value if account_value > 0 else 0,
            "largest_position_pct": (largest_position / account_value) * 100 if account_value > 0 else 0,
            "concentration_score": self._calculate_concentration_score(position_exposures),
            "portfolio_heat": self._calculate_portfolio_heat(positions),
            "risk_adjusted_return": self._calculate_risk_adjusted_return(positions),
            "margin_utilization": sum(p.margin_used for p in positions) / account_value * 100
        }

        # Add portfolio-wide warnings
        self._add_portfolio_warnings(metrics)

        return metrics

    def _calculate_position_risk_score(self, position: HyperliquidPosition, dist_to_liq: float) -> float:
        """Calculate risk score for individual position (0-100, higher is riskier)"""
        # Weights for different risk factors
        weights = {
            'leverage': 0.3,
            'distance_to_liq': 0.3,
            'size': 0.2,
            'pnl': 0.2
        }

        # Normalize each factor to 0-100 scale
        leverage_score = (position.leverage / self.risk_limits['max_leverage']) * 100
        liq_score = max(0, (1 - dist_to_liq / self.risk_limits['min_distance_to_liq'])) * 100
        size_score = (position.size * position.entry_price / self.risk_limits['max_position_size_usd']) * 100
        pnl_score = max(0, -position.unrealized_pnl / position.margin_used * 100) if position.margin_used > 0 else 0

        return (weights['leverage'] * leverage_score +
                weights['distance_to_liq'] * liq_score +
                weights['size'] * size_score +
                weights['pnl'] * pnl_score)

    def _calculate_concentration_score(self, exposures: List[float]) -> float:
        """Calculate portfolio concentration score using HHI"""
        if not exposures:
            return 0
        total = sum(exposures)
        if total == 0:
            return 0
        weights = [e/total for e in exposures]
        hhi = sum(w*w for w in weights) * 100
        return hhi

    def _calculate_portfolio_heat(self, positions: List[HyperliquidPosition]) -> float:
        """Calculate portfolio heat based on leverage and distance to liquidation"""
        if not positions:
            return 0
        
        heat_scores = []
        for pos in positions:
            dist_to_liq = abs(pos.entry_price - pos.liquidation_price) / pos.entry_price
            heat = (pos.leverage / self.risk_limits['max_leverage']) * (1 / dist_to_liq if dist_to_liq > 0 else 1)
            heat_scores.append(heat)
            
        return sum(heat_scores) / len(heat_scores) * 100

    def _calculate_risk_adjusted_return(self, positions: List[HyperliquidPosition]) -> float:
        """Calculate risk-adjusted return (simple Sharpe-like ratio)"""
        if not positions:
            return 0
            
        returns = [p.unrealized_pnl / p.margin_used if p.margin_used > 0 else 0 for p in positions]
        if not returns:
            return 0
            
        avg_return = np.mean(returns)
        std_return = np.std(returns) if len(returns) > 1 else 1
        
        return avg_return / std_return if std_return > 0 else 0

    def _add_position_warnings(self, warnings: List[str], position: HyperliquidPosition, metrics: Dict):
        """Add warnings for individual position risks"""
        if metrics['distance_to_liquidation'] < self.risk_limits['min_distance_to_liq']:
            warnings.append(f"WARNING: {position.coin} position close to liquidation ({metrics['distance_to_liquidation']:.1f}%)")
        
        if metrics['pct_of_account'] > self.risk_limits['max_position_pct']:
            warnings.append(f"WARNING: {position.coin} position size exceeds maximum ({metrics['pct_of_account']:.1f}%)")
        
        if position.leverage > self.risk_limits['max_leverage']:
            warnings.append(f"WARNING: {position.coin} leverage exceeds maximum ({position.leverage}x)")

    def _add_portfolio_warnings(self, metrics: Dict):
        """Add warnings for portfolio-wide risks"""
        portfolio = metrics['portfolio_risks']
        
        if portfolio['margin_utilization'] > 80:
            metrics['risk_warnings'].append(f"WARNING: High margin utilization ({portfolio['margin_utilization']:.1f}%)")
        
        if portfolio['portfolio_heat'] > 70:
            metrics['risk_warnings'].append(f"WARNING: High portfolio heat ({portfolio['portfolio_heat']:.1f})")

    def suggest_risk_adjustments(self, positions: List[HyperliquidPosition], account_value: float) -> List[str]:
        """Suggest position adjustments to reduce risk"""
        risk_metrics = self.calculate_risk_metrics(positions, account_value)
        suggestions = []

        for coin, metrics in risk_metrics["position_risks"].items():
            if metrics['distance_to_liquidation'] < self.risk_limits['min_distance_to_liq']:
                suggestions.append(f"Consider reducing leverage or adding margin to {coin} position")
            
            if metrics['pct_of_account'] > self.risk_limits['max_position_pct']:
                suggestions.append(f"Consider reducing {coin} position size")

        return suggestions

def main():
    tracker = HyperliquidPositionTracker()
    wallet = "0xC9739116b8759B5a0B5834Ed62E218676EA9776F"
    
    try:
        print("\nFetching positions and calculating risk metrics...")
        positions = tracker.get_user_positions(wallet)
        summary = tracker.get_account_summary(wallet)
        
        # Calculate risk metrics
        risk_metrics = tracker.calculate_risk_metrics(positions, summary['account_value'])
        
        # Print positions with risk metrics
        print("\n=== Open Positions with Risk Metrics ===")
        for pos in positions:
            pos_risk = risk_metrics["position_risks"].get(pos.coin, {})
            print(f"\n{pos.coin} {pos.side.upper()}:")
            print(f"├── Size: {pos.size:.4f}")
            print(f"├── Entry Price: ${pos.entry_price:.2f}")
            print(f"├── Current PnL: ${pos.unrealized_pnl:.2f}")
            print(f"├── Leverage: {pos.leverage}x")
            print(f"├── Distance to Liquidation: {pos_risk.get('distance_to_liquidation', 0):.2f}%")
            print(f"├── Position Value: ${pos_risk.get('position_value_usd', 0):,.2f}")
            print(f"├── % of Account: {pos_risk.get('pct_of_account', 0):.2f}%")
            print(f"└── Risk Score: {pos_risk.get('risk_score', 0):.1f}/100")

        # Print portfolio risk metrics
        print("\n=== Account Summary ===")
        print(f"Total Position Value: ${summary['total_position_value']:,.2f}")
        print(f"Total Margin Used: ${summary['total_margin_used']:,.2f}")
        print(f"Total Unrealized PnL: ${summary['total_unrealized_pnl']:,.2f}")
        print(f"Account Value: ${summary['account_value']:,.2f}")
        print(f"Account Leverage: {summary['account_leverage']:.2f}x")
        print(f"Withdrawable: ${summary['withdrawable']:,.2f}")

        print("\n=== Portfolio Risk Metrics ===")
        portfolio_risks = risk_metrics["portfolio_risks"]
        print(f"Total Exposure: ${portfolio_risks['total_exposure_usd']:,.2f}")
        print(f"Exposure/Equity Ratio: {portfolio_risks['exposure_to_equity_ratio']:.2f}")
        print(f"Concentration Score: {portfolio_risks['concentration_score']:.1f}")
        print(f"Portfolio Heat: {portfolio_risks['portfolio_heat']:.1f}")
        print(f"Risk-Adjusted Return: {portfolio_risks['risk_adjusted_return']:.2f}")
        print(f"Margin Utilization: {portfolio_risks['margin_utilization']:.1f}%")

        # Print risk warnings
        if risk_metrics["risk_warnings"]:
            print("\n=== Risk Warnings ===")
            for warning in risk_metrics["risk_warnings"]:
                print(warning)

        # Print risk adjustment suggestions
        suggestions = tracker.suggest_risk_adjustments(positions, summary['account_value'])
        if suggestions:
            print("\n=== Risk Management Suggestions ===")
            for suggestion in suggestions:
                print(suggestion)

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 