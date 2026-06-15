#!/bin/bash
# Auto-install WordPress

set -e

WP_URL="https://litimez.ai"
BLOG_TITLE="LiTimez"
ADMIN_USER="admin"
ADMIN_EMAIL="admin@litimez.ai"

echo "Installing WordPress..."

# Get nonce from install page
INSTALL_PAGE=$(curl -s -c /tmp/wp_cookies.txt "${WP_URL}/wp-admin/install.php")
echo "Got install page"

# Submit installation
curl -s -b /tmp/wp_cookies.txt -c /tmp/wp_cookies.txt \
  -X POST "${WP_URL}/wp-admin/install.php?step=2" \
  -d "weblog_title=${BLOG_TITLE}" \
  -d "user_name=${ADMIN_USER}" \
  -d "admin_email=${ADMIN_EMAIL}" \
  -d "Submit=Install+WordPress" \
  -d "language=en_US" \
  | head -20

echo ""
echo "Done!"
