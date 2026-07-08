from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import os
import json
import httpx
import re
import time
import unicodedata
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


BACKEND_API_BASE_URL = os.getenv("SOPE_BACKEND_API_URL", "http://localhost:8080/api").rstrip("/")
PRODUCTS_ENDPOINT = f"{BACKEND_API_BASE_URL}/products"


def get_int_env(name: str, default: int) -> int:
    try:
        return max(int(os.getenv(name, str(default))), 1)
    except ValueError:
        return default


PRODUCTS_CACHE_TTL_SECONDS = get_int_env("SOPE_PRODUCTS_CACHE_TTL_SECONDS", 60)
MAX_PRODUCTS_FOR_PROMPT = get_int_env("SOPE_CHATBOT_MAX_PRODUCTS_FOR_PROMPT", 15)
_product_cache: Dict[str, Any] = {"expires_at": 0.0, "products": []}

PRODUCT_INTENT_TERMS = (
    "san pham",
    "goi y",
    "tu van",
    "mua",
    "gia",
    "dien thoai",
    "smartphone",
    "iphone",
    "samsung",
    "oppo",
    "xiaomi",
    "vivo",
    "laptop",
    "macbook",
    "may tinh",
    "may tinh bang",
    "tablet",
    "ipad",
    "bao hanh",
    "khuyen mai",
    "con hang",
)

CATEGORY_ALIASES = {
    "phone": ("phone", "dien thoai", "smartphone", "iphone", "samsung", "oppo", "xiaomi", "vivo"),
    "laptop": ("laptop", "macbook", "may tinh xach tay"),
    "tablet": ("tablet", "ipad", "may tinh bang"),
}

PRODUCT_FAMILY_ALIASES = (
    "iphone",
    "ipad",
    "macbook",
    "samsung",
    "oppo",
    "xiaomi",
    "redmi",
    "vivo",
    "realme",
)

STOPWORDS = {
    "anh", "ban", "can", "co", "cho", "cua", "de", "duoc", "gi", "goi",
    "dung", "hang", "hoi", "khong", "la", "lam", "may", "minh", "mot", "mua", "muon",
    "nao", "nen", "nhat", "nhung", "san", "pham", "so", "toi", "tot",
    "tu", "van", "va", "ve", "voi", "xem", "y",
}

SPEC_PRIORITY_TERMS = (
    "chip xu ly",
    "cpu",
    "chip do hoa",
    "gpu",
    "toc do cpu",
    "cong nghe cpu",
    "ram",
    "bo nho",
    "o cung",
    "dung luong",
    "man hinh",
    "pin",
)

CPU_SPEC_TERMS = ("chip xu ly", "cpu", "cong nghe cpu")
GPU_SPEC_TERMS = ("chip do hoa", "gpu", "card man hinh")


def normalize_text(value: Any) -> str:
    text = str(value or "").lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = text.replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip()


