# Linew Setup Guide - Complete Reference
# ======================================
# Document này chứa toàn bộ cấu hình của Linew để setup trên máy mới
# Domain: example.com
# Last Updated: 2026-04-28

---

## PART 1: KIẾN TRÚC HỆ THỐNG

### 1.1 Các Service Chạy Trong Docker

| Service | Image | Port | Mô tả |
|---------|-------|------|-------|
| postgres | postgres:16 | 5432 | Database chính |
| redis | redis:7-alpine | 6379 | Cache & Queue |
| api | Dockerfile.api | 8000 | FastAPI Backend |
| worker | Dockerfile.worker | - | Celery Worker |
| beat | Dockerfile.worker | - | Celery Beat (scheduler) |
| dashboard | Dockerfile.dashboard | - | React Dashboard |
| nginx | nginx:alpine | 80 | Reverse Proxy |
| mysql | mysql:8 | 3306 | WordPress Database |
| wordpress | wordpress:6-php8.2-apache | 8888 | CMS |
| flaresolverr | ghcr.io/flaresolverr/flaresolverr | 8191 | Cloudflare bypass |

### 1.2 Các Volume Docker

| Volume | Type | Mount Path |
|--------|------|------------|
| pgdata | Docker volume | /var/lib/postgresql/data |
| redis_data | Docker volume | /data |
| wpdata | Docker volume | /var/www/html |
| mysql_data | Docker volume | /var/lib/mysql |
| linew-data | Bind mount | ${LINEW_DATA_PATH} |

---

## PART 2: CẤU HÌNH MÔI TRƯỜNG (.env)

### 2.1 Database

```
DATABASE_URL=postgresql+asyncpg://linew:rootpassword@postgres:5432/linew
DB_PASSWORD=rootpassword
```

### 2.2 Redis

```
REDIS_URL=redis://redis:6379/0
```

### 2.3 AI Gateway - MiniMax via Vertex Key

```
VERTEX_API_KEY=vai-UxnjozXiH9qmxRZ31ONDa-0zX3ds5GVmbmuZXBJA2u__URLd
VERTEX_PROJECT_ID=minimax-chat
VERTEX_LOCATION=global
VERTEX_BASE_URL=https://vertex-key.com/api/v1

# AI Models (MiniMax M2.5)
AI_WRITER_MODEL=aws/minimax-m2.5
AI_LIGHT_MODEL=aws/minimax-m2.5
AI_RESEARCHER_MODEL=aws/minimax-m2.5
AI_SUMMARIZER_MODEL=aws/minimax-m2.5
```

### 2.4 WordPress

```
WP_URL=https://example.com
WP_USERNAME=Litimez
WP_APP_PASSWORD=hFI9 cndU zU0U 1yHo UrFq A6Vv
```

### 2.5 FlareSolverr

```
FLARESOLVERR_URL=http://flaresolverr:8191/v1
```

### 2.6 Application

```
SECRET_KEY=linew-production-secret-key-2026
ENVIRONMENT=production
LOG_LEVEL=info
```

### 2.7 TimesFM

```
TIMESFM_DEVICE=mps
```

### 2.8 API

```
API_HOST=0.0.0.0
API_PORT=8000
```

### 2.9 Distribution - Telegram

```
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHANNEL_ID=@linews_vn
TELEGRAM_CHANNEL_ENABLED=false
```

### 2.10 Distribution - Facebook

```
FACEBOOK_PAGE_ID=
FACEBOOK_PAGE_ACCESS_TOKEN=
FACEBOOK_APP_ID=
FACEBOOK_APP_SECRET=
FACEBOOK_ENABLED=false
FACEBOOK_SCHEDULE_MINUTES=80
FACEBOOK_MIN_TREND_SCORE=0.3
FACEBOOK_ARTICLE_SEARCH_HOURS=24
```

### 2.11 Distribution - Twitter/X

```
TWITTER_API_KEY=
TWITTER_API_SECRET=
TWITTER_ACCESS_TOKEN=
TWITTER_ACCESS_SECRET=
TWITTER_ENABLED=false
```

### 2.12 Newsletter

```
NEWSLETTER_ENABLED=false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
NEWSLETTER_FROM_NAME=Linews
NEWSLETTER_FROM_EMAIL=linews@gmail.com
```

### 2.13 Analytics & SEO

```
GA_MEASUREMENT_ID=
SITE_URL=https://example.com
SITE_NAME=Linews
```

### 2.14 CORS

```
CORS_ORIGINS=
```

### 2.15 Linew Data Path

```
LINEW_DATA_PATH=C:/Users/tmnha/Linew/data
```

---

## PART 3: DOCKER CONFIGURATION

