"""
Libya PMM - West Region Municipality Food & NFI MEB Charts (Gap Linked)
Shows West municipalities with National comparison

Gap behaviour:
- X-axis always shows the last 12 months (including months with no data).
- Lines break over missing months (NaNs).
- Faded connector segments are drawn across gaps between the last month
  before the gap and the first month after it for each municipality and
  the national line.

Styling (same as non-gap version):
- Most Expensive Municipality: Red (#E57373) - Solid
- Least Expensive Municipality: Green (#97C1A8) - Solid
- Other Municipalities: Grey (#BFBFBF, 20% alpha) - Solid
- National: Blue (#73B4E0) - Dashed
- Font: Aptos Narrow, 36pt
- Lines: 10pt

Usage:
    python scripts/06_Visualizations/charts/west_meb_charts.py <year> <month>

Examples:
    python scripts/06_Visualizations/charts/west_meb_charts.py 2025 11
    python scripts/06_Visualizations/charts/west_meb_charts.py 2025 11 --type food
    python scripts/06_Visualizations/charts/west_meb_charts.py 2025 11 --type nfi
"""

import json
import sys
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib
import matplotlib.font_manager as fm
import warnings
from sqlalchemy import text

# Auto-detect environment and set project root
import os

if os.path.exists('/app'):  # Running in Docker
    PROJECT_ROOT = Path('/app')
else:  # Running locally
    # Script is in scripts/06_Visualizations/charts/ or map/
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Add project root to path to import config
sys.path.insert(0, str(PROJECT_ROOT))

from config import get_engine, get_month_paths

# ============================================================================
# MUNICIPALITY NAME MAPPING
# ============================================================================

def fix_municipality_names(df, column='municipality'):
    """Fix municipality names to official spellings"""
    if column not in df.columns:
        return df
    
    name_mapping = {
        'Ejdabia': 'Ajdabiya',
        'Tripoli Center': 'Tripoli'
    }
    
    df[column] = df[column].replace(name_mapping)
    return df

# ============================================================================
# STYLING CONFIGURATION
# ============================================================================

# Colors
COLOR_MOST_EXPENSIVE = "#E57373"    # Red
COLOR_LEAST_EXPENSIVE = "#97C1A8"   # Green
COLOR_OTHER = "#BFBFBF"             # Grey
COLOR_NATIONAL = "#73B4E0"          # Blue
COLOR_TEXT = "#000000"              # Text color

# Line styles
LINE_WIDTH_HIGHLIGHTED = 10         # Most/Least expensive + National
LINE_WIDTH_GREY = 7.0               # Other municipalities
LINE_STYLE_MUNI = "-"               # Solid for municipalities
LINE_STYLE_NATIONAL = "--"          # Dashed for national
ALPHA_GREY = 0.2                    # 20% opacity for grey lines
CONNECTOR_ALPHA = 0.2               # 80% transparent connectors

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
# DATABASE & DATA LOADING
# ============================================================================

