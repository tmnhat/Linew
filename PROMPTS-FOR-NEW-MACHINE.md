# Linew - Prompts for New Machine Setup
# ======================================
# Copy các prompt bên dưới để setup Linew trên máy mới
# ======================================

---

## PROMPT 1: Initial Setup - Docker & Prerequisites

```
Tôi muốn setup một dự án tên là Linew trên máy tính mới.

Đây là dự án tin tức tự động sử dụng:
- Python FastAPI làm backend
- React làm frontend (dashboard)
- WordPress làm CMS
- PostgreSQL làm database
- Redis làm cache
- Celery làm task queue
- Docker để deploy

Cấu trúc thư mục hiện tại:
Linew/
├── app/                      # Python FastAPI application
├── dashboard/                # React frontend
├── nginx/                    # Nginx configurations
├── wordpress/                # WordPress customizations
├── scripts/                  # Utility scripts
├── docker-compose.yml        # Docker services
├── Dockerfile.api, Dockerfile.worker, Dockerfile.dashboard
├── requirements.txt          # Python dependencies
└── .env                     # Environment variables

Hãy giúp tôi:
1. Cài đặt Docker Desktop trên Windows
2. Kiểm tra Docker đã chạy đúng chưa
3. Cài đặt các công cụ cần thiết khác (Git, Python, Node.js)
```

---

## PROMPT 2: Clone & Setup Project

```
Tôi đã clone dự án Linew từ repository về máy mới.

Bây giờ hãy giúp tôi setup:
1. Copy file `.env.newcomputer` thành `.env`
2. Cập nhật các giá trị PLACEHOLDER trong .env:
   - DB_PASSWORD: đặt mật khẩu mới cho database
   - VERTEX_API_KEY: lấy từ https://vertex-key.com
   - WP_USERNAME, WP_APP_PASSWORD: thông tin WordPress
   - SECRET_KEY: tạo secret key mới
   - LINEW_DATA_PATH: đường dẫn tới thư mục data

3. Tạo thư mục data theo LINEW_DATA_PATH
4. Chạy `docker-compose up -d` để khởi động tất cả services

Các file cấu hình đã có sẵn:
- docker-compose.yml
- Dockerfile.api, Dockerfile.worker, Dockerfile.dashboard
- nginx/default.conf
- requirements.txt
```

---

## PROMPT 3: Domain & DNS Setup

```
Tôi đang setup domain litimez.ai cho dự án Linew.

Domain hiện đang đăng ký tại Spaceship.

Hãy giúp tôi:
1. Cập nhật DNS records tại Spaceship:
   - Type A: @ → YOUR_PUBLIC_IP
   - Type A: www → YOUR_PUBLIC_IP

2. Sau khi DNS propagation hoàn tất (5-48 giờ), kiểm tra:
   - nslookup litimez.ai

3. Nếu sử dụng Cloudflare:
   - Thêm domain vào Cloudflare Dashboard
   - Cập nhật nameservers tại Spaceship
   - Bật Proxy (orange cloud)
   - Đặt SSL mode: Full hoặc Full strict

4. Mở firewall trên Windows:
   - Port 80 (HTTP)
   - Port 443 (HTTPS)

Public IP hiện tại của tôi là: [YOUR_IP]
```

---

## PROMPT 4: Cloudflare Tunnel Setup (Alternative to DNS)

```
Thay vì sử dụng DNS record truyền thống, tôi muốn dùng Cloudflare Tunnel
để expose dịch vụ ra internet.

Hãy giúp tôi setup Cloudflare Tunnel:

1. Đăng ký tài khoản Cloudflare Zero Trust: https://dash.cloudflare.com/

2. Download cloudflared:
   - Windows: tải từ https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/

3. Authenticate:
   cloudflared tunnel login

4. Tạo tunnel mới:
   cloudflared tunnel create linew-tunnel

5. Configure tunnel:
   Tạo file config.yml tại C:\Users\YOUR_USERNAME\.cloudflared\config.yml:
   ```yaml
   tunnel: YOUR_TUNNEL_ID
   credentials-file: C:\Users\YOUR_USERNAME\.cloudflared\YOUR_TUNNEL_ID.json
   
   ingress:
     - hostname: litimez.ai
       service: http://localhost:80
     - hostname: www.litimez.ai
       service: http://localhost:80
     - service: http_status:404
   ```

6. Route DNS:
   cloudflared tunnel route dns linew-tunnel litimez.ai

7. Chạy tunnel:
   cloudflared tunnel run --token YOUR_TOKEN

8. (Optional) Chạy như service:
   cloudflared service install
```

---

## PROMPT 5: WordPress Setup

```
Sau khi Docker containers đã chạy, tôi cần setup WordPress.

Hãy hướng dẫn tôi:

1. Truy cập WordPress setup:
   - Local: http://localhost:8888
   - Sau khi có domain: https://litimez.ai

2. Installation Wizard:
   - Chọn ngôn ngữ: Vietnamese
   - Database Name: wordpress
   - Username: linew
   - Password: (từ DB_PASSWORD trong .env)
   - Database Host: mysql
   - Table Prefix: wp_

3. Site Information:
   - Site Title: Linews - Tin tức Công nghệ & Tài chính
   - Username: (chọn username admin mới)
   - Password: (chọn password mạnh)
   - Email: admin@litimez.ai

4. Sau khi install, vào Settings → General:
   - WordPress Address (URL): https://litimez.ai
   - Site Address (URL): https://litimez.ai

5. Cài plugins:
   - WP Super Cache (caching)
   - Wordfence (security)
   - Yoast SEO (SEO)

6. Settings → Permalinks:
   - Chọn: Post name

7. Users → Application Passwords:
   - Tạo app password mới
   - Copy vào WP_APP_PASSWORD trong .env
```

