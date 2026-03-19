"""
Libya PMM - Export PMM Data from MoDa API
Downloads monthly PMM coded data and saves to OneDrive

Exports:
  PMM_<MonYY>_Codes.xlsx  - Raw coded values for analysis

Usage:
    python scripts/01_Data_Export/export_pmm_data.py <year> <month> <form_id>

Example:
    python scripts/01_Data_Export/export_pmm_data.py 2025 11 329382
"""

import os
import sys
from pathlib import Path

# Auto-detect environment and set project root
if os.path.exists('/app'):  # Running in Docker
    PROJECT_ROOT = Path('/app')
else:  # Running locally
    # Script is in scripts/01_Data_Export/
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Add project root to path to import config
sys.path.insert(0, str(PROJECT_ROOT))

import requests
from dotenv import load_dotenv
from config import get_month_paths, ensure_month_directories, MODA_ENV_PATH, MODA_API_BASE

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def export_pmm_data(year: int, month: int, form_id: int):
    """
    Export PMM coded data from MoDa API
    
    Downloads one Excel file:
      PMM_<MonYY>_Codes.xlsx - Raw coded values for analysis
    
    Args:
        year: Year (e.g., 2025)
        month: Month (1-12)
        form_id: MoDa form ID for this round
    """
    
    print("="*70)
    print("LIBYA PMM - MODA DATA EXPORT")
    print("="*70)
    
    # Get month paths and create directories
    paths = ensure_month_directories(year, month)
    
    print(f"\nExporting data for: {paths['month_name']} {year}")
    print(f"Month tag: {paths['month_tag']}")
    print(f"Form ID: {form_id}")
    
    # Check if folder was created or already exists
    if paths['raw'].exists():
        print(f"\nFolder: {paths['raw']}")
    
    # Load API token
    loaded = load_dotenv(MODA_ENV_PATH)
    TOKEN = os.getenv("MODA_TOKEN")
    
    if not loaded or not TOKEN:
        raise RuntimeError(
            f"Could not read MODA_TOKEN from {MODA_ENV_PATH}. "
            "Please confirm the .env path and that it contains: MODA_TOKEN=your_token"
        )
    
    # API setup
    headers = {"Authorization": f"Token {TOKEN}"}
    url = f"{MODA_API_BASE}/data/{form_id}.xlsx"
    
    def fetch_and_save(params: dict, out_path) -> None:
        r = requests.get(url, headers=headers, params=params, timeout=180)
        r.raise_for_status()
        out_path.write_bytes(r.content)
        print(f"  ✓ Saved: {out_path.name}")
    
    # Export labeled data (human-readable with question and choice labels)
    # Uncomment below to also export labeled version:
    # print("\n1. Exporting labeled data (human-readable)...")
    # label_params = {
    #     "remove_group_name": "true",
    #     "include_labels_only": "true",
    #     "show_choice_labels": "true",
    #     "language": "English",
    # }
    # fetch_and_save(label_params, paths['raw_labels'])
    
    # Export coded data (raw values for analysis)
    print("\nExporting coded data (raw values)...")
    code_params = {
        "remove_group_name": "true",
        "include_labels_only": "false",
        "show_choice_labels": "false",
        "language": "English",
    }
    fetch_and_save(code_params, paths['raw_codes'])
    
    print("\n" + "="*70)
    print("EXPORT COMPLETE")
    print("="*70)
    print(f"\n✓ File saved:")
    print(f"  {paths['raw_codes'].name} (coded - for analysis)")
    print(f"\n📂 Location: {paths['raw']}")
    print(f"\n📝 Next step: Run QA/QC validation")
    
    return True

# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Export PMM coded data from MoDa API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
    Examples:
    # Export November 2025 data with form ID 329382
    python export_pmm_data.py 2025 11 329382
    
    # This will create ONE file:
    #   PMM_Nov25_Codes.xlsx  (coded values for analysis)
    
    # Export October 2025 data
    python export_pmm_data.py 2025 10 329100

    Output Location:
    Monthly Reports/<Year>/<Month>/Data/Raw/
    Example: Monthly Reports/2025/November/Data/Raw/
        - PMM_Nov25_Codes.xlsx
        """
    )
    
    parser.add_argument('year', type=int, help='Year (e.g., 2025)')
    parser.add_argument('month', type=int, help='Month (1-12)')
    parser.add_argument('form_id', type=int, help='MoDa form ID')
    
    args = parser.parse_args()
    
    # Validate month
    if not 1 <= args.month <= 12:
        print(f"Error: Month must be between 1 and 12, got {args.month}")
        sys.exit(1)
    
    try:
        success = export_pmm_data(args.year, args.month, args.form_id)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)