#!/bin/bash
# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
# Backup from Docker container
# Usage: ./scripts/docker-backup.sh [container_name] [backup_dir]

set -e

CONTAINER="${1:-homeoffice-assistant}"
BACKUP_DIR="${2:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="homeoffice_assistant_backup_${TIMESTAMP}"

mkdir -p "$BACKUP_DIR"

echo "Copying data from container..."
docker cp "${CONTAINER}:/app/data" "${BACKUP_DIR}/${BACKUP_NAME}_data" 2>/dev/null || true
docker cp "${CONTAINER}:/app/static/avatars" "${BACKUP_DIR}/${BACKUP_NAME}_avatars" 2>/dev/null || true

# Create tarball
cd "$BACKUP_DIR"
tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}_data" "${BACKUP_NAME}_avatars" 2>/dev/null || \
tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}_data"
rm -rf "${BACKUP_NAME}_data" "${BACKUP_NAME}_avatars"

echo "Backup complete: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
