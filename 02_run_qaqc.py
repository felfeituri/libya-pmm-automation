#!/usr/bin/env python3
"""
Libya PMM - Phase 2: QA/QC
Generates quality assurance notebooks and tracking files

Usage:
    python 02_run_qaqc.py <year> <month>

Example:
    python 02_run_qaqc.py 2025 12

What it does:
    1. Generates QA/QC Jupyter notebook with data quality checks
    2. Generates Progress Tracker Excel (submission status by municipality)
    3. Generates Follow-up Excel (outliers and data issues)

Output location:
    - QA/QC notebook: Monthly Reports/YYYY/Month/QA_QC/
    - Progress tracker: Progress/PMM_Progress_Tracker_MonYY.xlsx
    - Follow-up file: Progress/PMM_Follow_Up_MonYY.xlsx

Prerequisites:
    - Raw PMM data exported (01_run_data_export.py)
"""

import subprocess
import sys
from pathlib import Path

def run_qaqc(year: int, month: int):
    """Run QA/QC scripts"""
    
    BASE_DIR = Path(__file__).resolve().parent
    QAQC_DIR = BASE_DIR / "scripts" / "02_QAQC"
    
    print("=" * 70)
    print("LIBYA PMM - QA/QC PHASE")
    print("=" * 70)
    print()
    
    # QA/QC scripts in order
    scripts = [
        ("QA/QC Notebook", QAQC_DIR / "generate_qaqc_notebook.py"),
        ("Progress Tracker", QAQC_DIR / "generate_progress_tracker.py"),
        ("Follow-up File", QAQC_DIR / "generate_followup.py"),
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
    
    # Summary
    print("\n" + "=" * 70)
    print("QA/QC SUMMARY")
    print("=" * 70)
    print()
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {name}")
    
    print()
    if success_count == total_count:
        print("✅ QA/QC phase complete!")
        print()
        print("Next: python 03_run_preprocessing.py {year} {month}")
        return 0
    else:
        print(f"⚠️  {total_count - success_count} script(s) failed")
        return 1

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python 02_run_qaqc.py <year> <month>")
        print()
        print("Example:")
        print("  python 02_run_qaqc.py 2025 12")
        sys.exit(1)
    
    try:
        year = int(sys.argv[1])
        month = int(sys.argv[2])
        
        if not 1 <= month <= 12:
            print(f"❌ Month must be between 1 and 12, got {month}")
            sys.exit(1)
        
        sys.exit(run_qaqc(year, month))
        
    except ValueError:
        print("❌ Year and month must be numbers")
        sys.exit(1)