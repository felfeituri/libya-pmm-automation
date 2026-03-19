#!/usr/bin/env python3
"""
Libya PMM - Phase 5: Data Outputs
Generates all data tables and exports

Usage:
    python 05_run_data_outputs.py <year> <month>

Example:
    python 05_run_data_outputs.py 2025 12

What it does:
    1. Monthly tables (to Monthly Reports/Tables/)
       - MEB comparison tables
       - Commodity price tables
       - Geopoints table (for mapping)
    
    2. DataBridges exports (to DataBridges/)
       - MEB export (wide format for WFP system)
       - Exchange rate export (monthly averages)
    
    3. Master files (to Master Data/)
       - Historical MEB data (all months)
       - MoM/YoY analysis
       - Exchange rate trends

Output locations:
    - Monthly Reports/YYYY/Month/Tables/
    - DataBridges/Prices/ and DataBridges/Exchange Rates/
    - Master Data/

Prerequisites:
    - Database loaded with monthly data (04_run_database_loading.py)
"""

import subprocess
import sys
from pathlib import Path

def run_data_outputs(year: int, month: int):
    """Generate all data outputs"""
    
    BASE_DIR = Path(__file__).resolve().parent
    OUTPUTS_DIR = BASE_DIR / "scripts" / "05_Data_Outputs"
    
    print("=" * 70)
    print("LIBYA PMM - DATA OUTPUTS PHASE")
    print("=" * 70)
    print()
    
    # Output scripts in order
    scripts = [
        # Monthly tables
        ("MEB Tables", OUTPUTS_DIR / "meb_tables.py"),
        ("Commodity Tables", OUTPUTS_DIR / "commodity_tables.py"),
        ("Geopoints Table", OUTPUTS_DIR / "geopoints_table.py"),
        
        # DataBridges exports
        ("DataBridges MEB Export", OUTPUTS_DIR / "export_databridges_meb.py"),
        ("DataBridges Exchange Rate", OUTPUTS_DIR / "export_databridges_exchangerate.py"),
        
        # Master files (no year/month args)
        ("Master MEB Data", OUTPUTS_DIR / "master_data.py", False),
        ("Master Exchange Rate", OUTPUTS_DIR / "master_exchange_rate_mom_yoy.py", False),
        ("Historical Data Export", OUTPUTS_DIR / "export_historical_data.py", False),
    ]
    
    results = []
    
    for item in scripts:
        if len(item) == 3:
            name, script_path, needs_args = item
        else:
            name, script_path = item
            needs_args = True
        
        print("=" * 70)
        print(f"🚀 {name}")
        print("=" * 70)
        print()
        
        if not script_path.exists():
            print(f"⚠️  Script not found: {script_path}")
            results.append((name, False))
            continue
        
        # Build command
        cmd = ["python", str(script_path)]
        if needs_args:
            cmd.extend([str(year), str(month)])
        
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
    print("DATA OUTPUTS SUMMARY")
    print("=" * 70)
    print()
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {name}")
    
    print()
    if success_count == total_count:
        print("✅ Data outputs phase complete!")
        print()
        print("Next: python 06_run_visualizations.py {year} {month}")
        return 0
    else:
        print(f"⚠️  {total_count - success_count} script(s) failed")
        return 1

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python 05_run_data_outputs.py <year> <month>")
        print()
        print("Example:")
        print("  python 05_run_data_outputs.py 2025 12")
        sys.exit(1)
    
    try:
        year = int(sys.argv[1])
        month = int(sys.argv[2])
        
        if not 1 <= month <= 12:
            print(f"❌ Month must be between 1 and 12, got {month}")
            sys.exit(1)
        
        sys.exit(run_data_outputs(year, month))
        
    except ValueError:
        print("❌ Year and month must be numbers")
        sys.exit(1)