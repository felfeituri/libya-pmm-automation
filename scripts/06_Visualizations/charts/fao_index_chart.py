"""
Libya PMM - FAO Food Price Index Chart (Direct from CSV)
Generates chart directly from FAO CSV file without database

Usage:
    python scripts/06_Visualizations/charts/fao_index_chart.py <year> <month>

Example:
    python scripts/06_Visualizations/charts/fao_index_chart.py 2025 11
"""

import sys
from pathlib import Path
import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib
import matplotlib.font_manager as fm
import matplotlib.ticker as mticker
import warnings

# Auto-detect environment and set project root
if os.path.exists('/app'):  # Running in Docker
    PROJECT_ROOT = Path('/app')
else:  # Running locally
    # Script is in scripts/06_Visualizations/charts/
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# ============================================================================
# STYLING CONFIGURATION
# ============================================================================

# Colors (updated specifications)
COLOR_FFPI = "#73B4E0"          # Blue for FAO Food Price Index (dashed)
COLOR_MEAT = "#E57373"          # Red for Meat (solid)
COLOR_DAIRY = "#97C1A8"         # Green for Dairy (solid)
COLOR_CEREALS = "#EACB76"       # Gold/Yellow for Cereals (solid)
COLOR_OILS = "#B39DDB"          # Purple for Oils (solid)
COLOR_SUGAR = "#A1887F"         # Brown for Sugar (solid)

# Line styles
LINE_WIDTH = 6.0
LINE_STYLE_SOLID = "-"
LINE_STYLE_DASHED = "--"

# Font settings
FONT_SIZE = 42
FONT_COLOR = "#000000"

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
# DATA LOADING
# ============================================================================

def load_fao_csv(file_path):
    """Load FAO CSV file"""

    print(f"\n📂 Loading CSV file: {file_path}")

    # CSV structure:
    # Row 0: "FAO Food Price Index" (title)
    # Row 1: "2014-2016=100" (base year)
    # Row 2: Headers (Date, Food Price Index, Meat, Dairy, Cereals, Oils, Sugar)
    # Row 3: Empty
    # Row 4+: Data

    # Read CSV, skip first 2 rows, use row 2 as header
    df = pd.read_csv(file_path, skiprows=2)

    # Remove empty first row (row 3 in original)
    df = df[df.iloc[:, 0].notna()]

    # Reset index
    df = df.reset_index(drop=True)

    print(f"   ✓ Loaded {len(df)} rows")
    print(f"   Columns: {df.columns.tolist()[:7]}")

    return df


def process_fao_data(df, months_back=48):
    """Process and filter FAO data"""

    print(f"\n📄 Processing data...")

    # Keep only relevant columns
    columns_needed = ['Date', 'Food Price Index', 'Meat', 'Dairy', 'Cereals', 'Oils', 'Sugar']

    # Check which columns exist
    available_cols = [col for col in columns_needed if col in df.columns]

    if not available_cols:
        print(f"   ❌ Could not find required columns")
        print(f"   Available: {df.columns.tolist()}")
        return None

    df = df[available_cols].copy()

    # Convert Date to datetime (format: YYYY-MM)
    df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m', errors='coerce')

    # Remove rows with invalid dates
    df = df[df['Date'].notna()]

    # Convert numeric columns
    for col in ['Food Price Index', 'Meat', 'Dairy', 'Cereals', 'Oils', 'Sugar']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Sort by date
    df = df.sort_values('Date').reset_index(drop=True)

    # Get last N months
    df = df.tail(months_back)

    print(f"   ✓ Processed {len(df)} records")
    print(f"   Date range: {df['Date'].min().strftime('%b %Y')} to {df['Date'].max().strftime('%b %Y')}")

    return df

# ============================================================================
# CHART GENERATION
# ============================================================================

