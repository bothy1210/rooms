#!/usr/bin/env bash
# ============================================================
# Restore the UZ Room System database from a gzip dump.
# Usage: ./restore_db.sh /var/roomsys/backups/roomsys-YYYYMMDD-HHMMSS.sql.gz
# WARNING: this overwrites the current database contents.
# ============================================================
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <backup-file.sql.gz>"
    exit 1
fi

BACKUP_FILE="$1"
DB_NAME="${ROOMSYS_DB_NAME:-roomsys_db}"
DB_USER="${ROOMSYS_DB_USER:-roomsys}"

if [[ ! -f "$BACKUP_FILE" ]]; then
    echo "Backup file not found: $BACKUP_FILE"
    exit 1
fi

read -r -p "This will OVERWRITE database '$DB_NAME'. Continue? [y/N] " confirm
[[ "$confirm" == "y" || "$confirm" == "Y" ]] || { echo "Aborted."; exit 0; }

echo "Restoring $BACKUP_FILE into $DB_NAME ..."
gunzip -c "$BACKUP_FILE" | psql --username="$DB_USER" "$DB_NAME"
echo "Restore complete."
