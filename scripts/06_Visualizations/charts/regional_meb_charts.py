"""
Libya PMM - Regional Food & NFI MEB Charts (Gap Linked)
Shows East, West, South regions with National comparison

Gap behaviour:
- X-axis always shows the last 12 months (including months with no data).
- Lines break over missing months (NaNs).
- Faint connector segments are drawn across gaps between the last month
  before the gap and the first month after it for each region and the
  national line.

Styling:
- East: Green (#9BC5AC)  - Solid
- West: Orange (#FBB189) - Solid
- South: Red (#EA8C8C)   - Solid
- National: Blue (#73B4E0) - Dashed
- Font: Aptos Narrow, 36pt
- Lines: 10pt for all

Usage:
    python scripts/06_Visualizations/charts/regional_meb_charts.py <year> <month>

Examples:
    python scripts/06_Visualizations/charts/regional_meb_charts.py 2025 11
    python scripts/06_Visualizations/charts/regional_meb_charts.py 2025 11 --type food
    python scripts/06_Visualizations/charts/regional_meb_charts.py 2025 11 --type nfi
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib
import matplotlib.font_manager as fm
import warnings

# Auto-detect environment and set project root
if os.path.exists('/app'):  # Running in Docker
    PROJECT_ROOT = Path('/app')
else:  # Running locally
    # Script is in scripts/06_Visualizations/charts/
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Add project root to path to import config
sys.path.insert(0, str(PROJECT_ROOT))

from config import get_month_paths

# ============================================================================
# MUNICIPALITY NAME MAPPING
# ============================================================================

def fix_municipality_names(municipality_name):
    """Fix municipality names to official spellings"""
    name_mapping = {
        'Ejdabia': 'Ajdabiya',
        'Tripoli Center': 'Tripoli'
    }
    return name_mapping.get(municipality_name, municipality_name)

# ============================================================================
# STYLING CONFIGURATION
# ============================================================================

# Colors
COLOR_EAST = "#9BC5AC"      # Green
COLOR_WEST = "#FBB189"      # Orange
COLOR_SOUTH = "#EA8C8C"     # Red
COLOR_NATIONAL = "#73B4E0"  # Blue (same as national chart)
COLOR_TEXT = "#000000"      # Text color

# Line styles
LINE_WIDTH = 10             # All lines same width
LINE_STYLE_REGIONAL = "-"   # Solid for regions
LINE_STYLE_NATIONAL = "--"  # Dashed for national

# Connector transparency
CONNECTOR_ALPHA = 0.2       # 80% transparent

# Font settings
FONT_SIZE = 42
FONT_COLOR = COLOR_TEXT

warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")

# ============================================================================
# FONT: Aptos Narrow
# ============================================================================

# PROJECT_ROOT already defined at top of file
APTOS_FONT_FILE = PROJECT_ROOT / "fonts" / "Aptos-Narrow.ttf"
APTOS_FONT_BOLD = PROJECT_ROOT / "fonts" / "Aptos-Narrow-Bold.ttf"

if not APTOS_FONT_FILE.exists():
    raise FileNotFoundError(
        f"Aptos Narrow font file not found at: {APTOS_FONT_FILE}\n"
        "Make sure fonts/Aptos-Narrow.ttf exists in the project."
    )

if not APTOS_FONT_BOLD.exists():
    raise FileNotFoundError(
        f"Aptos Narrow Bold font file not found at: {APTOS_FONT_BOLD}\n"
        "Make sure fonts/Aptos-Narrow-Bold.ttf exists in the project."
    )

# Load both regular and bold fonts
fm.fontManager.addfont(str(APTOS_FONT_FILE))
fm.fontManager.addfont(str(APTOS_FONT_BOLD))
font_props = fm.FontProperties(fname=str(APTOS_FONT_FILE))
font_name = font_props.get_name()

matplotlib.rcParams["font.family"] = font_name
plt.rcParams["font.size"] = FONT_SIZE
plt.rcParams["text.color"] = FONT_COLOR
plt.rcParams["axes.labelcolor"] = FONT_COLOR
plt.rcParams["xtick.color"] = FONT_COLOR
plt.rcParams["ytick.color"] = FONT_COLOR

# ============================================================================
# DATA PREPARATION
# ============================================================================

def prepare_regional_data(data, meb_type="food_meb", months_back=12):
    """
    Prepare regional and national data for charting.
    Builds a continuous 12-month index ending at metadata.target_date,
    so missing months still appear on the x-axis as gaps.

    meb_type: 'food_meb' or 'nfi_meb'
    """
    # Continuous monthly index like the national chart
    target_date = datetime.fromisoformat(data["metadata"]["target_date"]).date()
    last_date = pd.to_datetime(target_date)
    last_month_start = last_date.replace(day=1)

    monthly_index = pd.date_range(
        end=last_month_start,
        periods=months_back,
        freq="MS"          # Month Start
    )

    # -------- National data --------
    nat_dates = pd.to_datetime(data["national"]["dates"])
    nat_months = nat_dates.to_period("M").to_timestamp()  # month start

    nat_series_raw = pd.Series(data["national"][meb_type], index=nat_months)
    nat_series = nat_series_raw.groupby(nat_series_raw.index).mean()
    national_values = nat_series.reindex(monthly_index)

    # -------- Regional data --------
    regional_data = {}
    for region in ["East", "West", "South"]:
        reg_dates = pd.to_datetime(data["regional"][region]["dates"])
        reg_months = reg_dates.to_period("M").to_timestamp()

        reg_series_raw = pd.Series(data["regional"][region][meb_type], index=reg_months)
        reg_series = reg_series_raw.groupby(reg_series_raw.index).mean()

        # Reindex to same 12-month window
        regional_data[region] = reg_series.reindex(monthly_index)

    return monthly_index, national_values, regional_data

# ============================================================================
# GAP DETECTION
# ============================================================================

def find_gap_segments(monthly_index, regional_data):
    """
    Find gap segments where ALL regions have NaN for that month.
    Returns a list of (pre_gap_date, post_gap_date) pairs.
    """
    # Combine regional series into a DataFrame
    df = pd.DataFrame({
        "East": regional_data["East"],
        "West": regional_data["West"],
        "South": regional_data["South"],
    })

    gap_mask = df.isna().all(axis=1)
    dates = list(monthly_index)

    segments = []
    in_gap = False
    gap_start_idx = None

    for i, (dt, is_gap) in enumerate(zip(dates, gap_mask)):
        if is_gap and not in_gap:
            in_gap = True
            gap_start_idx = i
        elif not is_gap and in_gap:
            # Gap ended just before i
            in_gap = False
            pre_idx = gap_start_idx - 1
            post_idx = i
            if pre_idx >= 0 and post_idx < len(dates):
                segments.append((dates[pre_idx], dates[post_idx]))

    return segments

# ============================================================================
# CHART GENERATION (GAP-LINKED)
# ============================================================================

def create_regional_meb_chart_gaplinked(
    data,
    meb_type="food_meb",
    year=None,
    month=None,
):
    """
    Create regional Food or NFI MEB comparison chart (gap-linked).
    meb_type: 'food_meb' or 'nfi_meb'
    """

    # Prepare data
    monthly_index, national_values, regional_data = prepare_regional_data(
        data, meb_type
    )

    # Detect gap segments
    gap_segments = find_gap_segments(monthly_index, regional_data)

    # Latest non-NaN values for legend labels
    latest_national = national_values.dropna().iloc[-1] if not national_values.dropna().empty else np.nan
    latest_east     = regional_data["East"].dropna().iloc[-1]  if not regional_data["East"].dropna().empty  else np.nan
    latest_west     = regional_data["West"].dropna().iloc[-1]  if not regional_data["West"].dropna().empty  else np.nan
    latest_south    = regional_data["South"].dropna().iloc[-1] if not regional_data["South"].dropna().empty else np.nan

    meb_label = "Food" if meb_type == "food_meb" else "Non-Food"

    print(f"\n{meb_label} MEB (Gap-Linked) - Latest Values:")
    print(f"  National: {latest_national:.2f} LYD")
    print(f"  East:     {latest_east:.2f} LYD")
    print(f"  West:     {latest_west:.2f} LYD")
    print(f"  South:    {latest_south:.2f} LYD")

    # ---------------- Figure & main lines ----------------
    fig, ax = plt.subplots(figsize=(34, 18))

    # Regional lines (solid)
    ax.plot(
        monthly_index,
        regional_data["East"],
        color=COLOR_EAST,
        linewidth=LINE_WIDTH,
        linestyle=LINE_STYLE_REGIONAL,
        label="East",
        zorder=2,
    )
    ax.plot(
        monthly_index,
        regional_data["West"],
        color=COLOR_WEST,
        linewidth=LINE_WIDTH,
        linestyle=LINE_STYLE_REGIONAL,
        label="West",
        zorder=2,
    )
    ax.plot(
        monthly_index,
        regional_data["South"],
        color=COLOR_SOUTH,
        linewidth=LINE_WIDTH,
        linestyle=LINE_STYLE_REGIONAL,
        label="South",
        zorder=2,
    )

    # National line (dashed) — label includes value
    ax.plot(
        monthly_index,
        national_values,
        color=COLOR_NATIONAL,
        linewidth=LINE_WIDTH,
        linestyle=LINE_STYLE_NATIONAL,
        label=f"National {meb_label} MEB (LYD {latest_national:,.2f})",
        zorder=3,
    )

    # ---------------- Gap connectors ----------------
    for pre_date, post_date in gap_segments:

        # Regions (dashed connectors, faded)
        for region, color in [
            ("East", COLOR_EAST),
            ("West", COLOR_WEST),
            ("South", COLOR_SOUTH),
        ]:
            y1 = regional_data[region].loc[pre_date]
            y2 = regional_data[region].loc[post_date]
            if np.isnan(y1) or np.isnan(y2):
                continue

            ax.plot(
                [pre_date, post_date],
                [y1, y2],
                color=color,
                linestyle="-",
                linewidth=LINE_WIDTH,
                alpha=CONNECTOR_ALPHA,
                zorder=1.5,
            )

        # National connector (blue, dashed, faded)
        y1_nat = national_values.loc[pre_date]
        y2_nat = national_values.loc[post_date]
        if not (np.isnan(y1_nat) or np.isnan(y2_nat)):
            ax.plot(
                [pre_date, post_date],
                [y1_nat, y2_nat],
                color=COLOR_NATIONAL,
                linestyle="--",
                linewidth=LINE_WIDTH,
                alpha=CONNECTOR_ALPHA,
                zorder=2.5,
            )

    # ---------------- Axis formatting ----------------
    # X-axis ticks (12 months)
    ax.set_xticks(monthly_index)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))

    # Horizontal padding like the national chart
    if len(monthly_index) > 1:
        step = monthly_index[1] - monthly_index[0]
    else:
        step = pd.Timedelta(days=30)

    xmin = monthly_index[0] - 0.3 * step
    xmax = monthly_index[-1] + 0.3 * step
    ax.set_xlim(xmin, xmax)

    # Automatic vertical padding
    ax.relim()
    ax.autoscale_view()

    y_min, y_max = ax.get_ylim()
    y_range = y_max - y_min if y_max > y_min else 1.0

    ax.set_ylim(top=y_max + 0.10 * y_range)   # Increase space above top trend line

    floor = y_min - 0.10 * y_range
    floor = max(0, floor)
    ax.set_ylim(bottom=floor)

    # Recompute for label placement
    y_min, y_max = ax.get_ylim()
    y_range = y_max - y_min

    # Month label spacing
    ax.tick_params(axis="x", pad=22)

    # Year labels
    years_shown = {}
    for dt in monthly_index:
        year_dt = dt.year
        if year_dt not in years_shown:
            years_shown[year_dt] = dt

    year_label_y = y_min - 0.10 * y_range

    # End ticks
    xaxis_transform = ax.get_xaxis_transform()
    ax.plot(
        [xmin, xmin],
        [0, -0.035],
        transform=xaxis_transform,
        color="#D9D9D9",
        linewidth=3,
        clip_on=False,
        zorder=20,
    )
    ax.plot(
        [xmax, xmax],
        [0, -0.035],
        transform=xaxis_transform,
        color="#D9D9D9",
        linewidth=3,
        clip_on=False,
        zorder=20,
    )

    # Draw year labels
    for year_dt, dt in years_shown.items():
        ax.text(
            dt,
            year_label_y,
            str(year_dt),
            ha="left",
            va="top",
            fontsize=FONT_SIZE + 6,
            fontweight="bold",
            color=FONT_COLOR,
        )

    # Axis styling
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.spines["left"].set_visible(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color("#D9D9D9")
    ax.spines["bottom"].set_linewidth(3)
    ax.grid(False)

    # Legend
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, 1.12),
        ncol=4,
        frameon=False,
        fontsize=FONT_SIZE + 4,
        labelcolor=FONT_COLOR,
        handlelength=3,
        handletextpad=0.4
    )

    plt.subplots_adjust(bottom=0.25)
    plt.tight_layout()

    # Save to monthly OneDrive folder (config already in path)
    from config import ensure_month_directories
    
    paths = ensure_month_directories(year, month)
    month_tag = datetime(year, month, 1).strftime("%b%y")
    
    chart_name = f"Regional_{meb_label}_MEB_{month_tag}.svg"
    output_file = paths['charts'] / chart_name

    plt.savefig(output_file, format="svg", bbox_inches="tight", transparent=True)
    plt.close()

    print(f"✓ Gap-linked chart saved: {output_file}")
    return output_file

# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("REGIONAL FOOD & NFI MEB COMPARISON CHARTS (GAP-LINKED)")
    print("=" * 70)

    # Get year and month from command line
    if len(sys.argv) < 3:
        print("❌ Usage: python scripts/06_Visualizations/charts/regional_meb_charts.py <year> <month>")
        print("   Example: python scripts/06_Visualizations/charts/regional_meb_charts.py 2025 11")
        print("   Optional: --type food|nfi (default: both)")
        sys.exit(1)
    
    year = int(sys.argv[1])
    month = int(sys.argv[2])

    # Get JSON file from config paths
    paths = get_month_paths(year, month)
    json_file = paths['trends_json']
    
    if not json_file.exists():
        print(f"❌ Trends JSON not found: {json_file}")
        print("   Run query_trends.py first!")
        sys.exit(1)

    print(f"\nUsing: {json_file}")

    # Load data
    with open(json_file, "r") as f:
        data = json.load(f)

    # Determine which charts to generate
    chart_type = "both"
    if "--type" in sys.argv:
        idx = sys.argv.index("--type")
        if idx + 1 < len(sys.argv):
            chart_type = sys.argv[idx + 1].lower()

    try:
        generated_files = []

        if chart_type in ["both", "food"]:
            print("\n" + "-" * 70)
            print("Generating Food MEB Chart (Gap-Linked)...")
            print("-" * 70)
            file = create_regional_meb_chart_gaplinked(data, "food_meb", year, month)
            generated_files.append(file)

        if chart_type in ["both", "nfi"]:
            print("\n" + "-" * 70)
            print("Generating NFI MEB Chart (Gap-Linked)...")
            print("-" * 70)
            file = create_regional_meb_chart_gaplinked(data, "nfi_meb", year, month)
            generated_files.append(file)

        print("\n" + "=" * 70)
        print("✅ GAP-LINKED REGIONAL CHART GENERATION COMPLETE")
        print("=" * 70)
        print(f"\nGenerated {len(generated_files)} chart(s):")
        for f in generated_files:
            print(f"  - {f.name}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()