#!/usr/bin/env python3
"""
Libya PMM - Phase 4: Database Loading
Loads processed data into PostgreSQL database

Usage:
    python 04_run_database_loading.py <year> <month>
    python 04_run_database_loading.py <year> <month> --force  # Skip confirmations

Example:
    python 04_run_database_loading.py 2025 12

What it does:
    1. Loads MEB data to database
       - Municipality MEB → municipality_meb table
       - Regional MEB → regional_meb table
       - National MEB → national_meb table
       - Commodity prices → products table
    2. Loads exchange rates to database
       - Monthly exchange rates → exchange_rates table

Prerequisites:
    - MEB calculations completed (03_run_preprocessing.py)
    - Parallel market rates filled in Exchange_Rate_MonYY.xlsx
    - PostgreSQL database running

Notes:
    - Will prompt before overwriting existing data (unless --force)
    - Safe to re-run if data needs to be reloaded
"""

import subprocess
import sys
from pathlib import Path

def run_database_loading(year: int, month: int, force: bool = False):
    """Load data to PostgreSQL database"""
    
    BASE_DIR = Path(__file__).resolve().parent
    LOADING_DIR = BASE_DIR / "scripts" / "04_Database_Loading"
    
    print("=" * 70)
    print("LIBYA PMM - DATABASE LOADING PHASE")
    print("=" * 70)
    print()
    
    # Database loading scripts in order
    scripts = [
        ("Load MEB Data", LOADING_DIR / "load_meb_to_db.py"),
        ("Load Exchange Rates", LOADING_DIR / "load_exchange_to_db.py"),
    ]
    
    results = []
    
    for name, script_path in scripts:
        print("=" * 70)
        print(f"🚀 {name}")
        print("=" * 70)
        print()
        
        if not script_path.exists():
            print(f"⚠️  Script not found: {script_path}")
            results.append((name, False))
            continue
        
        # Build command
        cmd = ["python", str(script_path), str(year), str(month)]
        if force:
            cmd.append("--force")
        
        try:
            result = subprocess.run(cmd, cwd=BASE_DIR, check=True)
            print(f"\n✅ {name} - Success")
            results.append((name, True))
        except subprocess.CalledProcessError:
            print(f"\n❌ {name} - Failed")
            results.append((name, False))
            # Don't stop - try next script
    
    # Summary
    print("\n" + "=" * 70)
    print("DATABASE LOADING SUMMARY")
    print("=" * 70)
    print()
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {name}")
    
    print()
    if success_count == total_count:
        print("✅ Database loading phase complete!")
        print()
        print("Next: python 05_run_data_outputs.py {year} {month}")
        return 0
    else:
        print(f"⚠️  {total_count - success_count} script(s) failed")
        return 1

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python 04_run_database_loading.py <year> <month> [--force]")
        print()
        print("Example:")
        print("  python 04_run_database_loading.py 2025 12")
        print("  python 04_run_database_loading.py 2025 12 --force")
        sys.exit(1)
    
    try:
        year = int(sys.argv[1])
        month = int(sys.argv[2])
        force = "--force" in sys.argv
        
        if not 1 <= month <= 12:
            print(f"❌ Month must be between 1 and 12, got {month}")
            sys.exit(1)
        
        sys.exit(run_database_loading(year, month, force))
        
    except ValueError:
        print("❌ Year and month must be numbers")
        sys.exit(1)