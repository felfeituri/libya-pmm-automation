#!/usr/bin/env python3
"""
Libya PMM - Run Complete Monthly Workflow
Automates Steps 3-6 of the monthly PMM workflow

⚠️  IMPORTANT: This script runs Steps 3-6 only.
   Step 1 (Data Export) and Step 2 (QA/QC) must be run first.

Usage:
    python 99_run_step03_to_step06.py <year> <month>
    python 99_run_step03_to_step06.py <year> <month> --force  # Skip database confirmations

Example:
    python 99_run_step03_to_step06.py 2025 12

What it runs:
    Step 3: Preprocessing (calculate_meb, process_exchange_rate)
    --- MANUAL PAUSE: Fill parallel market rates ---
    Step 4: Database Loading (load_meb_to_db, load_exchange_to_db)
    Step 5: Data Outputs (tables, DataBridges, master files)
    Step 6: Visualizations (query_trends, charts, map)

What you must do manually:
    BEFORE: python 01_run_data_export.py <year> <month> <form_id>  [LOCAL - Step 1]
    BEFORE: python 02_run_qaqc.py <year> <month>  [Review & fix issues - Step 2]
    DURING: Fill parallel market rates in Exchange_Rate_MonYY.xlsx
    AFTER:  python 07_run_report.py <year> <month> [Copy & edit report]

Prerequisites:
    - Step 1 complete: Raw PMM data exported from MoDa
    - Step 2 complete: QA/QC validation done and issues fixed
    - PostgreSQL database running
    - Docker container running (for Docker execution)
"""

import subprocess
import sys
from pathlib import Path
import time

def run_phase(phase_num: int, phase_name: str, year: int, month: int, extra_args: list = None):
    """Run a phase script"""
    
    BASE_DIR = Path(__file__).resolve().parent
    script = BASE_DIR / f"{phase_num:02d}_run_{phase_name}.py"
    
    if not script.exists():
        print(f"❌ Script not found: {script}")
        return False
    
    cmd = ["python", str(script), str(year), str(month)]
    if extra_args:
        cmd.extend(extra_args)
    
    try:
        result = subprocess.run(cmd, cwd=BASE_DIR, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def run_all_phases(year: int, month: int, force: bool = False):
    """Run Steps 3-6 of the monthly workflow"""
    
    print("=" * 70)
    print("LIBYA PMM - AUTOMATED WORKFLOW (STEPS 3-6)")
    print("=" * 70)
    print()
    print(f"Target Month: {year}-{month:02d}")
    print()
    print("⚠️  PREREQUISITES CHECKLIST:")
    print("  ✓ Step 1 complete: Data exported from MoDa")
    print("  ✓ Step 2 complete: QA/QC validation done and issues fixed")
    print()
    
    input("Press Enter to continue (Ctrl+C to cancel)...")
    print()
    
    results = []
    
    # Step 3: Preprocessing
    print("\n" + "=" * 70)
    print("STEP 3: PREPROCESSING")
    print("=" * 70)
    success = run_phase(3, "preprocessing", year, month)
    results.append(("Step 3: Preprocessing", success))
    if not success:
        print("\n❌ Step 3 failed. Stopping.")
        return False
    
    # MANUAL PAUSE: Fill parallel market rates
    print("\n" + "=" * 70)
    print("⏸️  MANUAL STEP REQUIRED")
    print("=" * 70)
    print()
    print("📝 Please fill parallel market rates in:")
    print(f"   Monthly Reports/{year}/{month}/Exchange Rate/Exchange_Rate_{month}.xlsx")
    print()
    print("Open the file and fill the 'Parallel Market USD/LYD' column")
    print("with data from Facebook marketplace.")
    print()
    
    input("Press Enter when done (Ctrl+C to cancel)...")
    print()
    
    # Step 4: Database Loading
    print("\n" + "=" * 70)
    print("STEP 4: DATABASE LOADING")
    print("=" * 70)
    extra_args = ["--force"] if force else []
    success = run_phase(4, "database_loading", year, month, extra_args)
    results.append(("Step 4: Database Loading", success))
    if not success:
        print("\n❌ Step 4 failed. Stopping.")
        return False
    
    # Step 5: Data Outputs
    print("\n" + "=" * 70)
    print("STEP 5: DATA OUTPUTS")
    print("=" * 70)
    success = run_phase(5, "data_outputs", year, month)
    results.append(("Step 5: Data Outputs", success))
    if not success:
        print("\n❌ Step 5 failed. Stopping.")
        return False
    
    # Step 6: Visualizations
    print("\n" + "=" * 70)
    print("STEP 6: VISUALIZATIONS")
    print("=" * 70)
    success = run_phase(6, "visualizations", year, month)
    results.append(("Step 6: Visualizations", success))
    if not success:
        print("\n❌ Step 6 failed. Stopping.")
        return False
    
    # Final Summary
    print("\n" + "=" * 70)
    print("🎉 AUTOMATED WORKFLOW COMPLETE!")
    print("=" * 70)
    print()
    print("Summary:")
    for step, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {step}")
    
    print()
    print("=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print()
    print("Step 7: Copy and edit report:")
    print(f"  python 07_run_report.py {year} {month}")
    print()
    print("  Then edit the PowerPoint manually with:")
    print("  - New charts (from Graphics/Charts/)")
    print("  - New tables (from Tables/)")
    print("  - Updated month name")
    print()
    print("All automated tasks complete! 🎊")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("=" * 70)
        print("LIBYA PMM - AUTOMATED WORKFLOW (STEPS 3-6)")
        print("=" * 70)
        print()
        print("Usage: python 99_run_step03_to_step06.py <year> <month> [--force]")
        print()
        print("Examples:")
        print("  python 99_run_step03_to_step06.py 2025 12")
        print("  python 99_run_step03_to_step06.py 2025 12 --force")
        print()
        print("Flags:")
        print("  --force       Skip database overwrite confirmations")
        print()
        print("Prerequisites (must complete first):")
        print("  1. Step 1: python 01_run_data_export.py 2025 12 <form_id>")
        print("  2. Step 2: python 02_run_qaqc.py 2025 12")
        print("  3. Review QA/QC results and fix any issues")
        print()
        print("What this script automates:")
        print("  - Step 3: Calculate MEB and create exchange rate file")
        print("  - Manual pause for parallel market data entry")
        print("  - Step 4: Load data to database")
        print("  - Step 5: Generate all tables and DataBridges exports")
        print("  - Step 6: Create all charts and maps")
        sys.exit(1)
    
    try:
        year = int(sys.argv[1])
        month = int(sys.argv[2])
        force = "--force" in sys.argv
        
        if not 1 <= month <= 12:
            print(f"❌ Month must be between 1 and 12, got {month}")
            sys.exit(1)
        
        success = run_all_phases(year, month, force)
        sys.exit(0 if success else 1)
        
    except ValueError:
        print("❌ Year and month must be numbers")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Workflow cancelled by user")
        sys.exit(1)