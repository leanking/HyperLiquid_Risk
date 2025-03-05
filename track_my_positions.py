from hyperliquid_positions import HyperliquidPositionTracker
from dotenv import load_dotenv
import os

def track_wallet(wallet_address: str):
    tracker = HyperliquidPositionTracker()
    
    try:
        print(f"\nFetching positions for {wallet_address}...")
        positions = tracker.get_user_positions(wallet_address)
        summary = tracker.get_account_summary(wallet_address)
        
        # Calculate risk metrics
        risk_metrics = tracker.calculate_risk_metrics(positions, summary['account_value'])
        
        if not positions:
            print("No open positions found")
            return
            
        # Print positions with risk metrics
        print("\n=== Open Positions with Risk Metrics ===")
        for pos in positions:
            pos_risk = risk_metrics["position_risks"].get(pos.coin, {})
            print(f"\n{pos.coin} {pos.side.upper()}")
            print(f"├── Size: {pos.size:.4f}")
            print(f"├── Entry Price: ${pos.entry_price:.2f}")
            print(f"├── Current PnL: ${pos.unrealized_pnl:.2f}")
            print(f"├── Leverage: {pos.leverage}x")
            print(f"├── Liquidation Price: ${pos.liquidation_price:.2f}")
            print(f"├── Distance to Liquidation: {pos_risk.get('distance_to_liquidation', 0):.2f}%")
            print(f"├── Position Value: ${pos_risk.get('position_value_usd', 0):,.2f}")
            print(f"├── % of Account: {pos_risk.get('pct_of_account', 0):.2f}%")
            print(f"└── Risk Score: {pos_risk.get('risk_score', 0):.1f}/100")
        
        # Print account summary
        print("\n=== Account Summary ===")
        print(f"Account Value: ${summary['account_value']:,.2f}")
        print(f"Total Position Value: ${summary['total_position_value']:,.2f}")
        print(f"Total Margin Used: ${summary['total_margin_used']:,.2f}")
        print(f"Free Margin (Withdrawable): ${summary['withdrawable']:,.2f}")
        print(f"Margin Utilization: {(summary['total_margin_used'] / summary['account_value']) * 100:.1f}%")
        print(f"Free Margin Ratio: {(summary['withdrawable'] / summary['account_value']) * 100:.1f}%")
        print(f"Total Unrealized PnL: ${summary['total_unrealized_pnl']:,.2f}")
        print(f"Account Leverage: {summary['account_leverage']:.2f}x")

        # Print portfolio risk metrics
        print("\n=== Portfolio Risk Metrics ===")
        portfolio_risks = risk_metrics["portfolio_risks"]
        print(f"Total Exposure: ${portfolio_risks['total_exposure_usd']:,.2f}")
        print(f"Exposure/Equity Ratio: {portfolio_risks['exposure_to_equity_ratio']:.2f}")
        print(f"Portfolio Heat: {portfolio_risks['portfolio_heat']:.1f}")
        print(f"Risk-Adjusted Return: {portfolio_risks['risk_adjusted_return']:.2f}")
        print(f"Margin Utilization: {portfolio_risks['margin_utilization']:.1f}%")
        print(f"Concentration Score: {portfolio_risks['concentration_score']:.1f}")

        # Print risk warnings
        if risk_metrics["risk_warnings"]:
            print("\n=== Risk Warnings ===")
            for warning in risk_metrics["risk_warnings"]:
                print(warning)
        
    except Exception as e:
        print(f"Error tracking positions: {str(e)}")

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Get wallet address from environment
    wallet_address = os.getenv('WALLET_ADDRESS')
    if not wallet_address:
        raise ValueError("WALLET_ADDRESS not found in .env file")
        
    track_wallet(wallet_address) 