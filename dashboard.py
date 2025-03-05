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
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DEFAULT_WALLET = os.getenv('WALLET_ADDRESS')

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
        
        # If is_open column doesn't exist, create it based on latest timestamps
        if 'is_open' not in position_history.columns:
            latest_timestamps = position_history.groupby('coin')['timestamp'].transform('max')
            position_history['is_open'] = (position_history['timestamp'] == latest_timestamps)
        
        # Filter for only open positions
        open_positions = position_history[position_history['is_open'] == True].copy()
        if open_positions.empty:
            print("No open positions found in data")
            return None
            
        # Normalize coin names to uppercase
        open_positions['coin'] = open_positions['coin'].str.upper()
        
        # Ensure numeric type for the metric column
        open_positions[metric] = pd.to_numeric(open_positions[metric], errors='coerce')
        
        print(f"\nPlotting {len(open_positions)} open position records")
        print(f"Time range: {open_positions['timestamp'].min()} to {open_positions['timestamp'].max()}")
        print(f"Coins: {open_positions['coin'].unique().tolist()}")
        
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
        print("Position history columns:", position_history.columns.tolist())
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
        # Ensure timestamp is datetime
        position_history['timestamp'] = pd.to_datetime(position_history['timestamp'])
        
        # Group by timestamp and calculate metrics
        combined_pnl = position_history.groupby('timestamp', as_index=False).agg({
            'unrealized_pnl': 'sum',
            'realized_pnl': 'last'  # Take last value since it's cumulative
        })
        
        # Calculate total PnL
        combined_pnl['total_pnl'] = combined_pnl['unrealized_pnl'] + combined_pnl['realized_pnl']
        
        # Apply smoothing to reduce noise
        window = '10min'
        combined_pnl.set_index('timestamp', inplace=True)
        combined_pnl['unrealized_pnl'] = combined_pnl['unrealized_pnl'].rolling(window=window, center=True, min_periods=1).mean()
        combined_pnl['total_pnl'] = combined_pnl['total_pnl'].rolling(window=window, center=True, min_periods=1).mean()
        combined_pnl.reset_index(inplace=True)
        
        fig = go.Figure()
        
        # Add traces with improved styling
        fig.add_trace(go.Scatter(
            x=combined_pnl['timestamp'],
            y=combined_pnl['unrealized_pnl'],
            name='Unrealized PnL',
            line=dict(color='#00B5FF', width=2, shape='spline'),
            mode='lines'
        ))
        
        fig.add_trace(go.Scatter(
            x=combined_pnl['timestamp'],
            y=combined_pnl['realized_pnl'],
            name='Realized PnL',
            line=dict(color='#00FF9F', width=2, shape='spline'),
            mode='lines'
        ))
        
        fig.add_trace(go.Scatter(
            x=combined_pnl['timestamp'],
            y=combined_pnl['total_pnl'],
            name='Total PnL',
            line=dict(color='#FF00E4', width=2, shape='spline'),
            mode='lines'
        ))
        
        # Update layout with better styling
        fig.update_layout(
            title='PnL Overview',
            plot_bgcolor='rgb(17,17,17)',
            paper_bgcolor='rgb(17,17,17)',
            font_color='white',
            xaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128,128,128,0.2)',
                color='white',
                title='Time',
                rangeslider=dict(visible=True)
            ),
            yaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128,128,128,0.2)',
                tickprefix='$',
                color='white',
                title='PnL ($)',
                zeroline=True,
                zerolinecolor='rgba(255,255,255,0.2)',
                zerolinewidth=1
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
        
        return fig
        
    except Exception as e:
        print(f"Error creating combined PnL chart: {str(e)}")
        import traceback
        traceback.print_exc()  # Add detailed error trace
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

