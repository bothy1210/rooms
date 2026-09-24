#!/usr/bin/env bash
# ============================================================
# Nightly PostgreSQL backup for the UZ Room System.
# Scheduled from deploy/cron/roomsys.cron.
# Keeps the last 14 daily dumps, gzip-compressed.
# ============================================================
set -euo pipefail

BACKUP_DIR="/var/roomsys/backups"
DB_NAME="${ROOMSYS_DB_NAME:-roomsys_db}"
DB_USER="${ROOMSYS_DB_USER:-roomsys}"
RETENTION_DAYS=14

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUTFILE="$BACKUP_DIR/roomsys-$STAMP.sql.gz"

# pg_dump reads the password from ~/.pgpass or the PGPASSWORD env var.
pg_dump --username="$DB_USER" --no-owner "$DB_NAME" | gzip > "$OUTFILE"
echo "$(date '+%F %T')  backup written: $OUTFILE"

# Prune old backups.
find "$BACKUP_DIR" -name 'roomsys-*.sql.gz' -mtime +"$RETENTION_DAYS" -delete
echo "$(date '+%F %T')  pruned backups older than ${RETENTION_DAYS} days"
