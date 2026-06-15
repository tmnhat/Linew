# Linew - WordPress Setup Guide

## Sau khi containers đã chạy, hoàn thành WordPress setup:

### Bước 1: Truy cập WordPress Setup
Mở trình duyệt và truy cập:
- **http://localhost:8888** (local)
- Hoặc **http://YOUR_PUBLIC_IP:8888**

### Bước 2: WordPress Installation Wizard

1. **Select Language**: Chọn "Vietnamese"
2. Click **Continue**

3. **Setup Configuration**:
   - Database Name: `wordpress`
   - Username: `linew`
   - Password: (xem trong file `.env`, field `DB_PASSWORD`)
   - Database Host: `mysql`
   - Table Prefix: `wp_`

4. Click **Submit**

5. **Run Installation**

6. **Site Information**:
   - Site Title: `Linews - Tin tức Công nghệ & Tài chính`
   - Username: `admin`
   - Password: `Use a strong password`
   - Email: `admin@example.com`
   - Search Engine Visibility: **UNCHECK** "Discourage search engines"

7. Click **Install WordPress**

### Bước 3: Cấu hình WordPress URL

Sau khi login:
1. Vào **Settings** → **General**
2.确保:
   - WordPress Address (URL): `https://example.com`
   - Site Address (URL): `https://example.com`
3. Click **Save Changes**

### Bước 4: Cài đặt Required Plugins

1. Vào **Plugins** → **Add New**
2. Search và cài đặt:
   - "WP Super Cache" (caching)
   - "Wordfence" (security)
   - "Yoast SEO" (SEO)

### Bước 5: Thiết lập Permalinks

1. Vào **Settings** → **Permalinks**
2. Chọn **Post name**
3. Click **Save Changes**

---

## Lưu ý quan trọng:

### Nếu dùng Cloudflare Proxy (Orange Cloud):
- SSL mode trong Cloudflare: **Full** hoặc **Full (strict)**
- WordPress sẽ tự động dùng HTTPS qua Cloudflare

### Nếu gặp lỗi "Too many redirects":
- Cài plugin "Really Simple SSL" hoặc
- Thêm vào wp-config.php:
```php
$_SERVER['HTTPS'] = 'on';
define('FORCE_SSL_ADMIN', true);
```
