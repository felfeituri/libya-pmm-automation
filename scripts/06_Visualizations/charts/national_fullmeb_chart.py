"""
Libya PMM - National Full MEB Chart with Municipality Comparison (Gap Linked)

Version 2:
- Same styling as the main chart
- Lines still break over months with missing data
- Additionally draws connector segments across the gap
  between the last month before the gap and the first month after it
  for all municipalities and for the national line.

Usage:
    python scripts/06_Visualizations/charts/national_fullmeb_chart.py <year> <month>

Example:
    python scripts/06_Visualizations/charts/national_fullmeb_chart.py 2025 11
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
COLOR_MOST_EXPENSIVE = "#E57373"    # Red
COLOR_LEAST_EXPENSIVE = "#97C1A8"   # Green
COLOR_NATIONAL = "#73B4E0"          # Blue
COLOR_OTHER = "#BFBFBF"             # Grey
COLOR_TEXT = "#000000"              # Text color

# Line styles and thickness
LINE_WIDTH_HIGHLIGHTED = 10         # thicker for highlighted lines
LINE_WIDTH_GREY = 7.0               # for other municipalities
LINE_STYLE_HIGHLIGHTED = "--"       # dashed
LINE_STYLE_GREY = "-"               # solid
ALPHA_GREY = 0.2                    # 20% opacity for normal grey lines

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
# DATA LOADING
# ============================================================================

def get_municipality_time_series(engine, target_date, months_back=12):
    """
    Query database for municipality Full MEB and return a pivoted DataFrame.

    We build a continuous monthly index (month start dates) for the last
    `months_back` months. Any month with no data remains NaN, so lines
    naturally break and there is NO coloured line drawn across the gap.
    """
    from sqlalchemy import text

    query = text(
        """
        SELECT 
            date,
            municipality,
            full_meb
        FROM municipality_meb
        WHERE date <= :target_date
        ORDER BY date DESC, municipality
        """
    )

    with engine.connect() as conn:
        result = conn.execute(query, {"target_date": target_date})
        df = pd.DataFrame(result.fetchall(), columns=["date", "municipality", "full_meb"])

    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"])
    df["full_meb"] = pd.to_numeric(df["full_meb"], errors="coerce")

    # Treat 0 as missing
    df.loc[df["full_meb"] == 0, "full_meb"] = np.nan

    # Continuous monthly index (month starts)
    last_date = pd.to_datetime(target_date)
    last_month_start = last_date.replace(day=1)
    monthly_index = pd.date_range(end=last_month_start, periods=months_back, freq="MS")

    # Normalize all dates to month start so they align with monthly_index
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()  # month start

    # Restrict to our 12-month window
    df = df[df["month"].isin(monthly_index)]

    # Aggregate (if multiple rows per month/municipality, take mean)
    df_agg = (
        df.groupby(["month", "municipality"], as_index=False)["full_meb"]
        .mean()
        .rename(columns={"month": "date"})
    )

    # Pivot to wide
    pivot_df = df_agg.pivot(index="date", columns="municipality", values="full_meb")

    # Reindex to full monthly_index; months with no data become NaN
    pivot_df = pivot_df.reindex(monthly_index)

    return pivot_df

# ============================================================================
# CHART GENERATION
# ============================================================================

def create_national_fullmeb_comparison_chart_gaplinked(
    json_file, year, month
):
    """
    Create National Full MEB chart with all municipalities (gap-linked version).

    - Coloured lines break over missing months (NaNs).
    - Additionally, connector segments are drawn across the gap between the last
      month before the gap and the first month after it for all municipalities
      and the national line.
      * coloured connectors (red/green/blue): dashed, alpha 0.2
      * grey connectors: solid, alpha 0.2
    """

    # Load trends JSON
    with open(json_file, "r") as f:
        data = json.load(f)

    # Import config for database connection (already in path)
    from config import get_engine
    
    engine = get_engine()

    # Target date
    target_date = datetime.fromisoformat(data["metadata"]["target_date"]).date()

    # Municipality time series (12 months)
    print("Loading municipality time series from database...")
    muni_df = get_municipality_time_series(engine, target_date, months_back=12)

    if muni_df.empty:
        raise ValueError("No municipality data returned for the selected period.")

    # National trend from JSON, aligned to same monthly index
    national_dates_all = pd.to_datetime(data["national"]["dates"])
    national_months = national_dates_all.to_period("M").to_timestamp()  # month start
    national_full_meb_all = pd.Series(
        data["national"]["full_meb"], index=national_months
    )

    national_full_meb = national_full_meb_all.reindex(muni_df.index)

    # Latest month with municipality data (ignore months where all are NaN)
    latest_non_na_row = muni_df.dropna(how="all").iloc[-1]
    latest_values = latest_non_na_row.dropna()

    most_expensive = latest_values.idxmax()
    least_expensive = latest_values.idxmin()
    most_val = float(latest_values[most_expensive])
    least_val = float(latest_values[least_expensive])
    
    # Fix names for display
    most_expensive_display = fix_municipality_names(most_expensive)
    least_expensive_display = fix_municipality_names(least_expensive)

    # Latest national where it is not NaN
    if national_full_meb.dropna().empty:
        raise ValueError("National Full MEB has no data in the 12-month window.")
    nat_val = float(national_full_meb.dropna().iloc[-1])

    print(f"\nMost Expensive: {most_expensive_display} — {most_val:,.2f} LYD")
    print(f"Least Expensive: {least_expensive_display} — {least_val:,.2f} LYD")
    print(f"National Full MEB: {nat_val:,.2f} LYD")
    print(f"Total Municipalities: {len(muni_df.columns)}")

    # ----------------------------------------------------------------------
    # Detect gap segments (months where ALL municipalities are NaN)
    # ----------------------------------------------------------------------
    gap_mask = muni_df.isna().all(axis=1)
    dates = list(muni_df.index)

    gap_bridge_segments = []  # list of (pre_gap_date, post_gap_date)

    in_gap = False
    gap_start_idx = None

    for i, (dt, is_gap) in enumerate(zip(dates, gap_mask)):
        if is_gap and not in_gap:
            in_gap = True
            gap_start_idx = i
        elif not is_gap and in_gap:
            # Gap finished just before this index
            in_gap = False
            pre_idx = gap_start_idx - 1
            post_idx = i
            if pre_idx >= 0 and post_idx < len(dates):
                gap_bridge_segments.append((dates[pre_idx], dates[post_idx]))

    # ----------------------------------------------------------------------
    # Plotting
    # ----------------------------------------------------------------------
    # Make the figure a bit taller to give more vertical space
    fig, ax = plt.subplots(figsize=(34, 18))  # wide, tall

    # Grey lines (other municipalities)
    for municipality in muni_df.columns:
        if municipality not in [most_expensive, least_expensive]:
            ax.plot(
                muni_df.index,
                muni_df[municipality],
                color=COLOR_OTHER,
                linewidth=LINE_WIDTH_GREY,
                linestyle=LINE_STYLE_GREY,
                alpha=ALPHA_GREY,
                zorder=1,
            )

    # Most expensive (red)
    ax.plot(
        muni_df.index,
        muni_df[most_expensive],
        color=COLOR_MOST_EXPENSIVE,
        linewidth=LINE_WIDTH_HIGHLIGHTED,
        linestyle=LINE_STYLE_HIGHLIGHTED,
        label=f"{most_expensive_display} (Most Expensive Market)",
        zorder=3,
    )

    # Least expensive (green)
    ax.plot(
        muni_df.index,
        muni_df[least_expensive],
        color=COLOR_LEAST_EXPENSIVE,
        linewidth=LINE_WIDTH_HIGHLIGHTED,
        linestyle=LINE_STYLE_HIGHLIGHTED,
        label=f"{least_expensive_display} (Least Expensive Market)",
        zorder=3,
    )

    # National mean (blue)
    ax.plot(
        muni_df.index,
        national_full_meb.values,
        color=COLOR_NATIONAL,
        linewidth=LINE_WIDTH_HIGHLIGHTED,
        linestyle=LINE_STYLE_HIGHLIGHTED,
        label="National Full MEB (Mean)",
        zorder=3,
    )

    # ----------------------------------------------------------------------
    # Add connector segments across each gap (faded)
    #   - coloured: dashed
    #   - grey: solid
    # ----------------------------------------------------------------------
    for pre_date, post_date in gap_bridge_segments:

        # --- Municipalities ---
        for municipality in muni_df.columns:
            y1 = muni_df.loc[pre_date, municipality]
            y2 = muni_df.loc[post_date, municipality]
            if np.isnan(y1) or np.isnan(y2):
                continue

            # Determine style based on highlighted vs normal
            if municipality == most_expensive:
                conn_color = COLOR_MOST_EXPENSIVE
                conn_width = LINE_WIDTH_HIGHLIGHTED
                conn_linestyle = "-"  # dashed faded red
            elif municipality == least_expensive:
                conn_color = COLOR_LEAST_EXPENSIVE
                conn_width = LINE_WIDTH_HIGHLIGHTED
                conn_linestyle = "-"  # dashed faded green
            else:
                conn_color = COLOR_OTHER
                conn_width = LINE_WIDTH_GREY
                conn_linestyle = "-"  # solid faded grey

            ax.plot(
                [pre_date, post_date],
                [y1, y2],
                color=conn_color,
                linestyle=conn_linestyle,
                linewidth=conn_width,
                alpha=0.2,  # 80% transparent
                zorder=2,
            )

        # --- National connector (blue, dashed) ---
        y1_nat = national_full_meb.loc[pre_date]
        y2_nat = national_full_meb.loc[post_date]

        if not (np.isnan(y1_nat) or np.isnan(y2_nat)):
            ax.plot(
                [pre_date, post_date],
                [y1_nat, y2_nat],
                color=COLOR_NATIONAL,
                linestyle="--",
                linewidth=LINE_WIDTH_HIGHLIGHTED,
                alpha=0.2,
                zorder=3,
            )

    # ----------------------------------------------------------------------
    # Axis formatting
    # ----------------------------------------------------------------------

    # Use exactly the 12 months from muni_df as tick positions
    ax.set_xticks(muni_df.index)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))

    # Extend x-limits slightly so there is padding and room for end ticks
    if len(muni_df.index) > 1:
        step = muni_df.index[1] - muni_df.index[0]
    else:
        step = pd.Timedelta(days=30)

    xmin = muni_df.index[0] - 0.3 * step   # a bit before first month
    xmax = muni_df.index[-1] + 0.3 * step  # a bit after last month
    ax.set_xlim(xmin, xmax)

    # -------- Dynamic vertical range so lines are not condensed --------
    # Collect all plotted values (municipalities + national)
    all_values = np.concatenate([
        muni_df.to_numpy().flatten(),
        national_full_meb.to_numpy().flatten(),
    ])
    all_values = all_values[~np.isnan(all_values)]

    data_min = float(np.min(all_values))
    data_max = float(np.max(all_values))
    data_range = data_max - data_min if data_max > data_min else 1.0

    # Small proportional padding so lines fill the height but do not touch edges
    pad = 0.08 * data_range   # tweak if you want more/less air
    bottom = max(0, data_min - pad)
    top = data_max + pad
    ax.set_ylim(bottom=bottom, top=top)

    # Control y-axis major ticks (e.g. every 100 LYD)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(100)) # change 100 → 50, 200, etc.

    # Re-read limits for label placement
    y_min, y_max = ax.get_ylim()
    y_range = y_max - y_min if y_max > y_min else 1.0

    # More space between x-axis line and month labels
    ax.tick_params(axis="x", pad=20)

    # Year labels (bold) under the axis
    years_shown = {}
    for dt in muni_df.index:
        year = dt.year
        if year not in years_shown:
            years_shown[year] = dt

    # Place years below months, proportional to the y-range
    year_label_y = y_min - 0.07 * y_range

    # ------------------------------------------------------------------
    # Custom end tick markers on the x-axis, pointing downward
    # ------------------------------------------------------------------
    xaxis_transform = ax.get_xaxis_transform()

    ax.plot(
        [xmin, xmin],
        [0, -0.03],                 # downward tick
        transform=xaxis_transform,
        color="#D9D9D9",
        linewidth=3,
        clip_on=False,
        zorder=20,
    )
    ax.plot(
        [xmax, xmax],
        [0, -0.03],                 # downward tick
        transform=xaxis_transform,
        color="#D9D9D9",
        linewidth=3,
        clip_on=False,
        zorder=20,
    )

    # Draw year labels
    for year, dt in years_shown.items():
        ax.text(
            dt,
            year_label_y,
            str(year),
            ha="left",
            va="top",
            fontsize=FONT_SIZE + 6,
            fontweight="bold",
            color=FONT_COLOR,
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

    ax.grid(False)

    # Legend
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, 1.04),
        ncol=3,
        frameon=False,
        fontsize=FONT_SIZE + 4,
        labelcolor=FONT_COLOR,
        handletextpad=0.4
    )

    plt.subplots_adjust(bottom=0.25)
    plt.tight_layout()

    # Save to monthly OneDrive folder (config already in path)
    from config import ensure_month_directories
    
    paths = ensure_month_directories(year, month)
    month_tag = datetime(year, month, 1).strftime("%b%y")
    output_file = paths['charts'] / f"National_FullMEB_{month_tag}.svg"
    
    plt.savefig(output_file, format="svg", bbox_inches="tight", transparent=True)
    plt.close()

    print(f"\n✓ Gap-linked chart saved: {output_file}")
    return output_file

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("NATIONAL FULL MEB - MUNICIPALITY COMPARISON CHART (GAP-LINKED)")
    print("=" * 70)

    # Get year and month from command line
    if len(sys.argv) < 3:
        print("❌ Usage: python scripts/06_Visualizations/charts/national_fullmeb_chart.py <year> <month>")
        print("   Example: python scripts/06_Visualizations/charts/national_fullmeb_chart.py 2025 11")
        sys.exit(1)
    
    year = int(sys.argv[1])
    month = int(sys.argv[2])
    
    # Get JSON path from config
    paths = get_month_paths(year, month)
    json_file = paths['trends_json']
    
    if not json_file.exists():
        print(f"❌ Trends JSON not found: {json_file}")
        print("   Run query_trends.py first!")
        sys.exit(1)

    print(f"\nUsing: {json_file}")

    try:
        create_national_fullmeb_comparison_chart_gaplinked(json_file, year, month)
        print("\n" + "=" * 70)
        print("✅ GAP-LINKED CHART COMPLETE")
        print("=" * 70)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)