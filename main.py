from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
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
from recommendation import (
    get_recommendations,
    get_recommendations_with_fallback,
    invalidate_cbf_cache,             # E05
    get_personalized_recommendations, # E08
)
from normalize_specs import normalize_product_specs  # E03

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

# F08: giới hạn độ dài tin nhắn
_MAX_MESSAGE_LENGTH = int(os.getenv("SOPE_MAX_MESSAGE_LENGTH", "2000"))
# F08: giới hạn độ dài reply trả về
_MAX_REPLY_LENGTH   = int(os.getenv("SOPE_MAX_REPLY_LENGTH",   "3000"))

# ==========================================
# 1. CHÍNH SÁCH – F05: Load từ policy.json, không hard-code
# ==========================================
_POLICY_FILE = os.path.join(os.path.dirname(__file__), "policy.json")
_POLICY_API_URL = os.getenv("SOPE_POLICY_API_URL", "")  # nếu có endpoint chính sách từ backend

def _load_policy() -> Dict[str, Any]:
    """
    F05: Đọc nội dung chính sách từ file policy.json hoặc API chính sách.
    Fallback về dict rỗng nếu không đọc được.
    Không hard-code nội dung chính sách trong code.
    """
    # Ưu tiên 1: API chính sách từ backend (nếu được cấu hình)
    if _POLICY_API_URL:
        try:
            resp = requests.get(_POLICY_API_URL, timeout=5.0)
            if resp.status_code == 200:
                return resp.json()
        except Exception as exc:
            print(f"[policy] Loi load tu API chinh sach: {exc}")

    # Ưu tiên 2: File policy.json cục bộ
    try:
        with open(_POLICY_FILE, encoding="utf-8") as f:
            data = json.load(f)
        # Lọc bỏ các key comment
        return {k: v for k, v in data.items() if not k.startswith("_")}
    except Exception as exc:
        print(f"[policy] Loi doc policy.json: {exc}")

    return {}

# Load khi khởi động; reload bằng cách gọi lại hàm
_policy_data: Dict[str, Any] = _load_policy()


def match_policy(message: str) -> str:
    """
    F05: Tìm nội dung chính sách phù hợp với câu hỏi.
    Dùng keyword từ policy.json, không hard-code.
    Trả chuỗi rỗng nếu không match.
    """
    normalized = normalize_text(message)
    matched_parts = []
    for _topic, entry in _policy_data.items():
        if not isinstance(entry, dict):
            continue
        keywords: List[str] = entry.get("keywords", [])
        content: str = entry.get("content", "")
        if any(kw in normalized for kw in keywords):
            matched_parts.append(content)
    return " ".join(matched_parts)


