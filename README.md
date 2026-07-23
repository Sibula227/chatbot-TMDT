# chatbot-TMDT

FastAPI chatbot của SOPE. Luồng dữ liệu: Backend Spring Boot gọi `/api/chat`; chatbot gọi lại API sản phẩm của Backend và dùng Gemini để tạo phản hồi.

## Chạy local trên Windows

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Sao chép `.env.example` thành `.env` và điền `GEMINI_API_KEY`. Không commit `.env`.

- Health: `GET http://localhost:8000/health`
- Chat: `POST http://localhost:8000/api/chat`
- Backend mặc định: `http://localhost:8080/api`

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
