"""
Libya PMM - Trend Query System
Extracts trends, calculations, and analysis data from PostgreSQL database
Outputs JSON to monthly Data/JSON folder

Usage:
    python scripts/06_Visualizations/query_trends.py <year> <month>

Examples:
    python scripts/06_Visualizations/query_trends.py                    # Get latest 12 months
    python scripts/06_Visualizations/query_trends.py --months 6         # Get latest 6 months
    python scripts/06_Visualizations/query_trends.py 2025 11            # Trends up to November 2025

Output Location:
    Monthly Reports/<Year>/<Month>/Data/JSON/trends_<MonYY>.json
    Example: Monthly Reports/2025/November/Data/JSON/trends_Nov25.json
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime, timedelta
import sys

# Auto-detect environment and set project root
import os

if os.path.exists('/app'):  # Running in Docker
    PROJECT_ROOT = Path('/app')
else:  # Running locally
    # Script is in scripts/06_Visualizations/
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Add project root to path to import config
sys.path.insert(0, str(PROJECT_ROOT))

from config import get_engine, get_month_paths
from sqlalchemy import text

# ============================================================================
# MUNICIPALITY NAME MAPPING
# ============================================================================

def fix_municipality_names(df, column='municipality'):
    """
    Fix municipality names to official spellings
    
    Mappings:
    - Ejdabia → Ajdabiya
    - Tripoli Center → Tripoli
    """
    if column not in df.columns:
        return df
    
    name_mapping = {
        'Ejdabia': 'Ajdabiya',
        'Tripoli Center': 'Tripoli'
    }
    
    df[column] = df[column].replace(name_mapping)
    return df

# ============================================================================
# TREND EXTRACTION FUNCTIONS
# ============================================================================

def get_national_trends(engine, target_date, months_back=12):
    """Extract national MEB trends for last N months"""
    query = text("""
        SELECT 
            date,
            food_meb,
            nfi_meb,
            full_meb
        FROM national_meb
        WHERE date <= :target_date
        AND full_meb IS NOT NULL
        AND full_meb > 0
        ORDER BY date DESC
        LIMIT :limit
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {'target_date': target_date, 'limit': months_back})
        df = pd.DataFrame(result.fetchall(), columns=['date', 'food_meb', 'nfi_meb', 'full_meb'])
    
    # Reverse to get chronological order
    df = df.sort_values('date').reset_index(drop=True)
    
    # Convert to float to avoid Decimal issues
    df['food_meb'] = df['food_meb'].astype(float)
    df['nfi_meb'] = df['nfi_meb'].astype(float)
    df['full_meb'] = df['full_meb'].astype(float)
    
    # Calculate MoM changes (fill_method=None to suppress warning)
    df['food_meb_mom_pct'] = df['food_meb'].pct_change(fill_method=None) * 100
    df['nfi_meb_mom_pct'] = df['nfi_meb'].pct_change(fill_method=None) * 100
    df['full_meb_mom_pct'] = df['full_meb'].pct_change(fill_method=None) * 100
    
    df['food_meb_mom_abs'] = df['food_meb'].diff()
    df['nfi_meb_mom_abs'] = df['nfi_meb'].diff()
    df['full_meb_mom_abs'] = df['full_meb'].diff()
    
    # Calculate YoY changes (if 12+ months available)
    if len(df) >= 13:
        df['food_meb_yoy_pct'] = df['food_meb'].pct_change(periods=12, fill_method=None) * 100
        df['nfi_meb_yoy_pct'] = df['nfi_meb'].pct_change(periods=12, fill_method=None) * 100
        df['full_meb_yoy_pct'] = df['full_meb'].pct_change(periods=12, fill_method=None) * 100
    
    return df

