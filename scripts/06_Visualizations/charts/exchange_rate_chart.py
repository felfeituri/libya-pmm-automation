"""
Libya PMM - Exchange Rate Trend Chart
Generates 12-month trend chart showing official, official+tax, and parallel market rates

Reads data from trends JSON file created by query_trends.py

Creates line chart with:
- USD/LYD (official rate) - Yellow/Gold
- USD/LYD + Gov Tax (official rate with 20% tax) - Orange  
- Parallel Market (black market rate) - Dark Gray/Black

Usage:
    python scripts/06_Visualizations/charts/exchange_rate_chart.py <year> <month>

Examples:
    python scripts/06_Visualizations/charts/exchange_rate_chart.py 2025 11
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

# Colors (matching your specifications)
COLOR_OFFICIAL = "#EACB76"      # Light Gold/Yellow for Official USD/LYD
COLOR_TAX = "#E46C0A"           # Orange for Official + Gov Tax
COLOR_PARALLEL = "#404040"      # Dark gray for Parallel Market
COLOR_TEXT = "#000000"          # Text color

# Line styles and thickness
LINE_WIDTH = 5.0                # Line thickness
LINE_STYLE = "-"                # Solid lines

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

def create_exchange_rate_chart(json_file, year, month):
    """
    Create exchange rate trend chart from trends JSON
    
    Shows 12-month trend of:
    - Official USD/LYD rate
    - Official + 20% Gov Tax
    - Parallel Market rate
    """
    
    # Load trends JSON
    print(f"\nLoading data from: {json_file}")
    with open(json_file, "r") as f:
        data = json.load(f)
    
    # Extract exchange rate data
    if 'exchange_rates' not in data or not data['exchange_rates']['dates']:
        raise ValueError("No exchange rate data found in JSON file. Make sure query_trends.py includes exchange rates.")
    
    exchange_data = data['exchange_rates']
    
    # Convert to DataFrame
    df = pd.DataFrame({
        'date': pd.to_datetime(exchange_data['dates']),
        'official_rate': exchange_data['official_rate'],
        'official_rate_with_tax': exchange_data['official_rate_with_tax'],
        'parallel_market_rate': exchange_data['parallel_market_rate']
    })
    
    # Remove any NaN values
    df = df.dropna()
    
    if df.empty:
        raise ValueError("No valid exchange rate data available")
    
    # Get the target date from metadata
    target_date = datetime.fromisoformat(data['metadata']['target_date'])
    
    # Calculate 12 months back from target date
    # Target is Nov 2025, so 12 months back is Dec 2024
    start_month = target_date - relativedelta(months=11)  # 11 months back gives us 12 months total
    start_month = start_month.replace(day=1)  # First day of start month
    
    # Filter data to exactly 12 months
    df = df[(df['date'] >= start_month) & (df['date'] <= target_date)]
    
    if df.empty:
        raise ValueError(f"No data available for 12-month period {start_month.date()} to {target_date.date()}")
    
    print(f"✓ Loaded {len(df)} data points")
    print(f"  12-month period: {start_month.strftime('%b %Y')} to {target_date.strftime('%b %Y')}")
    print(f"  Date range: {df['date'].min().date()} to {df['date'].max().date()}")
    
    # Latest values for summary
    latest = df.iloc[-1]
    print(f"\nLatest rates ({latest['date'].strftime('%Y-%m-%d')}):")
    print(f"  Official: {latest['official_rate']:.4f} LYD")
    print(f"  Official + Tax: {latest['official_rate_with_tax']:.2f} LYD")
    print(f"  Parallel Market: {latest['parallel_market_rate']:.2f} LYD")
    
    # ----------------------------------------------------------------------
    # Plotting
    # ----------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(34, 18))
    
    # Plot the three lines
    ax.plot(
        df['date'],
        df['official_rate'],
        color=COLOR_OFFICIAL,
        linewidth=LINE_WIDTH,
        linestyle=LINE_STYLE,
        label="USD/LYD",
        zorder=3
    )
    
    ax.plot(
        df['date'],
        df['official_rate_with_tax'],
        color=COLOR_TAX,
        linewidth=LINE_WIDTH,
        linestyle=LINE_STYLE,
        label="USD/LYD + Gov Tax",
        zorder=3
    )
    
    ax.plot(
        df['date'],
        df['parallel_market_rate'],
        color=COLOR_PARALLEL,
        linewidth=LINE_WIDTH,
        linestyle=LINE_STYLE,
        label="Parallel Market",
        zorder=3
    )
    
    # ----------------------------------------------------------------------
    # Axis formatting
    # ----------------------------------------------------------------------
    
    # X-axis: Show exactly 12 months (Dec 2024 to Nov 2025)
    # Create monthly ticks for the 12-month period
    monthly_ticks = []
    current = start_month
    for i in range(12):
        monthly_ticks.append(current)
        current = current + relativedelta(months=1)
    
    ax.set_xticks(monthly_ticks)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    
    # Extend x-limits with more padding for space before Dec and after Nov
    # Calculate time span between months
    month_span = (monthly_ticks[1] - monthly_ticks[0]).days if len(monthly_ticks) > 1 else 30
    
    # Add 50% of a month as padding on each side
    padding_days = month_span * 0.5
    
    xmin = monthly_ticks[0] - pd.Timedelta(days=padding_days)
    xmax = monthly_ticks[-1] + pd.Timedelta(days=padding_days)
    ax.set_xlim(xmin, xmax)
    
    # Y-axis: Dynamic range with better visibility
    # Collect all values
    all_values = np.concatenate([
        df['official_rate'].values,
        df['official_rate_with_tax'].values,
        df['parallel_market_rate'].values
    ])
    
    data_min = float(np.min(all_values))
    data_max = float(np.max(all_values))
    data_range = data_max - data_min if data_max > data_min else 1.0
    
    # Add more padding for better visibility (15% instead of 8%)
    pad = 0.15 * data_range
    bottom = max(0, data_min - pad)
    top = data_max + pad
    ax.set_ylim(bottom=bottom, top=top)
    
    # Y-axis ticks (every 0.5 or 1.0 depending on range)
    if data_range < 3:
        ax.yaxis.set_major_locator(mticker.MultipleLocator(0.5))
    else:
        ax.yaxis.set_major_locator(mticker.MultipleLocator(1.0))
    
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
    for dt in monthly_ticks:
        year_dt = dt.year
        if year_dt not in years_shown:
            years_shown[year_dt] = dt
    
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
    
    # End tick markers on x-axis
    xaxis_transform = ax.get_xaxis_transform()
    
    ax.plot(
        [xmin, xmin],
        [0, -0.03],
        transform=xaxis_transform,
        color="#D9D9D9",
        linewidth=3,
        clip_on=False,
        zorder=20,
    )
    ax.plot(
        [xmax, xmax],
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
    
    # Legend
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, 1.07),
        ncol=3,
        frameon=False,
        fontsize=FONT_SIZE + 4,
        labelcolor=FONT_COLOR,
        handletextpad=0.4
    )
    
    # Extra space for labels
    plt.subplots_adjust(bottom=0.25)
    plt.tight_layout()
    
    # Save to monthly OneDrive folder
    from config import ensure_month_directories
    
    paths = ensure_month_directories(year, month)
    month_tag = datetime(year, month, 1).strftime("%b%y")
    
    output_file = paths['charts'] / f"Exchange_Rate_{month_tag}.svg"
    
    plt.savefig(output_file, format="svg", bbox_inches="tight", transparent=True)
    plt.close()
    
    print(f"\n✓ Chart saved: {output_file}")
    return output_file

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("EXCHANGE RATE TREND CHART")
    print("=" * 70)
    
    # Get year and month from command line
    if len(sys.argv) < 3:
        print("❌ Usage: python scripts/06_Visualizations/charts/exchange_rate_chart.py <year> <month>")
        print("   Example: python scripts/06_Visualizations/charts/exchange_rate_chart.py 2025 11")
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
        create_exchange_rate_chart(json_file, year, month)
        print("\n" + "=" * 70)
        print("✅ CHART COMPLETE")
        print("=" * 70)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)