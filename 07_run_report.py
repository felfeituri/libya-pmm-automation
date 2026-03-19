#!/usr/bin/env python3
"""
Libya PMM - Phase 7: Report
Copies previous month's report files to current month

Usage:
    python 07_run_report.py <year> <month>

Example:
    python 07_run_report.py 2025 12

What it does:
    - Copies report files (.pptx, .docx) from previous month
    - Places them in current month's Report folder
    - Won't overwrite existing files

After running this:
    1. Open the Word file in Monthly Reports/YYYY/Month/Report/
    2. Update with new charts (drag SVG files from Charts/)
    3. Update tables (copy from Excel files in Tables/)
    4. Change month name
    5. Save as new filename

Prerequisites:
    - Previous month has Report folder with files
"""

import subprocess
import sys
from pathlib import Path

def run_report(year: int, month: int):
    """Copy previous month's report"""
    
    BASE_DIR = Path(__file__).resolve().parent
    
    # Call the actual implementation script
    script = BASE_DIR / "scripts" / "07_Report" / "copy_previous_report.py"
    
    if not script.exists():
        print(f"❌ Script not found: {script}")
        return 1
    
    # Run it
    cmd = ["python", str(script), str(year), str(month)]
    
    try:
        result = subprocess.run(cmd, cwd=BASE_DIR, check=True)
        
        print()
        print("=" * 70)
        print("📝 MANUAL STEP: Edit PowerPoint Report")
        print("=" * 70)
        print()
        print("Open the report in Monthly Reports/YYYY/Month/Report/")
        print("and update with new charts and data.")
        
        return 0
        
    except subprocess.CalledProcessError:
        print()
        print("❌ Report copy failed")
        return 1

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python 07_run_report.py <year> <month>")
        print()
        print("Example:")
        print("  python 07_run_report.py 2025 12")
        sys.exit(1)
    
    try:
        year = int(sys.argv[1])
        month = int(sys.argv[2])
        
        if not 1 <= month <= 12:
            print(f"❌ Month must be between 1 and 12, got {month}")
            sys.exit(1)
        
        sys.exit(run_report(year, month))
        
    except ValueError:
        print("❌ Year and month must be numbers")
        sys.exit(1)