def create_fao_chart(df, year, month):
    """Create FAO Food Price Index chart"""

    print(f"\n📈 Generating chart...")

    fig, ax = plt.subplots(figsize=(48, 22))

    # ----------------------------------------------------------------------
    # Lines
    # ----------------------------------------------------------------------
    if 'Food Price Index' in df.columns:
        ax.plot(
            df['Date'], df['Food Price Index'],
            color=COLOR_FFPI, linewidth=LINE_WIDTH,
            linestyle=LINE_STYLE_DASHED,
            label='FAO Food Price Index', zorder=3
        )

    if 'Meat' in df.columns:
        ax.plot(df['Date'], df['Meat'],
                color=COLOR_MEAT, linewidth=LINE_WIDTH,
                linestyle=LINE_STYLE_SOLID, label='Meat', zorder=3)

    if 'Dairy' in df.columns:
        ax.plot(df['Date'], df['Dairy'],
                color=COLOR_DAIRY, linewidth=LINE_WIDTH,
                linestyle=LINE_STYLE_SOLID, label='Dairy', zorder=3)

    if 'Cereals' in df.columns:
        ax.plot(df['Date'], df['Cereals'],
                color=COLOR_CEREALS, linewidth=LINE_WIDTH,
                linestyle=LINE_STYLE_SOLID, label='Cereals', zorder=3)

    if 'Oils' in df.columns:
        ax.plot(df['Date'], df['Oils'],
                color=COLOR_OILS, linewidth=LINE_WIDTH,
                linestyle=LINE_STYLE_SOLID, label='Oils', zorder=3)

    if 'Sugar' in df.columns:
        ax.plot(df['Date'], df['Sugar'],
                color=COLOR_SUGAR, linewidth=LINE_WIDTH,
                linestyle=LINE_STYLE_SOLID, label='Sugar', zorder=3)

    # ----------------------------------------------------------------------
    # Peak & trough labels (no endpoints)
    # ----------------------------------------------------------------------
    series_info = [
        ('Food Price Index', COLOR_FFPI),
        ('Meat', COLOR_MEAT),
        ('Dairy', COLOR_DAIRY),
        ('Cereals', COLOR_CEREALS),
        ('Oils', COLOR_OILS),
        ('Sugar', COLOR_SUGAR),
    ]

    for col, color in series_info:
        if col not in df.columns:
            continue

        values = df[col]
        mask = values.notna()
        valid_idx = values[mask].index.tolist()
        if len(valid_idx) == 0:
            continue

        # exclude first & last valid points when possible
        if len(valid_idx) > 2:
            inner_idx = valid_idx[1:-1]
        else:
            inner_idx = valid_idx

        sub = values.loc[inner_idx]
        if sub.empty:
            continue

        peak_idx = sub.idxmax()
        trough_idx = sub.idxmin()
        peak_val = values.loc[peak_idx]
        trough_val = values.loc[trough_idx]
        peak_date = df.loc[peak_idx, 'Date']
        trough_date = df.loc[trough_idx, 'Date']

        ax.text(
            peak_date, peak_val + 3,
            f"{peak_val:.1f}",
            fontsize=FONT_SIZE - 6,
            ha='center', va='bottom',
            color=color
        )

        if trough_idx != peak_idx:
            ax.text(
                trough_date, trough_val - 3,
                f"{trough_val:.1f}",
                fontsize=FONT_SIZE - 6,
                ha='center', va='top',
                color=color
            )

    # ----------------------------------------------------------------------
    # Axis formatting
    # ----------------------------------------------------------------------
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))

    # X padding
    date_min = df['Date'].min()
    date_max = df['Date'].max()
    date_range = (date_max - date_min).days
    padding_days = date_range * 0.02
    ax.set_xlim(
        date_min - pd.Timedelta(days=padding_days),
        date_max + pd.Timedelta(days=padding_days),
    )

    # Y range
    ax.set_ylim(80, 270)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(20))

    ax.tick_params(axis="x", pad=20)

    # Year labels (same as your original)
    y_min, y_max = ax.get_ylim()
    y_range = y_max - y_min
    year_label_y = y_min - 0.07 * y_range

    years_shown = {}
    for dt in pd.date_range(start=df['Date'].min(), end=df['Date'].max(), freq='YS'):
        year_dt = dt.year
        if year_dt not in years_shown:
            years_shown[year_dt] = dt

    for year_dt, dt in years_shown.items():
        ax.text(
            dt, year_label_y, str(year_dt),
            ha="left", va="top",
            fontsize=FONT_SIZE + 6,
            fontweight="bold",
            color=FONT_COLOR
        )

    ax.set_xlabel("")
    ax.set_ylabel("")

    # Spines
    ax.spines["left"].set_visible(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color("#D9D9D9")
    ax.spines["bottom"].set_linewidth(3)

    ax.grid(False)

    # ----------------------------------------------------------------------
    # Legend (higher) + clear gap to footnote
    # ----------------------------------------------------------------------
    handles, labels = ax.get_legend_handles_labels()
    label_order = ['FAO Food Price Index', 'Meat', 'Dairy', 'Cereals', 'Oils', 'Sugar']
    ordered_handles, ordered_labels = [], []

    for desired_label in label_order:
        for h, lab in zip(handles, labels):
            if lab == desired_label:
                ordered_handles.append(h)
                ordered_labels.append(lab)
                break

    ax.legend(
        ordered_handles,
        ordered_labels,
        loc="upper left",
        bbox_to_anchor=(0, 1.08),   # above the axes, not inside it
        frameon=False,
        fontsize=FONT_SIZE,
        labelcolor=FONT_COLOR,
        ncol=6,
        handletextpad=0.2
    )

    # ----------------------------------------------------------------------
    # End ticks + trim bottom spine so no extra line shows
    # ----------------------------------------------------------------------
    xaxis_transform = ax.get_xaxis_transform()
    x_min, x_max = ax.get_xlim()
    span = x_max - x_min
    end_pad = span * 0.005  # controls gap between ticks and y-axis

    left_tick_x = x_min + end_pad
    right_tick_x = x_max - end_pad

    # downward ticks
    ax.plot(
        [left_tick_x, left_tick_x],
        [0, -0.01],
        transform=xaxis_transform,
        color="#D9D9D9",
        linewidth=3,
        clip_on=False,
        zorder=20,
    )
    ax.plot(
        [right_tick_x, right_tick_x],
        [0, -0.01],
        transform=xaxis_transform,
        color="#D9D9D9",
        linewidth=3,
        clip_on=False,
        zorder=20,
    )

    # 🔒 trim the bottom spine so it starts/ends at the ticks
    ax.spines["bottom"].set_bounds(left_tick_x, right_tick_x)

    # ----------------------------------------------------------------------
    # Footnote
    # ----------------------------------------------------------------------
    footnote_text = (
        "* The FAO Food Price Index (FFPI) is a measure of the monthly change "
        "in international prices of a basket of food commodities"
    )

    ax.text(
        0.01, 0.98,
        footnote_text,
        transform=ax.transAxes,
        fontsize=FONT_SIZE - 10,
        va='bottom', ha='left',
        color=FONT_COLOR,
        style='italic',
    )

    # ----------------------------------------------------------------------
    # Layout – give the plot more vertical space (fixes "squeezed" look)
    # ----------------------------------------------------------------------
    # You can tweak these if you want slightly more/less top or bottom space.
    plt.subplots_adjust(left=0.02, right=0.75, top=0.80, bottom=0.12)

    # Save to monthly OneDrive folder
    from datetime import datetime
    # Add to path if not already there
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from config import ensure_month_directories
    
    paths = ensure_month_directories(year, month)
    output_file = paths['charts'] / "FAO_Food_Price_Index.svg"

    plt.savefig(output_file, format="svg", bbox_inches="tight", transparent=True)
    plt.close()

    print(f"   ✓ Chart saved: {output_file}")
    return output_file

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("FAO FOOD PRICE INDEX CHART (FROM CSV)")
    print("=" * 70)

    # Get year and month from command line
    if len(sys.argv) < 3:
        print("❌ Usage: python scripts/06_Visualizations/charts/fao_index_chart.py <year> <month>")
        print("   Example: python scripts/06_Visualizations/charts/fao_index_chart.py 2025 11")
        sys.exit(1)
    
    year = int(sys.argv[1])
    month = int(sys.argv[2])

    # Default file path
    file_path = 'inputs/food_price_indices_data.csv'

    if '--file' in sys.argv:
        idx = sys.argv.index('--file')
        file_path = sys.argv[idx + 1]

    months_back = 48
    if '--months' in sys.argv:
        idx = sys.argv.index('--months')
        months_back = int(sys.argv[idx + 1])

    try:
        # Load CSV
        df = load_fao_csv(file_path)

        # Process data
        df_processed = process_fao_data(df, months_back)

        if df_processed is None or df_processed.empty:
            print("\n❌ No valid data to plot")
            sys.exit(1)

        # Generate chart
        create_fao_chart(df_processed, year, month)

        print("\n" + "=" * 70)
        print("✅ CHART COMPLETE")
        print("=" * 70)
        print(f"\nChart shows last {months_back} months of FAO food price indices")

    except FileNotFoundError as e:
        print(f"\n❌ Error: File not found")
        print(f"   {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)