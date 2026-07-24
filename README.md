# chatbot-TMDT

FastAPI chatbot của SOPE. Luồng dữ liệu: Backend Spring Boot gọi `/api/chat`; chatbot gọi lại API sản phẩm của Backend và dùng Gemini để tạo phản hồi.

## Chạy local trên Windows

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Sao chép `.env.example` thành `.env` và điền các giá trị. Không commit `.env`.

## Biến môi trường

| Biến | Mặc định | Mô tả |
|---|---|---|
| `GEMINI_API_KEY` | _(bắt buộc)_ | API key Google Gemini |
| `SOPE_BACKEND_API_URL` | `http://localhost:8080/api` | URL backend Spring Boot |
| `SOPE_SERVICE_KEY` | `` | Khóa dịch vụ nội bộ (gửi qua header `X-Service-Key`) |
| `SOPE_API_TIMEOUT` | `10` | Timeout (giây) khi gọi backend |
| `SOPE_PRODUCTS_CACHE_TTL_SECONDS` | `60` | TTL cache danh sách sản phẩm (giây) |
| `SOPE_CHATBOT_MAX_PRODUCTS_FOR_PROMPT` | `15` | Số sản phẩm tối đa đưa vào prompt Gemini |
| `SOPE_CBF_CACHE_TTL` | `3600` | TTL cache ma trận TF-IDF CBF (giây) |
| `SOPE_MAX_MESSAGE_LENGTH` | `2000` | Giới hạn độ dài tin nhắn đầu vào |
| `SOPE_MAX_REPLY_LENGTH` | `3000` | Giới hạn độ dài reply trả về |
| `SOPE_MAX_RECOMMENDATIONS` | `10` | Số sản phẩm gợi ý tối đa |
| `SOPE_RATE_LIMIT_MAX_REQUESTS` | `30` | Số request tối đa mỗi user mỗi cửa sổ |
| `SOPE_RATE_LIMIT_WINDOW_SEC` | `60` | Cửa sổ rate limiting (giây) |

- Health: `GET http://localhost:8000/health`
- Chat: `POST http://localhost:8000/api/chat`
- Backend mặc định: `http://localhost:8080/api`

## Test nhanh

```powershell
# Test health
Invoke-RestMethod -Uri http://localhost:8000/health

# Test chat
Invoke-RestMethod -Uri http://localhost:8000/api/chat -Method Post `
  -ContentType "application/json" `
  -Body '{"user_id":"test","message":"goi y dien thoai samsung"}'
```

## Deploy

Image Docker chạy Python 3.12 bằng user không có quyền root và có healthcheck:

```bash
docker build -t sope-chatbot .
docker run --rm -p 8000:8000 --env-file .env sope-chatbot
```

`.dockerignore` loại `.env`, cache và test khỏi image. Khi chạy production,
chatbot chỉ nên nằm trong private network; Backend Spring Boot là cổng duy nhất
nhận request chatbot từ frontend.

Để deploy đủ MySQL + Backend + Chatbot + Frontend, dùng
`../docker-compose.yml`, `../.env.example` và `../DEPLOYMENT.md`.
