"""
Libya PMM - Exchange Rate Processing
Creates monthly exchange rate file with official rates and empty parallel market column

Steps:
1. Clean official CBL rates from inputs
2. Create combined file with official + empty parallel column
3. Save to OneDrive Monthly Reports folder
4. User manually fills parallel market column with Facebook data
5. Load to database after manual entry

Usage:
    python scripts/03_Data_Processing/process_exchange_rate.py <year> <month>

Example:
    python scripts/03_Data_Processing/process_exchange_rate.py 2025 11
"""

import sys
from pathlib import Path
import os

# Auto-detect environment and set project root
if os.path.exists('/app'):  # Running in Docker
    PROJECT_ROOT = Path('/app')
else:  # Running locally
    # Script is in scripts/03_Data_Processing/
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Add project root to path to import config
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from datetime import datetime
from config import PATHS, get_month_paths, ensure_month_directories

def process_exchange_rate(year, month):
    """
    Create monthly exchange rate file with official rates and empty parallel column
    
    Returns path to monthly exchange rate file (ready for manual parallel market entry)
    """
    
    month_name = datetime(year, month, 1).strftime('%B')
    
    print("="*70)
    print(f"EXCHANGE RATE PROCESSING - {month_name} {year}")
    print("="*70)
    
    # Get paths
    paths = ensure_month_directories(year, month)
    
    # ========================================================================
    # STEP 1: Clean Official Rates
    # ========================================================================
    print("\n" + "-"*70)
    print("STEP 1: CLEAN OFFICIAL EXCHANGE RATES")
    print("-"*70)
    
    input_file = PATHS['inputs'] / 'Currency Exchange Rates - The Central Bank of Libya.xlsx'
    
    print(f"\nInput file: {input_file.name}")
    
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    # Read the Excel file (skip first row which is title)
    df = pd.read_excel(input_file, header=None, skiprows=1)
    
    # Set column names
    df.columns = ['Date', 'Currency', 'Unit', 'Average', 'Sell', 'Buy']
    
    # Filter for American Dollar only
    df_usd = df[df['Currency'].str.contains('American Dollar', na=False)].copy()
    
    print(f"✅ Loaded {len(df_usd)} USD records")
    
    # Clean Date column
    df_usd['Date_Clean'] = df_usd['Date'].str.replace('Date: ', '', regex=False)
    df_usd['Date_dt'] = pd.to_datetime(df_usd['Date_Clean'])
    
    # Clean Average column
    df_usd['Average_Clean'] = df_usd['Average'].str.replace('Average: ', '', regex=False)
    df_usd['Average_Clean'] = df_usd['Average_Clean'].str.replace('\xa0LYD', '', regex=False)
    df_usd['Average_Clean'] = df_usd['Average_Clean'].str.replace(' LYD', '', regex=False)
    df_usd['USD_LYD'] = pd.to_numeric(df_usd['Average_Clean'], errors='coerce')
    
    print(f"✅ Date range: {df_usd['Date_dt'].min().date()} to {df_usd['Date_dt'].max().date()}")
    
    # ========================================================================
    # STEP 2: Create Combined File (Official + Empty Parallel)
    # ========================================================================
    print("\n" + "-"*70)
    print("STEP 2: CREATE COMBINED FILE")
    print("-"*70)
    
    # Create output dataframe with all columns
    output_df = pd.DataFrame({
        'Date': df_usd['Date_dt'].dt.strftime('%Y-%m-%d'),
        'USD': 1,
        'Date (MMM)': df_usd['Date_dt'].dt.strftime('%B'),
        'USD/LYD': df_usd['USD_LYD'],
        'USD/LYD + Gov Tax': (df_usd['USD_LYD'] * 1.2).round(2),
        'Parallel Market USD/LYD': ''  # Empty column for manual entry
    })
    
    # Sort by date
    output_df = output_df.sort_values('Date', ascending=True).reset_index(drop=True)
    
    print(f"✅ Created combined file with {len(output_df)} records")
    print(f"   Columns: {', '.join(output_df.columns)}")
    
    # ========================================================================
    # STEP 3: Save to OneDrive Monthly Reports
    # ========================================================================
    print("\n" + "-"*70)
    print("STEP 3: SAVE TO ONEDRIVE")
    print("-"*70)
    
    # Save to monthly folder in OneDrive
    output_file = paths['exchange_rate_monthly']
    output_df.to_excel(output_file, index=False, engine='openpyxl')
    
    print(f"\n✅ Saved monthly exchange rate file:")
    print(f"   {output_file}")
    print(f"   File size: {output_file.stat().st_size / 1024:.1f} KB")
    
    # Print statistics
    print(f"\n📊 File Statistics:")
    print(f"   Total records: {len(output_df)}")
    print(f"   Date range: {output_df['Date'].min()} to {output_df['Date'].max()}")
    print(f"   Official rate range: {output_df['USD/LYD'].min():.4f} - {output_df['USD/LYD'].max():.4f}")
    
    # ========================================================================
    # Manual Step Instructions
    # ========================================================================
    print("\n" + "="*70)
    print("⚠️  MANUAL STEP REQUIRED")
    print("="*70)
    print(f"\n📝 Please fill in parallel market rates from Facebook:")
    print(f"\n   File location:")
    print(f"   {output_file}")
    print(f"\n   What to do:")
    print(f"   1. Open the Excel file")
    print(f"   2. Fill in 'Parallel Market USD/LYD' column with Facebook data")
    print(f"   3. Save the file")
    print(f"\n   After filling parallel market data:")
    print(f"   python scripts/03_Database_Loading/load_exchange_to_db.py {year} {month}")
    
    print("\n" + "="*70)
    print("✅ EXCHANGE RATE FILE CREATED")
    print("="*70)
    print(f"\n📄 File ready for manual entry:")
    print(f"   {paths['month_name']} {year}")
    print(f"   {output_file.name}")
    
    return output_file

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Create monthly exchange rate file with official rates + empty parallel column",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create exchange rate file for November 2025
  python scripts/03_Data_Processing/process_exchange_rate.py 2025 11

Workflow:
  1. Run this script → Creates file with official rates + empty parallel column
  2. Open file in Excel → Fill 'Parallel Market USD/LYD' column with Facebook data
  3. Save file
  4. Load to database → python scripts/04_Database_Loading/load_exchange_to_db.py 2025 11

Output Location:
  Monthly Reports/YYYY/MonthName/Exchange Rate/Exchange_Rate_MonthYY.xlsx

Prerequisites:
  - Official CBL rates file in inputs/ folder
  - Facebook data for parallel market rates (you enter manually in Excel)
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
        output_file = process_exchange_rate(args.year, args.month)
        print(f"\n✅ Exchange rate file created successfully!")
        print(f"\n💡 Next: Fill parallel market column in Excel, then load to database")
        sys.exit(0)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)