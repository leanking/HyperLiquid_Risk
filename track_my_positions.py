from hyperliquid_positions import HyperliquidPositionTracker
from position_logger import PositionLogger
from datetime import datetime, timezone
import time
from dotenv import load_dotenv
import os

def track_wallet(wallet_address: str, interval: int = 60):
    """
    Track wallet positions continuously
    :param wallet_address: The wallet address to track
    :param interval: How often to check positions (in seconds)
    """
    tracker = HyperliquidPositionTracker()
    logger = PositionLogger()
    
    consecutive_errors = 0
    max_consecutive_errors = 5
    
    while True:
        try:
            if consecutive_errors > 0:
                print(f"\nRetrying after previous error (attempt {consecutive_errors}/{max_consecutive_errors})")
            
            print(f"\nFetching positions for {wallet_address}...")
            positions = tracker.get_user_positions(wallet_address)
            summary = tracker.get_account_summary(wallet_address)
            
            # Reset error counter on successful API call
            consecutive_errors = 0
            
            # Calculate risk metrics
            risk_metrics = tracker.calculate_risk_metrics(positions, summary['account_value'])
            
            # Get current UTC time
            current_time = datetime.now(timezone.utc)
            
            if positions:
                print("\nLogging positions...")
                if not logger.log_positions(positions, current_time):
                    print("Warning: Failed to log positions")
                    # Increment error counter if position logging fails
                    consecutive_errors += 1
            else:
                print("\nNo open positions to log")
                # Still log an empty position state to maintain history
                logger.log_positions([], current_time)

            # Always log metrics regardless of open positions
            print("\nLogging metrics...")
            logger.log_metrics(risk_metrics, summary, current_time)
            
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
            else:
                print("No open positions found")
            
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
            
            # Print confirmation of logging
            print(f"\nData logged successfully at {current_time.isoformat()}")
            print(f"Waiting {interval} seconds before next update...")
            time.sleep(interval)
            
        except Exception as e:
            consecutive_errors += 1
            print(f"\nError tracking positions: {str(e)}")
            
            if consecutive_errors >= max_consecutive_errors:
                print(f"\nToo many consecutive errors ({consecutive_errors}). Exiting...")
                break
                
            retry_delay = min(30 * consecutive_errors, 300)  # Exponential backoff, max 5 minutes
            print(f"Retrying in {retry_delay} seconds... (attempt {consecutive_errors}/{max_consecutive_errors})")
            time.sleep(retry_delay)

if __name__ == "__main__":
    load_dotenv()
    wallet_address = os.getenv('WALLET_ADDRESS')
    if not wallet_address:
        raise ValueError("WALLET_ADDRESS not found in environment variables")
    
    print("\nStarting continuous position tracking...")
    print(f"Wallet address: {wallet_address}")
    print("Press Ctrl+C to stop\n")
    
    # Track positions with 1-minute interval
    track_wallet(wallet_address, interval=60) 