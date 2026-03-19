#!/usr/bin/env python3
"""
Libya PMM - Phase 6: Visualizations
Generates all charts and map for a specific month

Usage:
    python 06_run_visualizations.py <year> <month>
    python 06_run_visualizations.py <year> <month> --skip-trends

Example:
    python 06_run_visualizations.py 2025 12

What it does:
    1. Query trends from database (creates JSON cache)
    2. Generate 12 charts:
       - National Full MEB (municipality comparison)
       - Regional Food & NFI MEB (East/West/South)
       - Food MEB with Transfer Values
       - Exchange Rate trends
       - FAO Food Price Index
    3. Generate interactive Libya MEB map

Output locations:
    - Charts: Monthly Reports/YYYY/Month/Charts/ (SVG format)
    - Map: Monthly Reports/YYYY/Month/Graphics/Map/ (HTML)
    - Trends JSON: Monthly Reports/YYYY/Month/Data/JSON/

Prerequisites:
    - Database loaded with monthly data
    - Libya boundaries bundled (inputs/libya_boundaries.geojson)
"""

import sys
import subprocess
from pathlib import Path
import argparse

# Get project root
BASE_DIR = Path(__file__).resolve().parent

# Script locations
TRENDS_SCRIPT = BASE_DIR / "scripts" / "06_Visualizations" / "query_trends.py"
CHARTS_DIR = BASE_DIR / "scripts" / "06_Visualizations" / "charts"
MAP_DIR = BASE_DIR / "scripts" / "06_Visualizations" / "map"

def run_script(script_path: Path, year: int, month: int, extra_args: list = None):
    """Run a script with year/month arguments"""
    print(f"\n{'='*70}")
    print(f"🚀 Running: {script_path.relative_to(BASE_DIR)}")
    print(f"{'='*70}")
    
    if not script_path.exists():
        print(f"⚠️ Skipping: {script_path} does not exist")
        return False
    
    # Build command
    cmd = ["python", str(script_path), str(year), str(month)]
    if extra_args:
        cmd.extend(extra_args)
    
    try:
        subprocess.run(cmd, check=True, cwd=BASE_DIR)
        print(f"✅ Success: {script_path.name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed: {script_path.name}")
        print(f"  Error: {e}")
        return False

def run_all_visualizations(year: int, month: int, skip_trends: bool = False):
    """Run all visualization scripts for a specific month"""
    
    print("=" * 70)
    print("LIBYA PMM - VISUALIZATIONS PHASE")
    print("=" * 70)
    print(f"\nTarget: {year}-{month:02d}")
    print(f"Skip trends: {skip_trends}")
    
    results = []
    
    # 1. Query trends (extract data from database)
    if not skip_trends:
        results.append(("Query Trends", run_script(TRENDS_SCRIPT, year, month)))
    else:
        print(f"\n{'='*70}")
        print("⏭️ Skipping query_trends.py (--skip-trends flag)")
        print(f"{'='*70}")
    
    # 2. MEB Charts (each generates both food and nfi)
    meb_charts = [
        ("National Full MEB", CHARTS_DIR / "national_fullmeb_chart.py"),
        ("Regional MEB", CHARTS_DIR / "regional_meb_charts.py"),  # both food & nfi
        ("East MEB", CHARTS_DIR / "east_meb_charts.py"),          # both food & nfi
        ("West MEB", CHARTS_DIR / "west_meb_charts.py"),          # both food & nfi
        ("South MEB", CHARTS_DIR / "south_meb_charts.py"),        # both food & nfi
    ]
    
    for name, script in meb_charts:
        results.append((name, run_script(script, year, month)))
    
    # 3. Other Charts
    other_charts = [
        ("Food MEB + Transfer Values", CHARTS_DIR / "food_meb_tv.py"),
        ("Exchange Rate", CHARTS_DIR / "exchange_rate_chart.py"),
        ("FAO Food Price Index", CHARTS_DIR / "fao_index_chart.py"),
    ]
    
    for name, script in other_charts:
        results.append((name, run_script(script, year, month)))
    
    # 4. Interactive Map
    results.append(("Libya MEB Map", run_script(MAP_DIR / "meb_map.py", year, month)))
    
    # Summary
    print("\n" + "=" * 70)
    print("VISUALIZATIONS SUMMARY")
    print("=" * 70)
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    print(f"\nCompleted: {success_count}/{total_count} scripts")
    print("\nResults:")
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {name}")
    
    print()
    if success_count == total_count:
        print("✅ Visualizations phase complete!")
        print()
        print(f"Next: python 07_run_report.py {year} {month}")
        return 0
    else:
        print(f"⚠️ {total_count - success_count} script(s) failed")
        return 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate all charts and map for a specific month",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate all visualizations for December 2025
  python 06_run_visualizations.py 2025 12
  
  # Skip query_trends if already run
  python 06_run_visualizations.py 2025 12 --skip-trends

Generated Outputs:
  1. Query Trends JSON (cached data)
  2. National Full MEB Chart (municipality comparison)
  3. Regional Food MEB Chart
  4. Regional Non-Food MEB Chart
  5. East Food MEB Chart
  6. East Non-Food MEB Chart
  7. West Food MEB Chart
  8. West Non-Food MEB Chart
  9. South Food MEB Chart
  10. South Non-Food MEB Chart
  11. Food MEB with Transfer Values Chart
  12. Exchange Rate Trend Chart
  13. FAO Food Price Index Chart
  14. Libya MEB Map (interactive HTML)

Total: 12 SVG charts + 1 HTML map

Prerequisites:
  - Database loaded with PMM data for target month
  - Libya boundaries file (inputs/libya_boundaries.geojson)
        """
    )
    
    parser.add_argument('year', type=int, help='Year (e.g., 2025)')
    parser.add_argument('month', type=int, help='Month (1-12)')
    parser.add_argument('--skip-trends', action='store_true',
                       help='Skip query_trends.py if already run')
    
    args = parser.parse_args()
    
    # Validate month
    if not 1 <= args.month <= 12:
        print(f"❌ Error: Month must be between 1 and 12, got {args.month}")
        sys.exit(1)
    
    try:
        sys.exit(run_all_visualizations(args.year, args.month, args.skip_trends))
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)