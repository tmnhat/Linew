# Linew - Hướng dẫn sử dụng Pipeline

## Tổng quan

Hệ thống Linew Pipeline đã được nâng cấp với các tính năng mới:
- **Continuous Mode**: Pipeline chạy liên tục cho đến khi bấm Stop
- **Batch Mode**: Pipeline xử lý một batch và tự động dừng
- **Real-time Status**: Theo dõi trạng thái pipeline theo thời gian thực

## Cách sử dụng

### 1. Dashboard UI (Khuyến nghị)

Truy cập: `http://localhost/dashboard/#/pipeline`

**Các nút điều khiển:**
- **Continuous** (màu xanh lá): Khởi động pipeline chạy liên tục
- **Stop** (màu đỏ): Dừng pipeline đang chạy
- **Batch Normal**: Chạy một batch với đầy đủ bước (categorize → trend → research → write → govern → publish)
- **Batch All-in**: Chạy nhanh không qua trend scoring

### 2. API Endpoints

#### Khởi động Pipeline

```bash
# Batch mode (xử lý 1 lần)
curl -X POST http://localhost:8000/api/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{"mode": "normal", "limit": 10}'

# Continuous mode (chạy liên tục)
curl -X POST http://localhost:8000/api/pipeline/continuous/start \
  -H "Content-Type: application/json" \
  -d '{"limit": 5}'
```

#### Dừng Pipeline

```bash
curl -X POST http://localhost:8000/api/pipeline/stop
```

#### Kiểm tra trạng thái

```bash
curl http://localhost:8000/api/pipeline/info | python3 -m json.tool
```

### 3. Script khởi động nhanh

```bash
cd /path/to/linew

# Khởi động toàn bộ hệ thống
./scripts/start-linew.sh docker

# Kiểm tra trạng thái
./scripts/start-linew.sh status

# Khởi động continuous pipeline
./scripts/start-linew.sh continuous

# Xem logs
./scripts/start-linew.sh logs worker

# Dừng tất cả
./scripts/start-linew.sh stop
```

## Trạng thái Pipeline

| Trạng thái | Mô tả |
|------------|--------|
| `stopped` | Pipeline đang dừng |
| `running` | Pipeline đang chạy |
| `stopping` | Pipeline đang dừng (sau khi bấm stop) |

## Chế độ Pipeline

| Chế độ | Mô tả |
|--------|--------|
| `normal` | Đầy đủ các bước, có trend scoring |
| `allin` | Nhanh, bỏ qua trend scoring |
| `continuous` | Chạy liên tục cho đến khi stop |

## Luồng xử lý

```
Signal → Categorize → Trending → Research → Write → Govern → Publish
   ↓           ↓          ↓         ↓        ↓        ↓        ↓
 RSS Feed   AI Classify AI Score  Content  AI Write AI Check  WordPress
```

## Xử lý sự cố

### Pipeline không chạy

1. Kiểm tra worker:
```bash
docker logs linew-worker-1 --tail 30
```

2. Kiểm tra API:
```bash
curl http://localhost:8000/api/health
```

3. Restart services:
```bash
docker-compose restart worker api beat
```

### Lỗi kết nối Redis

```bash
docker-compose restart redis
```

### Lỗi kết nối Database

```bash
docker-compose restart postgres
```

## Monitoring

### Kiểm tra logs real-time

```bash
# Worker logs
docker logs -f linew-worker-1

# API logs
docker logs -f linew-api-1

# Beat scheduler logs
docker logs -f linew-beat-1
```

### Kiểm tra Celery tasks

```bash
# Xem active tasks
docker exec linew-redis-1 redis-cli LLEN celery

# Xem pending tasks
docker exec linew-redis-1 redis-cli LRANGE celery.pidbox 0 -1
```

## Cấu hình nâng cao

### Thay đổi batch size

```bash
# Khi khởi động continuous mode
curl -X POST http://localhost:8000/api/pipeline/continuous/start \
  -H "Content-Type: application/json" \
  -d '{"limit": 20}'  # Mặc định là 10
```

### Thay đổi interval trong scheduler

Sửa file `app/worker/scheduler.py`:
- RSS Fetch: Mặc định 30 phút
- Pipeline Run: Mặc định 60 phút (batch mode)
- Watchdog: Mặc định 5 phút

## Lưu ý

1. **Continuous Mode**: Pipeline sẽ tự động dừng sau 12 batch trống liên tiếp (~1 phút) nếu không có bài viết nào để xử lý.

2. **AI Rate Limits**: Hệ thống có rate limit cho AI calls (10 calls/phút cho task_write). Nếu gặp lỗi, đợi và thử lại.

3. **FlareSolverr**: Một số trang web cần FlareSolverr để bypass Cloudflare. Nếu FlareSolverr không hoạt động, hệ thống sẽ fallback sang RSS summary.

4. **Database Cleanup**: Bài viết thất bại sau 24 giờ sẽ được tự động xóa (có thể cấu hình trong settings).
