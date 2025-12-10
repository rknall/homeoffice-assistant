#!/bin/bash
# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
# Restore HomeOffice Assistant data from backup
# Usage: ./scripts/restore.sh <backup_file.tar.gz>

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file.tar.gz>"
    exit 1
fi

BACKUP_FILE="$1"
TEMP_DIR=$(mktemp -d)

echo "Extracting backup..."
tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"
BACKUP_NAME=$(ls "$TEMP_DIR")

# Restore database
if [ -f "${TEMP_DIR}/${BACKUP_NAME}/homeoffice_assistant.db" ]; then
    echo "Restoring database..."
    mkdir -p ./data
    cp "${TEMP_DIR}/${BACKUP_NAME}/homeoffice_assistant.db" ./data/
fi

# Restore avatars
if [ -d "${TEMP_DIR}/${BACKUP_NAME}/avatars" ]; then
    echo "Restoring avatars..."
    mkdir -p ./static
    cp -r "${TEMP_DIR}/${BACKUP_NAME}/avatars" ./static/
fi

# Cleanup
rm -rf "$TEMP_DIR"

echo "Restore complete!"
echo "Note: Restart the application to apply changes."
