"""
Libya PMM - MEB Calculator
Calculates Minimum Expenditure Basket from raw PMM data
Generates Analysis Excel file

Usage:
    python scripts/03_Data_Processing/calculate_meb.py <year> <month>

Example:
    python scripts/03_Data_Processing/calculate_meb.py 2025 11
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
import numpy as np
from datetime import datetime
import warnings
from config import get_month_paths, ensure_month_directories

warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================

# Product configurations
MEB_WEIGHTS = {
    # Food items (18 total)
    'bread': 32, 'rice': 10.5, 'pasta': 9.5, 'couscous': 5.5,
    'beans': 15, 'chicken': 7.5, 'tuna': 20, 'eggs': 4,
    'milk': 8.5, 'tomatoes': 10, 'potatoes': 12, 'onions': 7,
    'peppers': 4.5, 'tomatop': 10, 'btea': 8, 'oil': 5,
    'sugar': 2, 'salt': 1,
    # Non-food items (6 total)
    'hwsoap': 9, 'toothpaste': 5, 'ldet': 1.3, 'dsoap': 1.3,
    'spads': 4, 'cookingfuel': 2,
}

PRODUCT_NAMES = {
    'bread': 'Bread (5pc)', 'rice': 'Rice (Kg)', 'pasta': 'Pasta (500g)',
    'couscous': 'Couscous (Kg)', 'beans': 'Beans (400g)', 'chicken': 'Chicken (Kg)',
    'tuna': 'Tuna (200g)', 'eggs': 'Eggs (30pc)', 'milk': 'Milk (L)',
    'tomatoes': 'Tomatoes (Kg)', 'potatoes': 'Potatoes (Kg)', 'onions': 'Onions (Kg)',
    'peppers': 'Pepper (Kg)', 'tomatop': 'Tomato Paste (400g)', 'btea': 'Black Tea (250g)',
    'oil': 'Oil (L)', 'sugar': 'Sugar (Kg)', 'salt': 'Salt (Kg)',
    'hwsoap': 'Handwash Soap (Pc)', 'toothpaste': 'Toothpaste (Pc)',
    'ldet': 'Laundry Detergent (L)', 'dsoap': 'Dishwashing Liquid (L)',
    'spads': 'Sanitary Pads (10Pc)', 'cookingfuel': 'Cooking Fuel (11Kg)',
}

PRICE_COLUMNS = {
    'bread': 'q_bread_price_per_5medium_pieces',
    'rice': 'q_rice_price_per_kilo',
    'pasta': 'q_pasta_price_per_500g',
    'couscous': 'q_couscous_price_per_kilo',
    'beans': 'q_beans_price_per_400g',
    'chicken': 'q_chicken_price_per_kilo',
    'tuna': 'q_tuna_price_per_200g',
    'eggs': 'q_eggs_price_per_30eggs',
    'milk': 'q_milk_price_per_liter',
    'tomatoes': 'q_tomatoes_price_per_kilo',
    'potatoes': 'q_potatoes_price_per_kilo',
    'onions': 'q_onions_price_per_kilo',
    'peppers': 'q_pepper_price_per_kilo',
    'tomatop': 'q_tomatop_price_per_400g',
    'btea': 'q_btea_price_per_250g',
    'oil': 'q_oil_price_per_liter',
    'sugar': 'q_sugar_price_per_kilo',
    'salt': 'q_salt_price_per_kilo',
    'hwsoap': 'q_hwsoap_price_per_piece',
    'toothpaste': 'q_toothpaste_price_per_tube',
    'ldet': 'q_ldet_price_per_litre',
    'dsoap': 'q_dsoap_price_per_liter',
    'spads': 'q_spads_price_per_10pads',
    'cookingfuel': 'q_fuel_public_price_per_11kg',
}

FOOD_ITEMS = ['bread', 'rice', 'pasta', 'couscous', 'beans', 'chicken', 'tuna', 'eggs',
              'milk', 'tomatoes', 'potatoes', 'onions', 'peppers', 'tomatop', 'btea',
              'oil', 'sugar', 'salt']

NFI_ITEMS = ['hwsoap', 'toothpaste', 'ldet', 'dsoap', 'spads', 'cookingfuel']

# Municipality name to ADM2 code mapping
MUNICIPALITY_CODE_MAPPING = {
    'AlBayda': 'LY0106',
    'Algatroun': 'LY0223',
    'AlJufra': 'LY0317',
    'AlKhums': 'LY0210',
    'AlKufra': 'LY0107',
    'Azzawya': 'LY0213',
    'Benghazi': 'LY0103',
    'Derna': 'LY0101',
    'Ejdabia': 'LY0105',
    'Ghat': 'LY0321',
    'Misrata': 'LY0214',
    'Murzuq': 'LY0322',
    'Nalut': 'LY0209',
    'Sebha': 'LY0319',
    'Sirt': 'LY0208',
    'Tobruk': 'LY0104',
    'Tripoli Center': 'LY0211',
    'Ubari': 'LY0320',
    'Wadi Alshati': 'LY0318',
    'Zliten': 'LY0216',
    'Zwara': 'LY0215',
    # Truncated names (for files with name length issues)
    'Wadi Al': 'LY0318',  # Wadi Alshati truncated
    'Algatro': 'LY0223',  # Algatroun truncated
    'Tripoli': 'LY0211',  # Tripoli Center truncated
    'Benghaz': 'LY0103',  # Benghazi truncated
}

# Region mapping
REGION_MAPPING = {
    'AlBayda': 'East', 'AlKufra': 'East', 'Benghazi': 'East', 'Derna': 'East',
    'Ejdabia': 'East', 'Tobruk': 'East', 'AlKhums': 'West', 'Azzawya': 'West',
    'Misrata': 'West', 'Nalut': 'West', 'Sirt': 'West', 'Tripoli Center': 'West',
    'Zliten': 'West', 'Zwara': 'West', 'Algatroun': 'South', 'AlJufra': 'South',
    'Ghat': 'South', 'Murzuq': 'South', 'Sebha': 'South', 'Ubari': 'South',
    'Wadi Alshati': 'South',
    # Truncated names (for files with issues)
    'Benghaz': 'East', 'Tripoli': 'West', 'Wadi Al': 'South', 'Algatro': 'South',
}

MUNICIPALITY_COL = 'S1_06'

# Reverse mapping: code to proper name
CODE_TO_NAME = {v: k for k, v in MUNICIPALITY_CODE_MAPPING.items() if k not in ['Benghaz', 'Tripoli', 'Wadi Al', 'Algatro']}

def normalize_municipality_name(name):
    """Convert truncated municipality names to proper full names"""
    name = str(name).strip()
    # If it's a truncated name, get the code and return the proper name
    if name in MUNICIPALITY_CODE_MAPPING:
        code = MUNICIPALITY_CODE_MAPPING[name]
        return CODE_TO_NAME.get(code, name)
    return name

# ============================================================================
# CORE FUNCTIONS
# ============================================================================

def load_and_process_data(file_path, municipality_col):
    """Load data and calculate average prices per municipality (excluding zeros)"""
    df = pd.read_excel(file_path)
    df[municipality_col] = df[municipality_col].str.strip()
    
    # Normalize truncated municipality names to proper full names
    df[municipality_col] = df[municipality_col].apply(normalize_municipality_name)
    
    # Convert price columns to numeric
    for product, price_col in PRICE_COLUMNS.items():
        if price_col in df.columns:
            df[price_col] = pd.to_numeric(df[price_col], errors='coerce')
    
    # Calculate average prices per municipality (excluding zeros)
    results = []
    for municipality in df[municipality_col].unique():
        muni_data = df[df[municipality_col] == municipality]
        row_dict = {municipality_col: municipality}
        
        for product, price_col in PRICE_COLUMNS.items():
            if price_col in df.columns:
                # Replace 0 with NaN before averaging
                prices = muni_data[price_col].replace(0, np.nan).dropna()
                row_dict[product] = prices.mean() if len(prices) > 0 else np.nan
            else:
                row_dict[product] = np.nan
        
        results.append(row_dict)
    
    return df, pd.DataFrame(results)

def calculate_meb_with_details(avg_prices_df, location_col):
    """Calculate MEB and return summary with price details"""
    meb_results = []
    price_details = []
    
    for _, row in avg_prices_df.iterrows():
        location = row[location_col]
        
        food_cost = sum(row[item] * MEB_WEIGHTS[item] 
                       for item in FOOD_ITEMS if pd.notna(row.get(item)))
        nfi_cost = sum(row[item] * MEB_WEIGHTS[item] 
                      for item in NFI_ITEMS if pd.notna(row.get(item)))
        
        meb_results.append({
            location_col: location,
            'FOOD MEB': food_cost,
            'NFI MEB': nfi_cost,
            'FULL MEB': food_cost + nfi_cost
        })
        
        # Store unweighted average prices for Commodities sheet
        price_row = {'Location': location, 'Type': 'Municipality' if location_col == MUNICIPALITY_COL else 'Region'}
        for product in PRICE_COLUMNS.keys():
            price_row[product] = row.get(product, np.nan)
        price_details.append(price_row)
    
    return pd.DataFrame(meb_results), pd.DataFrame(price_details)

def calculate_regional_averages(muni_avg_prices, municipality_col):
    """Calculate regional averages from municipality averages (excluding zeros)"""
    muni_with_region = muni_avg_prices.copy()
    muni_with_region['Region'] = muni_with_region[municipality_col].map(REGION_MAPPING)
    
    regional_avgs = []
    for region in ['East', 'West', 'South']:
        region_data = muni_with_region[muni_with_region['Region'] == region]
        row_dict = {'Region': region}
        
        for product in PRICE_COLUMNS.keys():
            prices = region_data[product].replace(0, np.nan).dropna()
            row_dict[product] = prices.mean() if len(prices) > 0 else np.nan
        
        regional_avgs.append(row_dict)
    
    return pd.DataFrame(regional_avgs)

def calculate_national_average(muni_avg_prices):
    """Calculate national average from municipality averages (excluding zeros)"""
    row_dict = {'Level': 'National'}
    
    for product in PRICE_COLUMNS.keys():
        prices = muni_avg_prices[product].replace(0, np.nan).dropna()
        row_dict[product] = prices.mean() if len(prices) > 0 else np.nan
    
    return pd.DataFrame([row_dict])

def generate_excel_report(muni_df, region_df, national_df, all_commodities_df, hierarchy_df, output_file):
    """Generate Excel report with Master sheet and regional breakdown sheets"""
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Sheet 1: Commodities (unweighted average prices)
        all_commodities_df.to_excel(writer, sheet_name='Commodities', index=False)
        
        # Sheet 2: Master (renamed from Hierarchy)
        # This contains: municipalities → Grand Total → regions
        hierarchy_df.to_excel(writer, sheet_name='Master', index=False)
        
        # Sheet 3-5: Regional breakdowns (East, West, South)
        # Each sheet contains only municipalities from that region
        # Region column is first, then Municipality
        
        # Prepare municipality data with Region column
        muni_output = muni_df[[MUNICIPALITY_COL, 'Region', 'FOOD MEB', 'NFI MEB', 'FULL MEB']].copy()
        muni_output.columns = ['Municipality', 'Region', 'Food MEB', 'NFI MEB', 'Full MEB']
        
        # East sheet - only East municipalities (Region first, then Municipality)
        east_df = muni_output[muni_output['Region'] == 'East'].copy()
        east_df = east_df[['Region', 'Municipality', 'Food MEB', 'NFI MEB', 'Full MEB']]  # Region first
        east_df.to_excel(writer, sheet_name='East', index=False)
        
        # West sheet - only West municipalities (Region first, then Municipality)
        west_df = muni_output[muni_output['Region'] == 'West'].copy()
        west_df = west_df[['Region', 'Municipality', 'Food MEB', 'NFI MEB', 'Full MEB']]  # Region first
        west_df.to_excel(writer, sheet_name='West', index=False)
        
        # South sheet - only South municipalities (Region first, then Municipality)
        south_df = muni_output[muni_output['Region'] == 'South'].copy()
        south_df = south_df[['Region', 'Municipality', 'Food MEB', 'NFI MEB', 'Full MEB']]  # Region first
        south_df.to_excel(writer, sheet_name='South', index=False)

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def calculate_meb_for_month(year, month):
    """
    Calculate MEB for a specific month
    
    Args:
        year: int (e.g., 2025)
        month: int (1-12)
    
    Returns:
        tuple: (muni_df, region_df, national_df, output_file)
    """
    # Get paths from config
    paths = ensure_month_directories(year, month)
    
    input_file = paths['raw_data']
    output_file = paths['analysis_file']
    
    print(f"\n{'='*70}")
    print(f"CALCULATING MEB - {paths['month_name']} {year}")
    print(f"{'='*70}")
    
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    # Step 1: Load and calculate municipality averages
    print(f"\n1. Loading data from: {input_file.name}")
    raw_df, muni_avg_prices = load_and_process_data(input_file, MUNICIPALITY_COL)
    print(f"   ✓ Loaded {len(raw_df)} records from {len(muni_avg_prices)} municipalities")
    
    # Step 2: Calculate municipality MEB
    print(f"\n2. Calculating municipality MEB...")
    muni_df, muni_prices = calculate_meb_with_details(muni_avg_prices, MUNICIPALITY_COL)
    muni_df['Region'] = muni_df[MUNICIPALITY_COL].map(REGION_MAPPING)
    print(f"   ✓ Processed {len(muni_df)} municipalities")
    
    # Step 3: Calculate regional MEB
    print(f"\n3. Calculating regional MEB...")
    region_avg_prices = calculate_regional_averages(muni_avg_prices, MUNICIPALITY_COL)
    region_df, region_prices = calculate_meb_with_details(region_avg_prices, 'Region')
    print(f"   ✓ Processed {len(region_df)} regions")
    
    # Step 4: Calculate national MEB
    print(f"\n4. Calculating national MEB...")
    national_avg_prices = calculate_national_average(muni_avg_prices)
    national_df, national_prices = calculate_meb_with_details(national_avg_prices, 'Level')
    print(f"   ✓ Calculated national average")
    
    # Step 5: Create Commodities sheet
    print(f"\n5. Creating commodity breakdown...")
    all_commodities = national_prices.to_dict('records') + region_prices.to_dict('records')
    commodity_rows = []
    for row in all_commodities:
        location = row['Location']
        for product in PRICE_COLUMNS.keys():
            if pd.notna(row.get(product)):
                # Determine type (Food or Non-Food)
                product_type = 'Food' if product in FOOD_ITEMS else 'Non-Food'
                commodity_rows.append({
                    'Region': location,
                    'Type': product_type,
                    'Item': PRODUCT_NAMES[product],
                    'Average Price': round(row[product], 2)
                })
    all_commodities_df = pd.DataFrame(commodity_rows)
    
    # Step 6: Create Hierarchy sheet
    print(f"\n6. Creating hierarchy...")
    municipality_order = [
        'AlBayda', 'Algatroun', 'AlJufra', 'AlKhums', 'AlKufra', 'Azzawya',
        'Benghazi', 'Derna', 'Ejdabia', 'Ghat', 'Misrata', 'Murzuq', 'Nalut',
        'Sebha', 'Sirt', 'Tobruk', 'Tripoli Center', 'Ubari', 'Wadi Alshati',
        'Zliten', 'Zwara'
    ]
    
    hierarchy_rows = []
    for muni_name in municipality_order:
        muni_row = muni_df[muni_df[MUNICIPALITY_COL] == muni_name]
        if not muni_row.empty:
            row = muni_row.iloc[0]
            hierarchy_rows.append({
                'Location': muni_name,
                'Food MEB': round(row['FOOD MEB'], 2),
                'NFI MEB': round(row['NFI MEB'], 2),
                'Full MEB': round(row['FULL MEB'], 2)
            })
    
    # Grand Total
    hierarchy_rows.append({
        'Location': 'Grand Total',
        'Food MEB': round(national_df['FOOD MEB'].values[0], 2),
        'NFI MEB': round(national_df['NFI MEB'].values[0], 2),
        'Full MEB': round(national_df['FULL MEB'].values[0], 2)
    })
    
    # Regions
    for region_name in ['East', 'West', 'South']:
        region_row = region_df[region_df['Region'] == region_name]
        if not region_row.empty:
            row = region_row.iloc[0]
            hierarchy_rows.append({
                'Location': region_name,
                'Food MEB': round(row['FOOD MEB'], 2),
                'NFI MEB': round(row['NFI MEB'], 2),
                'Full MEB': round(row['FULL MEB'], 2)
            })
    
    hierarchy = pd.DataFrame(hierarchy_rows)
    
    # Step 7: Generate report
    print(f"\n7. Generating Excel report...")
    generate_excel_report(muni_df, region_df, national_df, all_commodities_df, hierarchy, output_file)
    print(f"   ✓ Saved: {output_file.name}")
    print(f"   Location: {paths['analysis']}")
    
    # Summary
    print(f"\n{'='*70}")
    print(f"SUMMARY - {paths['month_name']} {year}")
    print(f"{'='*70}")
    print(f"\nNational MEB:")
    print(f"  Food MEB:  {national_df['FOOD MEB'].values[0]:>10.2f} LYD")
    print(f"  NFI MEB:   {national_df['NFI MEB'].values[0]:>10.2f} LYD")
    print(f"  Full MEB:  {national_df['FULL MEB'].values[0]:>10.2f} LYD")
    print(f"\n{'='*70}")
    
    return muni_df, region_df, national_df, output_file

# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Calculate MEB for a specific month",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Calculate MEB for November 2025
  python scripts/03_Data_Processing/calculate_meb.py 2025 11
  
  # Calculate MEB for October 2025
  python scripts/03_Data_Processing/calculate_meb.py 2025 10
        """
    )
    
    parser.add_argument('year', type=int, help='Year (e.g., 2025)')
    parser.add_argument('month', type=int, help='Month (1-12)')
    
    args = parser.parse_args()
    
    # Validate month
    if not 1 <= args.month <= 12:
        print(f"Error: Month must be between 1 and 12, got {args.month}")
        sys.exit(1)
    
    try:
        muni_df, region_df, national_df, output_file = calculate_meb_for_month(args.year, args.month)
        print("\n✅ MEB calculation completed successfully!")
        print(f"\n📝 Next step: Export DataBridges file")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)