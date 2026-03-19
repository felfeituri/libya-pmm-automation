#!/usr/bin/env python3
"""
Libya PMM - Phase 1: Data Export
Exports PMM data from MoDa platform

⚠️  MUST RUN LOCALLY (NOT IN DOCKER)
This script requires MoDa API credentials from your .env file

Usage:
    python 01_run_data_export.py <year> <month> <form_id>

Example:
    python 01_run_data_export.py 2025 12 329382

What it does:
    1. Connects to MoDa API using credentials from .env
    2. Downloads PMM survey data for the specified month
    3. Saves TWO Excel files to Monthly Reports/YYYY/Month/Data/Raw/:
       - PMM_MonYY_Labels.xlsx (human-readable with question labels)
       - PMM_MonYY_Codes.xlsx (raw coded values for analysis)

After running this:
    1. Review the exported data files
    2. Continue with QA/QC: python 02_run_qaqc.py <year> <month>

Prerequisites:
    - .env file with MODA_TOKEN at project root
    - Internet connection
    - MUST RUN LOCALLY (credentials should not be in Docker)

Note:
    The .env file should contain:
        MODA_TOKEN=your_token_here
"""

import subprocess
import sys
from pathlib import Path

def run_data_export(year: int, month: int, form_id: int):
    """Export PMM data from MoDa"""
    
    BASE_DIR = Path(__file__).resolve().parent
    script = BASE_DIR / "scripts" / "01_Data_Export" / "export_pmm_data.py"
    
    print("=" * 70)
    print("LIBYA PMM - DATA EXPORT PHASE")
    print("=" * 70)
    print()
    print("⚠️  Running locally (requires MoDa API credentials)")
    print()
    
    if not script.exists():
        print(f"❌ Script not found: {script}")
        print()
        print("Expected location:")
        print(f"  {script}")
        return 1
    
    # Check for .env file
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        print("❌ Missing .env file")
        print()
        print("Create a .env file in the project root with:")
        print("  MODA_TOKEN=your_token_here")
        print()
        print(f"Expected location: {env_file}")
        return 1
    
    # Run the export script
    cmd = ["python", str(script), str(year), str(month), str(form_id)]
    
    try:
        result = subprocess.run(cmd, cwd=BASE_DIR, check=True)
        
        print()
        print("=" * 70)
        print("✅ DATA EXPORT PHASE COMPLETE")
        print("=" * 70)
        print()
        print("Next: python 02_run_qaqc.py {year} {month}")
        
        return 0
        
    except subprocess.CalledProcessError:
        print()
        print("=" * 70)
        print("❌ DATA EXPORT FAILED")
        print("=" * 70)
        print()
        print("Common issues:")
        print("  • Missing or invalid MODA_TOKEN in .env file")
        print("  • Network connection issues")
        print("  • Invalid form ID")
        print("  • MoDa API service unavailable")
        print()
        print("Check error messages above for details.")
        return 1

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("=" * 70)
        print("LIBYA PMM - DATA EXPORT")
        print("=" * 70)
        print()
        print("Usage: python 01_run_data_export.py <year> <month> <form_id>")
        print()
        print("Arguments:")
        print("  year     : Year (e.g., 2025)")
        print("  month    : Month number 1-12 (e.g., 12 for December)")
        print("  form_id  : MoDa form ID (integer, e.g., 329382)")
        print()
        print("Examples:")
        print("  python 01_run_data_export.py 2025 12 329382")
        print("  python 01_run_data_export.py 2025 11 329350")
        print()
        print("What gets exported:")
        print("  Two Excel files to Monthly Reports/YYYY/Month/Data/Raw/:")
        print("    1. PMM_MonYY_Labels.xlsx (human-readable)")
        print("    2. PMM_MonYY_Codes.xlsx (coded values for analysis)")
        print()
        print("⚠️  Note: This script MUST be run locally (not in Docker)")
        print("   It requires MoDa API credentials from .env file")
        sys.exit(1)
    
    try:
        year = int(sys.argv[1])
        month = int(sys.argv[2])
        form_id = int(sys.argv[3])
        
        if not 1 <= month <= 12:
            print(f"❌ Error: Month must be between 1 and 12, got {month}")
            sys.exit(1)
        
        if form_id <= 0:
            print(f"❌ Error: Form ID must be a positive integer, got {form_id}")
            sys.exit(1)
        
        sys.exit(run_data_export(year, month, form_id))
        
    except ValueError as e:
        print("=" * 70)
        print("❌ INVALID ARGUMENTS")
        print("=" * 70)
        print()
        print("All arguments must be numbers:")
        print("  year     : Integer (e.g., 2025)")
        print("  month    : Integer 1-12 (e.g., 12)")
        print("  form_id  : Integer (e.g., 329382)")
        print()
        print(f"Error: {e}")
        sys.exit(1)