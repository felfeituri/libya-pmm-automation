"""
Libya PMM - Central Configuration
Manages all paths for monthly data and project outputs

Usage:
    from config import get_month_paths, PATHS
"""

import os
from pathlib import Path
from datetime import datetime

# ============================================================================
# BASE PATHS
# ============================================================================

# Project Directory
PROJECT_ROOT = Path(__file__).parent

# Monthly Reports root
# Priority:
#   1) MONTHLY_REPORTS_ROOT env var (Docker, other machines, local dev)
#   2) /app/Monthly Reports (inside container)
env_monthly_root = os.getenv("MONTHLY_REPORTS_ROOT")

if env_monthly_root:
    MONTHLY_REPORTS_ROOT = Path(env_monthly_root)
elif os.path.exists("/app/Monthly Reports"):
    MONTHLY_REPORTS_ROOT = Path("/app/Monthly Reports")
else:
    raise EnvironmentError(
        "MONTHLY_REPORTS_ROOT is not set. "
        "Set it in your .env file (see .env.example)."
    )

# DataBridges base
# Priority:
#   1) DATABRIDGES_BASE env var
#   2) /app/DataBridges (inside container)
env_databridges_base = os.getenv("DATABRIDGES_BASE")

if env_databridges_base:
    DATABRIDGES_BASE = Path(env_databridges_base)
elif os.path.exists("/app/DataBridges"):
    DATABRIDGES_BASE = Path("/app/DataBridges")
else:
    raise EnvironmentError(
        "DATABRIDGES_BASE is not set. "
        "Set it in your .env file (see .env.example)."
    )

# Master Data base (shared OneDrive - for master files accessible to team)
# Priority:
#   1) MASTER_DATA_BASE env var
#   2) /app/Master Data (inside container)
env_master_data_base = os.getenv("MASTER_DATA_BASE")

if env_master_data_base:
    MASTER_DATA_BASE = Path(env_master_data_base)
elif os.path.exists("/app/Master Data"):
    MASTER_DATA_BASE = Path("/app/Master Data")
else:
    raise EnvironmentError(
        "MASTER_DATA_BASE is not set. "
        "Set it in your .env file (see .env.example)."
    )

# ============================================================================
# MODA API CONFIGURATION
# ============================================================================

# Path to MoDa API .env file containing MODA_TOKEN
# 
# The .env file should contain one line:
#   MODA_TOKEN=your_moda_api_token_here
#
# You can store this file anywhere you want. The config looks for it in 3 places:
#
# Option 1: Set MODA_ENV_PATH environment variable (most flexible)
#    Example: export MODA_ENV_PATH="/Users/yourname/Documents/moda_api.env"
#    Add to ~/.zshrc or ~/.bashrc to make it permanent
#
# Option 2: Put .env file in project root folder
#    Libya PMM Automation Pipeline/.env
#
# Option 3: Edit the fallback path below to point to your .env file location
#    Change the path to wherever you stored your .env file
#
# IMPORTANT: 
# - Each person has their own unique MoDa API token
# - Keep your token secure (don't share it or commit to Git)
# - The .env file is ignored by Git (see .gitignore)

env_moda_path = os.getenv("MODA_ENV_PATH")

if env_moda_path:
    # Option 1: Environment variable (if set)
    MODA_ENV_PATH = Path(env_moda_path)
elif (PROJECT_ROOT / ".env").exists():
    # Option 2: Project root .env (if it exists)
    MODA_ENV_PATH = PROJECT_ROOT / ".env"
else:
    # Option 3: No .env found — user must configure one
    raise EnvironmentError(
        "MoDa API .env file not found. Either:\n"
        "  1) Set MODA_ENV_PATH env var pointing to your .env file, or\n"
        "  2) Place a .env file in the project root with MODA_TOKEN=your_token\n"
        "See .env.example for details."
    )

MODA_API_BASE = "https://api.moda.wfp.org/api/v1"

# ============================================================================
# PROJECT PATHS
# ============================================================================

PATHS = {
    # Base
    "project": PROJECT_ROOT,

    # Master files (saved to shared OneDrive for team access)
    "master_data": MASTER_DATA_BASE / "MEB",
    "exchange_rate_working": MASTER_DATA_BASE / "Exchange Rate",

    # Inputs (FAO data, historical exchange rates, etc.)
    "inputs": PROJECT_ROOT / "inputs",
    "fonts": PROJECT_ROOT / "fonts",
    # Note: No shapefiles folder - maps use ArcGIS REST API instead
}

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", ""),
    "user": os.getenv("DB_USER", ""),
    "password": os.getenv("DB_PASSWORD", ""),
}


def get_engine():
    """
    Create SQLAlchemy engine for database connections

    Returns:
        SQLAlchemy engine object
    """
    from sqlalchemy import create_engine

    connection_string = (
        f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
        f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    )
    return create_engine(connection_string)

