"""
Libya PMM - Food MEB Bar Chart with Transfer Values
Generates 12-month bar chart showing Food MEB for National and Regions with transfer value lines

Reads data from trends JSON file created by query_trends.py

Creates bar chart with:
- National Food MEB (bars)
- East, West, South Food MEB (bars)
- Transfer Value Regular line (370 LYD)
- Transfer Value Emergency line (515 LYD)

Usage:
    python scripts/06_Visualizations/charts/food_meb_tv.py <year> <month>

Example:
    python scripts/06_Visualizations/charts/food_meb_tv.py 2025 11
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
import matplotlib.ticker as mticker
import warnings
from dateutil.relativedelta import relativedelta

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
# STYLING CONFIGURATION
# ============================================================================

# Colors (from specifications)
COLOR_NATIONAL = "#156082"      # Dark blue for National
COLOR_EAST = "#97C1A8"          # Green for East
COLOR_WEST = "#F2AA84"          # Orange for West
COLOR_SOUTH = "#E57373"         # Red for South
COLOR_REGULAR = "#4E95D9"       # Blue for Transfer Value (Regular)
COLOR_EMERGENCY = "#595959"     # Dark gray for Transfer Value (Emergency)
COLOR_TEXT = "#000000"          # Text color

# Transfer values
TRANSFER_VALUE_REGULAR = 370
TRANSFER_VALUE_EMERGENCY = 515

# Bar settings
BAR_WIDTH = 0.7                 # Width of each bar group

# Line settings
LINE_WIDTH = 6.0
LINE_STYLE = "-"

# Font settings
FONT_SIZE = 42
FONT_COLOR = COLOR_TEXT

warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")

# ============================================================================
# FONT: Aptos Narrow from project /fonts
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
# CHART GENERATION
# ============================================================================

def create_food_meb_chart(json_file, year, month):
    """
    Create Food MEB bar chart with transfer value lines from trends JSON
    
    Shows 12-month trend of:
    - National, East, West, South Food MEB (bars)
    - Transfer Value Regular (370 LYD horizontal line)
    - Transfer Value Emergency (515 LYD horizontal line)
    """
    
    # Load trends JSON
    print(f"\nLoading data from: {json_file}")
    with open(json_file, "r") as f:
        data = json.load(f)
    
    # Get target date and calculate 12-month period
    target_date = datetime.fromisoformat(data['metadata']['target_date'])
    start_month = target_date - relativedelta(months=11)
    start_month = start_month.replace(day=1)
    
    # Extract national Food MEB data
    national_dates = pd.to_datetime(data['national']['dates'])
    national_food_meb = pd.Series(data['national']['food_meb'], index=national_dates)
    
    # Extract regional Food MEB data
    regional_data = {}
    for region in ['East', 'West', 'South']:
        if region in data['regional']:
            region_dates = pd.to_datetime(data['regional'][region]['dates'])
            region_food_meb = pd.Series(data['regional'][region]['food_meb'], index=region_dates)
            regional_data[region] = region_food_meb
    
    # Create monthly index for 12 months
    monthly_dates = []
    current = start_month
    for i in range(12):
        monthly_dates.append(current)
        current = current + relativedelta(months=1)
    
    # Align all data to monthly index
    national_values = [national_food_meb.get(pd.Timestamp(d), np.nan) for d in monthly_dates]
    east_values = [regional_data.get('East', pd.Series()).get(pd.Timestamp(d), np.nan) for d in monthly_dates]
    west_values = [regional_data.get('West', pd.Series()).get(pd.Timestamp(d), np.nan) for d in monthly_dates]
    south_values = [regional_data.get('South', pd.Series()).get(pd.Timestamp(d), np.nan) for d in monthly_dates]
    
    print(f"✓ Loaded 12-month data")
    print(f"  Period: {start_month.strftime('%b %Y')} to {target_date.strftime('%b %Y')}")
    print(f"  Latest National Food MEB: {national_values[-1]:.2f} LYD" if not np.isnan(national_values[-1]) else "  Latest: N/A")
    
    # ----------------------------------------------------------------------
    # Plotting
    # ----------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(39, 20))  # Increased width from 40 to 48
    
    # X-axis positions for bars
    x_pos = np.arange(len(monthly_dates))
    bar_width = 0.2  # Width of each individual bar
    
    # Plot bars for each region/national
    bars1 = ax.bar(x_pos - 1.5*bar_width, national_values, bar_width, 
                   label=f'National Food MEB (LYD {national_values[-1]:.2f})', 
                   color=COLOR_NATIONAL, zorder=2)
    bars2 = ax.bar(x_pos - 0.5*bar_width, east_values, bar_width, 
                   label='East', 
                   color=COLOR_EAST, zorder=2)
    bars3 = ax.bar(x_pos + 0.5*bar_width, west_values, bar_width, 
                   label='West', 
                   color=COLOR_WEST, zorder=2)
    bars4 = ax.bar(x_pos + 1.5*bar_width, south_values, bar_width, 
                   label='South', 
                   color=COLOR_SOUTH, zorder=2)
    
    # ========================================================================
    # TRANSFER VALUE LINES - Control line length here
    # ========================================================================
    # Plot transfer value lines (higher zorder to be in front)
    # xmin and xmax control how far the lines extend (0 to 1 = full width)
    # To shorten lines:
    #   - Increase xmin (e.g., 0.05 starts line 5% from left)
    #   - Decrease xmax (e.g., 0.95 ends line 5% from right)
    # Current: xmin=0, xmax=1 (full width)
    
    ax.axhline(y=TRANSFER_VALUE_REGULAR, color=COLOR_REGULAR, 
               linewidth=LINE_WIDTH, linestyle=LINE_STYLE,
               label=f'Transfer Value (Regular)', zorder=5,
               xmin=0.05, xmax=0.95)  # ← CHANGE THESE VALUES (0-1) TO ADJUST LINE LENGTH
    
    ax.axhline(y=TRANSFER_VALUE_EMERGENCY, color=COLOR_EMERGENCY, 
               linewidth=LINE_WIDTH, linestyle=LINE_STYLE,
               label=f'Transfer Value (Emergency)', zorder=5,
               xmin=0.05, xmax=0.95)  # ← CHANGE THESE VALUES (0-1) TO ADJUST LINE LENGTH
    # ========================================================================
    
    # ----------------------------------------------------------------------
    # Axis formatting
    # ----------------------------------------------------------------------
    
    # X-axis: Month labels
    ax.set_xticks(x_pos)
    ax.set_xticklabels([d.strftime("%b") for d in monthly_dates])
    
    # Add padding on x-axis (space before first bar and after last bar)
    ax.set_xlim(-0.6, len(x_pos) - 0.4)  # More padding on left (-0.8 instead of -0.5)
    
    # Y-axis: Dynamic range
    all_values = np.concatenate([national_values, east_values, west_values, south_values])
    all_values = all_values[~np.isnan(all_values)]
    
    if len(all_values) > 0:
        data_min = float(np.min(all_values))
        data_max = float(np.max(all_values))
        
        # Include transfer values in range calculation
        data_min = min(data_min, TRANSFER_VALUE_REGULAR)
        data_max = max(data_max, TRANSFER_VALUE_EMERGENCY)
        
        data_range = data_max - data_min if data_max > data_min else 100
        
        # Add padding
        pad = 0.15 * data_range
        bottom = max(0, data_min - pad)
        top = data_max + pad
        ax.set_ylim(bottom=bottom, top=top)
    
    # Y-axis ticks
    ax.yaxis.set_major_locator(mticker.MultipleLocator(100))
    
    # Space between x-axis and month labels
    ax.tick_params(axis="x", pad=20)
    
    # ========================================================================
    # YEAR LABEL POSITIONING - Adjust these values to change spacing
    # ========================================================================
    # Year labels (bold) under the axis
    y_min, y_max = ax.get_ylim()
    y_range = y_max - y_min if y_max > y_min else 1.0
    
    # This controls vertical distance between x-axis and year labels
    # Increase 0.10 (e.g., to 0.12, 0.15) to move years FURTHER DOWN
    # Decrease 0.10 (e.g., to 0.08, 0.05) to move years CLOSER UP
    year_label_y = y_min - 0.07 * y_range  # ← CHANGE THIS VALUE TO ADJUST SPACING
    # ========================================================================
    
    # Get unique years from the 12-month period
    years_shown = {}
    for i, dt in enumerate(monthly_dates):
        year_dt = dt.year
        if year_dt not in years_shown:
            years_shown[year_dt] = i  # Use x_pos index
    
    # Draw year labels
    for year_dt, idx in years_shown.items():
        ax.text(
            idx,
            year_label_y,
            str(year_dt),
            ha="left",
            va="top",
            fontsize=FONT_SIZE + 6,
            fontweight="bold",
            color=FONT_COLOR,
        )
    
    # End tick markers on x-axis
    xaxis_transform = ax.get_xaxis_transform()
    
    # Left end tick (downward only, at the padding boundary)
    ax.plot(
        [-0.6, -0.6],  # Match the xlim left boundary
        [0, -0.03],
        transform=xaxis_transform,
        color="#D9D9D9",
        linewidth=3,
        clip_on=False,
        zorder=20,
    )
    # Right end tick
    ax.plot(
        [len(x_pos) - 0.4, len(x_pos) - 0.4],  # Match the xlim right boundary
        [0, -0.03],
        transform=xaxis_transform,
        color="#D9D9D9",
        linewidth=3,
        clip_on=False,
        zorder=20,
    )
    
    # Remove axis labels
    ax.set_xlabel("")
    ax.set_ylabel("")
    
    # Styling of spines
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color("#D9D9D9")
    ax.spines["bottom"].set_linewidth(3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    
    # No gridlines
    ax.grid(False)
    
    # Legend - explicitly reorder to: National, East, West, South, Transfer Regular, Transfer Emergency
    # matplotlib may collect them in any order, so we explicitly reorder
    handles, labels = ax.get_legend_handles_labels()
    
    print(f"\n  Original legend order: {labels}")
    
    # Find indices by label content
    national_idx = next(i for i, label in enumerate(labels) if 'National' in label)
    east_idx = next(i for i, label in enumerate(labels) if label == 'East')
    west_idx = next(i for i, label in enumerate(labels) if label == 'West')
    south_idx = next(i for i, label in enumerate(labels) if label == 'South')
    regular_idx = next(i for i, label in enumerate(labels) if 'Regular' in label)
    emergency_idx = next(i for i, label in enumerate(labels) if 'Emergency' in label)
    
    # Reorder
    ordered_handles = [handles[national_idx], handles[east_idx], handles[west_idx], 
                      handles[south_idx], handles[regular_idx], handles[emergency_idx]]
    ordered_labels = [labels[national_idx], labels[east_idx], labels[west_idx], 
                     labels[south_idx], labels[regular_idx], labels[emergency_idx]]
    
    print(f"  Reordered legend: {ordered_labels}")
    
    ax.legend(
        ordered_handles,
        ordered_labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.07),
        ncol=6,  # All 6 items in one row
        frameon=False,
        fontsize=FONT_SIZE + 2,
        labelcolor=FONT_COLOR,
        columnspacing=1.5,  # Reduced from 2.0 to bring items closer
        handletextpad=0.2   # Space between symbol and text
    )
    
    # Extra space for labels
    plt.subplots_adjust(bottom=0.25)
    plt.tight_layout()
    
    # Save to monthly OneDrive folder
    from config import ensure_month_directories
    
    paths = ensure_month_directories(year, month)
    month_tag = datetime(year, month, 1).strftime("%b%y")
    
    output_file = paths['charts'] / f"Food_MEB_TV_{month_tag}.svg"
    
    plt.savefig(output_file, format="svg", bbox_inches="tight", transparent=True)
    plt.close()
    
    print(f"\n✓ Chart saved: {output_file}")
    return output_file

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("FOOD MEB - NATIONAL & REGIONAL WITH TRANSFER VALUES")
    print("=" * 70)
    
    # Get year and month from command line
    if len(sys.argv) < 3:
        print("❌ Usage: python scripts/06_Visualizations/charts/food_meb_tv.py <year> <month>")
        print("   Example: python scripts/06_Visualizations/charts/food_meb_tv.py 2025 11")
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
    
    try:
        create_food_meb_chart(json_file, year, month)
        print("\n" + "=" * 70)
        print("✅ CHART COMPLETE")
        print("=" * 70)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)