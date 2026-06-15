#!/bin/bash
# Linew Storage Setup Script
# Run once when setting up Linew for the first time
# Creates data directories and prepares for archiving and backup

set -e

echo "=== Linew Storage Setup ==="
echo ""

# Configuration
DATA_DIR="/Users/tmnhat/Backup-Linew"

# 1. Create data directories
echo "Creating data directories at ${DATA_DIR}..."

mkdir -p "${DATA_DIR}/archive/signals"
mkdir -p "${DATA_DIR}/archive/articles"
mkdir -p "${DATA_DIR}/archive/predictions"
mkdir -p "${DATA_DIR}/archive/market_research"
mkdir -p "${DATA_DIR}/backup/tmp"
mkdir -p "${DATA_DIR}/backup/logs"
mkdir -p "${DATA_DIR}/models"

echo "  ✅ Archive directories created"
echo "  ✅ Backup directories created"
echo "  ✅ Models directory created"
echo ""

# 2. Check for rclone
echo "Checking for rclone..."
if ! command -v rclone &> /dev/null; then
    echo "  ⚠️  rclone not found - Google Drive backup will not be configured"
    echo "  To install: brew install rclone"
    echo ""
else
    echo "  ✅ rclone is installed"

    # 3. Check if rclone is configured with Google Drive
    echo ""
    echo "Checking Google Drive configuration..."
    if rclone listremotes | grep -q "^gdrive:"; then
        echo "  ✅ Google Drive remote 'gdrive' is configured"

        # Create Drive folders
        echo "Creating Google Drive folder structure..."
        rclone mkdir gdrive:Linew-Backups/archive/signals
        rclone mkdir gdrive:Linew-Backups/archive/articles
        rclone mkdir gdrive:Linew-Backups/archive/predictions
        rclone mkdir gdrive:Linew-Backups/archive/market_research
        rclone mkdir gdrive:Linew-Backups/daily
        echo "  ✅ Google Drive folders created"
    else
        echo "  ⚠️  Google Drive remote not configured"
        echo ""
        echo "To configure Google Drive:"
        echo "  1. Run: rclone config"
        echo "  2. Choose: New remote"
        echo "  3. Name: gdrive"
        echo "  4. Type: Google Drive"
        echo "  5. Follow the prompts to authorize"
        echo ""
    fi
fi

# 4. Create .gitkeep files to preserve directory structure
echo "Creating .gitkeep files..."
touch "${DATA_DIR}/archive/signals/.gitkeep"
touch "${DATA_DIR}/archive/articles/.gitkeep"
touch "${DATA_DIR}/archive/predictions/.gitkeep"
touch "${DATA_DIR}/archive/market_research/.gitkeep"
touch "${DATA_DIR}/backup/tmp/.gitkeep"
touch "${DATA_DIR}/backup/logs/.gitkeep"
touch "${DATA_DIR}/models/.gitkeep"
echo "  ✅ .gitkeep files created"

# 5. Summary
echo ""
echo "=== Setup Complete ==="
echo ""
echo "Data directory:    ${DATA_DIR}"
echo ""
echo "Archive structure:"
echo "  ${DATA_DIR}/archive/signals/YYYY-MM.db"
echo "  ${DATA_DIR}/archive/articles/YYYY-MM.db"
echo "  ${DATA_DIR}/archive/predictions/YYYY-MM.db"
echo "  ${DATA_DIR}/archive/market_research/YYYY-MM.db"
echo ""
echo "Backup structure:"
echo "  ${DATA_DIR}/backup/tmp/YYYY-MM-DD/  (daily backups)"
echo "  ${DATA_DIR}/backup/logs/             (backup logs)"
echo ""
echo "Next steps:"
echo "  1. Run database migration: alembic upgrade head"
echo "  2. Restart Docker containers: docker-compose down && docker-compose up -d"
echo "  3. Test the storage API: curl http://localhost:8000/api/storage/stats"
echo ""
echo "Schedule:"
echo "  2:00 AM  - Daily incremental archive"
echo "  2:00 AM  - Monthly full archive (1st of month)"
echo "  3:00 AM  - PostgreSQL cleanup (1st of month)"
echo "  4:00 AM  - Google Drive backup"
echo ""
