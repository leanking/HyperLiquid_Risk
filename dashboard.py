import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
import time
from hyperliquid_positions import HyperliquidPositionTracker, HyperliquidPosition
from position_logger import PositionLogger
import plotly.express as px
from streamlit import cache_data, cache_resource
from dataclasses import asdict

# Initialize
st.set_page_config(page_title="Hyperliquid Position Monitor", layout="wide")

# Use cache_resource for the tracker and logger instances
@st.cache_resource
def get_tracker_and_logger():
    try:
        tracker = HyperliquidPositionTracker()
        logger = PositionLogger()
        # Force initialization of logger methods
        _ = logger.verify_database_connection()
        return tracker, logger
    except Exception as e:
        st.error(f"Failed to initialize tracker/logger: {str(e)}")
        raise e

# Get a fresh instance of tracker and logger
if 'tracker' not in st.session_state or 'logger' not in st.session_state:
    st.session_state.tracker, st.session_state.logger = get_tracker_and_logger()
tracker = st.session_state.tracker
logger = st.session_state.logger

def create_position_chart(position_history, metric='unrealized_pnl'):
    if position_history.empty:
        return None
        
    try:
        # Convert timestamp to UTC and remove timezone info for consistent comparison
        position_history['timestamp'] = pd.to_datetime(position_history['timestamp']).dt.tz_localize(None)
        
        # Filter for only open positions
        open_positions = position_history[position_history['is_open'] == True]
        if open_positions.empty:
            return None
            
        # Normalize coin names to uppercase
        open_positions['coin'] = open_positions['coin'].str.upper()
        
        fig = px.line(open_positions, 
                     x='timestamp', 
                     y=metric, 
                     color='coin',
                     title=f'Open Positions {metric.replace("_", " ").title()} Over Time')
        
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
        st.error(f"Chart error: {str(e)}")
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
        # Ensure timestamp is datetime and remove any timezone info
        position_history['timestamp'] = pd.to_datetime(position_history['timestamp']).dt.tz_localize(None)
        
        # Sort by timestamp and remove any duplicates
        position_history = position_history.sort_values('timestamp')
        position_history = position_history.drop_duplicates(subset=['timestamp', 'coin'])
        
        # Group by timestamp and calculate metrics
        combined_pnl = position_history.groupby('timestamp').agg({
            'unrealized_pnl': 'sum',
            'realized_pnl': 'max'  # Take the max value since it's cumulative
        }).reset_index()
        
        # Calculate total PnL
        combined_pnl['total_pnl'] = combined_pnl['unrealized_pnl'] + combined_pnl['realized_pnl']
        
        # Debug info
        print("Combined PnL shape:", combined_pnl.shape)
        print("Timestamp range:", combined_pnl['timestamp'].min(), "to", combined_pnl['timestamp'].max())
        print("Realized PnL range:", combined_pnl['realized_pnl'].min(), "to", combined_pnl['realized_pnl'].max())
        
        fig = go.Figure()
        
        # Add traces for each PnL type
        fig.add_trace(go.Scatter(
            x=combined_pnl['timestamp'],
            y=combined_pnl['unrealized_pnl'],
            name='Unrealized PnL',
            line=dict(color='#00B5FF', width=2)
        ))
        
        fig.add_trace(go.Scatter(
            x=combined_pnl['timestamp'],
            y=combined_pnl['realized_pnl'],
            name='Realized PnL',
            line=dict(color='#00FF9F', width=2)
        ))
        
        fig.add_trace(go.Scatter(
            x=combined_pnl['timestamp'],
            y=combined_pnl['total_pnl'],
            name='Total PnL',
            line=dict(color='#FF00E4', width=2)
        ))
        
        # Update layout
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
                title='Time'
            ),
            yaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128,128,128,0.2)',
                tickprefix='$',
                color='white',
                title='PnL ($)'
            ),
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                font=dict(color='white'),
                bgcolor='rgba(0,0,0,0.5)'
            ),
            hovermode='x unified'
        )
        
        # Add debug info
        print("Chart Data Points:", len(combined_pnl))
        print("Time Range:", combined_pnl['timestamp'].min(), "to", combined_pnl['timestamp'].max())
        print("Realized PnL Range:", combined_pnl['realized_pnl'].min(), "to", combined_pnl['realized_pnl'].max())
        
        return fig
    except Exception as e:
        print(f"Error creating combined PnL chart: {str(e)}")
        st.error(f"Chart error: {str(e)}")
        return None

