#!/bin/bash
# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
# Backup Travel Manager data
# Usage: ./scripts/backup.sh [backup_dir]

set -e

BACKUP_DIR="${1:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="travel_manager_backup_${TIMESTAMP}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

mkdir -p "$BACKUP_PATH"

# Backup SQLite database
if [ -f "./data/travel_manager.db" ]; then
    echo "Backing up database..."
    sqlite3 ./data/travel_manager.db ".backup '${BACKUP_PATH}/travel_manager.db'"
else
    echo "Warning: Database not found at ./data/travel_manager.db"
fi

# Backup avatars
if [ -d "./static/avatars" ] && [ "$(ls -A ./static/avatars 2>/dev/null)" ]; then
    echo "Backing up avatars..."
    cp -r ./static/avatars "$BACKUP_PATH/"
fi

# Create tarball
echo "Creating archive..."
cd "$BACKUP_DIR"
tar -czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME"
rm -rf "$BACKUP_NAME"

echo "Backup complete: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
