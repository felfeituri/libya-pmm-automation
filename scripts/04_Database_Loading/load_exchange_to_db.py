"""
Libya PMM - Load Monthly Exchange Rate to Database
Loads monthly exchange rate file from OneDrive to PostgreSQL database

This script loads ONE MONTH of exchange rate data.
For initial historical load, use load_historical_exchange_rate.py

Usage:
    python scripts/04_Database_Loading/load_exchange_to_db.py <year> <month>

Example:
    python scripts/04_Database_Loading/load_exchange_to_db.py 2025 11
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
from datetime import datetime
from sqlalchemy import text
from config import get_month_paths, get_engine

def load_monthly_exchange_rate(year, month):
    """
    Load exchange rate data for a specific month from OneDrive
    
    Reads monthly exchange rate file and loads to database
    """
    
    month_name = datetime(year, month, 1).strftime('%B')
    
    print("="*70)
    print(f"LOAD EXCHANGE RATE - {month_name} {year}")
    print("="*70)
    
    # Get paths
    paths = get_month_paths(year, month)
    exchange_file = paths['exchange_rate_monthly']
    collection_date = paths['date'].date()
    
    print(f"\nInput file: {exchange_file}")
    
    if not exchange_file.exists():
        raise FileNotFoundError(
            f"\n❌ Monthly exchange rate file not found: {exchange_file}\n"
            f"   Please run process_exchange_rate.py first and fill parallel market data"
        )
    
    # ========================================================================
    # STEP 1: Read Monthly Exchange Rate File
    # ========================================================================
    print(f"\n📂 Reading monthly file...")
    df = pd.read_excel(exchange_file)
    
    print(f"   ✅ Loaded {len(df)} rows")
    print(f"   Columns: {df.columns.tolist()}")
    
    # Validate required columns
    required_columns = ['Date', 'USD/LYD', 'USD/LYD + Gov Tax', 'Parallel Market USD/LYD']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")
    
    # Convert date to datetime
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Check data quality
    missing_official = df['USD/LYD'].isna().sum()
    missing_parallel = (df['Parallel Market USD/LYD'] == '').sum() + df['Parallel Market USD/LYD'].isna().sum()
    
    print(f"\n   Data Quality:")
    print(f"   - Date range: {df['Date'].min().date()} to {df['Date'].max().date()}")
    print(f"   - Missing official rates: {missing_official}")
    print(f"   - Missing parallel rates: {missing_parallel}")
    
    if missing_parallel > len(df) * 0.5:  # More than 50% missing
        print(f"\n   ⚠️  Warning: Many parallel market rates are missing!")
        print(f"   Make sure you filled the 'Parallel Market USD/LYD' column in Excel")
    
    # ========================================================================
    # STEP 2: Prepare for Database
    # ========================================================================
    print(f"\n🔄 Preparing data for database...")
    
    # Rename columns to match database schema
    df_db = pd.DataFrame({
        'date': df['Date'].dt.date,
        'usd_unit': 1,  # Always 1 for monthly files
        'month_name': df['Date'].dt.strftime('%B'),  # Month name
        'official_rate': df['USD/LYD'],
        'official_rate_with_tax': df['USD/LYD + Gov Tax'],
        'parallel_market_rate': df['Parallel Market USD/LYD']
    })
    
    # Convert empty strings to None for parallel rate
    df_db['parallel_market_rate'] = df_db['parallel_market_rate'].replace('', None)
    
    # Filter for only this month's data
    month_start = datetime(year, month, 1).date()
    if month == 12:
        month_end = datetime(year + 1, 1, 1).date()
    else:
        month_end = datetime(year, month + 1, 1).date()
    
    df_db = df_db[(df_db['date'] >= month_start) & (df_db['date'] < month_end)]
    
    print(f"   ✅ Prepared {len(df_db)} rows for {month_name} {year}")
    
    # ========================================================================
    # STEP 3: Load to Database
    # ========================================================================
    print(f"\n💾 Loading to database...")
    
    engine = get_engine()
    
    with engine.connect() as conn:
        # Check if this month already has data
        result = conn.execute(
            text("SELECT COUNT(*) FROM exchange_rates WHERE date >= :start AND date < :end"),
            {'start': month_start, 'end': month_end}
        )
        existing_count = result.scalar()
        
        if existing_count > 0:
            print(f"\n   ⚠️  This month already has {existing_count} records in database")
            response = input("   Delete existing data and reload? (yes/no): ")
            
            if response.lower() != 'yes':
                print("\n   ❌ Load cancelled by user")
                return 0
            
            # Delete existing data for this month
            print(f"\n   🗑️  Deleting {existing_count} existing records...")
            conn.execute(
                text("DELETE FROM exchange_rates WHERE date >= :start AND date < :end"),
                {'start': month_start, 'end': month_end}
            )
            conn.commit()
            print(f"   ✅ Cleared existing data")
        
        # Load new data
        print(f"\n   Loading {len(df_db)} records...")
        df_db.to_sql('exchange_rates', engine, if_exists='append', index=False)
        conn.commit()
        
        # Verify
        result = conn.execute(
            text("SELECT COUNT(*) FROM exchange_rates WHERE date >= :start AND date < :end"),
            {'start': month_start, 'end': month_end}
        )
        final_count = result.scalar()
        
        print(f"\n   ✅ Successfully loaded {final_count} records")
    
    # ========================================================================
    # Summary
    # ========================================================================
    print("\n" + "="*70)
    print("✅ EXCHANGE RATE LOADED SUCCESSFULLY")
    print("="*70)
    
    print(f"\n📊 Summary:")
    print(f"   Month: {month_name} {year}")
    print(f"   File: {exchange_file.name}")
    print(f"   Records loaded: {final_count}")
    print(f"   Date range: {df_db['date'].min()} to {df_db['date'].max()}")
    
    return final_count

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Load monthly exchange rate to database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Load November 2025 exchange rates
  python scripts/04_Database_Loading/load_exchange_to_db.py 2025 11
  
  # Load December 2025 exchange rates
  python scripts/04_Database_Loading/load_exchange_to_db.py 2025 12

Workflow:
  1. Create monthly file: python scripts/03_Data_Processing/process_exchange_rate.py 2025 11
  2. Fill parallel market column in Excel
  3. Load to database: python scripts/04_Database_Loading/load_exchange_to_db.py 2025 11

Prerequisites:
  - Monthly exchange rate file created (process_exchange_rate.py)
  - Parallel market column filled in Excel
  - File location: Monthly Reports/YYYY/MonthName/Exchange Rate/Exchange_Rate_MonthYY.xlsx

Note:
  For initial historical load, use: load_historical_exchange_rate.py
        """
    )
    
    parser.add_argument('year', type=int, help='Year (e.g., 2025)')
    parser.add_argument('month', type=int, help='Month (1-12)')
    
    args = parser.parse_args()
    
    # Validate month
    if not 1 <= args.month <= 12:
        print(f"❌ Error: Month must be between 1 and 12, got {args.month}")
        sys.exit(1)
    
    try:
        count = load_monthly_exchange_rate(args.year, args.month)
        print(f"\n✅ Successfully loaded {count} exchange rate records!")
        sys.exit(0)
            
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)