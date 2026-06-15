#!/bin/bash
# Create WordPress App Password and save to .env

WP_URL="https://example.com"
ADMIN_USER="admin"
ADMIN_PASS="Linew2026!"

echo "Creating WordPress App Password..."

# Login to WordPress
echo "1. Logging in..."
COOKIES=$(curl -s -c - -d "
log=${ADMIN_USER}&pwd=${ADMIN_PASS}&rememberme=forever&wp-submit=Log+In&redirect_to=${WP_URL}/wp-admin/&testcookie=1
" "${WP_URL}/wp-login.php" 2>&1)

# Get nonce for app-passwords
echo "2. Getting nonce..."
NONCE=$(curl -s -b /tmp/wp_cookies.txt "${WP_URL}/wp-admin/admin-ajax.php?action=appp_get_list&format=json" 2>/dev/null)

# Or try to get user ID
echo "3. Getting user info..."
USER_ID=$(curl -s -b /tmp/wp_cookies.txt "${WP_URL}/wp-admin/user-edit.php?user_id=1" 2>/dev/null | grep -oP 'user_id=\K\d+' | head -1)
echo "   User ID: $USER_ID"

# Try to create app password via REST API
echo "4. Creating app password via REST API..."
APP_PASS=$(curl -s -b /tmp/wp_cookies.txt \
  -X POST "${WP_URL}/wp-json/wp/v2/users/${USER_ID:-1}/application-passwords" \
  -H "Content-Type: application/json" \
  -d '{"name":"Linew API","grants":[]}' \
  2>&1)

echo "Response: $APP_PASS"

# If REST API doesn't work, try direct database
if [[ "$APP_PASS" == *"error"* ]] || [[ "$APP_PASS" == *"<"* ]]; then
    echo ""
    echo "⚠️  Cannot create app password via API."
    echo "   Please do this manually:"
    echo "   1. Go to: https://example.com/wp-admin/"
    echo "   2. Login as admin / Linew2026!"
    echo "   3. Go to: Users > Profile"
    echo "   4. Scroll to 'Application Passwords'"
    echo "   5. Enter 'Linew API' and click 'Add New'"
    echo "   6. Copy the generated password"
    echo "   7. Update .env with WP_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx"
fi
