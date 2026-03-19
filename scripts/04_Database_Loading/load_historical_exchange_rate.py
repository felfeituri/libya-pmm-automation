"""
Libya PMM - Load Historical Exchange Rate Data
ONE-TIME SCRIPT: Loads historical master exchange rate file to database

This script should only be run ONCE to load all historical exchange rate data.
For monthly updates, use load_exchange_to_db.py instead.

Usage:
    python scripts/04_Database_Loading/load_historical_exchange_rate.py
    python scripts/04_Database_Loading/load_historical_exchange_rate.py --file path/to/Master_Exchange_Rate.xlsx
"""

import sys
from pathlib import Path
import os

# Auto-detect environment and set project root
if os.path.exists('/app'):  # Running in Docker
    PROJECT_ROOT = Path('/app')
else:  # Running locally
    # Script is in scripts/04_Database_Loading/
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Add project root to path to import config
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from sqlalchemy import text
from config import PATHS, get_engine

def load_historical_exchange_rates(file_path=None):
    """
    Load historical master exchange rate file to database
    
    Clears existing exchange_rates table and loads all historical data
    """
    
    print("="*70)
    print("LOAD HISTORICAL EXCHANGE RATES (ONE-TIME)")
    print("="*70)
    
    # Use default path if not provided
    if file_path is None:
        file_path = PATHS['inputs'] / 'Master_Exchange_Rate.xlsx'
    else:
        file_path = Path(file_path)
    
    print(f"\nInput file: {file_path}")
    
    if not file_path.exists():
        raise FileNotFoundError(
            f"Master exchange rate file not found: {file_path}\n"
            f"Please place the Master_Exchange_Rate.xlsx file in inputs/ folder"
        )
    
    # Read master file
    print(f"\n📂 Reading master file...")
    df = pd.read_excel(file_path)
    
    print(f"   ✅ Loaded {len(df)} rows")
    print(f"   Columns: {df.columns.tolist()}")
    
    # Standardize column names
    column_mapping = {
        'Date': 'date',
        'USD': 'usd_unit',
        'Date (Mmm)': 'month_name',
        'Date (MMM)': 'month_name',
        'USD/LYD': 'official_rate',
        'USD/LYD + Gov Tax': 'official_rate_with_tax',
        'Parallel Market': 'parallel_market_rate',
        'Parallel Market USD/LYD': 'parallel_market_rate'
    }
    
    df = df.rename(columns=column_mapping)
    
    # Convert date to datetime
    df['date'] = pd.to_datetime(df['date'])
    
    # Select needed columns
    columns_needed = ['date', 'usd_unit', 'month_name', 'official_rate', 'official_rate_with_tax', 'parallel_market_rate']
    
    # Check which columns exist
    available_columns = [col for col in columns_needed if col in df.columns]
    df_load = df[available_columns].copy()
    
    # Add missing columns with None
    for col in columns_needed:
        if col not in df_load.columns:
            df_load[col] = None
    
    # Set default values for required columns
    if 'usd_unit' in df_load.columns and df_load['usd_unit'].isna().all():
        df_load['usd_unit'] = 1
    
    # Ensure month_name is filled
    if 'month_name' not in df_load.columns or df_load['month_name'].isna().any():
        df_load['month_name'] = df_load['date'].dt.strftime('%B')
    
    # Remove rows with no date
    df_load = df_load.dropna(subset=['date'])
    
    # Ensure columns are in the correct order for the database
    final_columns = ['date', 'usd_unit', 'month_name', 'official_rate', 'official_rate_with_tax', 'parallel_market_rate']
    df_load = df_load[final_columns]
    
    print(f"\n📊 Data to load:")
    print(f"   Total records: {len(df_load)}")
    print(f"   Date range: {df_load['date'].min()} to {df_load['date'].max()}")
    print(f"   Columns to insert: {df_load.columns.tolist()}")
    
    # Data quality check
    missing_official = df_load['official_rate'].isna().sum()
    missing_parallel = df_load['parallel_market_rate'].isna().sum()
    
    print(f"   Missing official rates: {missing_official}")
    print(f"   Missing parallel rates: {missing_parallel}")
    
    # Connect to database
    print(f"\n🔌 Connecting to database...")
    engine = get_engine()
    
    with engine.connect() as conn:
        # Check if table has data
        result = conn.execute(text("SELECT COUNT(*) FROM exchange_rates"))
        existing_count = result.scalar()
        
        if existing_count > 0:
            print(f"\n⚠️  WARNING: exchange_rates table already has {existing_count} records")
            response = input("   Do you want to DELETE all existing data and reload? (yes/no): ")
            
            if response.lower() != 'yes':
                print("\n❌ Load cancelled by user")
                return
            
            # Delete all existing data
            print(f"\n🗑️  Deleting {existing_count} existing records...")
            conn.execute(text("DELETE FROM exchange_rates"))
            conn.commit()
            print(f"   ✅ Cleared existing data")
        
        # Load data to database
        print(f"\n💾 Loading {len(df_load)} records to database...")
        df_load.to_sql('exchange_rates', engine, if_exists='append', index=False)
        conn.commit()
        
        # Verify
        result = conn.execute(text("SELECT COUNT(*) FROM exchange_rates"))
        final_count = result.scalar()
        
        print(f"\n✅ Load complete!")
        print(f"   Records in database: {final_count}")
        
        # Get date range from database
        result = conn.execute(text("SELECT MIN(date), MAX(date) FROM exchange_rates"))
        min_date, max_date = result.first()
        print(f"   Date range: {min_date} to {max_date}")
    
    print("\n" + "="*70)
    print("✅ HISTORICAL EXCHANGE RATES LOADED SUCCESSFULLY")
    print("="*70)
    print(f"\n📋 Summary:")
    print(f"   File: {file_path.name}")
    print(f"   Records loaded: {final_count}")
    print(f"   Date range: {min_date} to {max_date}")
    print(f"\n💡 For monthly updates, use: load_exchange_to_db.py")
    
    return final_count

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Load historical master exchange rate file to database (ONE-TIME)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Load from default location (inputs/Master_Exchange_Rate.xlsx)
  python scripts/04_Database_Loading/load_historical_exchange_rate.py
  
  # Load from custom location
  python scripts/04_Database_Loading/load_historical_exchange_rate.py --file path/to/file.xlsx

IMPORTANT:
  This script should only be run ONCE to load all historical data.
  It will DELETE all existing exchange rate data before loading.
  
  For monthly updates after initial load, use:
  python scripts/03_Database_Loading/load_exchange_to_db.py 2025 11
        """
    )
    
    parser.add_argument('--file', type=str, help='Path to Master_Exchange_Rate.xlsx file (optional)')
    
    args = parser.parse_args()
    
    try:
        count = load_historical_exchange_rates(args.file)
        print(f"\n✅ Successfully loaded {count} historical exchange rate records!")
        sys.exit(0)
            
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)