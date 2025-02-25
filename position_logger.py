import pandas as pd
from datetime import datetime
import os
import json

class PositionLogger:
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        self.position_log_file = f"{log_dir}/position_history.csv"
        self.metrics_log_file = f"{log_dir}/metrics_history.csv"
        
        # Create log directory if it doesn't exist
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # Initialize or load existing logs
        self.position_history = self._load_or_create_position_log()
        self.metrics_history = self._load_or_create_metrics_log()
    
    def _load_or_create_position_log(self):
        if os.path.exists(self.position_log_file):
            return pd.read_csv(self.position_log_file)
        return pd.DataFrame()
    
    def _load_or_create_metrics_log(self):
        if os.path.exists(self.metrics_log_file):
            return pd.read_csv(self.metrics_log_file)
        return pd.DataFrame()
    
    def log_positions(self, positions, timestamp=None):
        if timestamp is None:
            timestamp = datetime.now()
            
        for position in positions:
            position_data = {
                'timestamp': timestamp,
                'coin': position.coin,
                'side': position.side,
                'size': position.size,
                'entry_price': position.entry_price,
                'leverage': position.leverage,
                'liquidation_price': position.liquidation_price,
                'unrealized_pnl': position.unrealized_pnl,
                'realized_pnl': position.realized_pnl,
                'margin_used': position.margin_used
            }
            
            self.position_history = pd.concat([
                self.position_history,
                pd.DataFrame([position_data])
            ])
            
        self.position_history.to_csv(self.position_log_file, index=False)
    
    def log_metrics(self, metrics, summary, timestamp=None):
        if timestamp is None:
            timestamp = datetime.now()
            
        metrics_data = {
            'timestamp': timestamp,
            'account_value': summary['account_value'],
            'total_position_value': summary['total_position_value'],
            'total_margin_used': summary['total_margin_used'],
            'free_margin': summary['withdrawable'],
            'total_unrealized_pnl': summary['total_unrealized_pnl'],
            'account_leverage': summary['account_leverage'],
            'total_exposure': metrics['portfolio_risks']['total_exposure_usd'],
            'exposure_equity_ratio': metrics['portfolio_risks']['exposure_to_equity_ratio'],
            'portfolio_heat': metrics['portfolio_risks']['portfolio_heat'],
            'risk_adjusted_return': metrics['portfolio_risks']['risk_adjusted_return'],
            'margin_utilization': metrics['portfolio_risks']['margin_utilization'],
            'concentration_score': metrics['portfolio_risks']['concentration_score']
        }
        
        self.metrics_history = pd.concat([
            self.metrics_history,
            pd.DataFrame([metrics_data])
        ])
        
        self.metrics_history.to_csv(self.metrics_log_file, index=False)
    
    def get_position_history(self, coin=None, timeframe=None):
        df = self.position_history.copy()
        if coin:
            df = df[df['coin'] == coin]
        if timeframe:
            # Convert timestamp column to datetime if it's string
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            cutoff_time = pd.Timestamp.now() - timeframe
            df = df[df['timestamp'] >= cutoff_time]
        return df
    
    def get_metrics_history(self, timeframe=None):
        df = self.metrics_history.copy()
        if timeframe:
            # Convert timestamp column to datetime if it's string
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            cutoff_time = pd.Timestamp.now() - timeframe
            df = df[df['timestamp'] >= cutoff_time]
        return df 