### 3.1 docker-compose.yml - Key Services

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: linew
      POSTGRES_USER: linew
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8000:8000"
    env_file: .env

  worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    command: celery -A app.worker.celery_app worker -l info -c 6
    volumes:
      - linew-data:/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
      - ./dashboard/dist:/usr/share/nginx/html/dashboard:ro

  mysql:
    image: mysql:8
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:-rootpassword}
      MYSQL_DATABASE: wordpress
      MYSQL_USER: linew
      MYSQL_PASSWORD: ${DB_PASSWORD}

  wordpress:
    image: wordpress:6-php8.2-apache
    ports:
      - "8888:80"
    environment:
      WORDPRESS_DB_HOST: mysql
      WORDPRESS_DB_NAME: wordpress
      WORDPRESS_DB_USER: linew
      WORDPRESS_DB_PASSWORD: ${DB_PASSWORD}
      WORDPRESS_TABLE_PREFIX: wp_
    volumes:
      - wpdata:/var/www/html
      - ./wordpress/mu-plugins:/var/www/html/wp-content/mu-plugins
      - ./wordpress/prediction-widget:/var/www/html/wp-content/prediction-widget
      - ./wordpress/themes:/var/www/html/wp-content/themes

  flaresolverr:
    image: ghcr.io/flaresolverr/flaresolverr:latest
    ports:
      - "8191:8191"
