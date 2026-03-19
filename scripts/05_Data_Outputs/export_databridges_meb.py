"""
Libya PMM - Export DataBridges File
Creates DataBridges format export for WFP global system

This script:
1. Reads raw PMM data from monthly folder
2. Calculates average prices per municipality (excluding zeros)
3. Creates wide-format table matching DataBridges schema exactly
4. Saves to DataBridges folder in OneDrive

Usage:
    python scripts/05_Data_Outputs/export_databridges_meb.py <year> <month>

Examples:
    python scripts/05_Data_Outputs/export_databridges_meb.py 2025 11
"""

import sys
from pathlib import Path
import os

# Auto-detect environment and set project root
if os.path.exists('/app'):  # Running in Docker
    PROJECT_ROOT = Path('/app')
else:  # Running locally
    # Script is in scripts/05_Data_Outputs/
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Add project root to path to import config
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import numpy as np
from datetime import datetime
from config import get_month_paths, DATABRIDGES_BASE

# ============================================================================
# CONFIGURATION
# ============================================================================

# Product mapping: (DataBridges column name, Raw data column name)
# IMPORTANT: Column names must match EXACTLY what's in the schema
PRODUCT_COLUMNS = [
    ('Salt Price Per Kilo', 'q_salt_price_per_kilo'),                           # Column B
    ('Sugar price_per_kilo', 'q_sugar_price_per_kilo'),                         # Column C
    ('Flour Price Per Kilo', 'q_flour_price_per_kilo'),                         # Column D
    ('Rice Price Per Kilo', 'q_rice_price_per_kilo'),                           # Column E
    ('Pasta price_per_500g', 'q_pasta_price_per_500g'),                         # Column F
    ('Couscous price_per_kilo18', 'q_couscous_price_per_kilo'),                 # Column G
    ('Tomato Paste_per_400g', 'q_tomatop_price_per_400g'),                      # Column H
    ('cannded chickpeas price_per_400g23', 'q_chickpeas_price_per_400g'),       # Column I
    ('canne beans price_per_400g27', 'q_beans_price_per_400g'),                 # Column J
    ('condesned milk price_per_200ml', 'q_cmilk_price_per_200ml'),              # Column K
    ('milk price_per_liter', 'q_milk_price_per_liter'),                         # Column L
    ('Green tea price_per_250g', 'q_gtea_price_per_250g'),                      # Column M
    ('black tea price_per_250g38', 'q_btea_price_per_250g'),                    # Column N
    ('veg oil price_per_liter41', 'q_oil_price_per_liter'),                     # Column O
    ('canned tuna price_per_200g', 'q_tuna_price_per_200g'),                    # Column P
    ('price_per_30eggs', 'q_eggs_price_per_30eggs'),                            # Column Q
    ('chicken meat price_per_kilo49', 'q_chicken_price_per_kilo'),              # Column R
    ('lamb meat price_per_kilo54', 'q_lamb_price_per_kilo'),                    # Column S
    ('wheat bread price_per_5medium_pieces', 'q_bread_price_per_5medium_pieces'), # Column T
    ('Tomatoes price_per_kilo58', 'q_tomatoes_price_per_kilo'),                 # Column U
    ('onions price_per_kilo62', 'q_onions_price_per_kilo'),                     # Column V
    ('Peppers price_per_kilo66', 'q_pepper_price_per_kilo'),                    # Column W
    ('Potatoes price_per_kilo69', 'q_potatoes_price_per_kilo'),                 # Column X
]

# Municipality order (alphabetical with specific ordering)
MUNICIPALITY_ORDER = [
    'AlBayda', 'Algatroun', 'AlJufra', 'AlKhums', 'AlKufra', 'Azzawya',
    'Benghazi', 'Derna', 'Ejdabia', 'Ghat', 'Misrata', 'Murzuq',
    'Nalut', 'Sebha', 'Sirt', 'Tobruk', 'Tripoli Center', 'Ubari',
    'Wadi Alshati', 'Zliten', 'Zwara'
]

MUNICIPALITY_COL = 'S1_06'

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def create_databridges(raw_df, target_date):
    """
    Create DataBridges format export
    
    Format (MUST match schema exactly):
    - Column A: Municipality (market)
    - Columns B-X: Products (23 products in specific order)
    - Column Y: Empty column (Unnamed: 24)
    - Column Z: date (as datetime object)
    """
    
    print("\n📊 Calculating average prices per municipality...")
    
    # Get municipalities that exist in data
    municipalities_in_data = set(raw_df[MUNICIPALITY_COL].unique())
    municipalities = [m for m in MUNICIPALITY_ORDER if m in municipalities_in_data]
    
    print(f"   Found {len(municipalities)} municipalities")
    
    # Initialize data structure with exact column names
    databridges_data = {'Municipality ': []}  # Note: Space after Municipality to match schema
    
    # Add product columns (B through X)
    for display_name, _ in PRODUCT_COLUMNS:
        databridges_data[display_name] = []
    
    # Add empty column Y (NO header name - completely empty)
    databridges_data[''] = []
    
    # Add date column Z
    databridges_data['date'] = []
    
    # Calculate averages for each municipality
    for muni in municipalities:
        muni_data = raw_df[raw_df[MUNICIPALITY_COL] == muni]
        databridges_data['Municipality '].append(muni)
        
        # Calculate average for each product
        for display_name, raw_col in PRODUCT_COLUMNS:
            if raw_col in muni_data.columns:
                # Get prices, excluding zeros and NaN
                prices = muni_data[raw_col].replace(0, np.nan).dropna()
                if len(prices) > 0:
                    avg_price = round(prices.mean(), 2)
                else:
                    avg_price = np.nan
            else:
                avg_price = np.nan
            
            databridges_data[display_name].append(avg_price)
        
        # Add empty column (Y) and date (Z)
        databridges_data[''].append(np.nan)
        databridges_data['date'].append(target_date)
    
    print(f"   Calculated averages for {len(PRODUCT_COLUMNS)} products")
    
    return pd.DataFrame(databridges_data)

