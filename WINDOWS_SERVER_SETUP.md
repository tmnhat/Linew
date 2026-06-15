# Linew Windows Server Setup Guide
# ================================
# This guide helps you deploy Linew on a Windows laptop as a production server

# ==========================================
# SECTION 1: DNS CONFIGURATION
# ==========================================
# 
# 1. Go to https://www.spaceship.com/
# 2. Login to your account
# 3. Find your domain: litimez.ai
# 4. Go to DNS Settings / DNS Management
# 5. Add the following DNS records:
#
#    Type    Name    Value/Target           TTL
#    A       @       YOUR_SERVER_IP         3600 (1 hour)
#    A       www     YOUR_SERVER_IP         3600
#
# NOTE: Replace YOUR_SERVER_IP with your laptop's public IP address.
# You can find your public IP by visiting: https://whatismyip.com
#
# IMPORTANT: If your ISP gives you a dynamic IP, consider:
# - Using a Dynamic DNS service (no-ip, DuckDNS)
# - Or set up ddclient to auto-update DNS when IP changes

# ==========================================
# SECTION 2: WINDOWS SERVICES ARCHITECTURE
# ==========================================
#
# Linew requires these services to run:
#
# 1. PostgreSQL 16  - Database (port 5432)
# 2. Redis 7        - Cache/Queue (port 6379)
# 3. FastAPI        - Backend API (port 8000)
# 4. Celery Worker  - Background tasks
# 5. Celery Beat    - Scheduled tasks
# 6. MySQL 8        - WordPress database (port 3306)
# 7. WordPress      - CMS (port 8888)
# 8. Nginx/Caddy    - Reverse Proxy (port 80, 443)
# 9. FlareSolverr   - Cloudflare bypass (port 8191)
#
# OPTION A: Use Docker Desktop (Recommended)
# -----------------------------------------
# Install Docker Desktop for Windows
# Download: https://www.docker.com/products/docker-desktop/
#
# Then run:
#   docker-compose up -d
#
# This will start all services automatically.
#
# OPTION B: Native Windows Services
# ---------------------------------
# For production without Docker, install each service natively.
# See Section 4 below.

# ==========================================
# SECTION 3: NGINX REVERSE PROXY (Windows)
# ==========================================
#
# Download Nginx for Windows:
#   http://nginx.org/en/download.html
#
# Configuration file: nginx.conf
#
# Place nginx.conf in the same directory as nginx.exe

# ==========================================
# SECTION 4: SSL/HTTPS SETUP (Let's Encrypt)
# ==========================================
#
# Option A: Using Caddy (Recommended - auto SSL)
# ----------------------------------------------
# Download Caddy from: https://caddyserver.com/download
# 
# Caddy automatically handles SSL certificates with Let's Encrypt.
# 
# Create Caddyfile:
# ---------------
# litimez.ai {
#     reverse_proxy /dashboard/api/* localhost:8000
#     reverse_proxy /dashboard/ws/* localhost:8000
#     reverse_proxy /dashboard/* localhost:3000
#     reverse_proxy /wp-admin/* localhost:8888
#     reverse_proxy /wp-login.php localhost:8888
#     reverse_proxy localhost:8888
# }
# ---------------
#
# Run: caddy run
#
# Option B: Using Nginx with Certbot
# ----------------------------------
# 1. Install Certbot: https://certbot.eff.org/instructions
# 2. Generate certificate:
#    certbot certonly --nginx -d litimez.ai -d www.litimez.ai
# 3. Update nginx.conf with SSL paths
#
# Option C: Cloudflare (Easiest)
# ------------------------------
# 1. Go to https://dash.cloudflare.com
# 2. Add your domain litimez.ai
# 3. Update nameservers at Spaceship to Cloudflare's
# 4. Enable "Proxy" mode (orange cloud)
# 5. SSL/TLS mode: "Full" or "Flexible"
# 6. No need for local SSL certs!

# ==========================================
# SECTION 5: QUICK START (Docker on Windows)
# ==========================================
#
# 1. Install Docker Desktop
# 2. Open PowerShell in Linew directory
# 3. Run:
#    docker-compose up -d
# 4. Wait for services to start (~2 minutes)
# 5. Access:
#    - WordPress: http://localhost:8888
#    - API:       http://localhost:8000
#    - Dashboard: http://localhost:3000
#
# For production with domain:
# --------------------------
# 1. Setup DNS at Spaceship (Section 1)
# 2. Install Caddy or configure Nginx with SSL
# 3. Access via https://litimez.ai

# ==========================================
# SECTION 6: NAT/Firewall CONFIGURATION
# ==========================================
#
# If server is behind router, configure port forwarding:
#
# Port  80  -> Windows Server IP (HTTP)
# Port 443  -> Windows Server IP (HTTPS)
# Port  22  -> SSH (optional, for remote access)
#
# Windows Firewall:
# Run PowerShell as Admin:
#   New-NetFirewallRule -DisplayName "Linew HTTP" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 80
#   New-NetFirewallRule -DisplayName "Linew HTTPS" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 443

# ==========================================
# SECTION 7: TROUBLESHOOTING
# ==========================================
#
# Check if services are running:
#   docker-compose ps
#
# View logs:
#   docker-compose logs -f api
#   docker-compose logs -f worker
#
# Restart services:
#   docker-compose restart
#
# Stop all:
#   docker-compose down
