# Linew - Cloudflare Setup Guide
# ======================================
# Hướng dẫn cấu hình Cloudflare cho example.com
# Last Updated: 2026-04-28

---

## TỔNG QUAN

Có 2 cách sử dụng Cloudflare với Linew:

1. **Cloudflare Proxy (DNS Only + Proxy)** - Đơn giản nhất, khuyên dùng
2. **Cloudflare Tunnel** - Dùng khi không có static IP hoặc muốn bảo mật hơn

---

## PHƯƠNG ÁN 1: Cloudflare Proxy (Khuyên dùng)

### 1.1 Đăng ký Cloudflare

1. Truy cập https://dash.cloudflare.com/
2. Đăng ký tài khoản mới hoặc login
3. Click "Add a site"
4. Nhập domain: `example.com`
5. Chọn plan: **Free** (đủ cho website thông thường)

### 1.2 Cập nhật Nameservers tại Spaceship

Sau khi thêm domain, Cloudflare sẽ cung cấp 2 nameservers:

```
ns1.cloudflare.com
ns2.cloudflare.com
```

Tại Spaceship (domain registrar):
1. Đăng nhập https://www.spaceship.com/
2. Vào **Domain Management** → **example.com**
3. Tìm **Nameservers** settings
4. Thay đổi thành Cloudflare nameservers:
   - Nameserver 1: `ns1.cloudflare.com`
   - Nameserver 2: `ns2.cloudflare.com`

### 1.3 Cập nhật DNS Records tại Cloudflare

1. Truy cập Cloudflare Dashboard → example.com → **DNS** → **Records**
2. Xóa các records cũ (nếu có)
3. Thêm mới:

| Type | Name | Content | Proxy status |
|------|------|---------|--------------|
| A | @ | YOUR_SERVER_PUBLIC_IP | Proxied (orange) |
| A | www | YOUR_SERVER_PUBLIC_IP | Proxied (orange) |

**Lưu ý:**
- Để Proxy status là "Proxied" (icon cam/orange) để Cloudflare cache và bảo vệ
- Nếu gặp lỗi "Too many redirects", chuyển sang "DNS only" tạm thời

### 1.4 Cấu hình SSL/TLS

1. Vào **SSL/TLS** → **Overview**
2. Chọn: **Full** hoặc **Full (strict)**

   - **Full**: Server có SSL certificate tự sign
   - **Full (strict)**: Server phải có valid SSL (recommended)

3. Nếu dùng **Full (strict)**, cần cài SSL trên server:
   - Option A: Caddy (auto SSL) - Xem phần Caddy
   - Option B: Let's Encrypt với Certbot
   - Option C: Dùng Cloudflare Origin Certificate (miễn phí)

### 1.5 Cấu hình Cloudflare Origin Certificate (Khuyên dùng)

Để dùng **Full (strict)** mà không cần cài SSL trên server:

1. Vào **SSL/TLS** → **Origin Server**
2. Click **Create Certificate**
3. Leave hostname as: `example.com` và `*.example.com`
4. Click **Create**
5. Copy **Origin Certificate** và **Private key**
6. Lưu vào server:
   - Certificate: `/etc/ssl/certs/example.com.pem`
   - Private key: `/etc/ssl/private/example.com.key`

7. Cập nhật nginx config để sử dụng SSL

---

## PHƯƠNG ÁN 2: Cloudflare Tunnel (Khuyên dùng khi không có static IP)

### 2.1 Khi nào nên dùng Cloudflare Tunnel?

- ISP không cung cấp static IP
- Muốn ẩn server IP thực
- Cần bảo mật cao hơn
- Muốn truy cập qua subdomain không cần port forwarding

### 2.2 Cài đặt cloudflared

#### Windows:

1. Download cloudflared từ: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/

2. Giải nén và đặt vào thư mục, ví dụ: `C:\cloudflared\`

3. Thêm vào PATH:
   ```powershell
   $env:Path += ";C:\cloudflared"
   ```

#### macOS/Linux:

```bash
# macOS (Homebrew)
brew install cloudflare/cloudflare/cloudflared

# Linux
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
chmod +x cloudflared
sudo mv cloudflared /usr/local/bin/
```

### 2.3 Đăng nhập Cloudflare

```bash
cloudflared tunnel login
```

Trình duyệt sẽ mở, chọn tài khoản và authorize.

### 2.4 Tạo Tunnel

```bash
cloudflared tunnel create linew-tunnel
```

Lưu ý **Tunnel ID** được hiển thị, ví dụ: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`

### 2.5 Tạo Configuration File

Tạo file tại `C:\Users\YOUR_USERNAME\.cloudflared\config.yml` (Windows)
hoặc `~/.cloudflared/config.yml` (Mac/Linux):

