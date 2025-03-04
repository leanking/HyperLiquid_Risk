import pandas as pd
from datetime import datetime, timedelta
import os
import json
from supabase import create_client
from dotenv import load_dotenv

class PositionLogger:
    def __init__(self, log_dir="logs"):
        # Initialize Supabase client
        load_dotenv()
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not found in environment variables")
            
        self.supabase = create_client(supabase_url, supabase_key)
        
    def log_positions(self, positions, timestamp):
        # Log open positions
        for position in positions:
            self.supabase.table('position_history').insert({
                'timestamp': timestamp.isoformat(),
                'coin': position.coin.upper(),
                'side': position.side,
                'size': float(position.size),
                'entry_price': float(position.entry_price),
                'unrealized_pnl': float(position.unrealized_pnl),
                'realized_pnl': float(position.realized_pnl)
            }).execute()
    
    def log_metrics(self, risk_metrics, summary, timestamp):
        self.supabase.table('metrics_history').insert({
            'timestamp': timestamp.isoformat(),
            'account_value': float(summary['account_value']),
            'total_position_value': float(summary['total_position_value']),
            'total_unrealized_pnl': float(summary['total_unrealized_pnl']),
            'account_leverage': float(summary['account_leverage']),
            'portfolio_heat': float(risk_metrics['portfolio_risks']['portfolio_heat']),
            'risk_adjusted_return': float(risk_metrics['portfolio_risks']['risk_adjusted_return']),
            'margin_utilization': float(risk_metrics['portfolio_risks']['margin_utilization']),
            'concentration_score': float(risk_metrics['portfolio_risks']['concentration_score'])
        }).execute()
    
    def log_closed_trade(self, trade, timestamp):
        self.supabase.table('closed_trades').insert({
            'timestamp': timestamp.isoformat(),
            'coin': trade['coin'].upper(),
            'side': trade['side'],
            'size': float(trade['size']),
            'entry_price': float(trade['entry_price']),
            'exit_price': float(trade['exit_price']),
            'profit': float(trade['profit'])
        }).execute()
    
    def get_position_history(self, timeframe=timedelta(hours=24)):
        cutoff_time = datetime.now() - timeframe
        
        # Get position history
        position_query = self.supabase.table('position_history').select("*").gte('timestamp', cutoff_time.isoformat())
        position_response = position_query.execute()
        position_df = pd.DataFrame(position_response.data)
        
        # Get closed trades
        closed_trades_query = self.supabase.table('closed_trades').select("*").gte('timestamp', cutoff_time.isoformat())
        closed_trades_response = closed_trades_query.execute()
        closed_trades_df = pd.DataFrame(closed_trades_response.data)
        
        # Process position history
        if not position_df.empty:
            position_df = position_df.groupby(['timestamp', 'coin']).agg({
                'unrealized_pnl': 'sum',
                'realized_pnl': 'sum'
            }).reset_index()
        
        # Process closed trades
        if not closed_trades_df.empty:
            closed_trades_df = closed_trades_df.groupby(['timestamp', 'coin']).agg({
                'profit': 'sum'
            }).reset_index()
            closed_trades_df = closed_trades_df.rename(columns={'profit': 'closed_trade_pnl'})
        
        # Merge position history with closed trades
        if not position_df.empty and not closed_trades_df.empty:
            df = pd.merge(position_df, closed_trades_df, on=['timestamp', 'coin'], how='outer').fillna(0)
        elif not position_df.empty:
            df = position_df
            df['closed_trade_pnl'] = 0
        elif not closed_trades_df.empty:
            df = closed_trades_df
            df['unrealized_pnl'] = 0
            df['realized_pnl'] = 0
        else:
            return pd.DataFrame()
        
        return df
    
    def get_closed_trades(self, timeframe=None):
        query = self.supabase.table('closed_trades').select("*")
        
        if timeframe:
            cutoff_time = (datetime.now() - timeframe).isoformat()
            query = query.gte('timestamp', cutoff_time)
            
        response = query.execute()
        return pd.DataFrame(response.data)
    
    def get_metrics_history(self, timeframe=None):
        query = self.supabase.table('metrics_history').select("*")
        
        if timeframe:
            cutoff_time = (datetime.now() - timeframe).isoformat()
            query = query.gte('timestamp', cutoff_time)
            
        response = query.execute()
        return pd.DataFrame(response.data) 