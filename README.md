# SOPE Chatbot

FastAPI service phụ trách hội thoại Gemini và recommendation cho hệ thống SOPE.

Luồng tích hợp:

```text
Frontend → Spring Boot Backend → FastAPI Chatbot → Gemini
                              ↘ catalog sản phẩm nhẹ từ Backend
```

Frontend không gọi trực tiếp service này. Khi chạy đầy đủ, hãy khởi động
Spring Boot backend trước chatbot.

## Mô tả dự án

SOPE Chatbot là AI service nội bộ của hệ thống, phụ trách:

- Nhận chat request do Spring Boot proxy tới.
- Dùng Gemini để tạo câu trả lời tiếng Việt.
- Chỉ tư vấn dựa trên catalog thật lấy từ Spring Boot backend.
- Lọc một nhóm product nhỏ trước khi tạo prompt, không gửi toàn bộ catalog.
- Tạo gợi ý content-based bằng TF-IDF và cosine similarity.
- Cache catalog/model CBF và chống build trùng khi có request đồng thời.
- Fallback về JSON/list rỗng khi backend hoặc recommendation tạm lỗi.
- Cung cấp health endpoint cho Render/Docker.

Các service production:

| Thành phần | Link deploy |
|---|---|
| Website SOPE | [https://sope-frontend-self.vercel.app/](https://sope-frontend-self.vercel.app/) |
| Spring Boot API | [https://sope-backend-wezh.onrender.com/](https://sope-backend-wezh.onrender.com/) |
| FastAPI Chatbot | [https://chatbot-tmdt.onrender.com/](https://chatbot-tmdt.onrender.com/) |

## Tài khoản admin mặc định

Tài khoản admin được xác thực và quản lý bởi Spring Boot backend, không phải
FastAPI chatbot:

| Thông tin | Giá trị |
|---|---|
| Tên đăng nhập | `admin` |
| Mật khẩu | `admin123` |

Đây là credential local/demo. Production phải đổi `APP_ADMIN_PASSWORD` ở
backend và không truyền tài khoản admin, JWT hoặc mật khẩu vào prompt Gemini.

## Cấu trúc dự án

```text
chatbot-TMDT/
├── main.py                       # FastAPI app, chat/Gemini và API routes
├── recommendation.py             # CF, CBF, TF-IDF, cache và fallback
├── normalize_specs.py            # Chuẩn hóa thông số sản phẩm
├── timeout_config.py             # Timeout requests/httpx tập trung
├── check_model.py                # Kiểm tra cấu hình/model Gemini
├── policy.json                   # Nội dung chính sách dùng trong chat
├── requirements.txt              # Python dependencies
├── .env.example                  # Mẫu cấu hình local/Render
├── Dockerfile                    # Python 3.12 non-root image
├── test_timeout.py               # Test parse và sử dụng timeout
├── test_concurrency_timeout.py   # Test cache, concurrency và fallback
├── test_day12.py ... day15.py    # Regression test các chức năng AI
├── CHANGELOG.md                  # Lịch sử thay đổi
├── CONTEXT.md                    # Ghi chú kỹ thuật của repository
└── README.md                     # Hướng dẫn hiện tại
```

Vai trò từng file/khu vực:

| File | Chức năng |
|---|---|
| `main.py` | Khởi tạo FastAPI, gọi Gemini, tải catalog chat và khai báo endpoint |
| `recommendation.py` | Tải dữ liệu backend, chuẩn hóa và tính recommendation |
| `normalize_specs.py` | Chuẩn hóa text/spec để so sánh ổn định hơn |
| `timeout_config.py` | Đọc timeout từ environment và tạo config HTTP client |
| `policy.json` | Nguồn nội dung chính sách, tránh hard-code trong prompt |
| `check_model.py` | Chẩn đoán API key/model trước khi chạy chat |
| `test_*.py` | Unit/regression test, mock network thay vì gọi production |
| `.env.example` | Danh sách biến môi trường; không chứa secret thật |

## Yêu cầu

- Python 3.12.
- Spring Boot backend chạy tại `http://localhost:8080`.
- Gemini API key.
- Service key dùng chung với backend:
  - chatbot: `SOPE_SERVICE_KEY`;
  - backend: `CHATBOT_SECRET`.

## 1. Cấu hình local

Mở PowerShell tại thư mục `chatbot-TMDT`:

```powershell
Copy-Item .env.example .env
```

Mở `.env` và cấu hình ít nhất:

```dotenv
PORT=8000
GEMINI_API_KEY=<your-gemini-api-key>
SOPE_BACKEND_API_URL=http://localhost:8080/api
SOPE_SERVICE_KEY=<same-value-as-backend-CHATBOT_SECRET>
```

Không commit `.env` và không đưa API key/service key vào source code hoặc log.

Các giá trị mặc định còn lại đã có trong `.env.example`:

| Biến | Mặc định | Ý nghĩa |
|---|---:|---|
| `SOPE_CONNECT_TIMEOUT` | `5` | Connect timeout khi gọi backend, tính bằng giây |
| `SOPE_API_TIMEOUT` | `30` | Read/write timeout, tính bằng giây |
| `SOPE_PRODUCTS_CACHE_TTL_SECONDS` | `60` | TTL catalog dùng cho chat |
| `SOPE_CHATBOT_MAX_PRODUCTS_FOR_PROMPT` | `15` | Số product tối đa đưa vào prompt |
| `SOPE_RECOMMENDATION_PAGE_SIZE` | `15` | Page size khi tải catalog cho CBF |
| `SOPE_RECOMMENDATION_MAX_PAGES` | `20` | Số page CBF tối đa |
| `SOPE_RECOMMENDATION_MAX_PRODUCTS` | `300` | Số product CBF tối đa |
| `CBF_CACHE_TTL_SECONDS` | `600` | TTL model TF-IDF/CBF |
| `SOPE_MAX_MESSAGE_LENGTH` | `2000` | Độ dài tối đa của tin nhắn |
| `SOPE_MAX_REPLY_LENGTH` | `3000` | Độ dài tối đa của câu trả lời |
| `SOPE_MAX_RECOMMENDATIONS` | `10` | Số gợi ý tối đa |

`SOPE_BACKEND_API_URL` phải kết thúc bằng `/api`. Không ghi
`/api/internal/chatbot/products` trực tiếp vào biến này.

## 2. Tạo môi trường Python và cài dependency

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Có thể kích hoạt virtual environment nếu PowerShell cho phép:

```powershell
.\.venv\Scripts\Activate.ps1
```

### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 3. Chạy chatbot

Windows:

```powershell
.\.venv\Scripts\python.exe main.py
```

macOS/Linux:

```bash
python main.py
```

Service mặc định chạy tại:

```text
http://127.0.0.1:8000
```

Các endpoint chính:

| Chức năng | Method | Endpoint |
|---|---|---|
| Health | `GET` | `/health` |
| Chat | `POST` | `/api/chat` |
| Content-based recommendation | `GET` | `/api/ai/recommend/content-based/{product_id}` |
| Similar products | `GET` | `/api/ai/recommend/similar/{product_id}` |
| Popular products | `GET` | `/api/ai/recommend/popular` |

## 4. Kiểm tra nhanh

Health:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/health"
```

Chat:

```powershell
$body = @{
  user_id = "local-test"
  message = "Tư vấn cho tôi iPhone 17"
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/chat" `
  -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Body $body
```

Recommendation:

```powershell
Invoke-RestMethod `
  "http://127.0.0.1:8000/api/ai/recommend/content-based/3?top_n=5"
```

`/health` có thể trả `200` khi chưa có Gemini key, nhưng `/api/chat` cần
`GEMINI_API_KEY`. Các luồng product/chat/recommendation cần backend đang chạy và
service key khớp.

## 5. Chạy test

Test concurrency, timeout và fallback:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -m unittest `
  test_timeout.py `
  test_concurrency_timeout.py `
  -v
```

Regression test cũ:

```powershell
.\.venv\Scripts\python.exe test_day12.py
.\.venv\Scripts\python.exe test_day13.py
.\.venv\Scripts\python.exe test_day14.py
.\.venv\Scripts\python.exe test_day15.py
```

Kiểm tra cú pháp:

```powershell
.\.venv\Scripts\python.exe -m py_compile `
  main.py `
  recommendation.py `
  timeout_config.py
```

Unit test đã mock network/Gemini, không yêu cầu gọi Render hoặc Gemini thật.

## 6. Chạy bằng Docker

```powershell
docker build -t sope-chatbot .
docker run --rm `
  --name sope-chatbot `
  -p 8000:8000 `
  --env-file .env `
  sope-chatbot
```

Image dùng Python 3.12, chạy bằng non-root user và có healthcheck `/health`.

Để chạy toàn bộ hệ thống bằng Docker Compose, dùng file ở thư mục cha:

```powershell
Set-Location ..
docker compose --env-file .env build
docker compose --env-file .env up -d
docker compose ps
```

## 7. Lỗi thường gặp

### `/api/chat` trả 503 vì chưa cấu hình Gemini

Kiểm tra `GEMINI_API_KEY` trong `.env`, sau đó khởi động lại chatbot.

### Không tải được catalog hoặc recommendation trả rỗng

Kiểm tra:

- Backend có chạy tại `http://localhost:8080`.
- `SOPE_BACKEND_API_URL=http://localhost:8080/api`.
- `SOPE_SERVICE_KEY` trùng `CHATBOT_SECRET` của backend.
- Endpoint backend `/api/internal/chatbot/products` không trả 403.

### Port 8000 đang được sử dụng

Đổi `PORT` trong `.env`, ví dụ:

```dotenv
PORT=8001
```

### PowerShell không cho chạy `Activate.ps1`

Không cần đổi execution policy. Dùng trực tiếp:

```powershell
.\.venv\Scripts\python.exe main.py
```

## 8. Deploy

- Render service hiện tại: `https://chatbot-tmdt.onrender.com`.
- Website tích hợp chatbot:
  [https://sope-frontend-self.vercel.app/](https://sope-frontend-self.vercel.app/).
- Đặt toàn bộ environment variables trên Render, không upload `.env`.
- Có thể giữ `WEB_CONCURRENCY=1`; các route CBF đồng bộ đã chạy trong thread
  pool và cache single-flight là theo từng process.
- Deploy backend trước chatbot vì chatbot phụ thuộc endpoint catalog nội bộ.

Xem thêm:

- `../DEPLOYMENT.md`
- `../CHATBOT_CONCURRENCY_TIMEOUT_FIX_REPORT.md`