def get_municipality_time_series(engine, target_date, region="West", months_back=12):
    """
    Query database for West municipality Full MEB and return pivoted DataFrame.
    Builds a continuous monthly index for the last N months.
    """
    query = text("""
        SELECT 
            m.date,
            m.municipality,
            m.full_meb,
            m.food_meb,
            m.nfi_meb
        FROM municipality_meb m
        JOIN keys k ON m.municipality = k.admin_name
        WHERE m.date <= :target_date
        AND k.parent_code = (
            SELECT admin_code FROM keys WHERE admin_name = :region
        )
        ORDER BY m.date DESC, m.municipality
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {"target_date": target_date, "region": region})
        df = pd.DataFrame(result.fetchall(), columns=["date", "municipality", "full_meb", "food_meb", "nfi_meb"])

    if df.empty:
        return df
    
    # Fix municipality names
    df = fix_municipality_names(df, 'municipality')

    df["date"] = pd.to_datetime(df["date"])
    for col in ["full_meb", "food_meb", "nfi_meb"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        df.loc[df[col] == 0, col] = np.nan

    # Continuous monthly index
    last_date = pd.to_datetime(target_date)
    last_month_start = last_date.replace(day=1)
    monthly_index = pd.date_range(end=last_month_start, periods=months_back, freq="MS")

    # Normalize dates to month start
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    df = df[df["month"].isin(monthly_index)]

    # Aggregate and pivot
    df_agg = (
        df.groupby(["month", "municipality"], as_index=False)[["full_meb", "food_meb", "nfi_meb"]]
        .mean()
        .rename(columns={"month": "date"})
    )

    # Return dictionary of DataFrames by MEB type
    result = {}
    for meb_col in ["full_meb", "food_meb", "nfi_meb"]:
        pivot_df = df_agg.pivot(index="date", columns="municipality", values=meb_col)
        pivot_df = pivot_df.reindex(monthly_index)
        result[meb_col] = pivot_df

    return result

def find_gap_segments(muni_df):
    """Find gap segments where ALL municipalities have NaN."""
    gap_mask = muni_df.isna().all(axis=1)
    dates = list(muni_df.index)

    segments = []
    in_gap = False
    gap_start_idx = None

    for i, (dt, is_gap) in enumerate(zip(dates, gap_mask)):
        if is_gap and not in_gap:
            in_gap = True
            gap_start_idx = i
        elif not is_gap and in_gap:
            in_gap = False
            pre_idx = gap_start_idx - 1
            post_idx = i
            if pre_idx >= 0 and post_idx < len(dates):
                segments.append((dates[pre_idx], dates[post_idx]))

    return segments

# ============================================================================
# CHART GENERATION (GAP-LINKED)
# ============================================================================

def create_west_meb_chart_gaplinked(data, meb_type="food_meb", year=None, month=None):
    """
    Create West region municipality Food or NFI MEB chart (gap-linked).
    meb_type: 'food_meb' or 'nfi_meb'
    """

    # Get engine and load municipality data
    engine = get_engine()
    target_date = datetime.fromisoformat(data["metadata"]["target_date"]).date()

    print(f"Loading West municipality time series from database...")
    muni_dfs = get_municipality_time_series(engine, target_date, region="West", months_back=12)
    muni_df = muni_dfs[meb_type]

    if muni_df.empty:
        raise ValueError("No West municipality data returned.")

    # National data from JSON
    national_dates = pd.to_datetime(data["national"]["dates"])
    national_months = national_dates.to_period("M").to_timestamp()
    national_series_raw = pd.Series(data["national"][meb_type], index=national_months)
    national_series = national_series_raw.groupby(national_series_raw.index).mean()
    national_values = national_series.reindex(muni_df.index)

    # Latest values
    latest_non_na_row = muni_df.dropna(how="all").iloc[-1]
    latest_values = latest_non_na_row.dropna()

    most_expensive = latest_values.idxmax()
    least_expensive = latest_values.idxmin()
    most_val = float(latest_values[most_expensive])
    least_val = float(latest_values[least_expensive])

    if national_values.dropna().empty:
        raise ValueError("National MEB has no data.")
    nat_val = float(national_values.dropna().iloc[-1])

    meb_label = "Food" if meb_type == "food_meb" else "Non-Food"

    print(f"\nWest {meb_label} MEB (Gap-Linked):")
    print(f"  Most Expensive: {most_expensive} — {most_val:,.2f} LYD")
    print(f"  Least Expensive: {least_expensive} — {least_val:,.2f} LYD")
    print(f"  National: {nat_val:,.2f} LYD")

    # Find gaps
    gap_segments = find_gap_segments(muni_df)

    # ---------------- Plotting ----------------
    fig, ax = plt.subplots(figsize=(34, 18))

    # Grey lines (other municipalities)
    for municipality in muni_df.columns:
        if municipality not in [most_expensive, least_expensive]:
            ax.plot(
                muni_df.index,
                muni_df[municipality],
                color=COLOR_OTHER,
                linewidth=LINE_WIDTH_GREY,
                linestyle=LINE_STYLE_MUNI,
                alpha=ALPHA_GREY,
                zorder=1,
            )

    # Most expensive (red)
    ax.plot(
        muni_df.index,
        muni_df[most_expensive],
        color=COLOR_MOST_EXPENSIVE,
        linewidth=LINE_WIDTH_HIGHLIGHTED,
        linestyle=LINE_STYLE_MUNI,
        label=f"{most_expensive} (Most Expensive)",
        zorder=3,
    )

    # Least expensive (green)
    ax.plot(
        muni_df.index,
        muni_df[least_expensive],
        color=COLOR_LEAST_EXPENSIVE,
        linewidth=LINE_WIDTH_HIGHLIGHTED,
        linestyle=LINE_STYLE_MUNI,
        label=f"{least_expensive} (Least Expensive)",
        zorder=3,
    )

    # National (blue, dashed)
    ax.plot(
        muni_df.index,
        national_values.values,
        color=COLOR_NATIONAL,
        linewidth=LINE_WIDTH_HIGHLIGHTED,
        linestyle=LINE_STYLE_NATIONAL,
        label=f"National {meb_label} MEB (Mean)",
        zorder=3,
    )

    # ---------------- Gap connectors ----------------
    for pre_date, post_date in gap_segments:
        # Municipalities
        for municipality in muni_df.columns:
            y1 = muni_df.loc[pre_date, municipality]
            y2 = muni_df.loc[post_date, municipality]
            if np.isnan(y1) or np.isnan(y2):
                continue

            if municipality == most_expensive:
                conn_color = COLOR_MOST_EXPENSIVE
                conn_width = LINE_WIDTH_HIGHLIGHTED
                conn_linestyle = "-"
            elif municipality == least_expensive:
                conn_color = COLOR_LEAST_EXPENSIVE
                conn_width = LINE_WIDTH_HIGHLIGHTED
                conn_linestyle = "-"
            else:
                conn_color = COLOR_OTHER
                conn_width = LINE_WIDTH_GREY
                conn_linestyle = "-"

            ax.plot(
                [pre_date, post_date],
                [y1, y2],
                color=conn_color,
                linestyle=conn_linestyle,
                linewidth=conn_width,
                alpha=CONNECTOR_ALPHA,
                zorder=2,
            )

        # National connector
        y1_nat = national_values.loc[pre_date]
        y2_nat = national_values.loc[post_date]
        if not (np.isnan(y1_nat) or np.isnan(y2_nat)):
            ax.plot(
                [pre_date, post_date],
                [y1_nat, y2_nat],
                color=COLOR_NATIONAL,
                linestyle="--",
                linewidth=LINE_WIDTH_HIGHLIGHTED,
                alpha=CONNECTOR_ALPHA,
                zorder=3,
            )

    # ---------------- Axis formatting ----------------
    ax.set_xticks(muni_df.index)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))

    if len(muni_df.index) > 1:
        step = muni_df.index[1] - muni_df.index[0]
    else:
        step = pd.Timedelta(days=30)

    xmin = muni_df.index[0] - 0.3 * step
    xmax = muni_df.index[-1] + 0.3 * step
    ax.set_xlim(xmin, xmax)

    # Dynamic vertical range
    all_values = np.concatenate([
        muni_df.to_numpy().flatten(),
        national_values.to_numpy().flatten(),
    ])
    all_values = all_values[~np.isnan(all_values)]

    data_min = float(np.min(all_values))
    data_max = float(np.max(all_values))
    data_range = data_max - data_min if data_max > data_min else 1.0

    pad = 0.08 * data_range
    bottom = max(0, data_min - pad)
    top = data_max + pad
    ax.set_ylim(bottom=bottom, top=top)

    y_min, y_max = ax.get_ylim()
    y_range = y_max - y_min if y_max > y_min else 1.0

    ax.tick_params(axis="x", pad=20)

    # Year labels
    years_shown = {}
    for dt in muni_df.index:
        year_dt = dt.year
        if year_dt not in years_shown:
            years_shown[year_dt] = dt

    year_label_y = y_min - 0.07 * y_range

    # End ticks
    xaxis_transform = ax.get_xaxis_transform()
    ax.plot([xmin, xmin], [0, -0.03], transform=xaxis_transform, color="#D9D9D9", linewidth=3, clip_on=False, zorder=20)
    ax.plot([xmax, xmax], [0, -0.03], transform=xaxis_transform, color="#D9D9D9", linewidth=3, clip_on=False, zorder=20)

    # Draw year labels
    for year_dt, dt in years_shown.items():
        ax.text(dt, year_label_y, str(year_dt), ha="left", va="top", fontsize=FONT_SIZE + 6, fontweight="bold", color=FONT_COLOR)

    # Axis styling
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color("#D9D9D9")
    ax.spines["bottom"].set_linewidth(3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
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

    plt.subplots_adjust(bottom=0.25)
    plt.tight_layout()

    # Save to monthly OneDrive folder
    from config import ensure_month_directories
    
    paths = ensure_month_directories(year, month)
    month_tag = datetime(year, month, 1).strftime("%b%y")
    
    chart_name = f"West_{meb_label}_MEB_{month_tag}.svg"
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
    print("WEST REGION - FOOD & NFI MEB CHARTS (GAP-LINKED)")
    print("=" * 70)

    # Get year and month from command line
    if len(sys.argv) < 3:
        print("❌ Usage: python scripts/06_Visualizations/charts/west_meb_charts.py <year> <month>")
        print("   Example: python scripts/06_Visualizations/charts/west_meb_charts.py 2025 11")
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

    # Chart type
    chart_type = "both"
    if "--type" in sys.argv:
        idx = sys.argv.index("--type")
        if idx + 1 < len(sys.argv):
            chart_type = sys.argv[idx + 1].lower()

    try:
        generated_files = []

        if chart_type in ["both", "food"]:
            print("\n" + "-" * 70)
            print("Generating West Food MEB Chart (Gap-Linked)...")
            print("-" * 70)
            file = create_west_meb_chart_gaplinked(data, "food_meb", year, month)
            generated_files.append(file)

        if chart_type in ["both", "nfi"]:
            print("\n" + "-" * 70)
            print("Generating West NFI MEB Chart (Gap-Linked)...")
            print("-" * 70)
            file = create_west_meb_chart_gaplinked(data, "nfi_meb", year, month)
            generated_files.append(file)

        print("\n" + "=" * 70)
        print("✅ GAP-LINKED WEST CHART GENERATION COMPLETE")
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