def get_regional_trends(engine, target_date, months_back=12):
    """Extract regional MEB trends for last N months"""
    query = text("""
        SELECT 
            date,
            region,
            food_meb,
            nfi_meb,
            full_meb
        FROM regional_meb
        WHERE date <= :target_date
        AND full_meb IS NOT NULL
        AND full_meb > 0
        ORDER BY region, date DESC
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {'target_date': target_date})
        df = pd.DataFrame(result.fetchall(), columns=['date', 'region', 'food_meb', 'nfi_meb', 'full_meb'])
    
    # Convert to float
    df['food_meb'] = df['food_meb'].astype(float)
    df['nfi_meb'] = df['nfi_meb'].astype(float)
    df['full_meb'] = df['full_meb'].astype(float)
    
    # Process each region separately
    regional_data = {}
    for region in ['East', 'West', 'South']:
        region_df = df[df['region'] == region].copy()
        region_df = region_df.sort_values('date').tail(months_back).reset_index(drop=True)
        
        # Calculate MoM changes
        region_df['food_meb_mom_pct'] = region_df['food_meb'].pct_change(fill_method=None) * 100
        region_df['nfi_meb_mom_pct'] = region_df['nfi_meb'].pct_change(fill_method=None) * 100
        region_df['full_meb_mom_pct'] = region_df['full_meb'].pct_change(fill_method=None) * 100
        
        regional_data[region] = region_df
    
    return regional_data

def get_municipality_rankings(engine, target_date):
    """Get current month municipality rankings"""
    query = text("""
        SELECT 
            municipality,
            food_meb,
            nfi_meb,
            full_meb
        FROM municipality_meb
        WHERE date = :target_date
        ORDER BY full_meb DESC
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {'target_date': target_date})
        df = pd.DataFrame(result.fetchall(), columns=['municipality', 'food_meb', 'nfi_meb', 'full_meb'])
    
    # Fix municipality names
    df = fix_municipality_names(df, 'municipality')
    
    # Convert to float for JSON serialization
    df['food_meb'] = df['food_meb'].astype(float)
    df['nfi_meb'] = df['nfi_meb'].astype(float)
    df['full_meb'] = df['full_meb'].astype(float)
    
    return df

def get_commodity_trends(engine, target_date, months_back=12):
    """Extract commodity price trends"""
    query = text("""
        SELECT 
            date,
            product_code,
            product_name,
            category,
            admin_name,
            average_price
        FROM products
        WHERE date <= :target_date
        AND admin_name = 'Libya'
        AND average_price IS NOT NULL
        AND average_price > 0
        ORDER BY product_code, date DESC
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {'target_date': target_date})
        df = pd.DataFrame(result.fetchall(), columns=['date', 'product_code', 'product_name', 'category', 'admin_name', 'average_price'])
    
    # Convert to float
    df['average_price'] = df['average_price'].astype(float)
    
    # Calculate MoM for each product
    commodity_data = {}
    for product in df['product_code'].unique():
        product_df = df[df['product_code'] == product].copy()
        product_df = product_df.sort_values('date').tail(months_back).reset_index(drop=True)
        
        if len(product_df) > 1:
            product_df['mom_pct'] = product_df['average_price'].pct_change(fill_method=None) * 100
        
        commodity_data[product] = product_df
    
    return commodity_data

def get_regional_commodity_mom(engine, target_date):
    """Get regional commodity MoM% for tables"""
    # Get current and previous month
    query = text("""
        SELECT 
            date,
            product_code,
            product_name,
            category,
            admin_name,
            average_price
        FROM products
        WHERE date IN (
            SELECT DISTINCT date 
            FROM products 
            WHERE date <= :target_date 
            ORDER BY date DESC 
            LIMIT 2
        )
        AND admin_name IN ('East', 'West', 'South')
        ORDER BY admin_name, product_code, date
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {'target_date': target_date})
        df = pd.DataFrame(result.fetchall(), columns=['date', 'product_code', 'product_name', 'category', 'admin_name', 'average_price'])
    
    dates = sorted(df['date'].unique())
    if len(dates) < 2:
        return {}
    
    current_date = dates[-1]
    previous_date = dates[-2]
    
    regional_mom = {}
    
    for region in ['East', 'West', 'South']:
        current = df[(df['date'] == current_date) & (df['admin_name'] == region)]
        previous = df[(df['date'] == previous_date) & (df['admin_name'] == region)]
        
        mom_data = []
        for _, curr_row in current.iterrows():
            product = curr_row['product_code']
            prev_row = previous[previous['product_code'] == product]
            
            if not prev_row.empty:
                prev_price = prev_row['average_price'].values[0]
                curr_price = curr_row['average_price']
                mom_pct = ((curr_price - prev_price) / prev_price) * 100 if prev_price > 0 else 0
            else:
                mom_pct = None
            
            mom_data.append({
                'product': curr_row['product_name'],
                'category': curr_row['category'],
                'current_price': float(curr_row['average_price']),
                'mom_pct': float(mom_pct) if mom_pct is not None else None
            })
        
        regional_mom[region] = mom_data
    
    return regional_mom

