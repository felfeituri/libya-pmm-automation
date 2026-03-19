"""
Libya PMM - Load PMM Data to Database
Loads MEB and commodity data from Analysis Excel files to PostgreSQL
Checks for existing data and only loads new months (no duplicates)

Usage:
    python scripts/04_Database_Loading/load_meb_to_db.py <year> <month>      # load specific month to the database
    python scripts/04_Database_Loading/load_meb_to_db.py --all                # Load all available months (skip existing)
    python scripts/04_Database_Loading/load_meb_to_db.py --all --force       # Force reload all months (overwrite existing)

Examples:
    python scripts/04_Database_Loading/load_meb_to_db.py 2025 11
    python scripts/04_Database_Loading/load_meb_to_db.py --all
    python scripts/04_Database_Loading/load_meb_to_db.py --all --force
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
from config import MONTHLY_REPORTS_ROOT, get_engine, get_month_paths

# ============================================================================
# CONFIGURATION
# ============================================================================

# Municipality name to ADM2 code
MUNICIPALITY_CODE_MAPPING = {
    'AlBayda': 'LY0106', 'Algatroun': 'LY0223', 'AlJufra': 'LY0317',
    'AlKhums': 'LY0210', 'AlKufra': 'LY0107', 'Azzawya': 'LY0213',
    'Benghazi': 'LY0103', 'Derna': 'LY0101', 'Ejdabia': 'LY0105',
    'Ghat': 'LY0321', 'Misrata': 'LY0214', 'Murzuq': 'LY0322',
    'Nalut': 'LY0209', 'Sebha': 'LY0319', 'Sirt': 'LY0208',
    'Tobruk': 'LY0104', 'Tripoli Center': 'LY0211', 'Ubari': 'LY0320',
    'Wadi Alshati': 'LY0318', 'Zliten': 'LY0216', 'Zwara': 'LY0215',
    # Truncated names
    'Wadi Al': 'LY0318', 'Algatro': 'LY0223', 'Tripoli': 'LY0211', 'Benghaz': 'LY0103',
}

REGION_CODE_MAPPING = {'East': 'LY01', 'West': 'LY02', 'South': 'LY03'}
NATIONAL_CODE, NATIONAL_NAME = 'LY', 'Libya'

# Product details
PRODUCT_DETAILS = {
    'bread': {'name': 'Bread (5pc)', 'weight': 32, 'unit': '5pc'},
    'rice': {'name': 'Rice (Kg)', 'weight': 10.5, 'unit': 'Kg'},
    'pasta': {'name': 'Pasta (500g)', 'weight': 9.5, 'unit': '500g'},
    'couscous': {'name': 'Couscous (Kg)', 'weight': 5.5, 'unit': 'Kg'},
    'beans': {'name': 'Beans (400g)', 'weight': 15, 'unit': '400g'},
    'chicken': {'name': 'Chicken (Kg)', 'weight': 7.5, 'unit': 'Kg'},
    'tuna': {'name': 'Tuna (200g)', 'weight': 20, 'unit': '200g'},
    'eggs': {'name': 'Eggs (30pc)', 'weight': 4, 'unit': '30pc'},
    'milk': {'name': 'Milk (L)', 'weight': 8.5, 'unit': 'L'},
    'tomatoes': {'name': 'Tomatoes (Kg)', 'weight': 10, 'unit': 'Kg'},
    'potatoes': {'name': 'Potatoes (Kg)', 'weight': 12, 'unit': 'Kg'},
    'onions': {'name': 'Onions (Kg)', 'weight': 7, 'unit': 'Kg'},
    'peppers': {'name': 'Pepper (Kg)', 'weight': 4.5, 'unit': 'Kg'},
    'tomatop': {'name': 'Tomato Paste (400g)', 'weight': 10, 'unit': '400g'},
    'btea': {'name': 'Black Tea (250g)', 'weight': 8, 'unit': '250g'},
    'oil': {'name': 'Oil (L)', 'weight': 5, 'unit': 'L'},
    'sugar': {'name': 'Sugar (Kg)', 'weight': 2, 'unit': 'Kg'},
    'salt': {'name': 'Salt (Kg)', 'weight': 1, 'unit': 'Kg'},
    'hwsoap': {'name': 'Handwash Soap (Pc)', 'weight': 9, 'unit': 'Pc'},
    'toothpaste': {'name': 'Toothpaste (Pc)', 'weight': 5, 'unit': 'Pc'},
    'ldet': {'name': 'Laundry Detergent (L)', 'weight': 1.3, 'unit': 'L'},
    'dsoap': {'name': 'Dishwashing Liquid (L)', 'weight': 1.3, 'unit': 'L'},
    'spads': {'name': 'Sanitary Pads (10Pc)', 'weight': 4, 'unit': '10Pc'},
    'cookingfuel': {'name': 'Cooking Fuel (11Kg)', 'weight': 2, 'unit': '11Kg'},
}

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def check_month_exists(engine, date):
    """Check if data for this month already exists in database"""
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT COUNT(*) FROM national_meb WHERE date = :date AND adm0_pcode = 'LY'"), 
            {'date': date}
        )
        return result.fetchone()[0] > 0

def delete_month_data(engine, date):
    """Delete all data for a specific month"""
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM products WHERE date = :date"), {'date': date})
        conn.execute(text("DELETE FROM municipality_meb WHERE date = :date"), {'date': date})
        conn.execute(text("DELETE FROM regional_meb WHERE date = :date"), {'date': date})
        conn.execute(text("DELETE FROM national_meb WHERE date = :date AND adm0_pcode = 'LY'"), {'date': date})
        conn.commit()

# ============================================================================
# LOADING FUNCTIONS
# ============================================================================

def load_municipality_meb(engine, master_df, date):
    """Load municipality-level MEB data"""
    records = []
    for _, row in master_df.iterrows():
        location = str(row['Location']).strip()
        if location in ['Grand Total', 'East', 'West', 'South']:
            continue
        
        adm2_code = MUNICIPALITY_CODE_MAPPING.get(location)
        if not adm2_code:
            print(f"    ⚠️  Unknown municipality: {location}")
            continue
        
        records.append({
            'adm2_pcode': adm2_code,
            'municipality': location,
            'date': date,
            'food_meb': float(row['Food MEB']) if pd.notna(row['Food MEB']) else None,
            'nfi_meb': float(row['NFI MEB']) if pd.notna(row['NFI MEB']) else None,
            'full_meb': float(row['Full MEB']) if pd.notna(row['Full MEB']) else None,
        })
    
    if records:
        pd.DataFrame(records).to_sql('municipality_meb', engine, if_exists='append', index=False)
    return len(records)

def load_regional_meb(engine, master_df, date):
    """Load regional-level MEB data"""
    records = []
    for _, row in master_df.iterrows():
        location = str(row['Location']).strip()
        if location not in ['East', 'West', 'South']:
            continue
        
        records.append({
            'adm1_pcode': REGION_CODE_MAPPING[location],
            'region': location,
            'date': date,
            'food_meb': float(row['Food MEB']) if pd.notna(row['Food MEB']) else None,
            'nfi_meb': float(row['NFI MEB']) if pd.notna(row['NFI MEB']) else None,
            'full_meb': float(row['Full MEB']) if pd.notna(row['Full MEB']) else None,
        })
    
    if records:
        pd.DataFrame(records).to_sql('regional_meb', engine, if_exists='append', index=False)
    return len(records)

def load_national_meb(engine, master_df, date):
    """Load national-level MEB data"""
    grand_total = master_df[master_df['Location'] == 'Grand Total']
    if grand_total.empty:
        return 0
    
    row = grand_total.iloc[0]
    records = [{
        'adm0_pcode': NATIONAL_CODE,
        'date': date,
        'food_meb': float(row['Food MEB']) if pd.notna(row['Food MEB']) else None,
        'nfi_meb': float(row['NFI MEB']) if pd.notna(row['NFI MEB']) else None,
        'full_meb': float(row['Full MEB']) if pd.notna(row['Full MEB']) else None,
    }]
    
    pd.DataFrame(records).to_sql('national_meb', engine, if_exists='append', index=False)
    return 1

def load_commodities(engine, commodities_df, date):
    """Load commodity price data"""
    records = []
    for _, row in commodities_df.iterrows():
        region_name = str(row['Region']).strip()
        item_name = str(row['Item']).strip()
        category = str(row['Type']).strip()
        avg_price = row['Average Price']
        
        if pd.isna(avg_price):
            continue
        
        # Map region to admin code
        if region_name in ['Libya', 'National']:
            admin_code, admin_name = NATIONAL_CODE, NATIONAL_NAME
        else:
            admin_code = REGION_CODE_MAPPING.get(region_name)
            if not admin_code:
                continue
            admin_name = region_name
        
        # Find product code
        product_code = None
        for code, details in PRODUCT_DETAILS.items():
            if details['name'] == item_name:
                product_code = code
                break
        
        if not product_code:
            continue
        
        # Remap cookingfuel to Fuel category
        if product_code == 'cookingfuel':
            category = 'Fuel'
        
        records.append({
            'product_code': product_code,
            'product_name': PRODUCT_DETAILS[product_code]['name'],
            'category': category,
            'admin_code': admin_code,
            'admin_name': admin_name,
            'date': date,
            'average_price': float(avg_price),
            'meb_weight': PRODUCT_DETAILS[product_code]['weight'],
            'unit': PRODUCT_DETAILS[product_code]['unit'],
        })
    
    if records:
        pd.DataFrame(records).to_sql('products', engine, if_exists='append', index=False)
    return len(records)

# ============================================================================
# MAIN LOADING
# ============================================================================

def load_month(year, month, engine, force=False):
    """Load data for a specific month"""
    paths = get_month_paths(year, month)
    analysis_file = paths['analysis_file']
    collection_date = paths['date'].date()
    
    if not analysis_file.exists():
        return {'status': 'skipped', 'reason': 'file_not_found', 'month_name': paths['month_name']}
    
    # Check if month exists in database
    month_exists = check_month_exists(engine, collection_date)
    
    if month_exists and not force:
        print(f"\n   ⚠️  This month already has data in database")
        response = input("   Delete existing data and reload? (yes/no): ")
        
        if response.lower() != 'yes':
            print("\n   ❌ Load cancelled by user")
            return {'status': 'skipped', 'reason': 'user_cancelled', 'month_name': paths['month_name']}
        
        # User confirmed, delete existing data
        print(f"\n   🗑️  Deleting existing data...")
        delete_month_data(engine, collection_date)
        print(f"   ✅ Cleared existing data")
    
    if force and month_exists:
        print(f"    🔄 Deleting existing data...")
        delete_month_data(engine, collection_date)
    
    try:
        master_df = pd.read_excel(analysis_file, sheet_name='Master')
        commodities_df = pd.read_excel(analysis_file, sheet_name='Commodities')
        
        muni_count = load_municipality_meb(engine, master_df, collection_date)
        region_count = load_regional_meb(engine, master_df, collection_date)
        national_count = load_national_meb(engine, master_df, collection_date)
        commodity_count = load_commodities(engine, commodities_df, collection_date)
        
        return {
            'status': 'success',
            'month_name': paths['month_name'],
            'municipalities': muni_count,
            'regions': region_count,
            'national': national_count,
            'commodities': commodity_count
        }
    except Exception as e:
        return {'status': 'error', 'month_name': paths['month_name'], 'error': str(e)}

def load_all(engine, force=False):
    """Load all available months"""
    print("="*70)
    print("LIBYA PMM - LOAD PMM DATA TO DATABASE")
    print("="*70)
    
    # Find all Analysis files
    analysis_files = list(MONTHLY_REPORTS_ROOT.glob("*/*/Analysis/MEB_Analysis_*.xlsx"))
    
    if not analysis_files:
        print(f"\n✗ No Analysis files found in {MONTHLY_REPORTS_ROOT}")
        return []
    
    print(f"\n✓ Found {len(analysis_files)} Analysis files")
    if force:
        print(f"⚠️  FORCE MODE: Will reload existing data")
    
    results = []
    for i, file_path in enumerate(sorted(analysis_files), 1):
        year = int(file_path.parts[-4])
        month_name = file_path.parts[-3]
        month = datetime.strptime(month_name, "%B").month
        
        month_label = f"{month_name} {year}"
        print(f"\n[{i}/{len(analysis_files)}] {month_label}")
        print("-"*70)
        
        result = load_month(year, month, engine, force)
        results.append(result)
        
        if result['status'] == 'success':
            print(f"  ✅ Loaded: {result['municipalities']} munis, {result['regions']} regions, {result['commodities']} commodities")
        elif result['status'] == 'skipped':
            reason = result['reason'].replace('_', ' ').title()
            print(f"  ⭐️ Skipped: {reason}")
        else:
            print(f"  ✗ Error: {result.get('error')}")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    success = sum(1 for r in results if r['status'] == 'success')
    skipped = sum(1 for r in results if r['status'] == 'skipped')
    errors = sum(1 for r in results if r['status'] == 'error')
    print(f"\n  ✅ Loaded:  {success}")
    print(f"  ⭐️ Skipped: {skipped}")
    print(f"  ✗ Errors:  {errors}")
    
    if success > 0:
        print(f"\n✅ Successfully loaded {success} month(s) to database!")
    
    print("\n" + "="*70)
    
    return results

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Load PMM data to PostgreSQL database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Load all available months (skip existing)
  python scripts/04_Database_Loading/load_meb_to_db.py --all
  
  # Load specific month
  python scripts/04_Database_Loading/load_meb_to_db.py 2025 11
  
  # Force reload all months (overwrite existing)
  python scripts/04_Database_Loading/load_meb_to_db.py --all --force
        """
    )
    
    parser.add_argument('year', nargs='?', type=int, help='Year (e.g., 2025)')
    parser.add_argument('month', nargs='?', type=int, help='Month (1-12)')
    parser.add_argument('--all', action='store_true', help='Load all available months')
    parser.add_argument('--force', action='store_true', help='Force reload (overwrite existing)')
    
    args = parser.parse_args()
    
    try:
        print(f"\n🔌 Connecting to database...")
        engine = get_engine()
        print(f"✓ Connected\n")
        
        if args.all:
            results = load_all(engine, args.force)
            if any(r['status'] == 'error' for r in results):
                sys.exit(1)
        elif args.year and args.month:
            # Validate month
            if not 1 <= args.month <= 12:
                print(f"Error: Month must be between 1 and 12, got {args.month}")
                sys.exit(1)
            
            result = load_month(args.year, args.month, engine, args.force)
            
            if result['status'] == 'success':
                print(f"\n✅ Successfully loaded {result['month_name']} {args.year}")
                print(f"   Municipalities: {result['municipalities']}")
                print(f"   Regions: {result['regions']}")
                print(f"   Commodities: {result['commodities']}")
            elif result['status'] == 'skipped':
                print(f"\n⭐️ Skipped: {result['reason'].replace('_', ' ')}")
                if result['reason'] == 'already_exists':
                    print(f"   Use --force to reload")
            else:
                print(f"\n✗ Error: {result.get('error')}")
                sys.exit(1)
        else:
            parser.print_help()
            sys.exit(1)
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)