#!/bin/bash
# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
# Restore HomeOffice Assistant data from a backup archive.
# Usage: ./scripts/restore.sh --force <backup_file.tar.gz>
#
# Replaces ./data/homeoffice_assistant.db, ./static/avatars and ./data/logos.
# Stop the application first. The current database is kept as a .pre-restore copy.

set -euo pipefail

FORCE=0
BACKUP_FILE=""
for arg in "$@"; do
    case "$arg" in
        --force) FORCE=1 ;;
        *) BACKUP_FILE="$arg" ;;
    esac
done

if [ -z "$BACKUP_FILE" ] || [ "$FORCE" -ne 1 ]; then
    echo "Usage: $0 --force <backup_file.tar.gz>" >&2
    echo "Restore overwrites the current database, avatars and logos." >&2
    exit 1
fi
if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: ${BACKUP_FILE} not found" >&2
    exit 1
fi
BACKUP_FILE="$(cd "$(dirname "$BACKUP_FILE")" && pwd)/$(basename "$BACKUP_FILE")"

# Validate archive member paths before extracting anything.
if ! tar -tzf "$BACKUP_FILE" > /dev/null; then
    echo "Error: ${BACKUP_FILE} is not a readable archive" >&2
    exit 1
fi
if tar -tzf "$BACKUP_FILE" | grep -Eq '^/|(^|/)\.\.(/|$)'; then
    echo "Error: archive contains absolute or '..' paths" >&2
    exit 1
fi
TOP_DIRS=$(tar -tzf "$BACKUP_FILE" | sed -e 's#^\./##' -e 's#/.*##' | grep -v '^$' | sort -u)
if [ "$(printf '%s\n' "$TOP_DIRS" | wc -l)" -ne 1 ]; then
    echo "Error: archive must contain exactly one top-level directory" >&2
    exit 1
fi

TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TEMP_DIR"' EXIT
tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"
SRC="${TEMP_DIR}/${TOP_DIRS}"
if [ ! -d "$SRC" ]; then
    echo "Error: archive top level is not a directory" >&2
    exit 1
fi

RESTORED=0
DB="./data/homeoffice_assistant.db"

if [ -f "${SRC}/homeoffice_assistant.db" ]; then
    mkdir -p ./data
    if [ -f "$DB" ]; then
        PRE="${DB}.pre-restore.$(date +%Y%m%d_%H%M%S)"
        echo "Backing up current database to ${PRE}"
        cp "$DB" "$PRE"
    fi
    echo "Restoring database..."
    rm -f "${DB}-wal" "${DB}-shm"
    cp "${SRC}/homeoffice_assistant.db" "$DB"
    RESTORED=1
fi

if [ -d "${SRC}/avatars" ]; then
    echo "Restoring avatars..."
    mkdir -p ./static
    rm -rf ./static/avatars
    cp -R "${SRC}/avatars" ./static/avatars
    RESTORED=1
fi

if [ -d "${SRC}/logos" ]; then
    echo "Restoring logos..."
    mkdir -p ./data
    rm -rf ./data/logos
    cp -R "${SRC}/logos" ./data/logos
    RESTORED=1
fi

if [ "$RESTORED" -ne 1 ]; then
    echo "Error: nothing restored; archive has no database, avatars or logos" >&2
    exit 1
fi

echo "Restore complete!"
echo "Note: Restart the application to apply changes."
