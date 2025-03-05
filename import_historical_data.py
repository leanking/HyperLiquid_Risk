from dotenv import load_dotenv
import os
import pandas as pd
from supabase import create_client
from datetime import datetime
import time

def import_csv_to_supabase(csv_path, table_name):
    # Load environment variables
    load_dotenv()
    
    # Get Supabase credentials
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("Supabase credentials not found in environment variables")
    
    # Initialize Supabase client
    supabase = create_client(supabase_url, supabase_key)
    
    print(f"Reading CSV file: {csv_path}")
    df = pd.read_csv(csv_path)
    
    # Convert timestamp column to proper format
    df['timestamp'] = pd.to_datetime(df['timestamp']).apply(lambda x: x.isoformat())
    
    # Convert all numeric columns to float
    numeric_columns = df.select_dtypes(include=['int64', 'float64']).columns
    for col in numeric_columns:
        df[col] = df[col].astype(float)
    
    # Convert DataFrame to list of dictionaries
    records = df.to_dict('records')
    
    print(f"Found {len(records)} records to import")
    
    # Insert records in batches
    batch_size = 100
    total_batches = len(records) // batch_size + (1 if len(records) % batch_size != 0 else 0)
    
    successful_imports = 0
    failed_imports = 0
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        batch_number = (i // batch_size) + 1
        
        try:
            print(f"Importing batch {batch_number}/{total_batches} ({len(batch)} records)")
            supabase.table(table_name).insert(batch).execute()
            successful_imports += len(batch)
            
            # Add a small delay to avoid rate limiting
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Error importing batch {batch_number}: {str(e)}")
            failed_imports += len(batch)
    
    print("\nImport Summary:")
    print(f"Successfully imported: {successful_imports} records")
    print(f"Failed to import: {failed_imports} records")
    
    return successful_imports, failed_imports

def main():
    # Define the paths to your CSV files
    position_csv = "logs/position_history.csv"
    metrics_csv = "logs/metrics_history.csv"
    
    print("Starting import process...")
    
    if os.path.exists(position_csv):
        print("\nImporting position history...")
        import_csv_to_supabase(position_csv, "position_history")
    else:
        print(f"Position history file not found: {position_csv}")
    
    if os.path.exists(metrics_csv):
        print("\nImporting metrics history...")
        import_csv_to_supabase(metrics_csv, "metrics_history")
    else:
        print(f"Metrics history file not found: {metrics_csv}")
    
    print("\nImport process completed!")

if __name__ == "__main__":
    main() 