def get_exchange_rate_trends(engine, target_date, months_back=12):
    """Extract exchange rate trends for last N months"""
    
    # Simpler query - get all data and filter in pandas
    query = text("""
        SELECT 
            date,
            official_rate,
            official_rate_with_tax,
            parallel_market_rate
        FROM exchange_rates
        ORDER BY date DESC
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query)
        df = pd.DataFrame(result.fetchall(), columns=['date', 'official_rate', 'official_rate_with_tax', 'parallel_market_rate'])
    
    if df.empty:
        return df
    
    # Convert date to datetime for filtering
    df['date'] = pd.to_datetime(df['date'])
    
    # Filter to last N months from target date
    cutoff_date = pd.to_datetime(target_date) - pd.Timedelta(days=months_back * 31)
    df = df[df['date'] <= pd.to_datetime(target_date)]
    df = df[df['date'] >= cutoff_date]
    
    # Sort chronologically
    df = df.sort_values('date').reset_index(drop=True)
    
    # Convert to float
    df['official_rate'] = pd.to_numeric(df['official_rate'], errors='coerce')
    df['official_rate_with_tax'] = pd.to_numeric(df['official_rate_with_tax'], errors='coerce')
    df['parallel_market_rate'] = pd.to_numeric(df['parallel_market_rate'], errors='coerce')
    
    return df

# ============================================================================
# MAIN QUERY FUNCTION
# ============================================================================

def extract_all_trends(target_year, target_month, months_back=12):
    """Extract all trends and analysis data from database"""
    engine = get_engine()
    
    target_date = datetime(target_year, target_month, 1).date()
    
    # Get month paths from config
    paths = get_month_paths(target_year, target_month)
    
    print("="*70)
    print("LIBYA PMM - TREND EXTRACTION")
    print("="*70)
    print(f"\nTarget month: {target_date.strftime('%B %Y')}")
    print(f"Months back: {months_back}")
    print(f"Output: {paths['json']}")
    
    print(f"\n1. Extracting national trends...")
    national_trends = get_national_trends(engine, target_date, months_back)
    print(f"   ✓ {len(national_trends)} months")
    
    print(f"\n2. Extracting regional trends...")
    regional_trends = get_regional_trends(engine, target_date, months_back)
    print(f"   ✓ 3 regions")
    
    print(f"\n3. Getting municipality rankings...")
    rankings = get_municipality_rankings(engine, target_date)
    print(f"   ✓ {len(rankings)} municipalities")
    
    print(f"\n4. Extracting commodity trends...")
    commodity_trends = get_commodity_trends(engine, target_date, months_back)
    print(f"   ✓ {len(commodity_trends)} products")
    
    print(f"\n5. Calculating regional commodity MoM%...")
    regional_commodity_mom = get_regional_commodity_mom(engine, target_date)
    print(f"   ✓ 3 regions")
    
    print(f"\n6. Extracting exchange rate trends...")
    exchange_rates = get_exchange_rate_trends(engine, target_date, months_back)
    print(f"   ✓ {len(exchange_rates)} days")
    
    # Build output JSON
    print(f"\n7. Building output JSON...")
    
    output = {
        'metadata': {
            'target_date': target_date.isoformat(),
            'target_year': target_year,
            'target_month': target_month,
            'months_back': months_back,
            'generated_at': datetime.now().isoformat()
        },
        'national': {
            'dates': [d.isoformat() if hasattr(d, 'isoformat') else str(d) for d in national_trends['date']],
            'food_meb': national_trends['food_meb'].round(2).tolist(),
            'nfi_meb': national_trends['nfi_meb'].round(2).tolist(),
            'full_meb': national_trends['full_meb'].round(2).tolist(),
            'food_meb_mom_pct': national_trends['food_meb_mom_pct'].round(2).tolist(),
            'nfi_meb_mom_pct': national_trends['nfi_meb_mom_pct'].round(2).tolist(),
            'full_meb_mom_pct': national_trends['full_meb_mom_pct'].round(2).tolist(),
        },
        'regional': {},
        'municipality_rankings': {
            'highest_5': rankings.head(5).to_dict('records'),
            'lowest_5': rankings.tail(5).to_dict('records'),
            'all': rankings.to_dict('records')
        },
        'commodities': {},
        'regional_commodity_mom': regional_commodity_mom,
        'exchange_rates': {
            'dates': [d.isoformat() if hasattr(d, 'isoformat') else str(d) for d in exchange_rates['date']] if not exchange_rates.empty else [],
            'official_rate': exchange_rates['official_rate'].round(4).tolist() if not exchange_rates.empty else [],
            'official_rate_with_tax': exchange_rates['official_rate_with_tax'].round(2).tolist() if not exchange_rates.empty else [],
            'parallel_market_rate': exchange_rates['parallel_market_rate'].round(2).tolist() if not exchange_rates.empty else []
        }
    }
    
    # Add regional trends
    for region, df in regional_trends.items():
        output['regional'][region] = {
            'dates': [d.isoformat() if hasattr(d, 'isoformat') else str(d) for d in df['date']],
            'food_meb': df['food_meb'].round(2).tolist(),
            'nfi_meb': df['nfi_meb'].round(2).tolist(),
            'full_meb': df['full_meb'].round(2).tolist(),
            'food_meb_mom_pct': df['food_meb_mom_pct'].round(2).tolist(),
            'nfi_meb_mom_pct': df['nfi_meb_mom_pct'].round(2).tolist(),
            'full_meb_mom_pct': df['full_meb_mom_pct'].round(2).tolist(),
        }
    
    # Add commodity trends
    for product, df in commodity_trends.items():
        if len(df) > 0:
            output['commodities'][product] = {
                'product_name': df['product_name'].iloc[0],
                'category': df['category'].iloc[0],
                'dates': [d.isoformat() if hasattr(d, 'isoformat') else str(d) for d in df['date']],
                'prices': df['average_price'].round(2).tolist(),
                'mom_pct': df['mom_pct'].round(2).tolist() if 'mom_pct' in df.columns else []
            }
    
    # Save output
    output_file = paths['trends_json']
    
    # Ensure JSON directory exists
    paths['json'].mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n✓ Saved to: {output_file}")
    
    # Summary
    print(f"\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    latest = national_trends.iloc[-1]
    print(f"\nLatest Month: {target_date.strftime('%B %Y')}")
    print(f"\nNational Full MEB: {latest['full_meb']:.2f} LYD")
    
    if len(national_trends) > 1:
        print(f"MoM Change: {latest['full_meb_mom_pct']:.2f}%")
    
    print(f"\nHighest Municipality: {rankings.iloc[0]['municipality']} ({rankings.iloc[0]['full_meb']:.2f} LYD)")
    print(f"Lowest Municipality:  {rankings.iloc[-1]['municipality']} ({rankings.iloc[-1]['full_meb']:.2f} LYD)")
    
    print(f"\n" + "="*70)
    print("✅ EXTRACTION COMPLETE")
    print("="*70)
    
    return output, output_file

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1].isdigit():
        target_year = int(sys.argv[1])
        target_month = int(sys.argv[2])
    else:
        # Get latest month from database
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT MAX(date) FROM national_meb"))
            latest_date = result.fetchone()[0]
            target_year = latest_date.year
            target_month = latest_date.month
    
    months_back = 12
    if '--months' in sys.argv:
        idx = sys.argv.index('--months')
        months_back = int(sys.argv[idx + 1])
    
    extract_all_trends(target_year, target_month, months_back)