# Split the data fetching into smaller, cacheable functions
@st.cache_data(ttl=30)
def fetch_positions(wallet_address: str):
    try:
        positions = tracker.get_user_positions(wallet_address)
        if positions:
            # Convert positions to dictionaries for serialization
            return [asdict(pos) for pos in positions]
        return None
    except Exception as e:
        st.error(f"Error fetching positions: {str(e)}")
        return None

@st.cache_data(ttl=30)
def fetch_summary(wallet_address: str):
    try:
        return tracker.get_account_summary(wallet_address)
    except Exception as e:
        st.error(f"Error fetching summary: {str(e)}")
        return None

@st.cache_data(ttl=30)
def fetch_risk_metrics(positions, account_value):
    """Fetch risk metrics with proper position objects"""
    if positions:
        # If positions are dictionaries, convert them to HyperliquidPosition objects
        if isinstance(positions[0], dict):
            positions = [
                HyperliquidPosition(
                    coin=pos['coin'],
                    side=pos['side'],
                    size=pos['size'],
                    leverage=pos['leverage'],
                    entry_price=pos['entry_price'],
                    liquidation_price=pos['liquidation_price'],
                    unrealized_pnl=pos['unrealized_pnl'],
                    realized_pnl=pos['realized_pnl'],
                    margin_used=pos['margin_used'],
                    timestamp=datetime.fromisoformat(pos['timestamp']) if isinstance(pos['timestamp'], str) else pos['timestamp']
                )
                for pos in positions
            ]
        return tracker.calculate_risk_metrics(positions, account_value)
    return None

@st.cache_data(ttl=30)
def fetch_fills(wallet_address: str):
    try:
        return tracker.get_user_fills(wallet_address)
    except Exception as e:
        st.error(f"Error fetching fills: {str(e)}")
        return None

