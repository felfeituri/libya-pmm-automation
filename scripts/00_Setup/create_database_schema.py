"""
Libya PMM Database Schema Creation
Creates PostgreSQL database with proper admin hierarchy and historical commodity prices

Tables:
1. keys - Administrative codes and labels
2. locations - Municipality geopoints
3. municipality_meb - Monthly MEB by municipality
4. regional_meb - Monthly MEB by region
5. national_meb - Monthly national MEB
6. products - Historical commodity prices
7. exchange_rates - Daily exchange rates

Usage:
    python scripts/00_Setup/create_database_schema.py
"""

import sys
from pathlib import Path
import os

# Auto-detect environment and set project root
if os.path.exists('/app'):  # Running in Docker
    PROJECT_ROOT = Path('/app')
else:  # Running locally
    # Script is in scripts/00_Setup/
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Add project root to path to import config
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import text
from config import get_engine, DB_CONFIG

# ============================================================================
# SCHEMA CREATION
# ============================================================================

def create_schema():
    """Create all tables for Libya PMM database"""
    
    engine = get_engine()
    
    print("="*70)
    print("CREATING LIBYA PMM DATABASE SCHEMA")
    print("="*70)
    
    print(f"\nConnecting to database...")
    print(f"  Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"  Database: {DB_CONFIG['database']}")
    print(f"  User: {DB_CONFIG['user']}")
    
    with engine.connect() as conn:
        print(f"\n✓ Connected to PostgreSQL")
        
        # Drop existing tables (in reverse order of dependencies)
        print(f"\nDropping existing tables (if any)...")
        conn.execute(text("DROP TABLE IF EXISTS products CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS municipality_meb CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS regional_meb CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS national_meb CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS exchange_rates CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS locations CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS keys CASCADE"))
        conn.commit()
        print(f"✓ Cleaned up old tables")
        
        # ====================================================================
        # TABLE 1: KEYS (Administrative codes and labels)
        # ====================================================================
        print(f"\nCreating table: keys")
        conn.execute(text("""
            CREATE TABLE keys (
                admin_code VARCHAR(10) PRIMARY KEY,
                admin_level VARCHAR(10) NOT NULL,
                admin_name VARCHAR(100) NOT NULL,
                parent_code VARCHAR(10),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.commit()
        
        # Insert data
        conn.execute(text("""
            INSERT INTO keys (admin_code, admin_level, admin_name, parent_code) VALUES
            -- National (ADM0)
            ('LY', 'ADM0', 'Libya', NULL),
            
            -- Regions (ADM1)
            ('LY01', 'ADM1', 'East', 'LY'),
            ('LY02', 'ADM1', 'West', 'LY'),
            ('LY03', 'ADM1', 'South', 'LY'),
            
            -- Municipalities (ADM2) - East
            ('LY0101', 'ADM2', 'Derna', 'LY01'),
            ('LY0103', 'ADM2', 'Benghazi', 'LY01'),
            ('LY0104', 'ADM2', 'Tobruk', 'LY01'),
            ('LY0105', 'ADM2', 'Ejdabia', 'LY01'),
            ('LY0106', 'ADM2', 'AlBayda', 'LY01'),
            ('LY0107', 'ADM2', 'AlKufra', 'LY01'),
            
            -- Municipalities (ADM2) - West
            ('LY0208', 'ADM2', 'Sirt', 'LY02'),
            ('LY0209', 'ADM2', 'Nalut', 'LY02'),
            ('LY0210', 'ADM2', 'AlKhums', 'LY02'),
            ('LY0211', 'ADM2', 'Tripoli Center', 'LY02'),
            ('LY0213', 'ADM2', 'Azzawya', 'LY02'),
            ('LY0214', 'ADM2', 'Misrata', 'LY02'),
            ('LY0215', 'ADM2', 'Zwara', 'LY02'),
            ('LY0216', 'ADM2', 'Zliten', 'LY02'),
            
            -- Municipalities (ADM2) - South
            ('LY0223', 'ADM2', 'Algatroun', 'LY03'),
            ('LY0317', 'ADM2', 'AlJufra', 'LY03'),
            ('LY0318', 'ADM2', 'Wadi Alshati', 'LY03'),
            ('LY0319', 'ADM2', 'Sebha', 'LY03'),
            ('LY0320', 'ADM2', 'Ubari', 'LY03'),
            ('LY0321', 'ADM2', 'Ghat', 'LY03'),
            ('LY0322', 'ADM2', 'Murzuq', 'LY03')
        """))
        conn.commit()
        print(f"  ✓ Inserted 25 administrative codes (1 country, 3 regions, 21 municipalities)")
        
        # ====================================================================
        # TABLE 2: LOCATIONS (Geographic reference)
        # ====================================================================
        print(f"\nCreating table: locations")
        conn.execute(text("""
            CREATE TABLE locations (
                adm0_pcode VARCHAR(10) NOT NULL,
                adm0_en VARCHAR(100) NOT NULL,
                adm1_pcode VARCHAR(10) NOT NULL,
                adm1_en VARCHAR(100) NOT NULL,
                adm2_pcode VARCHAR(10) PRIMARY KEY,
                adm2_en VARCHAR(100) NOT NULL,
                x DECIMAL(12, 6),
                y DECIMAL(12, 6),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (adm2_pcode) REFERENCES keys(admin_code)
            )
        """))
        conn.commit()
        
        # Insert location data with geopoints
        conn.execute(text("""
            INSERT INTO locations (adm0_pcode, adm0_en, adm1_pcode, adm1_en, adm2_pcode, adm2_en, x, y) VALUES
            -- East region
            ('LY', 'Libya', 'LY01', 'East', 'LY0106', 'AlBayda', 21.7514684, 32.7846114),
            ('LY', 'Libya', 'LY01', 'East', 'LY0103', 'Benghazi', 20.0848234, 32.0571694),
            ('LY', 'Libya', 'LY01', 'East', 'LY0101', 'Derna', 22.6369408, 32.7414691),
            ('LY', 'Libya', 'LY01', 'East', 'LY0105', 'Ejdabia', 20.1872971, 30.7653657),
            ('LY', 'Libya', 'LY01', 'East', 'LY0107', 'AlKufra', 23.2894689, 24.216939),
            ('LY', 'Libya', 'LY01', 'East', 'LY0104', 'Tobruk', 23.9404853, 32.0498775),
            
            -- West region
            ('LY', 'Libya', 'LY02', 'West', 'LY0210', 'AlKhums', 14.2687789, 32.6450313),
            ('LY', 'Libya', 'LY02', 'West', 'LY0213', 'Azzawya', 12.7115843, 32.7567377),
            ('LY', 'Libya', 'LY02', 'West', 'LY0214', 'Misrata', 15.1069397, 32.3633237),
            ('LY', 'Libya', 'LY02', 'West', 'LY0209', 'Nalut', 10.9756719, 31.8691456),
            ('LY', 'Libya', 'LY02', 'West', 'LY0208', 'Sirt', 16.6294126, 31.1832948),
            ('LY', 'Libya', 'LY02', 'West', 'LY0211', 'Tripoli Center', 13.232873, 32.8912921),
            ('LY', 'Libya', 'LY02', 'West', 'LY0216', 'Zliten', 14.5656447, 32.4785206),
            ('LY', 'Libya', 'LY02', 'West', 'LY0215', 'Zwara', 12.0967942, 32.9292542),
            
            -- South region
            ('LY', 'Libya', 'LY03', 'South', 'LY0223', 'Algatroun', 14.546337, 24.9652808),
            ('LY', 'Libya', 'LY03', 'South', 'LY0317', 'AlJufra', 15.9393491, 29.1419397),
            ('LY', 'Libya', 'LY03', 'South', 'LY0321', 'Ghat', 10.1781564, 24.9549167),
            ('LY', 'Libya', 'LY03', 'South', 'LY0322', 'Murzuq', 13.9246199, 25.9057191),
            ('LY', 'Libya', 'LY03', 'South', 'LY0319', 'Sebha', 14.4597034, 26.997824),
            ('LY', 'Libya', 'LY03', 'South', 'LY0320', 'Ubari', 12.797176, 26.5948519),
            ('LY', 'Libya', 'LY03', 'South', 'LY0318', 'Wadi Alshati', 14.2693218, 27.5627019)
        """))
        conn.commit()
        print(f"  ✓ Inserted 21 municipalities with geopoints (X, Y format)")
        
        # ====================================================================
        # TABLE 3: MUNICIPALITY_MEB (Monthly municipality-level MEB)
        # ====================================================================
        print(f"\nCreating table: municipality_meb")
        conn.execute(text("""
            CREATE TABLE municipality_meb (
                adm2_pcode VARCHAR(10) NOT NULL,
                municipality VARCHAR(100) NOT NULL,
                date DATE NOT NULL,
                food_meb DECIMAL(10, 2),
                nfi_meb DECIMAL(10, 2),
                full_meb DECIMAL(10, 2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (adm2_pcode, date),
                FOREIGN KEY (adm2_pcode) REFERENCES keys(admin_code)
            )
        """))
        conn.commit()
        print(f"  ✓ Table created with composite key (adm2_pcode, date)")
        
        # ====================================================================
        # TABLE 4: REGIONAL_MEB (Monthly regional-level MEB)
        # ====================================================================
        print(f"\nCreating table: regional_meb")
        conn.execute(text("""
            CREATE TABLE regional_meb (
                adm1_pcode VARCHAR(10) NOT NULL,
                region VARCHAR(100) NOT NULL,
                date DATE NOT NULL,
                food_meb DECIMAL(10, 2),
                nfi_meb DECIMAL(10, 2),
                full_meb DECIMAL(10, 2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (adm1_pcode, date),
                FOREIGN KEY (adm1_pcode) REFERENCES keys(admin_code)
            )
        """))
        conn.commit()
        print(f"  ✓ Table created with composite key (adm1_pcode, date)")
        
        # ====================================================================
        # TABLE 5: NATIONAL_MEB (Monthly national-level MEB)
        # ====================================================================
        print(f"\nCreating table: national_meb")
        conn.execute(text("""
            CREATE TABLE national_meb (
                adm0_pcode VARCHAR(10) NOT NULL,
                date DATE NOT NULL,
                food_meb DECIMAL(10, 2),
                nfi_meb DECIMAL(10, 2),
                full_meb DECIMAL(10, 2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (adm0_pcode, date),
                FOREIGN KEY (adm0_pcode) REFERENCES keys(admin_code)
            )
        """))
        conn.commit()
        print(f"  ✓ Table created with composite key (adm0_pcode, date)")
        
        # ====================================================================
        # TABLE 6: PRODUCTS (Historical commodity prices)
        # ====================================================================
        print(f"\nCreating table: products")
        conn.execute(text("""
            CREATE TABLE products (
                product_code VARCHAR(50) NOT NULL,
                product_name VARCHAR(100) NOT NULL,
                category VARCHAR(20) NOT NULL,
                admin_code VARCHAR(10) NOT NULL,
                admin_name VARCHAR(100) NOT NULL,
                date DATE NOT NULL,
                average_price DECIMAL(10, 2),
                meb_weight DECIMAL(10, 2),
                unit VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (product_code, admin_code, date),
                FOREIGN KEY (admin_code) REFERENCES keys(admin_code)
            )
        """))
        conn.commit()
        print(f"  ✓ Table created with composite key (product_code, admin_code, date)")
        
        # ====================================================================
        # TABLE 7: EXCHANGE_RATES (Daily exchange rates)
        # ====================================================================
        print(f"\nCreating table: exchange_rates")
        conn.execute(text("""
            CREATE TABLE exchange_rates (
                date DATE PRIMARY KEY,
                usd_unit INTEGER NOT NULL,
                month_name VARCHAR(20),
                official_rate DECIMAL(10, 4),
                official_rate_with_tax DECIMAL(10, 2),
                parallel_market_rate DECIMAL(10, 2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Create indexes for exchange_rates
        conn.execute(text("""
            CREATE INDEX idx_exchange_rates_date ON exchange_rates(date);
            CREATE INDEX idx_exchange_rates_month ON exchange_rates(month_name)
        """))
        conn.commit()
        print(f"  ✓ Table created with primary key (date)")
        
        # Summary
        print(f"\n" + "="*70)
        print(f"SCHEMA CREATED SUCCESSFULLY")
        print(f"="*70)
        
        print(f"\nTables created:")
        print(f"  1. keys                (25 records: 1 country + 3 regions + 21 municipalities)")
        print(f"  2. locations           (21 municipalities with geopoints)")
        print(f"  3. municipality_meb    (monthly MEB data per municipality)")
        print(f"  4. regional_meb        (monthly MEB data per region)")
        print(f"  5. national_meb        (monthly national MEB data)")
        print(f"  6. products            (historical commodity prices)")
        print(f"  7. exchange_rates      (daily official and parallel market rates)")
        
        print(f"\nDatabase is ready for data loading!")
        print(f"="*70)

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Create Libya PMM database schema",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Creates 7 tables:
  1. keys - Administrative codes (country, regions, municipalities)
  2. locations - Municipality geopoints for mapping
  3. municipality_meb - Monthly MEB by municipality
  4. regional_meb - Monthly MEB by region (East, West, South)
  5. national_meb - Monthly national MEB
  6. products - Historical commodity prices (23 products)
  7. exchange_rates - Daily exchange rates (official + parallel market)

Prerequisites:
  PostgreSQL must be running and accessible with credentials in config.py

WARNING:
  This script will DROP existing tables and recreate them.
  All existing data will be lost.
        """
    )
    
    args = parser.parse_args()
    
    try:
        create_schema()
        print(f"\n✅ Schema creation completed successfully!")
        print(f"\nNext steps:")
        print(f"  1. Run data preprocessing scripts (Phase 2)")
        print(f"  2. Load data into database (Phase 3)")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error creating schema: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)