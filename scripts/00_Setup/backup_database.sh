#!/bin/bash
# Libya PMM - Database Backup Script
# Creates a PostgreSQL backup of the libya_pmm database
#
# Usage:
#     bash scripts/00_Setup/backup_database.sh
#     bash scripts/00_Setup/backup_database.sh /path/to/custom/location
#
# Output:
#     Creates a timestamped .sql backup file:
#     backups/libya_pmm_backup_YYYYMMDD_HHMMSS.sql
#
# The backup includes:
#     - All tables (schema + data)
#     - keys, locations (reference data)
#     - municipality_meb, regional_meb, national_meb (all historical MEB data)
#     - products (all historical commodity prices)
#     - exchange_rates (all historical exchange rates)
#
# To restore:
#     bash scripts/00_Setup/restore_database.sh backups/libya_pmm_backup_YYYYMMDD_HHMMSS.sql

# Default backup directory
BACKUP_DIR="${1:-backups}"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Generate timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Backup filename
BACKUP_FILE="$BACKUP_DIR/libya_pmm_backup_$TIMESTAMP.sql"

echo "======================================================================"
echo "LIBYA PMM - DATABASE BACKUP"
echo "======================================================================"
echo ""
echo "Database: libya_pmm"
echo "Output: $BACKUP_FILE"
echo ""

# Check if running in Docker or locally
if [ -f /.dockerenv ]; then
    # Running in Docker
    echo "📦 Running in Docker container..."
    DB_HOST="postgres"
    DB_PORT="5432"
else
    # Running locally
    echo "💻 Running locally..."
    DB_HOST="${DB_HOST:-localhost}"
    DB_PORT="${DB_PORT:-5433}"
fi

echo "🔌 Connecting to: $DB_HOST:$DB_PORT"
echo ""

# Create backup using pg_dump
PGPASSWORD="${DB_PASSWORD:?Set DB_PASSWORD environment variable}" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "${DB_USER:?Set DB_USER environment variable}" \
    -d "${DB_NAME:?Set DB_NAME environment variable}" \
    --clean \
    --if-exists \
    --create \
    -f "$BACKUP_FILE"

# Check if backup was successful
if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✅ BACKUP COMPLETE"
    echo ""
    echo "📁 File: $BACKUP_FILE"
    echo "💾 Size: $BACKUP_SIZE"
    echo ""
    echo "This backup includes:"
    echo "  • Database schema (all 7 tables)"
    echo "  • Reference data (keys, locations)"
    echo "  • All historical MEB data"
    echo "  • All historical commodity prices"
    echo "  • All historical exchange rates"
    echo ""
    echo "To restore this backup:"
    echo "  bash scripts/00_Setup/restore_database.sh $BACKUP_FILE"
    echo ""
    echo "To transfer to another machine:"
    echo "  1. Copy $BACKUP_FILE to new machine"
    echo "  2. Run restore script on new machine"
else
    echo "❌ BACKUP FAILED"
    echo ""
    echo "Common issues:"
    echo "  • PostgreSQL not running: docker-compose up -d"
    echo "  • Wrong database credentials"
    echo "  • Network connection issues"
    exit 1
fi