# ============================================================================
# MONTH-SPECIFIC PATHS
# ============================================================================


def get_month_paths(year: int, month: int) -> dict:
    """
    Get all paths for a specific month

    Args:
        year: Year (e.g., 2025)
        month: Month (1-12)

    Returns:
        Dictionary with all paths for that month
    """

    date = datetime(year, month, 1)
    month_name = date.strftime("%B")   # "November"
    month_tag = date.strftime("%b%y")  # "Nov25"

    # Month root folder
    month_root = MONTHLY_REPORTS_ROOT / str(year) / month_name

    return {
        # Main folder paths
        "root": month_root,
        "data": month_root / "Data",
        "raw": month_root / "Data" / "Raw",
        "json": month_root / "Data" / "JSON",  # Trends JSON data
        "analysis": month_root / "Analysis",
        "progress": month_root / "Progress",
        "qaqc": month_root / "QAQC",
        "tables": month_root / "Tables",
        "report": month_root / "Report",  # Monthly report folder
        "exchange_rate": month_root / "Exchange Rate",
        "graphics": month_root / "Graphics",
        "charts": month_root / "Graphics" / "Charts",
        "map": month_root / "Graphics" / "Map",

        # Specific data files
        "raw_data": month_root / "Data" / "Raw" / f"PMM_{month_tag}_Codes.xlsx",
        "raw_codes": month_root / "Data" / "Raw" / f"PMM_{month_tag}_Codes.xlsx",
        "raw_labels": month_root / "Data" / "Raw" / f"PMM_{month_tag}_Labels.xlsx",
        "trends_json": month_root / "Data" / "JSON" / f"trends_{month_tag}.json",  # Trends data
        "analysis_file": month_root / "Analysis" / f"MEB_Analysis_{month_tag}.xlsx",

        # QA/QC output files
        "followup": month_root / "QAQC" / f"FollowUp_{month_tag}.xlsx",
        "missing_prices": month_root / "QAQC" / f"Missing_Prices_{month_tag}.xlsx",

        # Monthly table files
        "meb_comparison": month_root / "Tables" / f"MEB_Comparison_{month_tag}.xlsx",
        "commodity_comparison": month_root / "Tables" / f"Commodity_Price_Comparison_{month_tag}.xlsx",
        "geopoints": month_root / "Tables" / f"Geopoints_MEB_{month_tag}.csv",

        # Monthly exchange rate file
        "exchange_rate_monthly": month_root / "Exchange Rate" / f"Exchange_Rate_{month_tag}.xlsx",

        # Metadata
        "year": year,
        "month": month,
        "month_name": month_name,
        "month_tag": month_tag,
        "date": date,
    }

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def ensure_month_directories(year: int, month: int) -> dict:
    """Create all directories for a specific month if they don't exist"""
    paths = get_month_paths(year, month)

    # Create monthly folders (under Monthly Reports only)
    paths["raw"].mkdir(parents=True, exist_ok=True)
    paths["json"].mkdir(parents=True, exist_ok=True)  # Trends JSON folder
    paths["analysis"].mkdir(parents=True, exist_ok=True)
    paths["progress"].mkdir(parents=True, exist_ok=True)
    paths["qaqc"].mkdir(parents=True, exist_ok=True)  # QAQC folder
    paths["tables"].mkdir(parents=True, exist_ok=True)
    paths["report"].mkdir(parents=True, exist_ok=True)  # Report folder
    paths["exchange_rate"].mkdir(parents=True, exist_ok=True)
    paths["charts"].mkdir(parents=True, exist_ok=True)
    paths["map"].mkdir(parents=True, exist_ok=True)

    # NOTE: DataBridges folders are NOT created here
    # DataBridges uses static paths (Exchange Rates/, Prices/)
    # not year-based folders

    return paths


