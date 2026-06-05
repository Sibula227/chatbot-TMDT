from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# Nhung ham thuat toan vua xu li tu file recommender.py
from recommender import get_collaborative_recommendations

# Load biến môi trường từ file .env
load_dotenv()

# Cấu hình Gemini API
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("Chưa tìm thấy GEMINI_API_KEY trong file .env")

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-3.1-flash-lite') 

# Khởi tạo ứng dụng FastAPI
app = FastAPI(title="Gemini Chatbot API")

# <--  CẤU HÌNH CORS  -->
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ENDPOINT KIỂM TRA SERVER ---
@app.get("/")
async def root():
    return {"message": "FastAPI & Gemini Server is running!"}

# --- ENDPOINT CHAT VỚI GEMINI ---
class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
async def chat_with_gemini(request: ChatRequest):
    try:
        response = model.generate_content(request.message)
        return {
            "status": "success",
            "reply": response.text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- ENDPOINT GỢI Ý SẢN PHẨM ---
class RecommendRequest(BaseModel):
    user_id: int
    top_n: int = 3

@app.post("/api/recommend")
async def recommend_products(request: RecommendRequest):
    try:
        # Gọi hàm xử lý thuật toán từ file recommender.py
        recommended_items = get_collaborative_recommendations(request.user_id, request.top_n)
        return {
            "status": "success",
            "user_id": request.user_id,
            "recommendations": recommended_items
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))