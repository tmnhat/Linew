#!/bin/bash
# Auto-install WordPress via HTTP POST

WP_URL="https://litimez.ai"
BLOG_TITLE="LiTimez"
ADMIN_USER="admin"
ADMIN_EMAIL="admin@litimez.ai"
ADMIN_PASS="Linew2026!"

echo "Installing WordPress..."

# Step 1: Get cookies and nonce
echo "1. Fetching install page..."
curl -s -c /tmp/wp_cookies.txt -b /tmp/wp_cookies.txt \
  "${WP_URL}/wp-admin/install.php" > /tmp/install.html 2>&1
echo "   ✓ Got install page (status: $?)"

# Step 2: Submit installation
echo "2. Submitting installation form..."
curl -s -b /tmp/wp_cookies.txt -c /tmp/wp_cookies.txt \
  -X POST "${WP_URL}/wp-admin/install.php?step=2" \
  -d "weblog_title=${BLOG_TITLE}" \
  -d "user_name=${ADMIN_USER}" \
  -d "admin_email=${ADMIN_EMAIL}" \
  -d "admin_password=${ADMIN_PASS}" \
  -d "admin_password2=${ADMIN_PASS}" \
  -d "Submit=Install+WordPress" \
  -d "language=en_US" \
  -D /tmp/install_headers.txt \
  -o /tmp/install_result.txt

echo "   Response: $(head -1 /tmp/install_headers.txt)"

# Step 3: Check if installed
echo "3. Verifying installation..."
curl -s -b /tmp/wp_cookies.txt "${WP_URL}/wp-login.php" | grep -q "log" && echo "   ✓ WordPress installed!" || echo "   ✗ Installation may have failed"

echo ""
echo "Installation script completed."
