# Hyperliquid Risk Management Dashboard

A real-time risk monitoring and analytics dashboard for Hyperliquid positions.

## Features

- Real-time position monitoring
- Comprehensive risk metrics
- Historical data logging
- Interactive charts
- Position and portfolio analytics

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

## Installation

1. Install required packages:
```pip install -r requirements.txt```

2. Configure your API keys in `config.yaml`:
```yaml
api_keys:
  hyperliquid:
    key: "your_key_here"
    secret: "your_secret_here"
```

## Usage

1. Start the dashboard:
```bash
python main.py
```

2. Access the dashboard at `http://localhost:8050`

## Configuration

Adjust risk thresholds and alerts in `config.yaml`:

```yaml
risk_thresholds:
  portfolio_heat_max: 80
  leverage_max: 5
  concentration_max: 0.5
  liquidation_distance_min: 0.15

alerts:
  email: true
  discord: false
  telegram: false
```

## Architecture

- `main.py`: Dashboard entry point
- `risk_calculator.py`: Core risk metric calculations
- `data_fetcher.py`: Real-time market data collection
- `position_monitor.py`: Position tracking and updates
- `alert_manager.py`: Risk alert system
- `utils/`: Helper functions and utilities

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