@st.cache_data(ttl=300)
def fetch_historical_data(timeframe=timedelta(hours=24), wallet_address=None):
    try:
        # Get position history
        position_history = logger.get_position_history(timeframe=timeframe)
        if position_history.empty:
            return pd.DataFrame()
            
        # Get fills history
        fills_history = logger.get_fills_history(timeframe=timeframe)
        
        # Create regular time series with minute intervals
        now = datetime.now(timezone.utc)
        start_time = now - timeframe
        date_range = pd.date_range(
            start=start_time,
            end=now,
            freq='1min',
            tz='UTC'
        )
        
        if not fills_history.empty:
            # Ensure timestamps are timezone-aware
            fills_history['timestamp'] = pd.to_datetime(fills_history['timestamp'], utc=True)
            
            # Ensure unique timestamps by grouping and summing closed_pnl
            fills_history = fills_history.groupby('timestamp')['closed_pnl'].sum().reset_index()
            fills_history = fills_history.sort_values('timestamp')
            
            # Calculate cumulative realized PnL
            fills_history['realized_pnl'] = fills_history['closed_pnl'].cumsum()
            
            # Resample PnL to regular intervals
            fills_history.set_index('timestamp', inplace=True)
            resampled_pnl = fills_history['realized_pnl'].reindex(date_range)
            sampled_pnl = resampled_pnl.interpolate(method='linear').ffill().fillna(0)
            
            # Create realized PnL series with timestamp column
            realized_pnl_series = pd.DataFrame({
                'timestamp': date_range,
                'realized_pnl': sampled_pnl
            }).set_index('timestamp')
            
            # Group position history by timestamp and coin, then aggregate
            agg_dict = {
                'unrealized_pnl': 'sum',
                'side': 'first',
                'size': 'first',
                'entry_price': 'first',
                'leverage': 'first',
                'liquidation_price': 'first',
                'margin_used': 'first',
                'is_open': 'max'
            }
            
            # Group by timestamp and coin
            position_history = position_history.groupby(['timestamp', 'coin']).agg(agg_dict).reset_index()
            
            # Convert timezone-aware timestamps to UTC
            position_history['timestamp'] = pd.to_datetime(position_history['timestamp']).dt.tz_convert('UTC')
            
            # Create a copy of position_history with timestamp as index for joining
            position_history_indexed = position_history.set_index('timestamp')
            
            # Join with realized PnL series
            merged = position_history_indexed.join(realized_pnl_series, how='outer')
            
            # Reset index to get timestamp back as a column
            position_history = merged.reset_index()
            
            # Remove timezone info after all operations are complete
            position_history['timestamp'] = position_history['timestamp'].dt.tz_localize(None)
            
            # Sort and fill any missing values
            position_history = position_history.sort_values('timestamp')
            position_history['realized_pnl'] = position_history['realized_pnl'].ffill().fillna(0)
            
            # Fill NaN values in other columns
            numeric_cols = position_history.select_dtypes(include=['float64', 'int64']).columns
            position_history[numeric_cols] = position_history[numeric_cols].fillna(0)
            
        else:
            # Handle case with no fills history
            position_history['realized_pnl'] = 0.0
            # Remove timezone info
            position_history['timestamp'] = position_history['timestamp'].dt.tz_localize(None)
            
            if wallet_address is None:
                wallet_address = DEFAULT_WALLET
            
            # Add is_open column if it doesn't exist
            if 'is_open' not in position_history.columns:
                position_history['is_open'] = False
                current_positions = {pos.coin for pos in tracker.get_user_positions(wallet_address)}
                latest_positions = position_history.sort_values('timestamp').groupby('coin').last()
                position_history.loc[position_history['coin'].isin(current_positions), 'is_open'] = True
        
        # Debug info
        print("\nProcessed position history:")
        print(f"Shape: {position_history.shape}")
        print(f"Columns: {position_history.columns.tolist()}")
        print(f"Time range: {position_history['timestamp'].min()} to {position_history['timestamp'].max()}")
        
        return position_history
        
    except Exception as e:
        print(f"Error fetching historical data: {str(e)}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

def create_account_value_chart(account_history):
    if account_history.empty:
        return None
        
    try:
        fig = go.Figure()
        
        # Add account value trace
        fig.add_trace(go.Scatter(
            x=account_history['timestamp'],
            y=account_history['account_value'],
            name='Account Value',
            line=dict(color='#00FF9F', width=2),
            mode='lines'
        ))
        
        # Add unrealized PnL trace
        fig.add_trace(go.Scatter(
            x=account_history['timestamp'],
            y=account_history['total_unrealized_pnl'],
            name='Unrealized PnL',
            line=dict(color='#00B5FF', width=2),
            mode='lines'
        ))
        
        # Update layout
        fig.update_layout(
            title='Account Value & PnL History',
            plot_bgcolor='rgb(17,17,17)',
            paper_bgcolor='rgb(17,17,17)',
            font_color='white',
            xaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128,128,128,0.2)',
                title='Time'
            ),
            yaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128,128,128,0.2)',
                tickprefix='$',
                title='Value ($)'
            ),
            hovermode='x unified'
        )
        
        return fig
        
    except Exception as e:
        print(f"Error creating account value chart: {str(e)}")
        return None