```

---

## PART 4: NGINX CONFIGURATION

### 4.1 Production Config (default.conf)

File: `nginx/default.conf`

Key routes:
- `/` → WordPress (port 8888)
- `/api/*` → FastAPI (port 8000)
- `/dashboard/*` → React Dashboard
- `/dashboard/api/*` → FastAPI (rewritten)
- `/wp-admin/*` → WordPress Admin
- `/wp-login.php` → WordPress Login
- `/sitemap.xml` → FastAPI
- `/robots.txt` → FastAPI

---

## PART 5: DNS & DOMAIN CONFIGURATION

### 5.1 Domain: example.com

**Registrar:** Spaceship (spaceship.com)

**DNS Records Required:**
| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | @ | YOUR_PUBLIC_IP | 3600 |
| A | www | YOUR_PUBLIC_IP | 3600 |

### 5.2 Cloudflare Setup (Recommended)

1. Go to https://dash.cloudflare.com
2. Add domain: `example.com`
3. Update nameservers at Spaceship to Cloudflare's nameservers
4. In Cloudflare Dashboard:
   - SSL/TLS Mode: **Full** or **Full (strict)**
   - Enable Proxy (orange cloud)

### 5.3 Cloudflare Tunnel (Optional - for bypassing dynamic IP)

If using Cloudflare Tunnel instead of static IP:

1. Download cloudflared: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
2. Run tunnel:
```bash
cloudflared tunnel --url http://localhost:80
```

Or create named tunnel:
```bash
cloudflared tunnel create linew-tunnel
cloudflared tunnel route dns linew-tunnel example.com
cloudflared tunnel run --token YOUR_TOKEN
```

---

## PART 6: WORDPRESS SETUP

### 6.1 After Containers Running

1. Access: http://localhost:8888
2. Installation Wizard:
   - Language: Vietnamese
   - Database Name: `wordpress`
   - Username: `linew`
   - Password: (from DB_PASSWORD)
   - Database Host: `mysql`
   - Table Prefix: `wp_`

### 6.2 Site Settings

- Site Title: `Linews - Tin tức Công nghệ & Tài chính`
- Username: `admin`
- Email: `admin@example.com`

### 6.3 After Installation

1. Settings → General:
   - WordPress Address (URL): `https://example.com`
   - Site Address (URL): `https://example.com`

2. Install Plugins:
   - WP Super Cache (caching)
   - Wordfence (security)
   - Yoast SEO (SEO)

3. Settings → Permalinks:
   - Select: Post name

---

## PART 7: AI GATEWAY CONFIGURATION

### 7.1 Vertex Key.com Setup

The system uses MiniMax M2.5 via vertex-key.com (OpenAI-compatible API).

**Current Configuration:**
- Base URL: `https://vertex-key.com/api/v1`
- API Key: `vai-UxnjozXiH9qmxRZ31ONDa-0zX3ds5GVmbmuZXBJA2u__URLd`
- Project ID: `minimax-chat`
- Location: `global`

**Models Used:**
- `aws/minimax-m2.5` (for all tasks)

---

## PART 8: DIRECTORY STRUCTURE

```
Linew/
├── app/                      # Python FastAPI application
│   ├── core/                 # Core modules (AI gateway, database, redis)
│   ├── models/               # SQLAlchemy models
│   ├── pipeline/             # News pipeline (analyzer, writer, etc.)
│   ├── publisher/            # WordPress publisher
│   ├── distribution/         # Social media distribution
│   ├── prediction/           # Stock/rypto prediction
│   ├── worker/               # Celery workers
│   ├── routers/              # API routes
│   └── main.py               # FastAPI entry point
├── dashboard/                # React frontend
│   ├── src/                  # React components
│   └── dist/                 # Built assets
├── nginx/                    # Nginx configurations
│   ├── default.conf          # Production config (for Docker)
│   └── nginx.windows.conf    # Windows dev config
├── wordpress/                # WordPress customizations
│   ├── mu-plugins/          # Must-use plugins
│   ├── prediction-widget/    # Stock prediction widget
│   └── themes/              # Custom themes
├── scripts/                  # Utility scripts
├── docker-compose.yml        # Docker services
├── Dockerfile.api           # FastAPI image
├── Dockerfile.worker        # Celery worker image
├── Dockerfile.dashboard      # React dashboard image
├── requirements.txt          # Python dependencies
└── .env                     # Environment variables
```

---

## PART 9: CÁC LỆNH QUAN TRỌNG

### 9.1 Docker Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api
docker-compose logs -f worker
docker-compose logs -f wordpress

# Restart specific service
docker-compose restart worker

# Stop all services
docker-compose down

# Rebuild after code changes
docker-compose build api
docker-compose build worker
docker-compose up -d
```

### 9.2 Database Commands

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U linew -d linew

# Backup database
docker-compose exec postgres pg_dump -U linew linew > backup.sql

# Restore database
cat backup.sql | docker-compose exec -T postgres psql -U linew linew
```

### 9.3 WordPress Commands

```bash
# Access WordPress container
docker-compose exec wordpress bash

# WordPress CLI (if wp-cli installed)
docker-compose exec wordpress wp user list
```

---

## PART 10: TROUBLESHOOTING

### 10.1 Common Issues

**1. API not responding:**
```bash
docker-compose logs api
docker-compose restart api
```

**2. Worker not processing tasks:**
```bash
docker-compose logs worker
docker-compose restart worker
```

**3. WordPress database connection error:**
```bash
docker-compose logs mysql
docker-compose restart mysql wordpress
```

**4. Cloudflare SSL error:**
- Check SSL mode is "Full" or "Full (strict)"
- Ensure WordPress URL is set to https://example.com

### 10.2 Health Check Endpoints

- API: http://localhost:8000/api/health
- Dashboard: http://localhost:3000
- WordPress: http://localhost:8888

---

## PART 11: BACKUP & DATA

### 11.1 Data Locations

- **PostgreSQL:** Docker volume `pgdata`
- **Redis:** Docker volume `redis_data`
- **WordPress:** Docker volume `wpdata`
- **Linew Data:** Bind mount at `${LINEW_DATA_PATH}`

### 11.2 Backup Script Location

Scripts in `app/backup/`:
- `postgres_dump.py` - Database backup
- `wordpress_backup.py` - WordPress backup
- `gdrive_service.py` - Google Drive upload

---

## PART 12: ENVIRONMENT VARIABLES TEMPLATE

Đây là template để copy sang máy mới:

```bash
# ========== LINEW ENVIRONMENT CONFIGURATION ==========
# Copy file này thành .env trên máy mới

# Database
DATABASE_URL=postgresql+asyncpg://linew:YOUR_DB_PASSWORD@postgres:5432/linew
DB_PASSWORD=YOUR_DB_PASSWORD

# Redis
REDIS_URL=redis://redis:6379/0

# AI Gateway - MiniMax via Vertex Key
VERTEX_API_KEY=YOUR_VERTEX_API_KEY
VERTEX_PROJECT_ID=minimax-chat
VERTEX_LOCATION=global
VERTEX_BASE_URL=https://vertex-key.com/api/v1

# AI Models
AI_WRITER_MODEL=aws/minimax-m2.5
AI_LIGHT_MODEL=aws/minimax-m2.5
AI_RESEARCHER_MODEL=aws/minimax-m2.5
AI_SUMMARIZER_MODEL=aws/minimax-m2.5

# WordPress
WP_URL=https://example.com
WP_USERNAME=YOUR_WP_USERNAME
WP_APP_PASSWORD=YOUR_WP_APP_PASSWORD

# FlareSolverr
FLARESOLVERR_URL=http://flaresolverr:8191/v1

# Application
SECRET_KEY=YOUR_SECRET_KEY
ENVIRONMENT=production
LOG_LEVEL=info

# TimesFM
TIMESFM_DEVICE=mps

# API
API_HOST=0.0.0.0
API_PORT=8000

# Distribution
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHANNEL_ID=@linews_vn
TELEGRAM_CHANNEL_ENABLED=false

FACEBOOK_PAGE_ID=
FACEBOOK_PAGE_ACCESS_TOKEN=
FACEBOOK_APP_ID=
FACEBOOK_APP_SECRET=
FACEBOOK_ENABLED=false

TWITTER_API_KEY=
TWITTER_API_SECRET=
TWITTER_ACCESS_TOKEN=
TWITTER_ACCESS_SECRET=
TWITTER_ENABLED=false

# Newsletter
NEWSLETTER_ENABLED=false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
NEWSLETTER_FROM_NAME=Linews
NEWSLETTER_FROM_EMAIL=linews@gmail.com

# Analytics & SEO
GA_MEASUREMENT_ID=
SITE_URL=https://example.com
SITE_NAME=Linews

# CORS
CORS_ORIGINS=

# Linew Data Path
LINEW_DATA_PATH=C:/Users/YOUR_USERNAME/Linew/data
```