def compact_text(value: Any, max_length: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= max_length:
        return text
    return text[:max_length].rstrip() + "..."


def extract_product_list(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, dict):
        content = payload.get("content", [])
        return content if isinstance(content, list) else []
    return payload if isinstance(payload, list) else []


def load_products_from_backend(force_refresh: bool = False) -> List[Dict[str, Any]]:
    now = time.time()
    cached_products = _product_cache.get("products") or []
    if not force_refresh and cached_products and now < float(_product_cache.get("expires_at", 0)):
        return cached_products

    all_products = []
    try:
        page = 0
        while True:
            response = requests.get(
                PRODUCTS_ENDPOINT,
                params={"page": page, "size": 100, "sortBy": "id", "sortDir": "asc"},
                timeout=5.0,
            )
            if response.status_code != 200:
                print(f"Lỗi API Spring Boot khi lấy sản phẩm: {response.status_code}")
                break

            payload = response.json()
            all_products.extend(extract_product_list(payload))

            if not isinstance(payload, dict):
                break
            total_pages = int(payload.get("totalPages") or page + 1)
            if payload.get("last", True) or page + 1 >= total_pages:
                break
            page += 1

        if all_products:
            _product_cache["products"] = all_products
            _product_cache["expires_at"] = now + PRODUCTS_CACHE_TTL_SECONDS
            return all_products
    except Exception as e:
        print(f"Lỗi kết nối tới Spring Boot khi lấy sản phẩm: {e}")

    return cached_products


def is_product_question(message: str) -> bool:
    normalized = normalize_text(message)
    return any(term in normalized for term in PRODUCT_INTENT_TERMS)


def detect_categories(message: str) -> List[str]:
    normalized = normalize_text(message)
    categories = []
    for category, aliases in CATEGORY_ALIASES.items():
        if any(alias in normalized for alias in aliases):
            categories.append(category)
    return categories


def detect_product_families(message: str) -> List[str]:
    normalized = normalize_text(message)
    return [alias for alias in PRODUCT_FAMILY_ALIASES if alias in normalized]


def detect_model_phrases(message: str) -> List[str]:
    tokens = re.findall(r"[a-z0-9]+", normalize_text(message))
    phrases = []
    for index, token in enumerate(tokens):
        if token not in PRODUCT_FAMILY_ALIASES:
            continue

        model_tokens = []
        for next_token in tokens[index + 1:index + 4]:
            if next_token in STOPWORDS:
                break
            model_tokens.append(next_token)

        if model_tokens and any(any(char.isdigit() for char in item) for item in model_tokens):
            phrases.append(" ".join([token, *model_tokens]))

    return phrases


def parse_price_value(value: str, unit: str) -> int:
    number = float(value.replace(",", "."))
    normalized_unit = normalize_text(unit)
    if normalized_unit in {"trieu", "tr", "m"}:
        return int(number * 1_000_000)
    if normalized_unit in {"nghin", "ngan", "k"}:
        return int(number * 1_000)
    return int(number)


def extract_price_bounds(message: str) -> tuple[Optional[int], Optional[int]]:
    normalized = normalize_text(message)
    matches = list(re.finditer(r"(\d+(?:[.,]\d+)?)\s*(trieu|tr|m|nghin|ngan|k|dong|vnd)?", normalized))
    if not matches:
        return None, None

    fallback_unit = next((match.group(2) for match in reversed(matches) if match.group(2)), "dong")
    values = [
        (parse_price_value(match.group(1), match.group(2) or fallback_unit), match.start())
        for match in matches
    ]
    min_price = None
    max_price = None

    if "tu" in normalized and "den" in normalized and len(values) >= 2:
        low, high = values[0][0], values[1][0]
        return min(low, high), max(low, high)

    for value, start in values:
        before = normalized[max(0, start - 24):start]
        if any(term in before for term in ("duoi", "toi da", "khong qua", "nho hon")):
            max_price = value if max_price is None else min(max_price, value)
        elif any(term in before for term in ("tren", "toi thieu", "lon hon", "hon")):
            min_price = value if min_price is None else max(min_price, value)

    return min_price, max_price


def product_price(product: Dict[str, Any]) -> Optional[int]:
    price = product.get("price")
    if isinstance(price, int):
        return price
    if isinstance(price, str):
        digits = re.sub(r"\D", "", price)
        return int(digits) if digits else None
    return None


def spec_contains_terms(key: Any, value: Any, terms: tuple[str, ...]) -> bool:
    haystack = f"{normalize_text(key)} {normalize_text(value)}"
    return any(term in haystack for term in terms)


def ordered_spec_items(specs: Any, priority_terms: tuple[str, ...] = SPEC_PRIORITY_TERMS) -> List[tuple[Any, Any]]:
    if not isinstance(specs, dict):
        return []

    items = [(key, value) for key, value in specs.items() if value]
    priority_items = [
        item for item in items
        if spec_contains_terms(item[0], item[1], priority_terms)
    ]
    normal_items = [item for item in items if item not in priority_items]
    return priority_items + normal_items


def specs_to_text(specs: Any, limit: Optional[int] = 12) -> str:
    parts = []
    items = ordered_spec_items(specs)
    if limit is not None:
        items = items[:limit]
    for key, value in items:
        if value:
            parts.append(f"{key}: {value}")
    return "; ".join(parts)


def find_spec_value(specs: Any, terms: tuple[str, ...]) -> Optional[str]:
    for key, value in ordered_spec_items(specs, terms):
        if spec_contains_terms(key, value, terms):
            return str(value)
    return None


def product_matches_category(product: Dict[str, Any], categories: List[str]) -> bool:
    if not categories:
        return True
    category_text = normalize_text(product.get("category"))
    name_text = normalize_text(product.get("name"))
    for category in categories:
        aliases = CATEGORY_ALIASES.get(category, ())
        if category == category_text or category in category_text:
            return True
        if any(alias in name_text for alias in aliases):
            return True
    return False


def product_matches_family(product: Dict[str, Any], families: List[str]) -> bool:
    if not families:
        return True
    haystack = " ".join(
        normalize_text(product.get(field))
        for field in ("name", "brand", "shortDescription")
    )
    return any(family in haystack for family in families)


def product_matches_model_phrase(product: Dict[str, Any], model_phrases: List[str]) -> bool:
    if not model_phrases:
        return True
    haystack = " ".join(
        normalize_text(product.get(field))
        for field in ("name", "shortDescription")
    )
    return any(phrase in haystack for phrase in model_phrases)


def query_tokens(message: str) -> List[str]:
    tokens = re.findall(r"[a-z0-9]+", normalize_text(message))
    return [token for token in tokens if len(token) > 1 and token not in STOPWORDS]


def score_product(product: Dict[str, Any], tokens: List[str]) -> int:
    name_text = normalize_text(product.get("name"))
    brand_text = normalize_text(product.get("brand"))
    category_text = normalize_text(product.get("category"))
    short_text = normalize_text(product.get("shortDescription"))
    specs_text = normalize_text(specs_to_text(product.get("specs"), limit=None))

    score = 0
    for token in tokens:
        if token in name_text:
            score += 6
        if token in brand_text:
            score += 4
        if token in category_text:
            score += 3
        if token in short_text:
            score += 2
        if token in specs_text:
            score += 1
    return score


def select_relevant_products(
    products: List[Dict[str, Any]],
    message: str,
    limit: int = MAX_PRODUCTS_FOR_PROMPT,
) -> List[Dict[str, Any]]:
    normalized = normalize_text(message)
    categories = detect_categories(message)
    families = detect_product_families(message)
    model_phrases = detect_model_phrases(message)
    min_price, max_price = extract_price_bounds(message)
    tokens = query_tokens(message)
    wants_cheap = any(term in normalized for term in ("gia re", "re nhat", "duoi", "tiet kiem"))
    wants_premium = any(term in normalized for term in ("cao cap", "flagship", "manh nhat", "dat nhat"))

    scored_products = []
    for product in products:
        price = product_price(product)
        if min_price is not None and (price is None or price < min_price):
            continue
        if max_price is not None and (price is None or price > max_price):
            continue
        if not product_matches_category(product, categories):
            continue
        if not product_matches_family(product, families):
            continue
        if not product_matches_model_phrase(product, model_phrases):
            continue

        score = score_product(product, tokens)
        if categories:
            score += 4
        if families:
            score += 5
        if model_phrases:
            score += 8
        if min_price is not None or max_price is not None:
            score += 3
        if score > 0 or categories or min_price is not None or max_price is not None:
            scored_products.append((score, price or 0, product))

    has_specific_filter = (
        bool(categories)
        or bool(families)
        or bool(model_phrases)
        or min_price is not None
        or max_price is not None
    )
    is_generic_recommendation = not tokens or wants_cheap or wants_premium
    if not scored_products and is_product_question(message) and not has_specific_filter and is_generic_recommendation:
        scored_products = [(0, product_price(product) or 0, product) for product in products]

    if wants_cheap:
        scored_products.sort(key=lambda item: (item[1] <= 0, item[1], -item[0]))
    elif wants_premium:
        scored_products.sort(key=lambda item: (-item[1], -item[0]))
    else:
        scored_products.sort(key=lambda item: (-item[0], item[1] <= 0, item[1]))

    return [product for _, _, product in scored_products[:limit]]


def product_to_prompt_item(product: Dict[str, Any]) -> Dict[str, Any]:
    specs = product.get("specs")
    return {
        "ID": str(product.get("id", "")),
        "SKU": str(product.get("sku", "")),
        "Tên": product.get("name", "Chưa cập nhật"),
        "Danh mục": product.get("category"),
        "Thương hiệu": product.get("brand"),
        "Giá": product.get("price"),
        "Giá cũ": product.get("oldPrice"),
        "Mô tả": compact_text(product.get("shortDescription"), 180),
        "Chip xử lý": find_spec_value(specs, CPU_SPEC_TERMS),
        "Chip đồ họa": find_spec_value(specs, GPU_SPEC_TERMS),
        "Cấu hình": compact_text(specs_to_text(specs, limit=14), 900),
    }

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
SPRING_BOOT_API_URL = f"{BACKEND_API_BASE_URL}/chat/save"

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
# 4. ENDPOINT CHATBOT (GEMINI + BACKEND PRODUCT RAG)
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

        product_catalog_str = "[]"
        if is_product_question(user_msg):
            backend_products = load_products_from_backend()
            if not backend_products:
                bot_reply = "Mình chưa lấy được dữ liệu sản phẩm từ backend SOPE, nên chưa thể tư vấn sản phẩm lúc này."
                background_tasks.add_task(
                    save_chat_to_springboot,
                    request.user_id,
                    user_msg,
                    bot_reply
                )
                return {"status": "success", "reply": bot_reply}

            relevant_products = select_relevant_products(backend_products, user_msg)
            if not relevant_products:
                bot_reply = "Mình chưa tìm thấy sản phẩm phù hợp trong dữ liệu hiện có của SOPE. Bạn thử nói rõ tên, hãng, danh mục hoặc khoảng giá nhé."
                background_tasks.add_task(
                    save_chat_to_springboot,
                    request.user_id,
                    user_msg,
                    bot_reply
                )
                return {"status": "success", "reply": bot_reply}

            product_catalog_str = json.dumps(
                [product_to_prompt_item(product) for product in relevant_products],
                ensure_ascii=False
            )

        system_instruction = f"""Bạn là chatbot CSKH của hệ thống SOPE, chuyên tư vấn các dòng thiết bị công nghệ. 
            FAQ liên quan: {context or "Không có"} 
            Sản phẩm lấy từ backend SOPE /api/products, đã lọc theo câu hỏi hiện tại: {product_catalog_str}

            Nhiệm vụ của bạn:
            - Luôn xưng hô thân thiện, nhiệt tình.
            - CHỈ được tư vấn, gợi ý, so sánh hoặc nhắc tên sản phẩm có trong danh sách JSON ở trên.
            - Không dùng kiến thức bên ngoài, web, hoặc folder data của chatbot để tự thêm sản phẩm.
            - Nếu danh sách JSON rỗng hoặc không đủ thông tin, hãy nói rõ chưa có dữ liệu phù hợp trong hệ thống SOPE.
            - Nếu khách hỏi tên rút gọn, chỉ được hiểu gần đúng trong phạm vi các sản phẩm có trong danh sách JSON.
            - Nếu khách hỏi một mẫu máy cụ thể, hãy trả lời trực tiếp theo sản phẩm khớp nhất trong JSON; không nhắc các sản phẩm khác trừ khi khách hỏi so sánh hoặc gợi ý thêm.
            - Khi gợi ý sản phẩm, bắt buộc đính kèm link Markdown bằng đúng ID trong JSON: [Tên sản phẩm](/products/ID).
            - Nếu khách hỏi "chip xử lý", "CPU" hoặc "dùng chip gì", hãy trả lời bằng field "Chip xử lý" trước; không lấy "Chip đồ họa" thay cho CPU.
            - Khi so sánh, chỉ dùng mô tả/cấu hình/giá trong JSON; thiếu thông tin nào thì nói rõ thiếu, không đoán.
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
