#!/bin/bash
# Download Libya ADM2 Boundaries from ArcGIS
# This is a ONE-TIME operation to bundle boundaries in the repo

echo "=================================="
echo "DOWNLOADING LIBYA BOUNDARIES"
echo "=================================="
echo ""

# Detect project root (works in Docker or locally)
if [ -d "/app" ]; then
    # Running in Docker
    PROJECT_ROOT="/app"
else
    # Running locally - assume script is in scripts/00_Setup/
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi

# Output file location
OUTPUT_FILE="$PROJECT_ROOT/inputs/libya_boundaries.geojson"

echo "📁 Project root: $PROJECT_ROOT"
echo ""

# ArcGIS URL with proper parameters
URL="https://services8.arcgis.com/ULOknP0QwPHCdswE/arcgis/rest/services/Libya_ADM2_Boundaries/FeatureServer/0/query"

echo "📍 Fetching from ArcGIS..."
echo "   URL: $URL"
echo ""

# Download boundaries as GeoJSON
curl -G "$URL" \
  --data-urlencode "where=1=1" \
  --data-urlencode "outFields=*" \
  --data-urlencode "f=geojson" \
  --output "$OUTPUT_FILE" \
  --silent \
  --show-error \
  --location \
  --max-time 30

# Check if download was successful
if [ $? -eq 0 ] && [ -s "$OUTPUT_FILE" ]; then
    echo "✅ Download successful!"
    echo ""
    echo "📊 File details:"
    echo "   Location: $OUTPUT_FILE"
    echo "   Size: $(du -h "$OUTPUT_FILE" | cut -f1)"
    echo ""
    
    # Validate it's valid JSON
    if python3 -c "import json; json.load(open('$OUTPUT_FILE'))" 2>/dev/null; then
        echo "✅ Valid GeoJSON file"
        
        # Count features
        FEATURES=$(python3 -c "import json; print(len(json.load(open('$OUTPUT_FILE'))['features']))")
        echo "   Features: $FEATURES municipalities"
    else
        echo "❌ Invalid JSON file - download may have failed"
        exit 1
    fi
else
    echo "❌ Download failed!"
    echo "   Check your internet connection"
    exit 1
fi

echo ""
echo "=================================="
echo "✅ BOUNDARIES DOWNLOADED"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Commit the file: git add inputs/libya_boundaries.geojson"
echo "2. Update meb_map.py to use local file"
echo ""