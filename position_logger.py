import pandas as pd
from datetime import datetime, timedelta
import os
import json
from supabase import create_client
from dotenv import load_dotenv
from typing import Dict, List
from functools import lru_cache

class PositionLogger:
    def __init__(self, log_dir="logs"):
        # Initialize Supabase client
        load_dotenv()
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not found in environment variables")
            
        self.supabase = create_client(supabase_url, supabase_key)
        
        self._last_log_time = datetime.min
        self._log_interval = timedelta(minutes=1)  # Log at most once per minute
    
    def should_log(self) -> bool:
        """Check if enough time has passed since last log"""
        now = datetime.now()
        if now - self._last_log_time >= self._log_interval:
            self._last_log_time = now
            return True
        return False
    
    def log_positions(self, positions, timestamp):
        """Log positions with rate limiting"""
        if not self.should_log():
            return
            
        # Log open positions with all required fields
        for position in positions:
            self.supabase.table('position_history').insert({
                'timestamp': timestamp.isoformat(),
                'coin': position.coin.upper(),
                'side': position.side,
                'size': float(position.size),
                'entry_price': float(position.entry_price),
                'leverage': float(position.leverage) if position.leverage else 0.0,  # Add missing fields
                'liquidation_price': float(position.liquidation_price) if position.liquidation_price else 0.0,
                'unrealized_pnl': float(position.unrealized_pnl),
                'realized_pnl': float(position.realized_pnl),
                'margin_used': float(position.margin_used) if position.margin_used else 0.0
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
        try:
            cutoff_time = datetime.now() - timeframe
            
            # Get position history with error handling
            position_query = self.supabase.table('position_history').select("*").gte('timestamp', cutoff_time.isoformat())
            position_response = position_query.execute()
            
            if not position_response.data:
                print("No position history data found")
                return pd.DataFrame()  # Return empty DataFrame instead of None
            
            position_df = pd.DataFrame(position_response.data)
            
            # Convert timestamp to datetime
            position_df['timestamp'] = pd.to_datetime(position_df['timestamp'])
            
            # Sort by timestamp
            position_df = position_df.sort_values('timestamp')
            
            return position_df
        
        except Exception as e:
            print(f"Error fetching position history: {str(e)}")
            return pd.DataFrame()
    
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
    
    def log_fill(self, fill: Dict, timestamp: datetime):
        """Log a single fill with its closed PnL, using upsert to handle duplicates"""
        self.supabase.table('fills_history').upsert({
            'timestamp': timestamp.isoformat(),
            'coin': fill['coin'].upper(),
            'side': fill['side'],
            'size': float(fill['sz']),
            'price': float(fill['px']),
            'closed_pnl': float(fill.get('closedPnl', 0)),
            'fill_id': fill['tid'],
            'order_id': fill.get('oid', '')
        }, on_conflict='fill_id').execute()
    
    def log_fills(self, fills: List[Dict]):
        """Log multiple fills from API response"""
        for fill in fills:
            timestamp = datetime.fromtimestamp(fill.get('time', 0) / 1000)
            self.log_fill(fill, timestamp)
    
    def get_fills_history(self, timeframe=None) -> pd.DataFrame:
        """Get historical fills with closed PnL"""
        try:
            # Build base query
            query = self.supabase.table('fills_history').select("*")
            
            # Add timeframe filter if provided
            if timeframe is not None:
                cutoff_time = datetime.now() - timeframe
                query = query.gte('timestamp', cutoff_time.isoformat())
            
            response = query.execute()
            if not response.data:
                return pd.DataFrame()
            
            return pd.DataFrame(response.data)
        
        except Exception as e:
            print(f"Error fetching fills history: {str(e)}")
            return pd.DataFrame()
    
    def get_total_realized_pnl(self, timeframe=None) -> float:
        """Calculate total realized PnL from fills"""
        try:
            fills_df = self.get_fills_history(timeframe)
            if fills_df.empty:
                return 0.0
            return float(fills_df['closed_pnl'].sum())
        except Exception as e:
            print(f"Error calculating total realized PnL: {str(e)}")
            return 0.0
    
    def debug_check(self) -> Dict:
        """Debug helper to check database tables and recent data"""
        debug_info = {
            'tables': {},
            'recent_data': {},
            'errors': []
        }
        
        # Check all tables exist and their structure
        tables = ['position_history', 'metrics_history', 'closed_trades', 'fills_history']
        for table in tables:
            try:
                response = self.supabase.table(table).select("*").limit(1).execute()
                debug_info['tables'][table] = {
                    'exists': True,
                    'columns': list(response.data[0].keys()) if response.data else []
                }
            except Exception as e:
                debug_info['tables'][table] = {
                    'exists': False,
                    'error': str(e)
                }
                debug_info['errors'].append(f"Table '{table}' error: {str(e)}")
        
        # Get recent data samples
        try:
            for table in tables:
                if debug_info['tables'][table].get('exists'):
                    response = self.supabase.table(table).select("*").order('timestamp.desc').limit(3).execute()
                    debug_info['recent_data'][table] = response.data
        except Exception as e:
            debug_info['errors'].append(f"Data fetch error: {str(e)}")
        
        return debug_info

    def print_debug_info(self):
        """Print formatted debug information"""
        debug_info = self.debug_check()
        
        print("\n=== Database Debug Information ===")
        
        print("\n== Table Status ==")
        for table, info in debug_info['tables'].items():
            print(f"\n{table}:")
            print(f"├── Exists: {info['exists']}")
            if info['exists']:
                print(f"└── Columns: {', '.join(info['columns'])}")
            else:
                print(f"└── Error: {info.get('error', 'Unknown error')}")
        
        print("\n== Recent Data Samples ==")
        for table, data in debug_info['recent_data'].items():
            print(f"\n{table} (last 3 records):")
            if data:
                for record in data:
                    print(f"├── {record}")
            else:
                print("└── No recent data found")
        
        if debug_info['errors']:
            print("\n== Errors ==")
            for error in debug_info['errors']:
                print(f"• {error}") 