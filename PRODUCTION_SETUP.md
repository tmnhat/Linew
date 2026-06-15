# Linew Production Deployment - litimez.ai
# =========================================

## Step 1: DNS Configuration at Spaceship

1. Login to https://www.spaceship.com/
2. Navigate to your domain: **litimez.ai**
3. Go to **DNS Settings** or **DNS Management**
4. Add these DNS records:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | @ | YOUR_PUBLIC_IP | 3600 |
| A | www | YOUR_PUBLIC_IP | 3600 |

**How to find your public IP:**
- Visit: https://whatismyip.com
- Or run in terminal: `curl ifconfig.me`

**Note:** If your ISP uses dynamic IP (IP changes occasionally):
- Consider using a Dynamic DNS service
- Or check if Spaceship supports dynamic DNS updates

---

## Step 2: Wait for DNS Propagation

DNS changes can take **5 minutes to 48 hours** to propagate globally.

**Verify DNS is working:**
```bash
nslookup litimez.ai
# Should return your server IP
```

---

## Step 3: Configure Firewall

On your Windows server, open these ports:

### Windows Firewall (PowerShell as Admin):
```powershell
# HTTP (port 80)
New-NetFirewallRule -DisplayName "HTTP" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 80

# HTTPS (port 443)
New-NetFirewallRule -DisplayName "HTTPS" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 443
```

### Router Port Forwarding (if behind router):
```
Port 80  -> Your Windows PC IP
Port 443 -> Your Windows PC IP
```

---

## Step 4: SSL Certificate (Choose One)

### Option A: Cloudflare (Easiest - Recommended)

1. Create free account at https://dash.cloudflare.com
2. Add your domain `litimez.ai`
3. Update nameservers at Spaceship to Cloudflare's nameservers
4. In Cloudflare dashboard:
   - SSL/TLS: Set to **Full** or **Flexible**
   - Enable "Proxy" (orange cloud)

**Pros:** Free, auto SSL, DDoS protection
**Cons:** Your traffic goes through Cloudflare

---

### Option B: Let's Encrypt with Caddy (Recommended for Self-Host)

1. Download Caddy: https://caddyserver.com/download
2. Place `Caddyfile` in the same directory as Caddy executable
3. Run: `caddy run`

Caddy automatically obtains SSL from Let's Encrypt.

**Pros:** Free, auto-renewal, simple config
**Cons:** Need port 80/443 open

---

### Option C: Let's Encrypt with Nginx + Certbot

1. Install Certbot: https://certbot.eff.org/instructions
2. Generate certificate:
```bash
certbot certonly --nginx -d litimez.ai -d www.litimez.ai
```

3. Update nginx config with SSL paths

---

## Step 5: Final URLs

After setup, access Linew at:

| Service | URL |
|---------|-----|
| **Main Site** | https://litimez.ai |
| **Dashboard** | https://litimez.ai/dashboard |
| **WordPress Admin** | https://litimez.ai/wp.admin |
| **API Docs** | https://litimez.ai/docs |

---

## Step 6: Verify Everything Works

1. Visit https://litimez.ai - should show WordPress
2. Visit https://litimez.ai/dashboard - should show Linew Dashboard
3. Visit https://litimez.ai/wp.admin - should show WordPress Admin login

---

## Troubleshooting

### DNS not working?
```bash
# Clear local DNS cache
ipconfig /flushdns

# Check propagation
nslookup litimez.ai 8.8.8.8
```

### Can't access from outside?
- Check Windows Firewall rules
- Check Router port forwarding
- Try: `curl http://localhost:8888` from server

### SSL certificate issues?
- If using Cloudflare, ensure orange cloud is enabled
- If using Caddy, check logs: `caddy.log`
