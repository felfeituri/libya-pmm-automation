#!/usr/bin/env python3
"""
Libya PMM - Phase 3: Data Preprocessing
Calculates MEB values and processes exchange rates

Usage:
    python 03_run_preprocessing.py <year> <month>

Example:
    python 03_run_preprocessing.py 2025 12

What it does:
    1. Calculates MEB (Minimum Expenditure Basket) from raw PMM data
       - Municipality-level MEB (Food, NFI, Full)
       - Regional MEB (East, West, South)
       - National MEB
    2. Processes exchange rates
       - Combines official CBL rates with manual parallel market data
       - Creates monthly exchange rate file

Output location:
    - MEB Analysis: Monthly Reports/YYYY/Month/Data/Analysis/
    - Exchange Rate: Monthly Reports/YYYY/Month/Exchange Rate/

Prerequisites:
    - Raw PMM data exported and QA/QC completed
    - Parallel market exchange rate data filled in Excel
"""

import subprocess
import sys
from pathlib import Path

def run_preprocessing(year: int, month: int):
    """Run data preprocessing scripts"""
    
    BASE_DIR = Path(__file__).resolve().parent
    PROCESSING_DIR = BASE_DIR / "scripts" / "03_Data_Processing"
    
    print("=" * 70)
    print("LIBYA PMM - DATA PREPROCESSING PHASE")
    print("=" * 70)
    print()
    
    # Processing scripts in order
    scripts = [
        ("Calculate MEB", PROCESSING_DIR / "calculate_meb.py"),
        ("Process Exchange Rates", PROCESSING_DIR / "process_exchange_rate.py"),
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
        
        try:
            result = subprocess.run(
                ["python", str(script_path), str(year), str(month)],
                cwd=BASE_DIR,
                check=True
            )
            print(f"\n✅ {name} - Success")
            results.append((name, True))
        except subprocess.CalledProcessError:
            print(f"\n❌ {name} - Failed")
            results.append((name, False))
            # Don't stop - try next script
    
    # Summary
    print("\n" + "=" * 70)
    print("PREPROCESSING SUMMARY")
    print("=" * 70)
    print()
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {name}")
    
    print()
    if success_count == total_count:
        print("✅ Preprocessing phase complete!")
        print()
        print("⚠️  MANUAL STEP: Fill parallel market rates in Exchange_Rate_MonYY.xlsx")
        print()
        print("Next: python 04_run_database_loading.py {year} {month}")
        return 0
    else:
        print(f"⚠️  {total_count - success_count} script(s) failed")
        return 1

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python 03_run_preprocessing.py <year> <month>")
        print()
        print("Example:")
        print("  python 03_run_preprocessing.py 2025 12")
        sys.exit(1)
    
    try:
        year = int(sys.argv[1])
        month = int(sys.argv[2])
        
        if not 1 <= month <= 12:
            print(f"❌ Month must be between 1 and 12, got {month}")
            sys.exit(1)
        
        sys.exit(run_preprocessing(year, month))
        
    except ValueError:
        print("❌ Year and month must be numbers")
        sys.exit(1)