---

## PROMPT 6: Build Dashboard

```
Tôi cần build React dashboard cho Linew.

Hãy giúp tôi:

1. Navigate vào thư mục dashboard:
   cd dashboard

2. Cài dependencies:
   npm install

3. Build production:
   npm run build

4. Kiểm tra output:
   - Dashboard build sẽ nằm ở dashboard/dist/

5. Copy build vào vị trí đúng cho nginx:
   - File đã được mount tự động trong docker-compose.yml:
     - ./dashboard/dist:/usr/share/nginx/html/dashboard:ro

6. Restart nginx service:
   docker-compose restart nginx
```

---

## PROMPT 7: Verify & Test Setup

```
Sau khi setup hoàn tất, hãy giúp tôi verify:

1. Kiểm tra tất cả Docker containers đang chạy:
   docker-compose ps

2. Kiểm tra logs của từng service:
   docker-compose logs -f api
   docker-compose logs -f worker
   docker-compose logs -f wordpress

3. Test các endpoints:
   - API Health: http://localhost:8000/api/health
   - WordPress: http://localhost:8888
   - Dashboard: http://localhost:3000 (dev) hoặc http://localhost/dashboard (production)

4. Kiểm tra kết nối database:
   docker-compose exec postgres psql -U linew -d linew -c "\dt"

5. Test WordPress API:
   - Truy cập https://litimez.ai/wp-json/

6. Test sitemap:
   - https://litimez.ai/sitemap.xml

7. Kiểm tra SSL certificate (nếu dùng Cloudflare):
   - Truy cập https://litimez.ai và kiểm tra certificate
```

---

## PROMPT 8: Migration & Backup

```
Tôi muốn migrate dữ liệu từ máy cũ sang máy mới.

Hãy giúp tôi:

1. Backup trên máy cũ:

   # Backup PostgreSQL
   docker-compose exec postgres pg_dump -U linew linew > linew_backup.sql

   # Backup WordPress files
   docker-compose cp wordpress:/var/www/html ./wp_backup

   # Backup Redis data
   docker-compose exec redis redis-cli SAVE

2. Copy backup files sang máy mới:
   - linew_backup.sql
   - wp_backup/

3. Restore trên máy mới:

   # Restore PostgreSQL
   cat linew_backup.sql | docker-compose exec -T postgres psql -U linew linew

   # Restore WordPress files
   docker-compose cp ./wp_backup/. wordpress:/var/www/html/

4. Backup volumes (alternative):
   docker-compose run --rm -v linew_pgdata:/data -v $(pwd):/backup postgres tar czf /backup/pgdata.tar.gz /data
```

---

## PROMPT 9: Troubleshooting

```
Tôi gặp vấn đề với Linew. Hãy giúp tôi troubleshoot:

Vấn đề: [MÔ TẢ VẤN ĐỀ CỦA BẠN]

Các thông tin cần kiểm tra:

1. Docker status:
   docker-compose ps
   docker-compose logs -f [service_name]

2. Network connectivity:
   docker-compose exec api ping wordpress
   docker-compose exec api ping postgres
   docker-compose exec api ping redis

3. Port conflicts:
   netstat -ano | findstr :80
   netstat -ano | findstr :443
   netstat -ano | findstr :8000

4. Disk space:
   docker system df

5. Reset và rebuild:
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d

6. Common issues:
   - "Port is already allocated": Thay đổi port trong docker-compose.yml
   - "Volume not found": Chạy `docker volume create linew_pgdata`
   - "Connection refused": Kiểm tra service đã start chưa
```

---

## QUICK START CHECKLIST

```
□ 1. Cài đặt Docker Desktop
□ 2. Clone repository
□ 3. Copy .env.newcomputer → .env và cập nhật PLACEHOLDER values
□ 4. Tạo thư mục data theo LINEW_DATA_PATH
□ 5. Setup DNS records tại Spaceship (litimez.ai → server IP)
□ 6. Setup Cloudflare (nếu dùng Cloudflare Proxy)
□ 7. Mở firewall ports 80, 443
□ 8. docker-compose up -d
□ 9. Setup WordPress qua http://localhost:8888
□ 10. Build dashboard: cd dashboard && npm install && npm run build
□ 11. Test các endpoints
□ 12. Verify SSL/HTTPS hoạt động
```

---

## FILE REFERENCES

Các file cấu hình đã được tạo:

1. **LINEW-SETUP-GUIDE.md** - Hướng dẫn setup chi tiết đầy đủ
2. **.env.newcomputer** - Template file để copy thành .env trên máy mới
3. **PROMPTS-FOR-NEW-MACHINE.md** - File này, chứa các prompt để copy

Các file cấu hình có sẵn trong project:

1. **docker-compose.yml** - Docker services configuration
2. **Dockerfile.api** - FastAPI Docker image
3. **Dockerfile.worker** - Celery worker Docker image
4. **Dockerfile.dashboard** - React dashboard Docker image
5. **nginx/default.conf** - Nginx reverse proxy config
6. **nginx/nginx.windows.conf** - Nginx config cho Windows
7. **.env.example** - Example environment variables
8. **requirements.txt** - Python dependencies