def copy_previous_month_report(year: int, month: int) -> bool:
    """
    Copy the previous month's report to the current month's Report folder
    Updates filename and document properties (for .docx files) to match new month
    
    Args:
        year: Current year
        month: Current month
        
    Returns:
        True if report was copied, False if no previous report found
    """
    import shutil
    
    # Get current month paths
    current_paths = get_month_paths(year, month)
    current_month_name = current_paths['month_name']
    
    # Ensure Report folder exists
    current_paths["report"].mkdir(parents=True, exist_ok=True)
    
    # Calculate previous month
    if month == 1:
        prev_year = year - 1
        prev_month = 12
    else:
        prev_year = year
        prev_month = month - 1
    
    # Get previous month paths
    prev_paths = get_month_paths(prev_year, prev_month)
    prev_month_name = prev_paths['month_name']
    
    # Check if previous month's Report folder exists
    if not prev_paths["report"].exists():
        print(f"ℹ️  No Report folder found for {prev_month_name} {prev_year}")
        return False
    
    # Find report files in previous month (look for .docx, .pptx only)
    report_extensions = ['.docx', '.pptx']
    report_files = []
    
    for ext in report_extensions:
        report_files.extend(list(prev_paths["report"].glob(f'*{ext}')))
    
    if not report_files:
        print(f"ℹ️  No report files found in {prev_month_name} {prev_year} Report folder")
        return False
    
    # Copy all report files to current month
    copied_count = 0
    for report_file in report_files:
        # Update filename to current month/year
        new_filename = report_file.name
        
        # Replace previous month name with current month name
        new_filename = new_filename.replace(prev_month_name, current_month_name)
        
        # Replace previous year with current year (if different)
        if prev_year != year:
            new_filename = new_filename.replace(str(prev_year), str(year))
        
        dest_file = current_paths["report"] / new_filename
        
        # Only copy if destination doesn't exist (don't overwrite)
        if not dest_file.exists():
            shutil.copy2(report_file, dest_file)
            
            # If it's a .docx file, update document properties
            if dest_file.suffix.lower() == '.docx':
                try:
                    from docx import Document
                    
                    # Open the copied document
                    doc = Document(dest_file)
                    
                    # Update core properties
                    core_props = doc.core_properties
                    
                    # Update subject (change month and year)
                    if core_props.subject:
                        # Replace previous month/year with current in subject
                        new_subject = core_props.subject
                        new_subject = new_subject.replace(prev_month_name, current_month_name)
                        if prev_year != year:
                            new_subject = new_subject.replace(str(prev_year), str(year))
                        core_props.subject = new_subject
                    else:
                        # If no subject, set it to current month/year
                        core_props.subject = f"{current_month_name} {year}"
                    
                    # Save the updated document
                    doc.save(dest_file)
                    
                    print(f"✓ Copied & updated: {new_filename}")
                    print(f"  - Document subject: {core_props.subject}")
                    
                except ImportError:
                    print(f"✓ Copied: {new_filename} (install python-docx to update properties)")
                except Exception as e:
                    print(f"✓ Copied: {new_filename} (couldn't update properties: {e})")
            else:
                print(f"✓ Copied: {new_filename}")
            
            copied_count += 1
        else:
            print(f"⊘ Skipped (already exists): {new_filename}")
    
    if copied_count > 0:
        print(f"\n✅ Copied {copied_count} file(s) from {prev_month_name} {prev_year}")
        return True
    else:
        print(f"\nℹ️  No new files to copy from {prev_month_name} {prev_year}")
        return False


def ensure_output_directories():
    """Create all output directories if they don't exist"""
    # All outputs go to OneDrive (Monthly Reports, DataBridges, Master Data)
    # Create OneDrive Master Data folders (shared with team)
    PATHS["master_data"].mkdir(parents=True, exist_ok=True)
    PATHS["exchange_rate_working"].mkdir(parents=True, exist_ok=True)
    PATHS["inputs"].mkdir(parents=True, exist_ok=True)
    PATHS["fonts"].mkdir(parents=True, exist_ok=True)
    
    # Note: Shapefiles folder not needed - maps use ArcGIS REST API


def print_config():
    """Print current configuration (useful for debugging)"""
    print("=" * 70)
    print("LIBYA PMM - CONFIGURATION")
    print("=" * 70)

    print("\nBase Paths:")
    print(f"  Monthly Reports: {MONTHLY_REPORTS_ROOT}")
    print(f"  DataBridges:     {DATABRIDGES_BASE}")
    print(f"  Master Data:     {MASTER_DATA_BASE}")
    print(f"  Project Root:    {PROJECT_ROOT}")

    print("\nMoDa API:")
    print(f"  .env file:       {MODA_ENV_PATH}")
    print(f"  API Base:        {MODA_API_BASE}")
    print(f"  .env exists:     {MODA_ENV_PATH.exists()}")

    print("\nMaster Files (OneDrive - Shared with Team):")
    print(f"  MEB Master Data: {PATHS['master_data']}")
    print(f"  Exchange Rate:   {PATHS['exchange_rate_working']}")

    print("\nDatabase:")
    print(f"  Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"  Database: {DB_CONFIG['database']}")

    print("\nExample - October 2025 paths:")
    paths = get_month_paths(2025, 10)
    print(f"  Raw data:        {paths['raw_data']}")
    print(f"  Trends JSON:     {paths['trends_json']}")
    print(f"  Analysis:        {paths['analysis_file']}")
    print(f"  QAQC folder:     {paths['qaqc']}")
    print(f"  Report folder:   {paths['report']}")
    print(f"  Tables folder:   {paths['tables']}")
    print(f"  Charts folder:   {paths['charts']}")
    print(f"  Map folder:      {paths['map']}")
    print(f"  MEB Comparison:  {paths['meb_comparison']}")

    print("=" * 70)

# ============================================================================
# INITIALIZATION
# ============================================================================

# Create output directories when config is imported
ensure_output_directories()

if __name__ == "__main__":
    print_config()