# Trading Platform Database Schema Documentation

This document outlines the database schema for what appears to be a trading or financial platform tracking positions, metrics, and order fills.

## Tables Overview

The database consists of three main tables:
1. `position_history` - Tracks individual trading positions
2. `metrics_history` - Stores account-level metrics and risk measurements
3. `fills_history` - Records individual order fills

## Table: position_history

Tracks individual trading positions, including entry prices, profitability, and margin usage.

| Column Name | Data Type | Default | Primary | Description |
|-------------|-----------|---------|---------|-------------|
| id | int8 | NULL | ✓ | Unique identifier for each position record |
| timestamp | timestamp | NULL | | When this position record was created |
| coin | text | NULL | | The cryptocurrency or asset being traded |
| side | text | NULL | | Trading direction (likely "buy" or "sell") |
| size | numeric | NULL | | Position size (quantity) |
| entry_price | numeric | NULL | | Average entry price for the position |
| leverage | numeric | NULL | | Leverage multiplier used for the position |
| liquidation_pri | numeric | NULL | | Liquidation price (price at which position would be liquidated) |
| unrealized_pnl | numeric | NULL | | Current unrealized profit/loss |
| realized_pnl | numeric | NULL | | Realized profit/loss from this position |
| margin_used | numeric | NULL | | Amount of margin allocated to this position |

## Table: metrics_history

Tracks account-level metrics including margin usage, exposure, and risk measurements.

| Column Name | Data Type | Default | Primary | Description |
|-------------|-----------|---------|---------|-------------|
| id | int8 | NULL | ✓ | Unique identifier for each metrics record |
| timestamp | timestamp | NULL | | When these metrics were recorded |
| account_value | numeric | NULL | | Total account value |
| total_position_ | numeric | NULL | | Total position value (likely truncated column name) |
| total_margin_u | numeric | NULL | | Total margin used (likely truncated column name) |
| free_margin | numeric | NULL | | Available margin not allocated to positions |
| total_unrealize | numeric | NULL | | Total unrealized PnL across all positions (likely truncated) |
| account_levera | numeric | NULL | | Account leverage ratio (likely truncated column name) |
| total_exposure | numeric | NULL | | Total market exposure |
| exposure_equi | numeric | NULL | | Exposure to equity ratio (likely truncated column name) |
| portfolio_heat | numeric | NULL | | Portfolio heat - risk measurement |
| risk_adjusted_ | numeric | NULL | | Risk-adjusted return or metric (likely truncated) |
| margin_utilizat | numeric | NULL | | Margin utilization ratio (likely truncated) |
| concentration_ | numeric | NULL | | Position concentration metric (likely truncated) |

## Table: fills_history

Records individual order fills, tracking execution details.

| Column Name | Data Type | Default | Primary | Description |
|-------------|-----------|---------|---------|-------------|
| id | int8 | NULL | ✓ | Unique identifier for each fill record |
| timestamp | timestamp | NULL | | When the fill occurred |
| coin | text | NULL | | The cryptocurrency or asset traded |
| side | text | NULL | | Order side ("buy" or "sell") |
| size | numeric | NULL | | Quantity filled |
| price | numeric | NULL | | Execution price |
| closed_pnl | numeric | NULL | | Profit/loss realized if this fill closed a position |
| fill_id | text | NULL | | Exchange-provided fill identifier |
| order_id | text | NULL | | Associated order identifier |
| created_at | timestamp | now() | | When this record was created in the database |

## Relationships

The tables appear to track different aspects of trading activity:

- `position_history` tracks individual positions
- `metrics_history` records account-level statistics
- `fills_history` stores individual trade executions

Time-based analysis can be performed by joining these tables on the `timestamp` fields.

## Notes

- Several column names appear to be truncated in the user interface
- All tables use `id` as their primary key
- The database follows a time-series pattern with `timestamp` fields in each table
- The schema suggests this is for a cryptocurrency trading platform that supports leverage