def export_databridges(year: int, month: int):
    """
    Export DataBridges file for a specific month
    
    Args:
        year: Year (e.g., 2025)
        month: Month number (1-12)
    """
    
    print("="*70)
    print("LIBYA PMM - DATABRIDGES EXPORT")
    print("="*70)
    
    # Get paths from config
    paths = get_month_paths(year, month)
    month_name = paths['month_name']
    month_tag = paths['month_tag']
    
    # DataBridges uses LAST day of month (not first)
    # Calculate last day of the month
    from calendar import monthrange
    last_day = monthrange(year, month)[1]
    target_date = datetime(year, month, last_day)
    
    print(f"\n📅 Exporting DataBridges for: {month_name} {year}")
    print(f"   Month tag: {month_tag}")
    print(f"   Date: {target_date.strftime('%Y-%m-%d')}")
    
    # Input file (raw PMM data)
    input_file = paths['raw_data']
    
    print(f"\n📂 Reading raw data from:")
    print(f"   {input_file}")
    
    # Check if file exists
    if not input_file.exists():
        print(f"\n❌ Error: Raw data file not found!")
        print(f"   Expected location: {input_file}")
        print(f"\n   Make sure you have:")
        print(f"   1. Exported data from MoDa")
        print(f"   2. File is in the correct location")
        return False
    
    # Read raw data
    raw_df = pd.read_excel(input_file)
    print(f"   ✅ Loaded {len(raw_df)} records")
    
    # Create DataBridges export
    databridges_df = create_databridges(raw_df, target_date)
    
    # Create output directory with year folder
    output_dir = DATABRIDGES_BASE / "Prices" / "New (Mean)" / str(year)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save file with correct naming convention
    output_file = output_dir / f"{month_name} {year}.xlsx"
    
    print(f"\n💾 Saving DataBridges file...")
    
    # Write to Excel with proper date formatting (M/DD/YY format)
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        databridges_df.to_excel(writer, index=False, sheet_name='Means')
        
        # Get the worksheet
        worksheet = writer.sheets['Means']
        
        # Format all price columns (B through X = columns 2-24) to show 2 decimal places
        for row in range(2, len(databridges_df) + 2):  # Skip header row
            for col in range(2, 25):  # Columns B through X (price columns)
                price_cell = worksheet.cell(row=row, column=col)
                # Set number format to always show 2 decimal places
                price_cell.number_format = '0.00'
        
        # Format date column (Column Z = 26) to match source: M/DD/YY (e.g., 5/30/25)
        for row in range(2, len(databridges_df) + 2):  # Skip header row
            date_cell = worksheet.cell(row=row, column=26)  # Column Z
            # Set Excel date format to M/DD/YY (shows as "Date" type in Excel)
            date_cell.number_format = 'M/DD/YY'
    
    print(f"   ✅ Saved: {output_file}")
    print(f"   Size: {output_file.stat().st_size / 1024:.1f} KB")
    
    # Verify the file
    print(f"\n🔍 Verifying export...")
    verify_df = pd.read_excel(output_file, nrows=3)
    print(f"   Columns: {len(verify_df.columns)}")
    print(f"   First column: '{verify_df.columns[0]}'")
    print(f"   Last column: '{verify_df.columns[-1]}'")
    print(f"   Date format: {verify_df['date'].dtype}")
    print(f"   Sample date: {verify_df['date'].iloc[0]}")
    
    print("\n" + "="*70)
    print("✅ EXPORT COMPLETE")
    print("="*70)
    print(f"\n📤 DataBridges export ready for upload to global system")
    print(f"\nFile structure:")
    print(f"  - Column A: Municipality (market)")
    print(f"  - Columns B-X: 23 product prices")
    print(f"  - Column Y: Empty (Unnamed: 24)")
    print(f"  - Column Z: date (datetime format)")
    
    return True

# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Export DataBridges file for WFP global system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export November 2025 DataBridges
  python scripts/05_Data_Outputs/export_databridges_meb.py 2025 11
  
  # Export October 2025 DataBridges
  python scripts/05_Data_Outputs/export_databridges_meb.py 2025 10

Note:
  The output file will match the DataBridges schema exactly:
  - Column A: Municipality
  - Columns B-X: Products (23 columns)
  - Column Y: Empty column
  - Column Z: date (datetime format)
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
        success = export_databridges(args.year, args.month)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)