from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
import json
import httpx
from dotenv import load_dotenv

import requests
import google.generativeai as genai

import recommendation
from recommendation import get_recommendations 

load_dotenv()

# ==========================================
# 0. KHAI BÁO CÁC PYDANTIC MODELS
# ==========================================
class RecommendResponse(BaseModel):
    status: str
    product_ids: List[int]

class ChatRequest(BaseModel):
    user_id: Optional[str] = "khach_hang_test"
    message: str

# ==========================================
# 1. KNOWLEDGE BASE (RAG CƠ BẢN)
# ==========================================
faq_data = { 
  'giao hàng': 'Đơn hàng giao trong 3-5 ngày làm việc. Hỏa tốc: 2h tại HCM.', 
  'đổi trả': 'Đổi trả trong 30 ngày, hàng còn nguyên tem mác.', 
  'thanh toán': 'Hỗ trợ COD, VNPAY, MoMo, ZaloPay, thẻ tín dụng.', 
}


def load_product_data():
    all_products = []
    try:
        # 1. Gọi API kèm tham số size=50 để lấy nhiều sản phẩm hơn vào Context của AI
        response = requests.get("http://localhost:8080/api/products?size=50", timeout=5.0)
        if response.status_code == 200:
            data = response.json()

            # 2. Xử lý PagedResponse của Spring Boot
            # Thông thường, mảng dữ liệu sẽ nằm trong trường 'content' hoặc 'data'
            # Tùy thuộc vào cách bạn định nghĩa PagedResponse.java
            product_list = data.get("content", []) if isinstance(data, dict) else data

            # 3. Lấy ra tối đa 15 sản phẩm để tránh lỗi 429 (Quá tải Token của Gemini)
            for item in product_list[:15]:
                # Ép chặt kiểu ID thành chuỗi để làm link /products/id
                prod_id = str(item.get("id"))

                all_products.append({
                    "ID": prod_id,
                    "Tên": item.get("name", "Chưa cập nhật"),
                    "Mô tả": str(item.get("shortDescription", ""))[:80] + "...", 
                    "Cấu hình": str(item.get("specs", ""))[:100] + "..." 
                })
                
            return json.dumps(all_products, ensure_ascii=False)
        else:
            print(f"Lỗi API Spring Boot: {response.status_code}")
    except Exception as e:
        print(f"Lỗi kết nối tới Spring Boot: {e}")
        
    return "[]" # Trả về chuỗi rỗng nếu có lỗi để AI không bị sập

product_catalog_str = load_product_data()

# ==========================================
# 2. CẤU HÌNH GEMINI API
# ==========================================
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    print("Chua tim thay GEMINI_API_KEY. Chat Gemini se tam dung, cac endpoint recommendation van chay.")

app = FastAPI(title="Gemini RAG Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        print(f"Không thể kết nối đến Spring Boot: {e}")

# ==========================================
# 4. ENDPOINT CHATBOT (GEMINI + MOCK RAG)
# ==========================================
@app.post("/api/chat")
async def chat_with_gemini(request: ChatRequest, background_tasks: BackgroundTasks):
    try:
        if not api_key:
            raise HTTPException(status_code=503, detail="Chua cau hinh GEMINI_API_KEY.")

        user_msg = request.message
        
        context = '' 
        for key, val in faq_data.items(): 
            if key in user_msg.lower(): 
                context += val + ' ' 

        # CẬP NHẬT SYSTEM INSTRUCTION (Prompt Engineering)
        # CẬP NHẬT SYSTEM INSTRUCTION (Prompt Engineering)
        system_instruction = f"""Bạn là chatbot CSKH của hệ thống SOPE, chuyên tư vấn các dòng thiết bị công nghệ. 
            FAQ liên quan: {context} 
            Danh mục sản phẩm của shop hiện có (kèm ID/SKU): {product_catalog_str}

            Nhiệm vụ của bạn:
            - Luôn xưng hô thân thiện, nhiệt tình.
            - XỬ LÝ TÊN SẢN PHẨM THÔNG MINH: Nếu khách hỏi tên rút gọn (VD: 'iPhone 17 Pro'), hãy tự động ngầm hiểu đó là các sản phẩm có tên dài trong danh mục (VD: 'Điện thoại iPhone 17 Pro 256GB'). TUYỆT ĐỐI KHÔNG báo hết hàng nếu shop có phiên bản dung lượng/màu sắc của dòng máy đó.
            - KHI GỢI Ý SẢN PHẨM: Bắt buộc đính kèm link theo đúng chuẩn Markdown: [Tên sản phẩm](/products/ID_sản_phẩm). VD: [iPhone 17 Pro](/products/342667).
            - KHI SO SÁNH: Trình bày rõ ưu/nhược điểm dựa trên 'Cấu hình', sau đó chốt lời khuyên mua dòng nào cho ai. Dùng gạch đầu dòng cho dễ đọc.
            - Trả lời súc tích, đi thẳng vào vấn đề."""

        model = genai.GenerativeModel(
            'gemini-2.5-flash',
            system_instruction=system_instruction
        )

        response = await model.generate_content_async(user_msg)
        
        if not response.parts:
            bot_reply = "Xin lỗi, mình không thể xử lý câu hỏi này."
        else:
            bot_reply = response.text
        
        background_tasks.add_task(
            save_chat_to_springboot, 
            request.user_id, 
            user_msg, 
            bot_reply
        )

        return {
            "status": "success",
            "reply": bot_reply
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"======== CHI TIẾT LỖI TỪ GEMINI ======== \n{str(e)}")
        raise HTTPException(status_code=500, detail="Đã xảy ra lỗi kết nối với Gemini API.")

# ==========================================
# 5. CÁC ENDPOINT RECOMMENDATION
# ==========================================
@app.get("/api/ai/recommend/cf/{user_id}")
def recommend_products(user_id: int, top_n: int = 5):
    try:
        recommendations = get_recommendations(user_id, top_n)
        return {"status": "success", "product_ids": recommendations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống tính toán: {str(e)}")

@app.get("/api/ai/recommend/similar/{product_id}", response_model=RecommendResponse)
def get_similar_products_api(product_id: int, top_n: int = 5):
    try:
        ids = recommendation.get_similar_products(product_id, top_n)
        return {"status": "success", "product_ids": ids}
    except Exception as e:
        return {"status": "error", "product_ids": []}

@app.get("/api/ai/recommend/content-based/{product_id}", response_model=RecommendResponse)
def get_content_based_api(product_id: int, top_n: int = 5):
    try:
        ids = recommendation.get_content_based_similar_products(product_id, top_n)
        return {"status": "success", "product_ids": ids}
    except Exception as e:
        return {"status": "error", "product_ids": []}

@app.get("/")
async def root():
    return {"message": "FastAPI Server: Gemini Chatbot & Recommendation System is running!"}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