@st.cache_data(ttl=300)  # Cache historical data for 5 minutes
def fetch_historical_data(timeframe=timedelta(hours=24)):
    try:
        # Get position history
        position_history = logger.get_position_history(timeframe=timeframe)
        
        # Ensure we have the basic position history
        if position_history.empty:
            return pd.DataFrame()
            
        # Convert timestamps to datetime if they aren't already
        position_history['timestamp'] = pd.to_datetime(position_history['timestamp'])
        
        # If timestamps are naive (no timezone), localize to UTC
        if position_history['timestamp'].dt.tz is None:
            position_history['timestamp'] = position_history['timestamp'].dt.tz_localize('UTC')
        # If timestamps have a different timezone, convert to UTC
        elif str(position_history['timestamp'].dt.tz) != 'UTC':
            position_history['timestamp'] = position_history['timestamp'].dt.tz_convert('UTC')
        
        # Get current time in UTC
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)
        
        # Remove timezone info after calculations
        position_history['timestamp'] = position_history['timestamp'].dt.tz_localize(None)
        now = now.replace(tzinfo=None)
        seven_days_ago = seven_days_ago.replace(tzinfo=None)
        
        # Filter to last 7 days and remove duplicates
        position_history = position_history[position_history['timestamp'] >= seven_days_ago]
        position_history = position_history.drop_duplicates(subset=['timestamp', 'coin'])
        
        # Initialize realized_pnl column with zeros
        position_history['realized_pnl'] = 0.0
        
        # Get fills history for realized PnL
        fills_history = logger.get_fills_history(timeframe=timedelta(days=7))
        
        if not fills_history.empty:
            # Convert fills timestamp to datetime and handle timezone
            fills_history['timestamp'] = pd.to_datetime(fills_history['timestamp'])
            
            # Handle timezone for fills similar to positions
            if fills_history['timestamp'].dt.tz is None:
                fills_history['timestamp'] = fills_history['timestamp'].dt.tz_localize('UTC')
            elif str(fills_history['timestamp'].dt.tz) != 'UTC':
                fills_history['timestamp'] = fills_history['timestamp'].dt.tz_convert('UTC')
                
            fills_history['timestamp'] = fills_history['timestamp'].dt.tz_localize(None)
            
            # Create a complete date range for the last 7 days up to now
            date_range = pd.date_range(
                start=seven_days_ago,
                end=now,
                freq='h',
                normalize=False  # Don't normalize to midnight
            )
            
            # Calculate cumulative PnL for each fill
            fills_history = fills_history.sort_values('timestamp')
            fills_history['cumulative_pnl'] = fills_history['closed_pnl'].cumsum()
            
            # Create hourly PnL series
            hourly_pnl = pd.DataFrame({'timestamp': date_range})
            
            # Ensure timestamps match exactly by flooring to hours
            fills_history['timestamp'] = fills_history['timestamp'].dt.floor('h')
            position_history['timestamp'] = position_history['timestamp'].dt.floor('h')
            
            # Merge with consistent timestamp format
            hourly_pnl = hourly_pnl.merge(
                fills_history[['timestamp', 'cumulative_pnl']],
                on='timestamp',
                how='left'
            )
            hourly_pnl['cumulative_pnl'] = hourly_pnl['cumulative_pnl'].ffill().fillna(0)
            
            # Merge with position history
            position_history = position_history.merge(
                hourly_pnl[['timestamp', 'cumulative_pnl']],
                on='timestamp',
                how='left'
            )
            position_history['realized_pnl'] = position_history['cumulative_pnl'].ffill().fillna(0)
            position_history = position_history.drop('cumulative_pnl', axis=1)
        
        # Sort by timestamp for consistent display
        position_history = position_history.sort_values('timestamp')
        
        # Add debug info
        print("\nHistorical Data Debug Info:")
        print(f"Current UTC time: {now}")
        print(f"Seven days ago UTC: {seven_days_ago}")
        print("Position History Shape:", position_history.shape)
        print("Position History Columns:", position_history.columns.tolist())
        print("Position History Timestamp dtype:", position_history['timestamp'].dtype)
        print("Time Range:", position_history['timestamp'].min(), "to", position_history['timestamp'].max())
        print("Sample timestamps:", position_history['timestamp'].head().tolist())
        print("Realized PnL Range:", position_history['realized_pnl'].min(), "to", position_history['realized_pnl'].max())
        
        return position_history
        
    except Exception as e:
        print(f"Error fetching historical data: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

def main():
    st.title("Hyperliquid Position Monitor")
    
    # Sidebar configuration
    st.sidebar.header("Configuration")
    wallet_address = st.sidebar.text_input(
        "Wallet Address",
        value="0xC9739116b8759B5a0B5834Ed62E218676EA9776F"
    )
    update_interval = st.sidebar.slider(
        "Update Interval (seconds)", 
        min_value=30,
        max_value=300,
        value=60
    )

    # Create placeholders for dynamic content
    metrics_container = st.empty()
    positions_container = st.empty()
    charts_container = st.empty()
    
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
            debug_info = st.session_state.logger.debug_check()
            st.json(debug_info)
        if st.button("Check Recent Positions"):
            recent = st.session_state.logger.get_position_history(timeframe=timedelta(minutes=30))
            st.dataframe(recent)
        if st.button("Verify Database"):
            if st.session_state.logger.verify_database_connection():
                st.success("Database connection verified")
            else:
                st.error("Database connection failed")
    
    try:
        while True:
            # Get current timestamp for unique keys
            current_time = datetime.now(timezone.utc)
            unique_timestamp = current_time.strftime('%Y%m%d%H%M%S')

            positions_data = fetch_positions(wallet_address)
            
            if not positions_data:
                with metrics_container:
                    st.warning("No open positions found. Please check your wallet address.")
                time.sleep(update_interval)
                continue

            summary = fetch_summary(wallet_address)
            if summary is None:
                with metrics_container:
                    st.error("Error fetching account summary")
                time.sleep(update_interval)
                continue

            # Convert dictionary positions back to HyperliquidPosition objects for logging
            positions = [
                HyperliquidPosition(
                    coin=pos['coin'],
                    side=pos['side'],
                    size=pos['size'],
                    leverage=pos['leverage'],
                    entry_price=pos['entry_price'],
                    liquidation_price=pos['liquidation_price'],
                    unrealized_pnl=pos['unrealized_pnl'],
                    realized_pnl=pos['realized_pnl'],
                    margin_used=pos['margin_used'],
                    timestamp=datetime.fromisoformat(pos['timestamp']) if isinstance(pos['timestamp'], str) else pos['timestamp']
                )
                for pos in positions_data
            ]

            risk_metrics = fetch_risk_metrics(positions, summary['account_value'])
            fills = fetch_fills(wallet_address)
            seven_day_pnl = logger.get_total_realized_pnl(timeframe=timedelta(days=7))

            # Update metrics
            with metrics_container:
                st.text(f"Last updated: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Account Summary")
                    st.metric("Account Value", f"${summary.get('account_value', 0):,.2f}")
                    st.metric("Total Position Value", f"${summary.get('total_position_value', 0):,.2f}")
                    st.metric("Unrealized PnL", f"${summary.get('total_unrealized_pnl', 0):,.2f}")
                    st.metric("7-Day Realized PnL", f"${seven_day_pnl:,.2f}")
                
                with col2:
                    st.subheader("Risk Metrics")
                    portfolio_risks = risk_metrics.get("portfolio_risks", {})
                    st.metric("Portfolio Heat", f"{portfolio_risks.get('portfolio_heat', 0):.1f}")
                    st.metric("Risk-Adjusted Return", f"{portfolio_risks.get('risk_adjusted_return', 0):.2f}")
                    st.metric("Margin Utilization", f"{portfolio_risks.get('margin_utilization', 0):.1f}%")

            # Update positions table
            with positions_container:
                st.subheader("Open Positions")
                position_data = []
                for pos in positions_data:
                    pos_risk = risk_metrics.get("position_risks", {}).get(pos['coin'], {})
                    position_data.append({
                        "Coin": pos['coin'],
                        "Side": pos['side'],
                        "Size": f"{pos['size']:.4f}",
                        "Entry Price": f"${pos['entry_price']:.2f}",
                        "Unrealized PnL": f"${pos['unrealized_pnl']:.2f}",
                        "Leverage": f"{pos['leverage']}x",
                        "Distance to Liq.": f"{pos_risk.get('distance_to_liquidation', 0):.2f}%",
                        "Risk Score": f"{pos_risk.get('risk_score', 0):.1f}/100"
                    })
                
                if position_data:
                    st.table(pd.DataFrame(position_data))

            # Update charts
            with charts_container:
                position_history = fetch_historical_data()
                if not position_history.empty:
                    st.subheader("Historical Charts")
                    tab1, tab2 = st.tabs(["PnL Charts", "Position Charts"])
                    
                    with tab1:
                        pnl_chart = create_combined_pnl_chart(position_history)
                        if pnl_chart:
                            st.plotly_chart(
                                pnl_chart, 
                                use_container_width=True,
                                key=f"pnl_chart_{unique_timestamp}"  # Make key unique
                            )
                    
                    with tab2:
                        pos_chart = create_position_chart(position_history, 'unrealized_pnl')
                        if pos_chart:
                            st.plotly_chart(
                                pos_chart, 
                                use_container_width=True,
                                key=f"position_chart_{unique_timestamp}"  # Make key unique
                            )

            # Update the logging section in the main loop
            if current_time.minute % 5 == 0 and current_time.second < 5:
                try:
                    print("\n=== Starting Logging Process ===")
                    print(f"Current UTC time: {current_time.isoformat()}")
                    print(f"Number of positions to log: {len(positions)}")
                    
                    # Debug position data
                    for pos in positions:
                        print(f"Position: {pos.coin} - Size: {pos.size} - Entry: {pos.entry_price}")
                    
                    # Now we can pass the proper Position objects to log_positions
                    logger.log_positions(positions, current_time)
                    
                    if fills:
                        print(f"\nLogging {len(fills)} fills")
                        logger.log_fills(fills)
                        print("Fills logged successfully")
                        
                    if risk_metrics and summary:
                        print("\nLogging metrics")
                        logger.log_metrics(risk_metrics, summary, current_time)
                        print("Metrics logged successfully")
                        
                    print("=== Logging Process Complete ===\n")
                    
                except Exception as e:
                    print(f"Error during logging: {str(e)}")
                    import traceback
                    traceback.print_exc()

            # Sleep for the specified interval
            time.sleep(update_interval)

    except Exception as e:
        st.error(f"Error updating data: {str(e)}")
        st.exception(e)
        time.sleep(5)
        st.rerun()

if __name__ == "__main__":
    main() 