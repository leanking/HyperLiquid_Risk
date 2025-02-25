import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
from hyperliquid_positions import HyperliquidPositionTracker
from position_logger import PositionLogger
import plotly.express as px

# Initialize
st.set_page_config(page_title="Hyperliquid Position Monitor", layout="wide")
tracker = HyperliquidPositionTracker()
logger = PositionLogger()

def create_position_chart(position_history, metric='unrealized_pnl'):
    fig = px.line(position_history, 
                  x='timestamp', 
                  y=metric, 
                  color='coin',
                  title=f'Position {metric.replace("_", " ").title()} Over Time')
    return fig

def create_metrics_chart(metrics_history, metric):
    fig = px.line(metrics_history, 
                  x='timestamp', 
                  y=metric,
                  title=f'{metric.replace("_", " ").title()} Over Time')
    return fig

def main():
    st.title("Hyperliquid Position Monitor")
    
    # Add risk metrics explanations in an expander
    with st.sidebar.expander("📊 Risk Metrics Explained"):
        st.markdown("""
        ### Portfolio Heat (0-100)
        Composite risk measure considering:
        - Leverage levels across positions
        - Distance to liquidation prices
        - Position concentration
        - Market volatility
        
        Lower values indicate lower risk. Values above 70 suggest high risk exposure.
        
        ### Risk-Adjusted Return
        Measures return per unit of risk (similar to Sharpe ratio):
        - Higher values indicate better risk-adjusted performance
        - Calculated using PnL relative to position volatility
        - Values > 1 suggest good risk-reward balance
        
        ### Margin Utilization (%)
        Percentage of account equity being used as margin:
        - Higher values mean less free capital
        - Above 80% indicates high risk of liquidation
        
        ### Concentration Score (0-100)
        Measures portfolio diversification:
        - Based on Herfindahl-Hirschman Index (HHI)
        - Higher values indicate more concentrated positions
        - Lower values suggest better diversification
        """)
    
    # Sidebar configuration
    st.sidebar.header("Configuration")
    wallet_address = st.sidebar.text_input(
        "Wallet Address",
        value="0xC9739116b8759B5a0B5834Ed62E218676EA9776F"
    )
    update_interval = st.sidebar.slider("Update Interval (seconds)", 30, 300, 60)
    
    # Main content
    col1, col2 = st.columns(2)
    
    try:
        # Fetch current data
        positions = tracker.get_user_positions(wallet_address)
        summary = tracker.get_account_summary(wallet_address)
        risk_metrics = tracker.calculate_risk_metrics(positions, summary['account_value'])
        
        # Log data
        current_time = datetime.now()
        logger.log_positions(positions, current_time)
        logger.log_metrics(risk_metrics, summary, current_time)
        
        # Display Account Summary
        with col1:
            st.subheader("Account Summary")
            st.metric("Account Value", f"${summary['account_value']:,.2f}")
            st.metric("Total Position Value", f"${summary['total_position_value']:,.2f}")
            st.metric("Unrealized PnL", f"${summary['total_unrealized_pnl']:,.2f}")
            total_realized_pnl = sum(p.realized_pnl for p in positions)
            st.metric("Realized PnL", f"${total_realized_pnl:,.2f}")
            st.metric("Total PnL", f"${(summary['total_unrealized_pnl'] + total_realized_pnl):,.2f}")
            st.metric("Account Leverage", f"{summary['account_leverage']:.2f}x")
        
        # Display Risk Metrics
        with col2:
            st.subheader("Risk Metrics")
            st.metric("Portfolio Heat", f"{risk_metrics['portfolio_risks']['portfolio_heat']:.1f}")
            st.metric("Risk-Adjusted Return", f"{risk_metrics['portfolio_risks']['risk_adjusted_return']:.2f}")
            st.metric("Margin Utilization", f"{risk_metrics['portfolio_risks']['margin_utilization']:.1f}%")
            st.metric("Concentration Score", f"{risk_metrics['portfolio_risks']['concentration_score']:.1f}")
        
        # Display Positions
        st.subheader("Open Positions")
        position_data = []
        total_long_size = 0
        total_short_size = 0
        
        for pos in positions:
            pos_risk = risk_metrics["position_risks"].get(pos.coin, {})
            position_value = pos.size * pos.entry_price
            
            # Track total sizes
            if pos.side == 'long':
                total_long_size += position_value
            else:
                total_short_size += position_value
                
            position_data.append({
                "Coin": pos.coin,
                "Side": pos.side,
                "Size": f"{pos.size:.4f}",
                "Entry Price": f"${pos.entry_price:.2f}",
                "Unrealized PnL": f"${pos.unrealized_pnl:.2f}",
                "Realized PnL": f"${pos.realized_pnl:.2f}",
                "Total PnL": f"${(pos.unrealized_pnl + pos.realized_pnl):.2f}",
                "Leverage": f"{pos.leverage}x",
                "Distance to Liq.": f"{pos_risk.get('distance_to_liquidation', 0):.2f}%",
                "Risk Score": f"{pos_risk.get('risk_score', 0):.1f}/100"
            })
            
        # Add summary row
        st.table(pd.DataFrame(position_data))
        
        # Display position size totals
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Long Exposure", f"${total_long_size:,.2f}")
        with col2:
            st.metric("Total Short Exposure", f"${total_short_size:,.2f}")
        
        # Display Charts
        st.subheader("Historical Charts")
        tab1, tab2, tab3 = st.tabs(["PnL", "Account Metrics", "Risk Metrics"])
        
        with tab1:
            try:
                position_history = logger.get_position_history(timeframe=timedelta(hours=24))
                if not position_history.empty:
                    st.plotly_chart(create_position_chart(position_history, 'unrealized_pnl'))
                else:
                    st.info("No historical position data available yet")
            except Exception as e:
                st.error(f"Error displaying PnL chart: {str(e)}")
        
        with tab2:
            try:
                metrics_history = logger.get_metrics_history(timeframe=timedelta(hours=24))
                if not metrics_history.empty:
                    st.plotly_chart(create_metrics_chart(metrics_history, 'account_value'))
                    st.plotly_chart(create_metrics_chart(metrics_history, 'total_unrealized_pnl'))
                else:
                    st.info("No historical metrics data available yet")
            except Exception as e:
                st.error(f"Error displaying account metrics: {str(e)}")
        
        with tab3:
            try:
                if not metrics_history.empty:
                    st.plotly_chart(create_metrics_chart(metrics_history, 'portfolio_heat'))
                    st.plotly_chart(create_metrics_chart(metrics_history, 'risk_adjusted_return'))
                else:
                    st.info("No historical risk metrics available yet")
            except Exception as e:
                st.error(f"Error displaying risk metrics: {str(e)}")
        
        # Display Warnings
        if risk_metrics["risk_warnings"]:
            st.subheader("⚠️ Risk Warnings")
            for warning in risk_metrics["risk_warnings"]:
                st.warning(warning)
        
        # Auto-refresh
        time.sleep(update_interval)
        st.rerun()
            
    except Exception as e:
        st.error(f"Error updating data: {str(e)}")
        time.sleep(update_interval)
        st.rerun()

if __name__ == "__main__":
    main() 