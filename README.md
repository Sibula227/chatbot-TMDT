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

Từ root workspace có thể dùng `scripts/start-local.ps1` để chạy đủ Backend, Chatbot và Frontend theo đúng thứ tự.
