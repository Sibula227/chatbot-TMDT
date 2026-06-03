from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# Load biến môi trường từ file .env
load_dotenv()

# Cấu hình Gemini API
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("Chưa tìm thấy GEMINI_API_KEY trong file .env")

genai.configure(api_key=api_key)

# Khởi tạo model (dùng gemini-1.5-flash cho các tác vụ chat thông thường vì nó nhanh và rẻ)
model = genai.GenerativeModel('gemini-1.5-flash')

# Khởi tạo ứng dụng FastAPI
app = FastAPI(title="Gemini Chatbot API")

# <--  CẤU HÌNH CORS  -->
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép tất cả các origin (domain) gọi API
    allow_credentials=True,
    allow_methods=["*"],  # Cho phép tất cả các HTTP method (GET, POST, OPTIONS, v.v.)
    allow_headers=["*"],  # Cho phép tất cả các headers
)
# Định nghĩa cấu trúc dữ liệu nhận vào từ Client (DTO)
class ChatRequest(BaseModel):
    message: str

# Tạo Endpoint POST để nhận tin nhắn và trả về phản hồi
@app.post("/api/chat")
async def chat_with_gemini(request: ChatRequest):
    try:
        # Gọi API tới Gemini
        response = model.generate_content(request.message)
        return {
            "status": "success",
            "reply": response.text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint kiểm tra sức khỏe của server
@app.get("/")
async def root():
    return {"message": "FastAPI & Gemini Server is running!"}