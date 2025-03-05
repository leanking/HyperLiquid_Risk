# Hyperliquid Risk Management Dashboard

A real-time risk monitoring and analytics dashboard for Hyperliquid positions with Streamlit.

## Features

- Real-time position monitoring
- Comprehensive risk metrics
- Historical data logging with Supabase
- Interactive dark-mode charts
- Position and portfolio analytics
- 7-day realized PnL tracking
- Rate-limited data logging
- Timezone-aware data handling
- Cached API requests for better performance

## Risk Metrics

### Portfolio Level
- Portfolio Heat (0-100): Composite risk measure of leverage, liquidation proximity, and concentration
- Risk-Adjusted Return: Return per unit of risk (similar to Sharpe ratio)
- Margin Utilization: Percentage of account equity used as margin
- Concentration Score: Portfolio diversification measure using HHI
- Total Exposure: Aggregate position value
- Account Leverage: Overall account leverage

### Position Level
- Distance to Liquidation
- Position Size vs Account
- Risk Score (0-100)
- Individual Position Leverage
- Unrealized PnL
- 7-Day Realized PnL
- Total PnL (including closed trades)

## Installation

1. Install required packages:
```bash
pip install -r requirements.txt
```

2. Set up environment variables in `.env`:
```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

3. Install Watchdog for better performance (optional):
```bash
# On macOS
xcode-select --install
pip install watchdog
```

## Usage

1. Start the dashboard:
```bash
streamlit run dashboard.py
```

2. Access the dashboard at `http://localhost:8501`

## Database Setup

Create the following tables in Supabase:

```sql
-- Position history table
create table position_history (
    id bigint primary key generated always as identity,
    timestamp timestamptz not null,
    coin text not null,
    side text not null,
    size numeric not null,
    entry_price numeric not null,
    leverage numeric,
    liquidation_price numeric,
    unrealized_pnl numeric not null,
    realized_pnl numeric not null,
    margin_used numeric
);

-- Metrics history table
create table metrics_history (
    id bigint primary key generated always as identity,
    timestamp timestamptz not null,
    account_value numeric not null,
    total_position_value numeric not null,
    total_unrealized_pnl numeric not null,
    account_leverage numeric not null,
    portfolio_heat numeric not null,
    risk_adjusted_return numeric not null,
    margin_utilization numeric not null,
    concentration_score numeric not null
);

-- Fills history table
create table fills_history (
    id bigint primary key generated always as identity,
    timestamp timestamptz not null,
    coin text not null,
    side text not null,
    size numeric not null,
    price numeric not null,
    closed_pnl numeric not null,
    fill_id text unique not null,
    order_id text
);
```

## Architecture

- `dashboard.py`: Streamlit dashboard interface with caching
- `hyperliquid_positions.py`: Position tracking and API integration
- `position_logger.py`: Rate-limited data logging and retrieval
- `hyperliquid_api.py`: Base API client implementation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

MIT License - See LICENSE file for details

## Support

For issues and feature requests, please open an issue on GitHub.

## Disclaimer

This tool is for informational purposes only. Always verify calculations and conduct your own risk assessment. Trading cryptocurrency involves substantial risk of loss.