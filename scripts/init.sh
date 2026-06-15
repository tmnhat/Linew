#!/bin/bash
#
# Linew initialization script.
# Run this before starting the application for the first time.
#

set -e

echo "=== Linew Initialization Script ==="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "Please edit .env and set your credentials before continuing."
    exit 1
fi

# Create backup directory for linew-data volume
if [ -n "$LINEW_DATA_PATH" ]; then
    BACKUP_DIR="$LINEW_DATA_PATH"
else
    BACKUP_DIR="/Users/tmnhat/Backup-Linew"
fi

if [ ! -d "$BACKUP_DIR" ]; then
    echo "Creating backup directory: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
    echo "Backup directory created."
else
    echo "Backup directory already exists: $BACKUP_DIR"
fi

echo ""
echo "=== Initialization Complete ==="
echo ""
echo "To start Linew, run:"
echo "  docker-compose up -d"
echo ""
