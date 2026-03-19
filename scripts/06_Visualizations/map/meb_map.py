"""
Libya PMM - Map Visualization (Folium Version with ArcGIS Data)
- Fetches accurate Libya admin boundaries from ArcGIS REST API
- Bubble size = MEB price
- Libya admin boundaries clearly visible
- Municipality labels with MEB and percent change
- Interactive map with pan and zoom

Usage:
    python scripts/06_Visualizations/map/meb_map.py <year> <month>

Example:
    python scripts/06_Visualizations/map/meb_map.py 2025 11
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import folium
from folium import plugins
import requests
import sys
import os

# Auto-detect environment and set project root
if os.path.exists('/app'):  # Running in Docker
    PROJECT_ROOT = Path('/app')
else:  # Running locally
    # Script is in scripts/06_Visualizations/map/
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Add project root to path to import config
sys.path.insert(0, str(PROJECT_ROOT))

from config import get_month_paths


# ============================================================================
# STYLING CONFIGURATION  🔧  (EDIT HERE)
# ============================================================================

# Data paths (fallback defaults when no year/month are provided)
INPUT_FILE = "outputs/tables/Geopoints_MEB.csv"
OUTPUT_DIR = "outputs/map"

# ArcGIS Feature Server URL
# Service ItemId: cdd05b98949743f98918c53ebe9aa789
ARCGIS_URL = "https://services8.arcgis.com/ULOknP0QwPHCdswE/arcgis/rest/services/Libya_ADM2_Boundaries/FeatureServer/0/query"
ARCGIS_ITEM_ID = "cdd05b98949743f98918c53ebe9aa789"

# Map settings
MAP_CENTER_LAT = 27.5
MAP_CENTER_LON = 17.5
MAP_ZOOM = 6.45

# Tileset options:
# - 'OpenStreetMap' (has labels - avoid)
# - 'CartoDB positron' (clean, minimal - has some labels)
# - 'CartoDB positron_nolabels' (BEST - no labels at all)
# - 'CartoDB dark_matter'
# - 'Stamen Terrain'
# - 'Stamen Toner'
TILESET = 'CartoDB positron_nolabels'  # No labels to avoid overlap

# Bubble styling
SIZE_SCALE = 0.15                 # global bubble size multiplier for Folium
BUBBLE_MIN_SIZE = 15               # base minimum radius in pixels
BUBBLE_MAX_SIZE = 75              # base maximum radius in pixels
BUBBLE_BORDER_COLOR = '#F2E5D5'
BUBBLE_BORDER_WIDTH = 1.0
BUBBLE_OPACITY = 0.80                  # Fill and border opacity (0.0 to 1.0)

# Boundary styling
BOUNDARY_COLOR = '#595959'        # Grey for boundaries (instead of black)
BOUNDARY_WIDTH = 1.0
BOUNDARY_OPACITY = 0.5
BOUNDARY_FILL_OPACITY = 0         # No fill, just outlines

# Basemap overlay darkness (adjust these to control contrast)
LIBYA_OVERLAY_OPACITY = 0.1      # Darkness over Libya area (0.0 = no darkening, 0.5 = very dark)
SURROUNDING_OVERLAY_OPACITY = 0.3 # Darkness over areas outside Libya (0.0 = no darkening, 0.5 = very dark)

# Label styling
LABEL_FONT_SIZE = 11.5
LABEL_COLOR = '#000000'

# Tableau-like diverging behavior
TABLEAU_FIXED_RANGE = None   # e.g. 15 to force +/-15%; keep None for automatic
TABLEAU_STEPS = None         # e.g. 7 for "Stepped Color"; keep None for smooth

# ============================================================================
# DATA & COLORS
# ============================================================================

def load_geopoints_data(input_file: str) -> pd.DataFrame:
    df = pd.read_csv(input_file)
    df = df.dropna(subset=["X", "Y", "MEB", "Percent Change"])
    
    # Map old municipality names to new names
    name_mapping = {
        'Ejdabia': 'Ajdabiya',
        'Tripoli Center': 'Tripoli'
    }
    
    # Apply name mapping to ADM2_EN column
    if 'ADM2_EN' in df.columns:
        df['ADM2_EN'] = df['ADM2_EN'].replace(name_mapping)
    
    return df


def fetch_libya_boundaries_from_arcgis(url: str = ARCGIS_URL):
    """
    Load Libya admin boundaries from local file or fetch from ArcGIS REST API.
    Returns GeoJSON FeatureCollection.
    
    Priority:
    1. Use bundled local file (inputs/libya_boundaries.geojson) - BEST for Docker
    2. Fallback to ArcGIS API if local file not available
    
    Service ItemId: cdd05b98949743f98918c53ebe9aa789
    """
    
    # First, try to use bundled local file (Docker-friendly, no network needed)
    local_boundary_file = Path(__file__).parent.parent.parent.parent / "inputs" / "libya_boundaries.geojson"
    
    if local_boundary_file.exists():
        print(f"✓ Using bundled Libya boundaries from local file...")
        print(f"  Location: {local_boundary_file}")
        
        try:
            with open(local_boundary_file, 'r') as f:
                geojson_data = json.load(f)
            
            print(f"✓ Successfully loaded {len(geojson_data.get('features', []))} boundaries")
            
            # Print available fields
            if geojson_data.get('features'):
                sample_props = geojson_data['features'][0]['properties']
                print(f"\nAvailable fields in boundary data:")
                for key in sample_props.keys():
                    print(f"  - {key}: {sample_props[key]}")
            
            return geojson_data
            
        except Exception as e:
            print(f"✗ Error loading local file: {e}")
            print("  Falling back to ArcGIS API...")
    else:
        print(f"ℹ Local boundary file not found: {local_boundary_file}")
        print(f"  Fetching from ArcGIS API instead...")
    
    # Fallback: Fetch from ArcGIS API (requires network access)
    print(f"Fetching boundaries from ArcGIS...")
    print(f"Service ItemId: {ARCGIS_ITEM_ID}")
    
    # Parameters for the ArcGIS REST API query
    params = {
        'where': '1=1',  # Get all features
        'outFields': '*',  # Get all attributes
        'returnGeometry': 'true',
        'f': 'geojson'  # Return as GeoJSON
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        geojson_data = response.json()
        
        print(f"✓ Successfully fetched {len(geojson_data.get('features', []))} boundaries from API")
        
        # Print available fields to help with matching
        if geojson_data.get('features'):
            sample_props = geojson_data['features'][0]['properties']
            print(f"\nAvailable fields in ArcGIS data:")
            for key in sample_props.keys():
                print(f"  - {key}: {sample_props[key]}")
        
        return geojson_data
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Error fetching data from ArcGIS: {e}")
        print("\n❌ Could not load boundaries from local file or API")
        print("   To fix: Download boundaries with download_libya_boundaries.sh")
        raise

def build_colorscale():
    """
    Diverging Green-to-Yellow-to-Red palette based on percent change
    - Dark Green = Highest percent decrease (good)
    - Yellow = 0% change (neutral)
    - Dark Red = Highest percent increase (inflation/bad)
    
    9-color diverging palette: Green → Yellow → Red
    """
    return [
        [0.00, "#1B7302"],  # Dark green (largest decrease)
        [0.125, "#488F31"],  # Medium-dark green
        [0.25, "#6B9E3C"],  # Medium green
        [0.375, "#8AAC4A"],  # Yellow-green
        [0.50, "#FFE794"],  # Yellow (neutral - 0% change)
        [0.625, "#EB7B53"],  # Medium orange-red
        [0.75, "#E15D50"],  # Red-orange
        [0.875, "#D9042B"],  # Medium red
        [1.00, "#BF0413"],  # Dark red (largest increase)
    ]


def tableau_diverging_color(pct: float, max_abs: float) -> str:
    """
    Tableau-like diverging mapping:
    - center at 0
    - symmetric range [-max_abs, +max_abs]
    - optionally stepped (like Tableau 'Stepped color')
    """
    colorscale = build_colorscale()

    if max_abs <= 0:
        return colorscale[1][1]  # neutral

    # clamp to symmetric range
    x = max(-max_abs, min(max_abs, pct))

    # map [-max_abs, +max_abs] -> [0, 1] with 0 at center
    t = (x / max_abs + 1) / 2

    # optional stepped colors
    if TABLEAU_STEPS and TABLEAU_STEPS > 1:
        step = 1 / (TABLEAU_STEPS - 1)
        t = round(t / step) * step
        t = max(0, min(1, t))

    # interpolate along stops
    for i in range(len(colorscale) - 1):
        v1, c1 = colorscale[i]
        v2, c2 = colorscale[i + 1]
        if v1 <= t <= v2:
            u = (t - v1) / (v2 - v1) if v2 != v1 else 0

            rgb1 = tuple(int(c1[j:j+2], 16) for j in (1, 3, 5))
            rgb2 = tuple(int(c2[j:j+2], 16) for j in (1, 3, 5))

            r = int(rgb1[0] + u * (rgb2[0] - rgb1[0]))
            g = int(rgb1[1] + u * (rgb2[1] - rgb1[1]))
            b = int(rgb1[2] + u * (rgb2[2] - rgb1[2]))

            return f"#{r:02X}{g:02X}{b:02X}"

    return colorscale[-1][1]


def calculate_bubble_sizes(df: pd.DataFrame) -> np.ndarray:
    """
    Bubble size based on SIGNED Percent Change:
    min (most negative) -> smallest bubble
    max (most positive) -> largest bubble
    """
    pct = df["Percent Change"].values.astype(float)
    pmin, pmax = pct.min(), pct.max()

    if pmax == pmin:
        return np.full(len(pct), BUBBLE_MIN_SIZE)

    normalized = (pct - pmin) / (pmax - pmin)  # signed scaling
    return BUBBLE_MIN_SIZE + normalized * (BUBBLE_MAX_SIZE - BUBBLE_MIN_SIZE)

def get_manual_label_positions():
    """Manual label offsets

        'Municipality': (X_offset, Y_offset)
                            ↑          ↑
                            |          |
                        Horizontal   Vertical

        X (first number): Horizontal position

        Negative = Move LEFT (west)
        Positive = Move RIGHT (east)


        Y (second number): Vertical position

        Negative = Move DOWN (south)
        Positive = Move UP (north)
    """
    return {
        # West
        'Azzawya':        (-0.3, 0.02),  
        'Tripoli':        (0.3, 0.3),   
        'AlKhums':        (-0.08, 1.0),    
        'Zliten':         (-0.2, -0.04),   
        'Misrata':        (0.1, -0.3),    
        'Zwara':          (-0.8, 1.26),   
        'Nalut':          (-0.5, -0.60),
        'Sirt':           (0.02, 0.07),

        # East
        'Benghazi':       (-0.10, -0.07),
        'Derna':          (0.0, 0.0),
        'AlBayda':        (-0.8, 0.8),
        'Tobruk':         (0.0, 0.0),
        'Ajdabiya':        (0.0, 0.0),
        'AlKufra':        (0.0, 0.0),

        # South
        'Sebha':          (0.0, 0.0),
        'Ubari':          (0.0, 0.0),
        'Ghat':           (0.0, 0.0),
        'Murzuq':         (0.0, 0.0),
        'AlJufra':        (0.0, 0.0),
        'Wadi Alshati':   (0.0, 0.0),
        'Algatroun':      (0.0, 0.0),
    }


# ============================================================================
# MAP CREATION (FOLIUM VERSION)
# ============================================================================

def create_libya_map_folium(df: pd.DataFrame, output_file: Path):
    """Create interactive map using Folium with visible admin boundaries."""

    df = df.copy()
    df["Percent Change"] = pd.to_numeric(df["Percent Change"], errors="coerce")
    df["MEB"] = pd.to_numeric(df["MEB"], errors="coerce")
    df = df.dropna(subset=["X", "Y", "MEB", "Percent Change"])

    # Bubble size based on signed percent change
    sizes = calculate_bubble_sizes(df)

    pct = df["Percent Change"].astype(float)

    # ---- Tableau-like range (pick ONE) ----
    # A) Tableau "Automatic"
    max_abs = float(pct.abs().quantile(0.95))

    # B) Tableau "Fixed" (uncomment if you want consistent colors month-to-month)
    # FIXED_RANGE = 15.0   # means -15%..+15%
    # max_abs = float(FIXED_RANGE)

    # Color: decrease (negative)=green, increase (positive)=red
    df["color"] = pct.apply(lambda p: tableau_diverging_color(p, max_abs))

    # Prints (debug)
    pct_min = float(pct.min())
    pct_max = float(pct.max())

    print(f"Tableau diverging range: {-max_abs:.1f}% to {max_abs:.1f}% (0% midpoint)")
    print(f"Raw change range: {pct_min:.1f}% to {pct_max:.1f}%")

    label_positions = get_manual_label_positions()

    print(f"MEB range: {df['MEB'].min():.2f} – {df['MEB'].max():.2f}")
    print(f"Change range: {pct_min:.1f}% to {pct_max:.1f}%\n")

    # Create base map
    m = folium.Map(
        location=[MAP_CENTER_LAT, MAP_CENTER_LON],
        zoom_start=MAP_ZOOM,
        tiles=TILESET,
        control_scale=True
    )

    # ------------------------------------------------------------------
    # 1) ADD ADMIN BOUNDARIES FROM ARCGIS
    # ------------------------------------------------------------------
    libya_geojson = fetch_libya_boundaries_from_arcgis()
    
    print(f"\nAdding {len(libya_geojson['features'])} admin boundaries to map...")
    
    # Determine the name field from the first feature
    # Common field names: 'ADM2_EN', 'NAME', 'admin2Name', 'name', etc.
    sample_feature = libya_geojson['features'][0]
    name_field = None
    for possible_name in ['ADM2_EN', 'admin2Name', 'NAME', 'name', 'Name', 'ADMIN2']:
        if possible_name in sample_feature['properties']:
            name_field = possible_name
            print(f"Using '{name_field}' as the region name field")
            break
    
    if not name_field:
        name_field = list(sample_feature['properties'].keys())[0]
        print(f"⚠ Could not find standard name field, using '{name_field}'")
    
    # Add dark overlay over Libya area
    if LIBYA_OVERLAY_OPACITY > 0:
        folium.GeoJson(
            libya_geojson,
            name='Libya Overlay',
            style_function=lambda feature: {
                'fillColor': '#000000',
                'fillOpacity': LIBYA_OVERLAY_OPACITY,
                'color': 'transparent',
                'weight': 0,
            },
            show=False
        ).add_to(m)
    
    # Add dark overlay over surrounding areas (outside Libya)
    if SURROUNDING_OVERLAY_OPACITY > 0:
        # Create inverse mask - covers world with Libya cut out as holes
        world_with_libya_hole = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        # Outer ring - world bounds
                        [
                            [-180, -90],
                            [-180, 90],
                            [180, 90],
                            [180, -90],
                            [-180, -90]
                        ]
                    ]
                }
            }]
        }
        
        # Add holes for each Libya admin region
        for feature in libya_geojson['features']:
            if feature['geometry']['type'] == 'Polygon':
                world_with_libya_hole['features'][0]['geometry']['coordinates'].append(
                    feature['geometry']['coordinates'][0]
                )
            elif feature['geometry']['type'] == 'MultiPolygon':
                for polygon in feature['geometry']['coordinates']:
                    world_with_libya_hole['features'][0]['geometry']['coordinates'].append(
                        polygon[0]
                    )
        
        folium.GeoJson(
            world_with_libya_hole,
            name='Surrounding Areas Overlay',
            style_function=lambda feature: {
                'fillColor': '#000000',
                'fillOpacity': SURROUNDING_OVERLAY_OPACITY,
                'color': 'transparent',
                'weight': 0,
            },
            show=False
        ).add_to(m)
    
    # Add the boundary lines
    folium.GeoJson(
        libya_geojson,
        name='Admin Boundaries',
        style_function=lambda feature: {
            'fillColor': 'transparent',
            'fillOpacity': BOUNDARY_FILL_OPACITY,
            'color': BOUNDARY_COLOR,
            'weight': BOUNDARY_WIDTH,
            'opacity': BOUNDARY_OPACITY
        },
        tooltip=folium.GeoJsonTooltip(
            fields=[name_field],
            aliases=['Region:'],
            style="background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;"
        )
    ).add_to(m)

    # ------------------------------------------------------------------
    # 2) ADD BUBBLES
    # ------------------------------------------------------------------
    print(f"Adding {len(df)} municipality bubbles...")
    
    for idx, row in df.iterrows():
        # Create popup with MEB info
        popup_html = f"""
        <div style="font-family: Arial; font-size: 12px; min-width: 150px;">
            <b>{row['ADM2_EN']}</b><br>
            MEB: LYD {row['MEB']:.2f}<br>
            Change: {row['Percent Change']:+.1f}%
        </div>
        """
        
        folium.CircleMarker(
            location=[row['Y'], row['X']],
            radius=sizes[idx],  
            color=BUBBLE_BORDER_COLOR,
            weight=BUBBLE_BORDER_WIDTH,
            opacity=BUBBLE_OPACITY,           # ✅ border opacity
            fill=True,
            fillColor=row['color'],
            fillOpacity=BUBBLE_OPACITY,       # ✅ fill opacity
            popup=folium.Popup(popup_html, max_width=200),
            tooltip=row['ADM2_EN']
        ).add_to(m)

    # ------------------------------------------------------------------
    # 3) ADD LABELS
    # ------------------------------------------------------------------
    print("Adding labels...")
    
    for idx, row in df.iterrows():
        muni = row["ADM2_EN"]
        if muni not in label_positions:
            continue

        offset_x, offset_y = label_positions[muni]
        label_lon = row["X"] + offset_x
        label_lat = row["Y"] + offset_y

        pct = row["Percent Change"]
        bubble_color = row["color"]  # Get the bubble's color
        symbol = "▲" if pct > 0 else ("▼" if pct < 0 else "")
        sign = "+" if pct > 0 else ""
        
        # Split label into municipality name (black) and change info (colored)
        muni_text = f"{muni} (LYD {row['MEB']:.2f}): "
        change_text = f"{symbol}{sign}{pct:.1f}%"
        
        # Use DivIcon for text labels with colored percent change
        folium.Marker(
            location=[label_lat, label_lon],
            icon=folium.DivIcon(html=f"""
                <div style="
                    font-size: {LABEL_FONT_SIZE}px;
                    font-family: Arial, sans-serif;
                    font-weight: normal;
                    white-space: nowrap;
                    text-shadow: 1px 1px 2px white, -1px -1px 2px white, 1px -1px 2px white, -1px 1px 2px white;
                ">
                    <span style="color: {LABEL_COLOR};">{muni_text}</span><span style="color: {bubble_color}; font-weight: bold;">{change_text}</span>
                </div>
            """)
        ).add_to(m)

    # ------------------------------------------------------------------
    # 4) ADD TITLE
    # ------------------------------------------------------------------
    title_html = '''
    <div style="position: fixed; 
                top: 10px; 
                left: 50%; 
                transform: translateX(-50%);
                width: 600px;
                z-index: 9999; 
                font-size: 18px;
                font-weight: bold;
                background-color: white;
                border: 2px solid grey;
                border-radius: 5px;
                padding: 10px;
                text-align: center;
                font-family: Arial, sans-serif;">
        Libya – Full MEB by Mantika
        <br>
        <span style="font-size: 12px; font-weight: normal;">
            Bubble size and Color = Percent Change
        </span>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))

    # Add layer control
    folium.LayerControl().add_to(m)

    # Save map
    output_file.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(output_file))
    print(f"✓ Saved: {output_file}")
    
    return m


# ============================================================================
# MAIN
# ============================================================================

def generate_libya_map(input_file: str, output_dir: str):
    """
    Generate Libya MEB map for a given geopoints CSV and output directory.
    """
    print("\n=== LIBYA MEB MAP (FOLIUM + ARCGIS) ===")
    df = load_geopoints_data(input_file)
    output_path = Path(output_dir) / "Libya_MEB_Map.html"
    create_libya_map_folium(df, output_path)
    return output_path


if __name__ == "__main__":
    # Usage:
    #   python meb_map.py <year> <month>
    # Example:
    #   python meb_map.py 2025 11
    if len(sys.argv) >= 3:
        year = int(sys.argv[1])
        month = int(sys.argv[2])

        # Use central config to get correct monthly paths
        paths = get_month_paths(year, month)

        # Monthly geopoints CSV:
        #   <Monthly Reports>/<year>/<Month>/Tables/Geopoints_MEB_<tag>.csv
        input_file = paths["geopoints"]

        # Monthly map folder:
        #   <Monthly Reports>/<year>/<Month>/Graphics/Map
        output_dir = paths["map"]

        print(f"Using geopoints file: {input_file}")
        print(f"Output directory: {output_dir}")

        generate_libya_map(str(input_file), str(output_dir))
    else:
        # Fallback for manual testing without year/month arguments
        # Uses original defaults in /outputs
        print("No year/month provided. Falling back to default INPUT_FILE and OUTPUT_DIR.")
        generate_libya_map(INPUT_FILE, OUTPUT_DIR)