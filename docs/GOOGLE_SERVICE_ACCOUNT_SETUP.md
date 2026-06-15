# Hướng Dẫn Tạo Google Service Account Key cho Linew

## Tổng Quan

Để Linew có thể tự động ping Google Indexing API khi bài viết mới được publish, bạn cần tạo một Service Account với quyền truy cập Indexing API.

---

## BƯỚC 1: Disable Organization Policy (TẠM THỜI)

Do Google Cloud đã enforce policy `iam.disableServiceAccountKeyCreation`, bạn cần tắt tạm thời policy này để tạo key.

### 1.1 Truy cập Organization Policies

1. Truy cập: **https://console.cloud.google.com/iam-admin/orgpolicies**
2. Đảm bảo bạn đã chọn **Organization** từ dropdown ở góc trên bên trái
3. Trong ô **Filter**, gõ: `disableServiceAccountKeyCreation`

### 1.2 Tắt Enforcement

1. Click vào **Disable service account key creation**
2. Click **Manage policy**
3. Trong phần **Policy source**, chọn **Override parent's policy**
4. Trong phần **Enforcement**, bỏ tick **Enforce**
5. Click **Set policy**

**Lưu ý:** Policy có thể mất 5-10 phút để apply.

---

## BƯỚC 2: Tạo Service Account

### 2.1 Tạo Service Account mới

1. Truy cập: **https://console.cloud.google.com/iam-admin/serviceaccounts**
2. Click **+ CREATE SERVICE ACCOUNT**

### 2.2 Điền thông tin

```
Service account name: linew-indexing
Service account ID: linew-indexing (sẽ tự điền)
Description: For Linew Google Indexing API
```

3. Click **CREATE AND CONTINUE**

### 2.3 Thêm quyền (Optional)

1. Trong phần **Grant this service account access to project**:
2. Click **ADD ANOTHER ROLE**
3. Tìm và chọn: **Indexing API Editor** (hoặc gõ trong filter)
4. Click **DONE**

---

## BƯỚC 3: Tạo Service Account Key

### 3.1 Tạo JSON Key

1. Trong danh sách Service Accounts, click vào **linew-indexing** vừa tạo
2. Chuyển sang tab **KEYS**
3. Click **ADD KEY** → **Create new key**
4. Chọn **JSON** (recommended)
5. Click **CREATE**

### 3.2 Lưu file

- File JSON sẽ được download tự động
- **QUAN TRỌNG:** Lưu file này ở nơi an toàn, KHÔNG commit vào git
- Đặt tên file: `google-service-account.json`

---

## BƯỚC 4: Thêm Service Account vào Google Search Console

### 4.1 Cấp quyền truy cập

1. Truy cập: **https://search.google.com/search-console**
2. Chọn property: `https://example.com`
3. Click **Settings** (Cài đặt) ở menu bên trái
4. Click **Users and permissions**
5. Click **ADD USER**

### 4.2 Thêm Service Account

```
Email: linew-indexing@YOUR_PROJECT_ID.iam.gserviceaccount.com
Permission: Owner (hoặc Editor)
```

**Cách tìm Project ID:**
- Truy cập: **https://console.cloud.google.com/home**
- Project ID nằm ở card project của bạn
- Thường có dạng: `your-project-123456` hoặc `my-gcp-project`

### 4.3 Xác nhận

- Click **ADD USER**
- Email của service account sẽ xuất hiện trong danh sách

---

## BƯỚC 5: Cấu hình trong Linew

### 5.1 Copy file credentials vào thư mục Linew

1. Copy file `google-service-account.json` đã download vào thư mục Linew
2. Đề xuất đặt ở: `C:\Users\duyen\Linew\config\google-service-account.json`

### 5.2 Chạy script để encode credentials

Mở PowerShell và chạy:

```powershell
cd C:\Users\duyen\Linew
.\scripts\encode-google-credentials.ps1
```

### 5.3 Hoặc copy trực tiếp vào .env

Mở file `google-service-account.json`, copy toàn bộ nội dung và paste vào `.env`:

```
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"your-project",...}
```

**Lưu ý:** Nội dung JSON phải trên một dòng, không có xuống dòng.

---

## BƯỚC 6: Khởi động lại Linew

```powershell
cd C:\Users\duyen\Linew
docker-compose down
docker-compose up -d
```

---

## BƯỚC 7: Kiểm tra kết nối

Truy cập dashboard Linew → SEO → Kiểm tra kết nối Google Indexing API.

Hoặc qua API:

```bash
curl http://localhost:8000/api/seo/test-connections
```

Kết quả mong đợi:
```json
{
  "google": {"status": "connected"},
  "bing": {"status": "not_configured"},
  "overall": "partial"
}
```

---

## BƯỚC 8: Bật lại Organization Policy (KHUYẾN NGHỊ)

Sau khi đã tạo key thành công, bạn nên bật lại enforcement để bảo mật:

1. Quay lại **https://console.cloud.google.com/iam-admin/orgpolicies**
2. Tìm `disableServiceAccountKeyCreation`
3. Click **Manage policy**
4. Bật **Enforce**
5. Click **Set policy**

---

## XỬ LÝ SỰ CỐ

### Lỗi: "Service account key creation is disabled"

→ Policy chưa được disable hoặc chưa apply. Đợi 5-10 phút và thử lại.

### Lỗi: "The project id not being fetched correctly"

→ Kiểm tra lại file JSON, đảm bảo không có lỗi format.

### Lỗi: "PERMISSION_DENIED" khi ping

→ Service account chưa được thêm vào Google Search Console. Xem Bước 4.

### Lỗi: "Socket timeout" hoặc connection error

→ Kiểm tra credentials và network connection.

---

## THÔNG TIN BỔ SUNG

### Tìm Project ID

1. Truy cập: **https://console.cloud.google.com/home/dashboard**
2. Project ID nằm ở phần **Project info** hoặc **Select a project**

### Tìm Service Account Email

1. Truy cập: **https://console.cloud.google.com/iam-admin/serviceaccounts**
2. Click vào service account
3. Email có dạng: `<name>@<project>.iam.gserviceaccount.com`

---

## BẢO MẬT

- **KHÔNG** commit file `google-service-account.json` vào git
- Thêm vào `.gitignore` nếu chưa có
- Store credentials ở nơi an toàn
- Xem xét sử dụng secret management (Vault, AWS Secrets Manager) cho production