```yaml
tunnel: YOUR_TUNNEL_ID
credentials-file: C:\Users\YOUR_USERNAME\.cloudflared\YOUR_TUNNEL_ID.json

# Proxy traffic đến các service trong Docker
ingress:
  # Dashboard và API
  - hostname: example.com
    service: http://localhost:80
  - hostname: www.example.com
    service: http://localhost:80
  # Fallback
  - service: http_status:404
```

### 2.6 Route DNS

```bash
# Tạo DNS record tự động
cloudflared tunnel route dns linew-tunnel example.com
cloudflared tunnel route dns linew-tunnel www.example.com
```

### 2.7 Chạy Tunnel

```bash
# Test run
cloudflared tunnel run --token YOUR_TOKEN

# Hoặc chạy với config file
cloudflared tunnel run linew-tunnel
```

### 2.8 Chạy như Service (Windows)

```powershell
# Install as Windows service
cloudflared service install

# Check status
cloudflared service list
```

### 2.9 Chạy như Service (Linux/systemd)

```bash
sudo cloudflared service install
sudo systemctl start cloudflared
sudo systemctl enable cloudflared
```

---

## CẤU HÌNH NGINX VỚI SSL

### Nếu dùng Cloudflare Origin Certificate

Cập nhật `nginx/default.conf` (production):

```nginx
server {
    listen 80;
    server_name example.com www.example.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name example.com www.example.com;

    # SSL from Cloudflare Origin Certificate
    ssl_certificate /etc/ssl/certs/example.com.pem;
    ssl_certificate_key /etc/ssl/private/example.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # ... rest of config same as before ...
}
```

### Nếu dùng Caddy (Auto SSL)

Tải Caddy: https://caddyserver.com/download

Tạo `Caddyfile`:

```
example.com {
    reverse_proxy /dashboard/api/* localhost:8000
    reverse_proxy /dashboard/ws/* localhost:8000
    reverse_proxy /dashboard/* localhost:3000
    reverse_proxy /wp-admin/* localhost:8888
    reverse_proxy /wp-login.php localhost:8888
    reverse_proxy localhost:8888
}
```

Chạy:
```bash
caddy run
```

---

## FIREWALL CONFIGURATION

### Windows Firewall

```powershell
# Open ports for HTTP/HTTPS
New-NetFirewallRule -DisplayName "Linew HTTP" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 80
New-NetFirewallRule -DisplayName "Linew HTTPS" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 443

# Nếu dùng Cloudflare Tunnel, chỉ cần localhost traffic
# Không cần mở port ra internet
```

### Nếu dùng Cloudflare Tunnel

- Không cần mở port 80/443 ra internet
- Chỉ cần cloudflared kết nối ra ngoài (port 443)
- Server được bảo vệ hoàn toàn

---

## KIỂM TRA & TROUBLESHOOTING

### Kiểm tra DNS

```bash
nslookup example.com
nslookup example.com 1.1.1.1
```

### Kiểm tra SSL Certificate

```bash
openssl s_client -connect example.com:443 -servername example.com
```

### Kiểm tra Cloudflare Tunnel

```bash
cloudflared tunnel list
cloudflared tunnel info linew-tunnel
```

### Kiểm tra logs

```bash
# Cloudflare Tunnel logs
cloudflared tunnel run linew-tunnel

# Nginx logs
docker-compose logs nginx
```

### Các lỗi thường gặp

| Lỗi | Nguyên nhân | Giải pháp |
|------|-------------|-----------|
| Too many redirects | SSL mode không đúng | Đổi SSL mode sang Full |
| 502 Bad Gateway | Service không chạy | Kiểm tra docker-compose ps |
| SSL certificate error | Certificate hết hạn | Renew Origin Certificate |
| Tunnel disconnected | Network issue | Restart cloudflared service |

---

## BẢO MẬT

### Khuyến nghị

1. **Dùng Cloudflare Proxy**: Bật orange cloud để Cloudflare bảo vệ
2. **WAF**: Bật Cloudflare WAF để chặn attacks
3. **Rate Limiting**: Cấu hình rate limit để tránh abuse
4. **Always Use HTTPS**: Bật "Always Use HTTPS" trong SSL/TLS settings

### Tắt các tính năng không cần thiết

1. Vào **Security** → **Settings**
2. Bật **I'm Under Attack Mode** chỉ khi cần
3. Cấu hình **Challenge Passage** theo nhu cầu

---

## QUICK REFERENCE

### Commands cho Cloudflare Tunnel

```bash
# Login
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create linew-tunnel

# Route DNS
cloudflared tunnel route dns linew-tunnel example.com

# Run tunnel
cloudflared tunnel run --token YOUR_TOKEN

# List tunnels
cloudflared tunnel list

# Delete tunnel
cloudflared tunnel delete linew-tunnel
```

### Environment Variables liên quan

Trong `.env` file:
```
WP_URL=https://example.com
SITE_URL=https://example.com
```

Trong WordPress Database hoặc wp-config.php:
```php
define('WP_HOME', 'https://example.com');
define('WP_SITEURL', 'https://example.com');
$_SERVER['HTTPS'] = 'on';
```
