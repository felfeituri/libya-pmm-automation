"""
Libya PMM - Copy Previous Month's Report
Copies report files from previous month to current month's Report folder

Usage:
    python scripts/07_Report/copy_previous_report.py <year> <month>

Examples:
    python scripts/07_Report/copy_previous_report.py 2025 12
"""

import sys
from pathlib import Path

# Auto-detect environment and set project root
import os

if os.path.exists('/app'):  # Running in Docker
    PROJECT_ROOT = Path('/app')
else:  # Running locally
    # Script is in scripts/07_Report/
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Add project root to path to import config
sys.path.insert(0, str(PROJECT_ROOT))

from config import copy_previous_month_report, get_month_paths

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Copy previous month's report to current month",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Copy November report to December
  python scripts/07_Report/copy_previous_report.py 2025 12
  
  # Copy December 2024 report to January 2025
  python scripts/07_Report/copy_previous_report.py 2025 1

What this does:
  - Finds report files (.docx, .pdf, .pptx, .xlsx) in previous month's Report folder
  - Copies them to current month's Report folder
  - Won't overwrite existing files
  - Useful for monthly report templates
        """
    )
    
    parser.add_argument('year', type=int, help='Target year (e.g., 2025)')
    parser.add_argument('month', type=int, help='Target month (1-12)')
    
    args = parser.parse_args()
    
    # Validate month
    if not 1 <= args.month <= 12:
        print(f"❌ Error: Month must be between 1 and 12, got {args.month}")
        sys.exit(1)
    
    print("="*70)
    print("COPY PREVIOUS MONTH'S REPORT")
    print("="*70)
    
    # Get current month info
    paths = get_month_paths(args.year, args.month)
    print(f"\nTarget: {paths['month_name']} {args.year}")
    print(f"Report folder: {paths['report']}")
    print()
    
    # Copy report
    try:
        success = copy_previous_month_report(args.year, args.month)
        
        if success:
            print("\n" + "="*70)
            print("✅ REPORT COPY COMPLETE")
            print("="*70)
            print(f"\nYou can now edit the report in:")
            print(f"  {paths['report']}")
            sys.exit(0)
        else:
            print("\n" + "="*70)
            print("ℹ️  NO FILES COPIED")
            print("="*70)
            print("\nEither:")
            print("  - Previous month has no Report folder")
            print("  - Previous month Report folder is empty")
            print("  - All files already exist in current month")
            sys.exit(0)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()