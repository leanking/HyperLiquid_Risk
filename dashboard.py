import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
from hyperliquid_positions import HyperliquidPositionTracker
from position_logger import PositionLogger
import plotly.express as px
from streamlit import cache_data

# Initialize
st.set_page_config(page_title="Hyperliquid Position Monitor", layout="wide")
tracker = HyperliquidPositionTracker()
logger = PositionLogger()

def create_position_chart(position_history, metric='unrealized_pnl'):
    if position_history.empty:
        return None
        
    try:
        # Convert timestamp to UTC and remove timezone info for consistent comparison
        position_history['timestamp'] = pd.to_datetime(position_history['timestamp']).dt.tz_localize(None)
        
        # Normalize coin names to uppercase
        position_history['coin'] = position_history['coin'].str.upper()
        
        fig = px.line(position_history, 
                      x='timestamp', 
                      y=metric, 
                      color='coin',
                      title=f'Position {metric.replace("_", " ").title()} Over Time')
        
        # Enhance the chart appearance
        fig.update_layout(
            plot_bgcolor='rgb(17,17,17)',
            paper_bgcolor='rgb(17,17,17)',
            font_color='white',
            xaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128,128,128,0.2)',
                color='white'
            ),
            yaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128,128,128,0.2)',
                tickprefix='$',
                color='white'
            )
        )
        return fig
    except Exception as e:
        print(f"Error creating position chart: {str(e)}")
        st.error(f"Chart error: {str(e)}")  # Add visible error in UI
        return None

def create_metrics_chart(metrics_history, metric):
    fig = px.line(metrics_history, 
                  x='timestamp', 
                  y=metric,
                  title=f'{metric.replace("_", " ").title()} Over Time')
    
    # Enhance the chart appearance with dark mode
    fig.update_layout(
        plot_bgcolor='rgb(17,17,17)',
        paper_bgcolor='rgb(17,17,17)',
        font_color='white',
        xaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(128,128,128,0.2)',
            color='white'
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(128,128,128,0.2)',
            tickprefix='$' if 'pnl' in metric.lower() or 'value' in metric.lower() else '',
            color='white'
        )
    )
    return fig

def create_combined_pnl_chart(position_history):
    if position_history.empty:
        return None
        
    try:
        # Normalize coin names to uppercase
        position_history['coin'] = position_history['coin'].str.upper()
        
        # Convert timestamp to UTC for consistent comparison
        position_history['timestamp'] = pd.to_datetime(position_history['timestamp']).dt.tz_localize(None)
        
        # Ensure we only show last 7 days of data
        seven_days_ago = datetime.now().replace(tzinfo=None)  # Remove timezone info
        seven_days_ago = seven_days_ago - timedelta(days=7)
        position_history = position_history[position_history['timestamp'] >= seven_days_ago]
        
        # Group by timestamp and sum PnL across all coins
        combined_pnl = position_history.groupby('timestamp').agg({
            'unrealized_pnl': 'sum',
            'realized_pnl': 'sum'
        }).reset_index()
        
        # Calculate total PnL
        combined_pnl['total_pnl'] = combined_pnl['unrealized_pnl'] + combined_pnl['realized_pnl']
        
        fig = go.Figure()
        
        # Add traces for each PnL type
        fig.add_trace(go.Scatter(
            x=combined_pnl['timestamp'],
            y=combined_pnl['unrealized_pnl'],
            name='Unrealized PnL',
            line=dict(color='#00B5FF')  # Bright blue
        ))
        fig.add_trace(go.Scatter(
            x=combined_pnl['timestamp'],
            y=combined_pnl['realized_pnl'],
            name='7-Day Realized PnL',
            line=dict(color='#00FF9F')  # Bright green
        ))
        fig.add_trace(go.Scatter(
            x=combined_pnl['timestamp'],
            y=combined_pnl['total_pnl'],
            name='Total PnL',
            line=dict(color='#FF00E4')  # Bright purple
        ))
        
        fig.update_layout(
            title='7-Day PnL Overview',
            plot_bgcolor='rgb(17,17,17)',
            paper_bgcolor='rgb(17,17,17)',
            font_color='white',
            xaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128,128,128,0.2)',
                color='white',
                title='Last 7 Days'
            ),
            yaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128,128,128,0.2)',
                tickprefix='$',
                color='white'
            ),
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                font=dict(color='white')
            )
        )
        return fig
    except Exception as e:
        print(f"Error creating combined PnL chart: {str(e)}")
        st.error(f"Chart error: {str(e)}")  # Add visible error in UI
        return None

# Add cached data fetching
@cache_data(ttl=10)  # Cache for 10 seconds
def fetch_position_data(wallet_address: str):
    positions = tracker.get_user_positions(wallet_address)
    summary = tracker.get_account_summary(wallet_address)
    fills = tracker.get_user_fills(wallet_address)
    if not positions:
        return None, None, None, None
    risk_metrics = tracker.calculate_risk_metrics(positions, summary['account_value'])
    # Get 7-day realized PnL
    seven_day_pnl = logger.get_total_realized_pnl(timeframe=timedelta(days=7))
    return positions, summary, risk_metrics, fills, seven_day_pnl

@cache_data(ttl=30)  # Cache for 30 seconds
def fetch_historical_data(timeframe=timedelta(hours=24)):
    return logger.get_position_history(timeframe=timeframe)