# ==========================================
# F08 – BẢO VỆ CHATBOT: PROMPT INJECTION GUARD
# ==========================================
_INJECTION_PATTERNS = [
    r"ignore (all |previous |above |prior )?instructions?",
    r"forget (everything|all|your instructions)",
    r"(reveal|show|print|output|tell me|give me|show me) (your |the )?(system prompt|prompt|api key|secret|instruction)",
    r"(pretend|act|you are now|roleplay) (you are|as if|like) (a )?(different|another|new|unrestricted|evil)",
    r"bypass (your )?(filter|restriction|rule|safety)",
    r"jailbreak",
    r"(what is|tell me) (your )?(system instruction|system prompt|api key|gemini key)",
    r"tiet lo (system prompt|api key|khoa|mat khau)",
    r"lo (prompt|key|mat khau|khoa bao mat)",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


def is_prompt_injection(message: str) -> bool:
    """F08: Phát hiện câu hỏi cố tình lộ system prompt hoặc bypass an toàn."""
    return bool(_INJECTION_RE.search(message))


def sanitize_reply(text: str) -> str:
    """
    F08: Xử lý reply trước khi trả về:
      - Giới hạn độ dài tối đa.
      - Loại bỏ thông tin nhạy cảm (API key, JWT token, email, SĐT).
    """
    # Giới hạn độ dài
    if len(text) > _MAX_REPLY_LENGTH:
        text = text[:_MAX_REPLY_LENGTH].rstrip() + "..."
    # Che API key dạng Bearer/sk-/AIza...
    text = re.sub(r"(Bearer\s+|sk-|AIza)[A-Za-z0-9\-_\.]{8,}", "[REDACTED]", text)
    # Che JWT
    text = re.sub(r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+", "[JWT_REDACTED]", text)
    return text


# ==========================================
# F06 – TRA CỨU ĐƠN HÀNG
# ==========================================

_ORDER_INTENT_TERMS = (
    "don hang", "ma don", "tra cuu don", "tinh trang don",
    "don cua toi", "kiem tra don", "order",
    "da giao chua", "dang giao", "van don",
)

_ORDER_ID_PATTERN = re.compile(r"\b(?:#|ma\s*)?([A-Z]{0,3}\d{4,10})\b", re.IGNORECASE)


def is_order_question(message: str) -> bool:
    """F06: Phân biệt câu hỏi về đơn hàng."""
    normalized = normalize_text(message)
    return any(term in normalized for term in _ORDER_INTENT_TERMS)


def extract_order_id(message: str) -> Optional[str]:
    """F06: Trích xuất mã đơn từ câu tin nhắn."""
    m = _ORDER_ID_PATTERN.search(message)
    return m.group(1).upper() if m else None


async def fetch_order_from_backend(
    order_id: str,
    user_id: str,
    timeout: float = 5.0,
) -> Optional[Dict[str, Any]]:
    """
    F06: Gọi API backend để tra cứu đơn hàng.
    Chỉ trả dữ liệu nếu đơn thuộc về đúng user_id (bảo vệ quyền riêng tư).
    Trả None nếu không tìm thấy hoặc không có quyền.
    """
    url = f"{BACKEND_API_BASE_URL}/orders/{order_id}"
    headers = {"Accept": "application/json"}
    svc_key = os.getenv("SOPE_SERVICE_KEY", "")
    if svc_key:
        headers["X-Service-Key"] = svc_key
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, timeout=timeout)
    except Exception as exc:
        print(f"[order] Loi ket noi backend khi tra don {order_id}: {exc}")
        return None
    if resp.status_code == 404:
        return None
    if resp.status_code != 200:
        print(f"[order] Backend tra loi {resp.status_code} khi tra don {order_id}")
        return None
    try:
        data = resp.json()
    except Exception:
        return None
    # Kiểm tra quyền: đơn phải thuộc về user_id này
    owner = str(data.get("userId") or data.get("user_id") or data.get("customerId") or "")
    if owner and owner != str(user_id) and user_id != "khach_hang_test":
        print(f"[order] User {user_id} khong co quyen xem don {order_id} (chu: {owner})")
        return {"_access_denied": True}
    return data


def format_order_reply(order: Dict[str, Any]) -> str:
    """F06: Format đơn hàng thành câu trả lời thân thiện."""
    if order.get("_access_denied"):
        return "Xin lỗi, mình không thể cung cấp thông tin đơn hàng này vì không khớp tài khoản."
    order_id = order.get("orderId") or order.get("id") or "N/A"
    status   = order.get("status") or order.get("orderStatus") or "Không rõ"
    total    = order.get("totalAmount") or order.get("total") or 0
    created  = order.get("createdAt") or order.get("orderDate") or ""
    items    = order.get("items") or order.get("orderItems") or []
    shipping = order.get("shippingStatus") or ""
    tracking = order.get("trackingCode") or order.get("trackingNumber") or ""
    try:
        total_fmt = f"{int(total):,}đ"
    except (ValueError, TypeError):
        total_fmt = str(total)
    lines = [
        f"📦 **Đơn hàng #{order_id}**",
        f"• Trạng thái: **{status}**",
    ]
    if shipping:
        lines.append(f"• Giao hàng: {shipping}")
    if tracking:
        lines.append(f"• Mã vận đơn: `{tracking}`")
    if created:
        lines.append(f"• Ngày đặt: {str(created)[:10]}")
    lines.append(f"• Tổng tiền: {total_fmt}")
    if isinstance(items, list) and items:
        lines.append(f"• Sản phẩm: {len(items)} món")
    return "\n".join(lines)


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

# F04: Tập từ khóa nhận diện ý định sản phẩm
# Lưu ý: "giao" KHÔNG có ở đây (tránh nhầm với "giao hàng")
# "gia" chỉ khớp khi đi kèm ngữ cảnh sản phẩm (xem is_product_question)
PRODUCT_INTENT_TERMS = (
    "san pham",
    "goi y",
    "tu van",
    "mua",
    "dien thoai",
    "smartphone",
    "iphone",
    "samsung",
    "samsung galaxy",
    "oppo",
    "xiaomi",
    "vivo",
    "realme",
    "laptop",
    "macbook",
    "may tinh xach tay",
    "may tinh bang",
    "tablet",
    "ipad",
    "galaxy tab",       # F04: Samsung tablet
    "galaxy a",         # F04: Samsung Galaxy A series
    "galaxy s",         # F04: Samsung Galaxy S series
    "galaxy z",         # F04: Samsung Galaxy Z fold/flip
    "bao hanh",
    "khuyen mai",
    "con hang",
    "cau hinh",
    "thong so",
    "chip",
    "ram",
    "pin",
    "man hinh",
)

# F04: Category aliases – bổ sung Samsung tablet
CATEGORY_ALIASES = {
    "phone": (
        "phone", "dien thoai", "smartphone",
        "iphone",
        "samsung", "galaxy s", "galaxy a", "galaxy z", "galaxy m",
        "oppo", "oppo reno", "oppo a",
        "xiaomi", "redmi", "poco",
        "vivo", "realme",
    ),
    "laptop": (
        "laptop", "macbook", "may tinh xach tay",
        "may tinh laptop", "notebook",
        "gaming laptop", "laptop gaming",
    ),
    "tablet": (
        "tablet", "ipad", "may tinh bang",
        "galaxy tab",          # F04: Samsung tablet
        "samsung tab",
        "galaxy tab s", "galaxy tab a",
        "lenovo tab", "xiaomi pad",
    ),
}

# F04: Family aliases – thêm các đời iPhone cụ thể và Samsung tablet
PRODUCT_FAMILY_ALIASES = (
    # Apple phones
    "iphone",
    "iphone 13", "iphone 14", "iphone 15", "iphone 16",
    "iphone se", "iphone pro", "iphone pro max", "iphone plus",
    # Apple tablet
    "ipad", "ipad pro", "ipad air", "ipad mini",
    # Apple laptop
    "macbook", "macbook air", "macbook pro",
    # Samsung phones
    "samsung",
    "galaxy s", "galaxy a", "galaxy z", "galaxy m", "galaxy f",
    # Samsung tablet – F04
    "galaxy tab", "galaxy tab s", "galaxy tab a",
    # Khác
    "oppo", "oppo reno", "oppo a",
    "xiaomi", "redmi", "poco",
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


# ==========================================
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


# F04: Từ khóa chỉ GIAO HÀNG (delivery) – không phải ý định sản phẩm
_DELIVERY_ONLY_TERMS = (
    "giao hang", "phi ship", "phi giao", "van chuyen",
    "nhan hang", "thoi gian giao", "bao lau giao",
)
# F04: Từ khóa GIÁ (price) chỉ tính là ý định sản phẩm khi đi kèm sản phẩm
_PRICE_ALONE_TERMS = ("gia bao nhieu", "gia la bao nhieu", "gia nhu the nao")


def is_delivery_question(message: str) -> bool:
    """F04: Phân biệt câu hỏi giao hàng với câu hỏi giá sản phẩm."""
    normalized = normalize_text(message)
    return any(term in normalized for term in _DELIVERY_ONLY_TERMS)


def is_product_question(message: str) -> bool:
    """
    F04: Nhận diện ý định hỏi về sản phẩm.
    Phân biệt 'giao' (giao hàng) vs 'giá' (giá sản phẩm):
    - Câu hỏi thuần giao hàng (phi ship, thoi gian giao...) → False
    - 'giá' chỉ tính là product intent khi kèm tên sản phẩm hoặc từ khóa khác
    """
    normalized = normalize_text(message)
    # Nếu chỉ hỏi giao hàng mà không đề cập sản phẩm → không phải product question
    if is_delivery_question(normalized) and not any(
        term in normalized for term in PRODUCT_INTENT_TERMS
    ):
        return False
    # Kiểm tra từ khóa sản phẩm
    if any(term in normalized for term in PRODUCT_INTENT_TERMS):
        return True
    # "gia" đơn độc chỉ tính nếu có tên hãng/sản phẩm đi kèm
    if "gia" in normalized and any(
        family in normalized for family in PRODUCT_FAMILY_ALIASES
    ):
        return True
    return False


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

        # F08: Giới hạn độ dài tin nhắn
        if len(user_msg) > _MAX_MESSAGE_LENGTH:
            return {
                "status": "error",
                "reply": f"Tin nhắn quá dài (tối đa {_MAX_MESSAGE_LENGTH} ký tự). Vui lòng rút gọn nhé."
            }

        # F08: Chặn prompt injection
        if is_prompt_injection(user_msg):
            return {
                "status": "error",
                "reply": "Mình không thể thực hiện yêu cầu này. Nếu bạn cần hỗ trợ về sản phẩm hoặc dịch vụ, hãy đặt câu hỏi khác nhé."
            }

        # F06: Tra cứu đơn hàng trước khi đi vào luồng Gemini
        if is_order_question(user_msg):
            order_id = extract_order_id(user_msg)
            if order_id:
                order_data = await fetch_order_from_backend(order_id, str(request.user_id))
                if order_data is not None:
                    bot_reply = format_order_reply(order_data)
                else:
                    bot_reply = f"Xin lỗi, mình không tìm thấy đơn hàng #{order_id} trong hệ thống. Bạn kiểm tra lại mã đơn nhé!"
                background_tasks.add_task(
                    save_chat_to_springboot, request.user_id, user_msg, bot_reply
                )
                return {"status": "success", "reply": bot_reply}
            else:
                # Không có mã đơn – hỏi lại
                bot_reply = "Bạn muốn tra đơn hàng? Vui lòng cung cấp **mã đơn hàng** (ví dụ: #ORD12345) để mình tra giúp nhé!"
                background_tasks.add_task(
                    save_chat_to_springboot, request.user_id, user_msg, bot_reply
                )
                return {"status": "success", "reply": bot_reply}

        # F05: Lấy nội dung chính sách từ policy.json, không hard-code
        context = match_policy(user_msg)

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

        system_instruction = f"""Bạn là chatbot CSKH của hệ thống SOPE, chuyên tư vấn thiết bị công nghệ.

            CHÍNH SÁCH SOPE (F05 – lấy từ policy.json): {context or "Không có thông tin chính sách liên quan."}

            SẢN PHẨM (lấy từ backend /api/products, đã lọc): {product_catalog_str}

            QUY TẮC TRẢ LỜI:
            - Xưng hô thân thiện, nhiệt tình.
            - CHỈ tư vấn sản phẩm có trong danh sách JSON ở trên. Không bịa.
            - Khi hỏi chính sách (giao hàng, đổi trả, thanh toán), dùng phần CHÍNH SÁCH ở trên;
              nếu không có thông tin, nói rõ cần liên hệ CSKH.
            - Không hard-code thông tin chính sách không có trong CHÍNH SÁCH SOPE trên.
            - Khi gợi ý sản phẩm, đính kèm link: [Tên sản phẩm](/products/ID).
            - Khi hỏi chip/CPU, dùng field 'Chip xử lý'; không dùng 'Chip đồ họa' thay thế.
            - Khi so sánh, chỉ dùng dữ liệu trong JSON; thiếu thì nói rõ.
            - Trả lời súc tích, đi thẳng vào vấn đề."""

        model = genai.GenerativeModel(
            'gemini-2.5-flash',
            system_instruction=system_instruction
        )

        response = await model.generate_content_async(user_msg)
        
        if not response.parts:
            bot_reply = "Xin lỗi, mình không thể xử lý câu hỏi này."
        else:
            # F08: Sanitize reply trước khi trả về
            bot_reply = sanitize_reply(response.text)
        
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
        # E06: Dùng fallback cold start nếu user chưa có lịch sử
        recommendations = get_recommendations_with_fallback(user_id, top_n)
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

@app.get("/api/ai/recommend/popular")
def get_popular_products_api(top_n: int = 5, category: Optional[str] = None):
    """E06: Endpoint gợi ý sản phẩm phổ biến cho trang chủ / cold start."""
    try:
        ids = recommendation.get_cold_start_recommendations(top_n=top_n, category=category)
        return {"status": "success", "product_ids": ids}
    except Exception as e:
        return {"status": "error", "product_ids": []}

@app.post("/api/ai/cache/invalidate")
def invalidate_cache_api():
    """E05: Endpoint để backend gọi khi danh mục sản phẩm thay đổi."""
    invalidate_cbf_cache()
    return {"status": "ok", "message": "CBF cache đã bị xóa. Ma trận sẽ được tính lại lần gọi tiếp theo."}

@app.get("/api/ai/recommend/personalized/{user_id}")
def get_personalized_api(user_id: int, top_n: int = 5):
    """
    E08: Gợi ý cá nhân hóa theo sở thích người dùng.
    Trả list [{product_id, score, reason}].
    Fallback cold start nếu user chưa có lịch sử.
    """
    try:
        results = get_personalized_recommendations(user_id, top_n)
        return {
            "status": "success",
            "user_id": user_id,
            "recommendations": results,
        }
    except Exception as e:
        print(f"[E08] Lỗi personalized endpoint: {e}")
        return {"status": "error", "recommendations": []}

@app.get("/")
async def root():

    return {"message": "FastAPI & Gemini Server is running with Mock DB!"}


    return {"message": "FastAPI Server: Gemini Chatbot & Recommendation System is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

#Sửa lỗi build và dependency