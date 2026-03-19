#!/bin/bash
# Libya PMM - Database Restore Script
# Restores a PostgreSQL backup to the libya_pmm database
#
# Usage:
#     bash scripts/00_Setup/restore_database.sh <backup_file>
#
# Example:
#     bash scripts/00_Setup/restore_database.sh backups/libya_pmm_backup_20251227_143022.sql
#
# ⚠️  WARNING: This will REPLACE the current database with the backup!
#    All current data will be lost.
#
# What gets restored:
#     - All tables (schema + data)
#     - keys, locations (reference data)
#     - All historical MEB data
#     - All historical commodity prices
#     - All historical exchange rates

# Check if backup file is provided
if [ $# -eq 0 ]; then
    echo "❌ Error: No backup file specified"
    echo ""
    echo "Usage: bash scripts/00_Setup/restore_database.sh <backup_file>"
    echo ""
    echo "Example:"
    echo "  bash scripts/00_Setup/restore_database.sh backups/libya_pmm_backup_20251227_143022.sql"
    exit 1
fi

BACKUP_FILE="$1"

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "======================================================================"
echo "LIBYA PMM - DATABASE RESTORE"
echo "======================================================================"
echo ""
echo "Backup file: $BACKUP_FILE"
echo "File size: $(du -h "$BACKUP_FILE" | cut -f1)"
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

# Confirmation prompt
echo "⚠️  WARNING: This will REPLACE the current database!"
echo "   All current data in libya_pmm will be DELETED."
echo ""
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo ""
    echo "❌ Restore cancelled"
    exit 0
fi

echo ""
echo "🔄 Restoring database..."
echo ""

# Restore using psql
PGPASSWORD="${DB_PASSWORD:?Set DB_PASSWORD environment variable}" psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "${DB_USER:?Set DB_USER environment variable}" \
    -d postgres \
    -f "$BACKUP_FILE"

# Check if restore was successful
if [ $? -eq 0 ]; then
    echo ""
    echo "======================================================================"
    echo "✅ DATABASE RESTORE COMPLETE"
    echo "======================================================================"
    echo ""
    echo "The libya_pmm database has been restored from:"
    echo "  $BACKUP_FILE"
    echo ""
    echo "Next steps:"
    echo "  1. Verify data: docker exec -it libya_pmm_app python -c 'from config import get_engine; print(get_engine())'"
    echo "  2. Continue monthly workflow: python 99_run_step03_to_step06.py 2025 12"
    echo ""
else
    echo ""
    echo "======================================================================"
    echo "❌ DATABASE RESTORE FAILED"
    echo "======================================================================"
    echo ""
    echo "Common issues:"
    echo "  • PostgreSQL not running: docker-compose up -d"
    echo "  • Wrong database credentials"
    echo "  • Corrupt backup file"
    echo "  • Insufficient permissions"
    exit 1
fi