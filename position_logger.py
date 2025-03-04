import pandas as pd
from datetime import datetime, timedelta, timezone
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
            
        print("\nInitializing PositionLogger...")
        print(f"- Log directory: {log_dir}")
        print(f"- Supabase URL configured: {'Yes' if supabase_url else 'No'}")
        print(f"- Supabase key configured: {'Yes' if supabase_key else 'No'}")
        
        try:
            self.supabase = create_client(supabase_url, supabase_key)
            print("Supabase client created successfully")
        except Exception as e:
            print(f"Error creating Supabase client: {str(e)}")
            raise
        
        self._last_log_time = datetime.min
        self._log_interval = timedelta(minutes=1)
        self._cache = {}
        
        # First try to verify connection and schema
        if not self.verify_database_connection():
            print("Initial verification failed, attempting to create tables...")
            if not self.create_tables():
                raise ValueError("Failed to create required tables")
            if not self.verify_database_connection():
                raise ValueError("Failed to verify database connection after creating tables")
        
        if not self.verify_database_schema():
            raise ValueError("Failed to verify database schema")
    
    def _verify_connection(self):
        """Internal method to verify connection during initialization"""
        print("\nInitializing database connection...")
        
        # Check environment variables
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        print(f"Environment check:")
        print(f"- SUPABASE_URL present: {'Yes' if supabase_url else 'No'}")
        print(f"- SUPABASE_KEY present: {'Yes' if supabase_key else 'No'}")
        
        if not self.verify_database_connection():
            raise ValueError("Failed to verify database connection - check logs for details")

    def verify_database_connection(self) -> bool:
        """Verify database connection and table structure"""
        try:
            print("\nVerifying database connection...")
            print(f"Using Supabase URL: {self.supabase.supabase_url}")
            
            # Test basic connection first - use a simpler query
            try:
                # Instead of count(*), just get one row to verify connection
                test_query = self.supabase.table('position_history').select("*").limit(1).execute()
                print(f"Connection test successful")
            except Exception as e:
                print(f"Basic connection test failed: {str(e)}")
                return False
            
            # Then check table structure
            try:
                table_info = self.supabase.table('position_history').select("*").limit(1).execute()
                if hasattr(table_info, 'data'):
                    print("Table structure:")
                    if table_info.data:
                        for column in table_info.data[0].keys():
                            print(f"- {column}")
                    else:
                        print("Table exists but is empty (this is okay)")
                else:
                    print("Warning: Unexpected response format from table info query")
                    print(f"Response: {table_info}")
            except Exception as e:
                print(f"Table structure check failed: {str(e)}")
                return False
            
            return True
        except Exception as e:
            print(f"Database verification failed: {str(e)}")
            print("Full error details:")
            import traceback
            traceback.print_exc()
            return False
    
    def should_log(self) -> bool:
        """Check if enough time has passed since last log"""
        now = datetime.now(timezone.utc)  # Use UTC for consistency
        if now - self._last_log_time >= self._log_interval:
            print(f"Logging allowed - Last log: {self._last_log_time.isoformat()}, Current time: {now.isoformat()}")
            self._last_log_time = now
            return True
        print(f"Logging skipped - Last log: {self._last_log_time.isoformat()}, Current time: {now.isoformat()}")
        return False
    
    def log_positions(self, positions, timestamp):
        """Log positions with rate limiting"""
        try:
            print("\n=== Debug: Position Logging ===")
            print(f"Attempting to log {len(positions)} positions at {timestamp}")
            
            # Ensure timestamp is in UTC
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            
            try:
                # First, mark all existing positions as closed
                self.supabase.table('position_history')\
                    .update({'is_open': False})\
                    .eq('is_open', True)\
                    .execute()
                print("✓ Marked existing positions as closed")
                
                # Create position records for current positions
                position_records = []
                for position in positions:
                    try:
                        record = {
                            'timestamp': timestamp.isoformat(),
                            'coin': position.coin.upper(),
                            'side': position.side,
                            'size': str(position.size),  # Convert to string to avoid precision issues
                            'entry_price': str(position.entry_price),
                            'leverage': str(position.leverage) if position.leverage else '0',
                            'liquidation_price': str(position.liquidation_price) if position.liquidation_price else '0',
                            'unrealized_pnl': str(position.unrealized_pnl),
                            'realized_pnl': str(position.realized_pnl),
                            'margin_used': str(position.margin_used) if position.margin_used else '0',
                            'is_open': True
                        }
                        position_records.append(record)
                        print(f"Prepared record for {position.coin}: {json.dumps(record, indent=2)}")
                    except Exception as e:
                        print(f"Error preparing position record for {position.coin}: {str(e)}")
                        continue

                # Insert new position records if we have any
                if position_records:
                    print(f"Inserting {len(position_records)} new position records...")
                    response = self.supabase.table('position_history').insert(position_records).execute()
                    print("✓ Position records inserted successfully")
                    
                    # Verify the insertion
                    self.verify_logging(timestamp)
                    return True
                else:
                    print("No positions to log")
                    return True

            except Exception as e:
                print(f"Database operation error: {str(e)}")
                import traceback
                traceback.print_exc()
                return False

        except Exception as e:
            print(f"Error in log_positions: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def log_metrics(self, risk_metrics: Dict, summary: Dict, timestamp: datetime):
        """Log risk metrics and account summary to database"""
        try:
            # Prepare metrics data
            metrics_data = {
                'timestamp': timestamp.isoformat(),
                'account_value': summary['account_value'],
                'total_position_value': summary['total_position_value'],
                'total_margin_used': summary['total_margin_used'],
                'total_unrealized_pnl': summary['total_unrealized_pnl'],
                'account_leverage': summary['account_leverage'],
                'withdrawable': summary['withdrawable'],
                'portfolio_heat': risk_metrics['portfolio_risks'].get('portfolio_heat', 0),
                'margin_utilization': risk_metrics['portfolio_risks'].get('margin_utilization', 0),
                'risk_adjusted_return': risk_metrics['portfolio_risks'].get('risk_adjusted_return', 0),
                'concentration_score': risk_metrics['portfolio_risks'].get('concentration_score', 0),
                'total_exposure': risk_metrics['portfolio_risks'].get('total_exposure_usd', 0),
                'exposure_to_equity': risk_metrics['portfolio_risks'].get('exposure_to_equity_ratio', 0)
            }

            # Insert into metrics_history table
            self.supabase.table('metrics_history').insert(metrics_data).execute()
            
            print("✓ Metrics logged successfully")
            return True

        except Exception as e:
            print(f"Error logging metrics: {str(e)}")
            return False
    
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
    
    @lru_cache(maxsize=32)
    def get_position_history(self, timeframe: timedelta = timedelta(days=7)) -> pd.DataFrame:
        """Retrieve position history for the specified timeframe"""
        try:
            # Calculate start time in UTC
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timeframe
            
            print(f"\nFetching position history from {start_time.isoformat()} to {end_time.isoformat()}")
            
            # Query position_history table with explicit UTC timestamps
            response = self.supabase.table('position_history')\
                .select('*')\
                .gte('timestamp', start_time.isoformat())\
                .lte('timestamp', end_time.isoformat())\
                .order('timestamp', desc=True)\
                .execute()
            
            if not response.data:
                print("No position history found")
                return pd.DataFrame()
            
            # Convert to DataFrame and process timestamps
            df = pd.DataFrame(response.data)
            
            # Ensure is_open column exists, default to True for older records
            if 'is_open' not in df.columns:
                df['is_open'] = True
            
            # Convert numeric columns from strings back to floats
            numeric_columns = ['size', 'entry_price', 'leverage', 'liquidation_price', 
                             'unrealized_pnl', 'realized_pnl', 'margin_used']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Convert timestamp to datetime with UTC timezone
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            
            # Sort by timestamp ascending for proper plotting
            df = df.sort_values('timestamp')
            
            print(f"Retrieved {len(df)} position records")
            print(f"Latest timestamp: {df['timestamp'].max() if not df.empty else 'No data'}")
            print("Columns:", df.columns.tolist())
            
            return df
            
        except Exception as e:
            print(f"Error retrieving position history: {str(e)}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def get_closed_trades(self, timeframe=None):
        query = self.supabase.table('closed_trades').select("*")
        
        if timeframe:
            cutoff_time = (datetime.now() - timeframe).isoformat()
            query = query.gte('timestamp', cutoff_time)
            
        response = query.execute()
        return pd.DataFrame(response.data)
    
    def get_metrics_history(self, timeframe: timedelta = timedelta(days=7)) -> pd.DataFrame:
        """Retrieve metrics history for the specified timeframe"""
        try:
            # Calculate start time in UTC
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timeframe
            
            print(f"\nFetching metrics from {start_time.isoformat()} to {end_time.isoformat()}")
            
            # Query metrics_history table with explicit UTC timestamps
            response = self.supabase.table('metrics_history')\
                .select('*')\
                .gte('timestamp', start_time.isoformat())\
                .lte('timestamp', end_time.isoformat())\
                .order('timestamp', desc=True)\
                .limit(1000)\
                .execute()
            
            if not response.data:
                print("No metrics data found")
                return pd.DataFrame()
            
            # Convert to DataFrame and process timestamps
            df = pd.DataFrame(response.data)
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            
            # Sort by timestamp ascending for proper plotting
            df = df.sort_values('timestamp')
            df.set_index('timestamp', inplace=True)
            
            print(f"Retrieved {len(df)} metrics records")
            print(f"Latest timestamp: {df.index[-1] if not df.empty else 'No data'}")
            
            return df
            
        except Exception as e:
            print(f"Error retrieving metrics history: {str(e)}")
            return pd.DataFrame()
    
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

    def verify_database_schema(self):
        """Verify that all required tables exist with correct schema"""
        required_tables = {
            'position_history': [
                'timestamp', 'coin', 'side', 'size', 'entry_price', 
                'leverage', 'liquidation_price', 'unrealized_pnl', 
                'realized_pnl', 'margin_used'
            ],
            'metrics_history': [
                'timestamp', 'account_value', 'total_position_value',
                'total_unrealized_pnl', 'account_leverage', 'portfolio_heat',
                'risk_adjusted_return', 'margin_utilization', 'concentration_score'
            ],
            'fills_history': [
                'timestamp', 'coin', 'side', 'size', 'price',
                'closed_pnl', 'fill_id', 'order_id'
            ]
        }
        
        missing_tables = []
        schema_issues = {}
        
        for table, required_columns in required_tables.items():
            try:
                response = self.supabase.table(table).select("*").limit(1).execute()
                if not response.data:
                    print(f"Table {table} exists but is empty")
                    continue
                    
                actual_columns = set(response.data[0].keys())
                missing_columns = set(required_columns) - actual_columns
                
                if missing_columns:
                    schema_issues[table] = list(missing_columns)
                    
            except Exception as e:
                missing_tables.append(table)
                print(f"Error checking table {table}: {str(e)}")
        
        if missing_tables or schema_issues:
            print("\nDatabase Schema Issues Found:")
            if missing_tables:
                print("\nMissing Tables:")
                for table in missing_tables:
                    print(f"- {table}")
            if schema_issues:
                print("\nMissing Columns:")
                for table, columns in schema_issues.items():
                    print(f"\n{table}:")
                    for column in columns:
                        print(f"- {column}")
            return False
        
        return True

    def create_tables(self):
        """Create required tables if they don't exist"""
        try:
            print("\nChecking and creating required tables...")
            
            # SQL for creating position_history table
            position_history_sql = """
            create table if not exists position_history (
                id bigint generated by default as identity primary key,
                timestamp timestamptz not null,
                coin text not null,
                side text not null,
                size numeric not null,
                entry_price numeric not null,
                leverage numeric,
                liquidation_price numeric,
                unrealized_pnl numeric,
                realized_pnl numeric,
                margin_used numeric,
                is_open boolean default true
            );
            """
            
            # SQL for creating metrics_history table
            metrics_history_sql = """
            create table if not exists metrics_history (
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
            """
            
            # SQL for creating fills_history table
            fills_history_sql = """
            create table if not exists fills_history (
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
            """
            
            # Execute the SQL statements
            for sql, table_name in [
                (position_history_sql, 'position_history'),
                (metrics_history_sql, 'metrics_history'),
                (fills_history_sql, 'fills_history')
            ]:
                try:
                    self.supabase.raw(sql).execute()
                    print(f"✓ {table_name} table verified/created")
                except Exception as e:
                    print(f"Error creating {table_name} table: {str(e)}")
                    raise
            
            return True
            
        except Exception as e:
            print(f"Error creating tables: {str(e)}")
            return False

    def verify_logging(self, timestamp):
        """Verify that data was logged successfully"""
        try:
            # Check for records within the last minute
            check_time = timestamp - timedelta(minutes=1)
            
            # Check position_history
            pos_response = self.supabase.table('position_history')\
                .select("*")\
                .gte('timestamp', check_time.isoformat())\
                .execute()
            
            # Check metrics_history
            metrics_response = self.supabase.table('metrics_history')\
                .select("*")\
                .gte('timestamp', check_time.isoformat())\
                .execute()
            
            print("\nLogging Verification:")
            print(f"Position records found: {len(pos_response.data) if pos_response.data else 0}")
            print(f"Metrics records found: {len(metrics_response.data) if metrics_response.data else 0}")
            
            return bool(pos_response.data and metrics_response.data)
            
        except Exception as e:
            print(f"Error verifying logging: {str(e)}")
            return False

    def get_open_positions(self) -> pd.DataFrame:
        """Get currently open positions"""
        try:
            response = self.supabase.table('position_history')\
                .select('*')\
                .eq('is_open', True)\
                .execute()
            
            if not response.data:
                return pd.DataFrame()
            
            df = pd.DataFrame(response.data)
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            return df
            
        except Exception as e:
            print(f"Error retrieving open positions: {str(e)}")
            return pd.DataFrame() 