def main():
    st.title("Hyperliquid Position Monitor")
    
    # Add column definitions at the start of main()
    col1, col2 = st.columns(2)
    
    # Add wallet address input to sidebar
    st.sidebar.header("Configuration")
    wallet_address = st.sidebar.text_input(
        "Wallet Address",
        value="0xC9739116b8759B5a0B5834Ed62E218676EA9776F"
    )
    update_interval = st.sidebar.slider("Update Interval (seconds)", 10, 300, 30)
    
    # Add a placeholder for the last update time
    last_update = st.empty()
    
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
    
    # Add debug expander
    with st.sidebar.expander("Debug Info"):
        if st.button("Check Database"):
            logger.print_debug_info()
    
    # Main content
    try:
        # Fetch data using cached functions
        positions, summary, risk_metrics, fills, seven_day_pnl = fetch_position_data(wallet_address)
        
        if positions is None:
            st.warning("No open positions found. Please check your wallet address.")
            time.sleep(update_interval)
            st.rerun()
            return
        
        # Log data only every minute to reduce database writes
        current_time = datetime.now()
        if current_time.second < 5:  # Log in the first 5 seconds of every minute
            logger.log_positions(positions, current_time)
            logger.log_fills(fills)
            logger.log_metrics(risk_metrics, summary, current_time)
        
        # Update last update time
        last_update.text(f"Last updated: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Display metrics using the cached data
        total_realized_pnl = logger.get_total_realized_pnl(timeframe=timedelta(hours=24))
        
        # Display Account Summary with 7-day realized PnL
        with col1:
            st.subheader("Account Summary")
            try:
                st.metric("Account Value", f"${summary.get('account_value', 0):,.2f}")
                st.metric("Total Position Value", f"${summary.get('total_position_value', 0):,.2f}")
                st.metric("Unrealized PnL", f"${summary.get('total_unrealized_pnl', 0):,.2f}")
                st.metric("7-Day Realized PnL", f"${seven_day_pnl:,.2f}")  # Changed label
                st.metric("Total PnL", f"${(summary.get('total_unrealized_pnl', 0) + seven_day_pnl):,.2f}")
                st.metric("Account Leverage", f"{summary.get('account_leverage', 0):.2f}x")
            except Exception as e:
                st.error(f"Error displaying account summary: {str(e)}")
        
        # Display Risk Metrics with safe value handling
        with col2:
            st.subheader("Risk Metrics")
            try:
                portfolio_risks = risk_metrics.get("portfolio_risks", {})
                st.metric("Portfolio Heat", f"{portfolio_risks.get('portfolio_heat', 0):.1f}")
                st.metric("Risk-Adjusted Return", f"{portfolio_risks.get('risk_adjusted_return', 0):.2f}")
                st.metric("Margin Utilization", f"{portfolio_risks.get('margin_utilization', 0):.1f}%")
                st.metric("Concentration Score", f"{portfolio_risks.get('concentration_score', 0):.1f}")
            except Exception as e:
                st.error(f"Error displaying risk metrics: {str(e)}")
        
        # Display Positions with safe value handling
        st.subheader("Open Positions")
        position_data = []
        
        for pos in positions:
            pos_risk = risk_metrics.get("position_risks", {}).get(pos.coin, {})
            position_data.append({
                "Coin": pos.coin,
                "Side": pos.side,
                "Size": f"{getattr(pos, 'size', 0):.4f}",
                "Entry Price": f"${getattr(pos, 'entry_price', 0):.2f}",
                "Unrealized PnL": f"${getattr(pos, 'unrealized_pnl', 0):.2f}",
                "Realized PnL": f"${getattr(pos, 'realized_pnl', 0):.2f}",
                "Total PnL": f"${(getattr(pos, 'unrealized_pnl', 0) + getattr(pos, 'realized_pnl', 0)):.2f}",
                "Leverage": f"{getattr(pos, 'leverage', 0)}x",
                "Distance to Liq.": f"{pos_risk.get('distance_to_liquidation', 0):.2f}%",
                "Risk Score": f"{pos_risk.get('risk_score', 0):.1f}/100"
            })
        
        if position_data:
            st.table(pd.DataFrame(position_data))
        else:
            st.info("No position data to display")
        
        # Fetch historical data using cache
        position_history = fetch_historical_data()
        
        # Display charts only if we have data
        if not position_history.empty:
            st.subheader("Historical Charts")
            tab1, tab2, tab3 = st.tabs(["PnL Charts", "Account Metrics", "Risk Metrics"])
            
            with tab1:
                pnl_chart = create_combined_pnl_chart(position_history)
                if pnl_chart:
                    st.plotly_chart(pnl_chart, use_container_width=True)
                
                pos_chart = create_position_chart(position_history, 'unrealized_pnl')
                if pos_chart:
                    st.plotly_chart(pos_chart, use_container_width=True)
        
        # Add data validation messages
        if st.sidebar.checkbox("Show Data Validation"):
            st.sidebar.json({
                "Positions Count": len(positions),
                "Has Summary": bool(summary),
                "Has Risk Metrics": bool(risk_metrics),
                "Database Status": "Connected" if logger else "Not Connected"
            })
        
        # Sleep for shorter intervals and update more frequently
        time.sleep(min(update_interval, 10))  # Never sleep more than 10 seconds
        st.rerun()
            
    except Exception as e:
        st.error(f"Error updating data: {str(e)}")
        st.exception(e)
        time.sleep(5)  # Short sleep on error
        st.rerun()

if __name__ == "__main__":
    main() 