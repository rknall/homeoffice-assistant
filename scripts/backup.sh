#!/bin/bash
# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
# Backup HomeOffice Assistant data (database, avatars, logos).
# Usage: ./scripts/backup.sh [--docker <container>] [backup_dir]
#
# Archive layout (one top-level directory):
#   <name>/homeoffice_assistant.db
#   <name>/avatars/
#   <name>/logos/

set -euo pipefail

CONTAINER=""
BACKUP_DIR=""
while [ $# -gt 0 ]; do
    case "$1" in
        --docker)
            if [ $# -lt 2 ]; then
                echo "Error: --docker needs a container name" >&2
                exit 1
            fi
            CONTAINER="$2"
            shift 2
            ;;
        -h | --help)
            echo "Usage: $0 [--docker <container>] [backup_dir]"
            exit 0
            ;;
        *)
            BACKUP_DIR="$1"
            shift
            ;;
    esac
done

BACKUP_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$BACKUP_DIR"
BACKUP_DIR="$(cd "$BACKUP_DIR" && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="homeoffice_assistant_backup_${TIMESTAMP}"

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
BACKUP_PATH="${STAGE}/${BACKUP_NAME}"
mkdir -p "$BACKUP_PATH"

if [ -n "$CONTAINER" ]; then
    # The online backup API runs inside the container (system python), so a
    # database being written to is copied consistently.
    echo "Backing up database from container ${CONTAINER}..."
    docker exec "$CONTAINER" python -c "
import sqlite3
src = sqlite3.connect('/app/data/homeoffice_assistant.db')
dst = sqlite3.connect('/tmp/hoa_backup.db')
src.backup(dst)
dst.close()
src.close()
"
    docker cp "${CONTAINER}:/tmp/hoa_backup.db" "${BACKUP_PATH}/homeoffice_assistant.db"
    docker exec "$CONTAINER" rm -f /tmp/hoa_backup.db

    for entry in "avatars:/app/static/avatars" "logos:/app/data/logos"; do
        name="${entry%%:*}"
        path="${entry#*:}"
        if docker exec "$CONTAINER" test -d "$path"; then
            echo "Backing up ${name}..."
            docker cp "${CONTAINER}:${path}" "${BACKUP_PATH}/${name}"
        fi
    done
else
    if ! command -v sqlite3 > /dev/null 2>&1; then
        echo "Error: sqlite3 not found in PATH" >&2
        exit 1
    fi
    DB="./data/homeoffice_assistant.db"
    if [ ! -f "$DB" ]; then
        echo "Error: database not found at ${DB}" >&2
        exit 1
    fi
    echo "Backing up database..."
    sqlite3 "$DB" ".backup '${BACKUP_PATH}/homeoffice_assistant.db'"

    for entry in "avatars:./static/avatars" "logos:./data/logos"; do
        name="${entry%%:*}"
        path="${entry#*:}"
        if [ -d "$path" ]; then
            echo "Backing up ${name}..."
            cp -R "$path" "${BACKUP_PATH}/${name}"
        fi
    done
fi

if [ ! -s "${BACKUP_PATH}/homeoffice_assistant.db" ]; then
    echo "Error: database backup is empty" >&2
    exit 1
fi

echo "Creating archive..."
tar -czf "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" -C "$STAGE" "$BACKUP_NAME"

echo "Backup complete: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
