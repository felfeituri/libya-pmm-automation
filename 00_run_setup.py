#!/usr/bin/env python3
"""
Libya PMM - Phase 0: Setup (ONE-TIME)
Creates database schema and downloads Libya boundaries for mapping

This is a ONE-TIME setup script. Run once when initializing the system.

Usage:
    python 00_run_setup.py
    python 00_run_setup.py --skip-boundaries        # Skip boundary download
    python 00_run_setup.py --force-download         # Re-download boundaries even if exist

What it does:
    1. Creates PostgreSQL database schema (7 tables)
       - keys (administrative codes)
       - locations (municipality coordinates)  
       - municipality_meb, regional_meb, national_meb
       - products (commodity prices)
       - exchange_rates
    
    2. Downloads Libya boundaries for map visualization (optional)
       - Fetches ADM2 boundaries from ArcGIS
       - Saves to inputs/libya_boundaries.geojson
       - Required for meb_map.py to work

Note: The schema creation script includes hardcoded INSERT statements
      for keys and locations, so no separate loading scripts are needed.

Prerequisites:
    - PostgreSQL database running (docker-compose up)
    - config.py configured with database credentials
    - Internet connection (for boundary download)
"""

import subprocess
import sys
from pathlib import Path

def run_database_setup(base_dir):
    """Create database schema"""
    
    setup_dir = base_dir / "scripts" / "00_Setup"
    schema_script = setup_dir / "create_database_schema.py"
    
    print("=" * 70)
    print("🗄️  STEP 1: DATABASE SCHEMA")
    print("=" * 70)
    print()
    
    if not schema_script.exists():
        print(f"❌ Script not found: {schema_script}")
        return False
    
    try:
        result = subprocess.run(
            ["python", str(schema_script)],
            cwd=base_dir,
            check=True
        )
        return True
    except subprocess.CalledProcessError:
        print("\n❌ Database schema creation failed")
        return False

def run_boundary_download(base_dir, force_download=False):
    """Download Libya boundaries for mapping"""
    
    setup_dir = base_dir / "scripts" / "00_Setup"
    download_script = setup_dir / "download_libya_boundaries.sh"
    boundary_file = base_dir / "inputs" / "libya_boundaries.geojson"
    
    print()
    print("=" * 70)
    print("🗺️  STEP 2: LIBYA BOUNDARIES (FOR MAPPING)")
    print("=" * 70)
    print()
    
    # Check if already downloaded (unless force)
    if boundary_file.exists() and not force_download:
        file_size = boundary_file.stat().st_size / 1024
        print(f"✓ Libya boundaries already exist!")
        print(f"  Location: {boundary_file}")
        print(f"  Size: {file_size:.1f} KB")
        print()
        print("Skipping download (file already exists)")
        print()
        print("💡 To re-download (if boundaries were updated):")
        print("   python 00_run_setup.py --force-download")
        return True
    
    if force_download and boundary_file.exists():
        print(f"🔄 Force re-download enabled")
        print(f"   Removing existing file: {boundary_file}")
        boundary_file.unlink()
        print()
    
    if not download_script.exists():
        print(f"⚠️  Download script not found: {download_script}")
        print()
        print("You can download boundaries manually later:")
        print("  bash scripts/00_Setup/download_libya_boundaries.sh")
        return True  # Not critical, continue anyway
    
    print("Downloading Libya ADM2 boundaries from ArcGIS...")
    print("(This may take 30 seconds)")
    print()
    
    try:
        result = subprocess.run(
            ["bash", str(download_script)],
            cwd=base_dir,
            check=True
        )
        return True
    except subprocess.CalledProcessError:
        print()
        print("⚠️  Boundary download failed")
        print()
        print("This is not critical - you can download later:")
        print("  bash scripts/00_Setup/download_libya_boundaries.sh")
        print()
        print("Or the map script will fetch boundaries from ArcGIS when needed.")
        return True  # Not critical, continue anyway

