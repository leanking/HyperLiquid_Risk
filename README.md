# Hyperliquid Risk Management Dashboard

A real-time risk monitoring and analytics dashboard for Hyperliquid positions.

## Features

- Real-time position monitoring and tracking
- Comprehensive risk metrics calculation
- Position-level and portfolio-level analytics
- Risk warnings and adjustment suggestions
- Historical position and metrics logging
- Detailed console output for quick analysis

## Risk Metrics

### Portfolio Level
- Portfolio Heat (0-100): Composite risk measure of leverage, liquidation proximity, and concentration
- Risk-Adjusted Return: Return per unit of risk (similar to Sharpe ratio)
- Margin Utilization: Percentage of account equity used as margin
- Concentration Score: Portfolio diversification measure
- Total Exposure: Aggregate position value
- Account Leverage: Overall account leverage
- Free Margin Ratio: Available margin for new positions
- Exposure/Equity Ratio: Total exposure relative to account value

### Position Level
- Distance to Liquidation: Percentage distance to liquidation price
- Position Size vs Account: Position's percentage of total account value
- Risk Score (0-100): Composite risk rating for individual positions
- Individual Position Leverage
- Unrealized PnL
- Entry and Liquidation Prices
- Margin Usage

## Installation

1. Install required packages:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the root directory with the following variables:
```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
WALLET_ADDRESS=your_wallet_address
```

## Usage

### Basic Position Tracking
Run the position tracker to get a detailed view of your current positions:
```bash
python track_my_positions.py
```

### Historical Data Logging
Import historical position data to your Supabase database:
```bash
python import_historical_data.py
```

### Position Logging
Enable continuous position logging:
```bash
python position_logger.py
```

## Project Structure

- `track_my_positions.py`: Main script for real-time position monitoring
- `hyperliquid_positions.py`: Core position tracking and risk calculation logic
- `hyperliquid_api.py`: API interaction with Hyperliquid
- `position_logger.py`: Historical position data logging
- `import_historical_data.py`: Data import utilities for Supabase
- `.env`: Configuration file for API keys and wallet address

## Risk Limits

The system monitors several risk thresholds:
- Maximum position size (USD)
- Maximum leverage
- Maximum drawdown percentage
- Maximum single position size (% of equity)
- Minimum distance to liquidation (%)
- Maximum position correlation

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