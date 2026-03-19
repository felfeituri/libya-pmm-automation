"""
Libya PMM - Geopoints Table for Mapping
Generates table with municipality locations, Full MEB prices, and MoM% change

Columns:
- ADM0_PCODE, ADM0_EN (Libya)
- ADM1_PCODE, ADM1_EN (Region: East/West/South)
- ADM2_PCODE, ADM2_EN (Municipality name)
- X, Y (Coordinates)
- MEB (Full MEB for specified month)
- MoM (Month-over-Month % change)
- Percent Change (same as MoM)

Usage:
    python scripts/05_Data_Outputs/geopoints_table.py <year> <month>

Examples:
    python scripts/05_Data_Outputs/geopoints_table.py 2025 11
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
from datetime import datetime
from sqlalchemy import text
from config import get_month_paths, ensure_month_directories, get_engine

# ============================================================================
# DATA EXTRACTION
# ============================================================================

def get_geopoints_data(engine, year, month):
    """Get municipality geopoints with Full MEB and MoM% change"""
    
    # Create target date
    target_date = datetime(year, month, 1)
    
    # Calculate previous month
    if target_date.month == 1:
        prev_date = target_date.replace(year=target_date.year - 1, month=12)
    else:
        prev_date = target_date.replace(month=target_date.month - 1)
    
    print(f"Current month: {target_date.strftime('%B %Y')}")
    print(f"Previous month: {prev_date.strftime('%B %Y')}")
    
    # Query to get municipality data with coordinates from locations table
    query = text("""
        WITH current_month AS (
            SELECT 
                municipality,
                full_meb as current_meb
            FROM municipality_meb
            WHERE date = :current_date
            AND full_meb IS NOT NULL
            AND full_meb > 0
        ),
        previous_month AS (
            SELECT 
                municipality,
                full_meb as prev_meb
            FROM municipality_meb
            WHERE date = :prev_date
            AND full_meb IS NOT NULL
            AND full_meb > 0
        )
        SELECT 
            l.adm2_pcode,
            l.adm2_en as municipality,
            l.adm1_pcode,
            l.adm1_en as region,
            l.x,
            l.y,
            c.current_meb,
            p.prev_meb
        FROM locations l
        INNER JOIN current_month c ON l.adm2_en = c.municipality
        LEFT JOIN previous_month p ON l.adm2_en = p.municipality
        WHERE l.adm2_pcode IS NOT NULL
        ORDER BY l.adm2_en
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {
            'current_date': target_date,
            'prev_date': prev_date
        })
        df = pd.DataFrame(result.fetchall(), 
                         columns=['adm2_pcode', 'municipality', 'adm1_pcode', 'region', 'x', 'y', 'current_meb', 'prev_meb'])
    
    return df

def build_geopoints_table(df):
    """Build final geopoints table with all required columns"""
    
    rows = []
    
    for _, row in df.iterrows():
        municipality = row['municipality']
        region = row['region']  # From locations table
        adm1_pcode = row['adm1_pcode']  # From locations table
        
        current_meb = float(row['current_meb']) if row['current_meb'] is not None else None
        prev_meb = float(row['prev_meb']) if row['prev_meb'] is not None else None
        
        # Calculate MoM (as decimal) and percent change
        if current_meb is not None and prev_meb is not None and prev_meb > 0:
            mom_decimal = (current_meb - prev_meb) / prev_meb  # Decimal form (e.g., 0.054 for 5.4%)
            percent_change = mom_decimal * 100  # Percent form (e.g., 5.4)
        else:
            mom_decimal = 0.0
            percent_change = 0.0
        
        rows.append({
            'ADM0_PCODE': 'LY',
            'ADM0_EN': 'Libya',
            'ADM1_PCODE': adm1_pcode,
            'ADM1_EN': region,
            'ADM2_PCODE': row['adm2_pcode'],
            'ADM2_EN': municipality,
            'X': float(row['x']) if row['x'] is not None else 0.0,
            'Y': float(row['y']) if row['y'] is not None else 0.0,
            'MEB': round(current_meb, 2) if current_meb is not None else 0.0,
            'MoM': round(mom_decimal, 4),  # Decimal form (e.g., 0.0540)
            'Percent Change': round(percent_change, 1)  # Percent (e.g., 5.4)
        })
    
    return pd.DataFrame(rows)

# ============================================================================
# EXPORT
# ============================================================================

def generate_geopoints_table(year, month):
    """Generate geopoints table for mapping"""
    
    engine = get_engine()
    
    print("="*70)
    print("LIBYA PMM - GEOPOINTS TABLE FOR MAPPING")
    print("="*70)
    
    # Get paths from config
    paths = ensure_month_directories(year, month)
    
    print(f"\nGenerating geopoints for: {paths['month_name']} {year}")
    print(f"Month tag: {paths['month_tag']}")
    
    # Get data
    print(f"\nExtracting municipality Full MEB data...")
    df = get_geopoints_data(engine, year, month)
    
    print(f"Found {len(df)} municipalities with Full MEB data")
    
    # Build table
    print(f"\nBuilding geopoints table...")
    geopoints_df = build_geopoints_table(df)
    
    # Output file (CSV only)
    csv_file = paths['geopoints']
    
    # Save as CSV (for GIS)
    geopoints_df.to_csv(csv_file, index=False)
    
    print("\n" + "="*70)
    print("GEOPOINTS TABLE GENERATION COMPLETE")
    print("="*70)
    print(f"\n✓ CSV file: {csv_file.name}")
    print(f"  Location: {paths['tables']}")
    print(f"  {len(geopoints_df)} municipalities")
    
    # Show sample
    print("\nSample data:")
    print(geopoints_df.head(5).to_string(index=False))
    
    return csv_file

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate geopoints table for mapping",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate geopoints for November 2025
  python scripts/05_Data_Outputs/geopoints_table.py 2025 11
  
  # Generate geopoints for October 2025
  python scripts/05_Data_Outputs/geopoints_table.py 2025 10

Output:
  Geopoints_MEB_Nov25.csv (for GIS/mapping software)
  
  Contains:
  - Municipality locations (X, Y coordinates)
  - Full MEB values
  - MoM (decimal format, e.g., 0.0540 for 5.4% change)
  - Percent Change (percentage, e.g., 5.4)
  - Administrative codes (ADM0, ADM1, ADM2)

Prerequisites:
  1. Database must be loaded with PMM data
  2. locations table must exist with municipality coordinates
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
        csv_file = generate_geopoints_table(args.year, args.month)
        print(f"\n✅ Ready for mapping in GIS software!")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)