def main():
    st.title("Hyperliquid Position Monitor")
    
    # Sidebar configuration
    st.sidebar.header("Configuration")
    wallet_address = st.sidebar.text_input(
        "Wallet Address",
        value=DEFAULT_WALLET
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
    
    # Add help expander
    with st.sidebar.expander("Help"):
        st.markdown("""
        ### Risk Metrics Explained
        
        ### Portfolio Heat (0-100)
        Composite risk score based on:
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
        
        ### Exposure/Equity Ratio
        Total position exposure relative to account equity:
        - Higher values indicate higher leverage
        - Represents overall account risk
        - Values > 3 suggest high leverage risk
        
        ### Concentration Score (0-100)
        Measures portfolio diversification:
        - Based on Herfindahl-Hirschman Index (HHI)
        - Higher values indicate more concentrated positions
        - Lower values suggest better diversification
        - Scores > 50 indicate high concentration risk
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
            current_time = datetime.now(timezone.utc)
            unique_timestamp = current_time.strftime('%Y%m%d%H%M%S')
            
            # Fetch current data
            positions_data = fetch_positions(wallet_address)
            summary = fetch_summary(wallet_address)
            
            if summary:
                try:
                    # Log account summary
                    logger.log_account_summary(summary, current_time)
                except Exception as e:
                    print(f"Error logging account summary: {str(e)}")
                    # Verify database connection
                    logger.verify_database_connection()
                    continue
            
            if not positions_data:
                with metrics_container:
                    st.warning("No open positions found. Please check your wallet address.")
                time.sleep(update_interval)
                continue

            risk_metrics = fetch_risk_metrics(positions_data, summary['account_value'])
            fills = fetch_fills(wallet_address)
            seven_day_pnl = logger.get_total_realized_pnl(timeframe=timedelta(days=7))

            # Update metrics
            with metrics_container:
                st.text(f"Last updated: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Account Summary")
                    col1_1, col1_2 = st.columns(2)
                    
                    with col1_1:
                        st.metric("Account Value", f"${summary.get('account_value', 0):,.2f}")
                        st.metric("Unrealized PnL", f"${summary.get('total_unrealized_pnl', 0):,.2f}")
                        st.metric("7-Day PnL", f"${seven_day_pnl:,.2f}")
                    
                    with col1_2:
                        st.metric("Position Value", f"${summary.get('total_position_value', 0):,.2f}")
                        st.metric("Realized PnL", f"${summary.get('total_realized_pnl', 0):,.2f}")
                        st.metric("Withdrawable", f"${summary.get('withdrawable', 0):,.2f}")
                
                with col2:
                    st.subheader("Risk Metrics")
                    portfolio_risks = risk_metrics.get("portfolio_risks", {})
                    col2_1, col2_2 = st.columns(2)
                    
                    with col2_1:
                        st.metric("Portfolio Heat", f"{portfolio_risks.get('portfolio_heat', 0):.1f}")
                        st.metric("Risk-Adjusted Return", f"{portfolio_risks.get('risk_adjusted_return', 0):.2f}")
                        st.metric("Margin Utilization", f"{portfolio_risks.get('margin_utilization', 0):.1f}%")
                    
                    with col2_2:
                        st.metric("Exposure/Equity", f"{portfolio_risks.get('exposure_to_equity_ratio', 0):.2f}x")
                        st.metric("Concentration", f"{portfolio_risks.get('concentration_score', 0):.1f}")
                        st.metric("Account Leverage", f"{summary.get('account_leverage', 0):.2f}x")

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
                position_history = fetch_historical_data(wallet_address=wallet_address)
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

                account_history = logger.get_account_history(timeframe=timedelta(hours=24))
                if not account_history.empty:
                    st.subheader("Account History")
                    account_chart = create_account_value_chart(account_history)
                    if account_chart:
                        st.plotly_chart(account_chart, use_container_width=True)

            # Update the logging section in the main loop
            if current_time.minute % 5 == 0 and current_time.second < 5:
                try:
                    print("\n=== Starting Logging Process ===")
                    print(f"Current UTC time: {current_time.isoformat()}")
                    print(f"Number of positions to log: {len(positions_data)}")
                    
                    # Debug position data
                    for pos in positions_data:
                        print(f"Position: {pos['coin']} - Size: {pos['size']} - Entry: {pos['entry_price']}")
                    
                    # Now we can pass the proper Position objects to log_positions
                    logger.log_positions(positions_data, current_time)
                    
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