from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional # Thêm thư viện để hỗ trợ Optional
import google.generativeai as genai
import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# 1. ĐỌC VÀ LỌC DỮ LIỆU TỪ MOCK DB (FILE JSON)
# ==========================================
def load_product_data():
    all_products = []
    files = ["data/data_phone.json", "data/data_tablet.json", "data/data_laptop.json"]
    
    for file_path in files:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # SỬA Ở ĐÂY: Lọc bỏ ảnh và review, chỉ lấy thông tin cốt lõi để AI hiểu
                # Việc này giúp tránh bị lỗi 500 do truyền dữ liệu quá lớn vào Gemini
                for item in data:
                    optimized_item = {
                        "Tên sản phẩm": item.get("product_name"),
                        "Mô tả": item.get("short_description"),
                        "Cấu hình": item.get("detailed_specs")
                    }
                    all_products.append(optimized_item)
                
    return json.dumps(all_products, ensure_ascii=False)

product_catalog_str = load_product_data()

# ==========================================
# 2. CẤU HÌNH GEMINI VỚI SYSTEM INSTRUCTION
# ==========================================
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("Chưa tìm thấy GEMINI_API_KEY trong file .env")

genai.configure(api_key=api_key)

system_instruction = f"""
Bạn là một nhân viên tư vấn bán hàng nhiệt tình và chuyên nghiệp. 
Dưới đây là danh sách các sản phẩm (điện thoại, tablet, laptop) mà cửa hàng đang có:
{product_catalog_str}

Khi khách hàng hỏi, hãy đối chiếu với danh sách sản phẩm này để tư vấn (tên, mô tả, cấu hình, v.v.). 
Nếu sản phẩm không có trong danh sách, hãy nói khéo léo là cửa hàng hiện chưa kinh doanh sản phẩm đó.
"""

model = genai.GenerativeModel(
    'gemini-2.5-flash',
    system_instruction=system_instruction
)

app = FastAPI(title="Gemini Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SỬA Ở ĐÂY: Cho phép user_id là không bắt buộc (Optional) để bạn dễ test trên Swagger
class ChatRequest(BaseModel):
    user_id: Optional[str] = "khach_hang_test" 
    message: str

# ==========================================
# 3. HÀM ĐẨY DATA VỀ SPRING BOOT
# ==========================================
SPRING_BOOT_API_URL = "http://localhost:8080/api/chat/save"

async def save_chat_to_springboot(user_id: str, user_message: str, bot_reply: str):
    payload = {
        "userId": user_id,
        "userMessage": user_message,
        "botReply": bot_reply
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(SPRING_BOOT_API_URL, json=payload, timeout=5.0)
            if response.status_code != 200:
                print(f"Lỗi khi lưu về Spring Boot: {response.text}")
    except Exception as e:
        # Nếu Spring Boot tắt, nó sẽ in dòng này ra Terminal nhưng không làm sập FastAPI
        print(f"Không thể kết nối đến Spring Boot: {e}")

# ==========================================
# 4. ENDPOINT CHÍNH
# ==========================================
@app.post("/api/chat")
async def chat_with_gemini(request: ChatRequest, background_tasks: BackgroundTasks):
    try:
        # Gọi API tới Gemini
        response = model.generate_content(request.message)
        
        # SỬA Ở ĐÂY: Thêm khối kiểm tra an toàn, phòng trường hợp AI bị chặn trả lời
        if not response.parts:
            bot_reply = "Xin lỗi, tôi không thể xử lý câu hỏi này."
        else:
            bot_reply = response.text
        
        # Gọi Spring Boot chạy ngầm
        background_tasks.add_task(
            save_chat_to_springboot, 
            request.user_id, 
            request.message, 
            bot_reply
        )

        return {
            "status": "success",
            "reply": bot_reply
        }
    except Exception as e:
        # SỬA Ở ĐÂY: In rõ lỗi ra màn hình Terminal để bạn dễ dàng bắt bệnh
        print(f"======== CHI TIẾT LỖI TỪ GEMINI ======== \n{str(e)}")
        raise HTTPException(status_code=500, detail="Đã xảy ra lỗi, vui lòng kiểm tra Terminal FastAPI")

@app.get("/")
async def root():
    return {"message": "FastAPI & Gemini Server is running with Mock DB!"}
#A10: Sửa lỗi build và dependency