def run_setup(skip_boundaries=False, force_download=False):
    """Run complete setup"""
    
    base_dir = Path(__file__).resolve().parent
    
    print("=" * 70)
    print("LIBYA PMM - ONE-TIME SETUP")
    print("=" * 70)
    print()
    
    results = []
    
    # Step 1: Database Schema (required)
    success = run_database_setup(base_dir)
    results.append(("Database Schema", success))
    
    if not success:
        print()
        print("=" * 70)
        print("❌ SETUP FAILED")
        print("=" * 70)
        print()
        print("Database setup is required. Please fix the error and try again.")
        return 1
    
    # Step 2: Libya Boundaries (optional)
    if not skip_boundaries:
        success = run_boundary_download(base_dir, force_download)
        results.append(("Libya Boundaries", success))
    else:
        print()
        print("=" * 70)
        print("⏭️  SKIPPING: LIBYA BOUNDARIES")
        print("=" * 70)
        print()
        print("You can download boundaries later if needed:")
        print("  bash scripts/00_Setup/download_libya_boundaries.sh")
        print("Or run: python 00_run_setup.py --force-download")
    
    # Final Summary
    print()
    print("=" * 70)
    print("✅ SETUP COMPLETE")
    print("=" * 70)
    print()
    
    print("Summary:")
    for step, success in results:
        status = "✅" if success else "⚠️"
        print(f"  {status} {step}")
    
    print()
    print("Database is ready with:")
    print("  • 7 tables created")
    print("  • 25 administrative codes loaded")
    print("  • 21 municipality locations loaded")
    
    if not skip_boundaries:
        boundary_file = base_dir / "inputs" / "libya_boundaries.geojson"
        if boundary_file.exists():
            print("  • Libya boundaries downloaded (for mapping)")
    
    print()
    print("=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print()
    print("1. Export data from MoDa (LOCAL):")
    print("   python 01_run_data_export.py 2025 12 <form_id>")
    print()
    print("2. Fill parallel market data in Excel")
    print()
    print("3. Run monthly workflow (DOCKER):")
    print("   docker exec -it libya_pmm_app python 99_run_all.py 2025 12")
    
    return 0

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Libya PMM one-time setup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Complete setup (database + boundaries)
  python 00_run_setup.py
  
  # Setup database only (skip boundary download)
  python 00_run_setup.py --skip-boundaries
  
  # Re-download boundaries (if updated on ArcGIS)
  python 00_run_setup.py --force-download
  
  # Database + force re-download boundaries
  python 00_run_setup.py --skip-boundaries  # First run
  bash scripts/00_Setup/download_libya_boundaries.sh  # Manual re-download

What gets created:
  1. PostgreSQL database with 7 tables:
     - keys (administrative codes)
     - locations (municipality coordinates)
     - municipality_meb, regional_meb, national_meb
     - products (commodity prices)
     - exchange_rates
  
  2. Libya boundaries file (optional):
     - inputs/libya_boundaries.geojson
     - Used by map visualization script
     - Can be re-downloaded with --force-download

Prerequisites:
  - PostgreSQL running: docker-compose up
  - Internet connection (for boundary download)
        """
    )
    
    parser.add_argument(
        '--skip-boundaries',
        action='store_true',
        help='Skip Libya boundaries download'
    )
    
    parser.add_argument(
        '--force-download',
        action='store_true',
        help='Re-download boundaries even if they exist (useful if boundaries updated)'
    )
    
    args = parser.parse_args()
    
    # Validate flags
    if args.skip_boundaries and args.force_download:
        print("❌ Error: Cannot use --skip-boundaries and --force-download together")
        print()
        print("Choose one:")
        print("  --skip-boundaries   : Don't download boundaries at all")
        print("  --force-download    : Download boundaries (overwrite if exists)")
        sys.exit(1)
    
    try:
        sys.exit(run_setup(args.skip_boundaries, args.force_download))
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)