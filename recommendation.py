"""
recommendation.py – SOPE Chatbot Recommendation Module
Cập nhật: 2026-07-14
Tasks:
  E01 – Không kết nối MySQL trực tiếp; lấy dữ liệu qua REST API nội bộ
         với service key và timeout.
  E02 – Hàm build_product_description() ghép tên, hãng, loại, thông số,
         mô tả và khoảng giá thành chuỗi text dùng cho so sánh sản phẩm.
  E03 – Chuẩn hóa thông số trước khi tính vector.
  E04 – Lọc sản phẩm gợi ý hợp lý: cùng loại, đang bán, còn hàng,
         không gợi ý chính sản phẩm đang xem, giới hạn số lượng.
  E05 – Cache ma trận TF-IDF in-memory; chỉ tính lại khi danh mục thay đổi.
  E06 – Cold start: gợi ý sản phẩm phổ biến / đánh giá cao khi chưa có lịch sử.
"""

import os
import time
import unicodedata
import re
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv
from normalize_specs import normalize_product_specs  # E03

load_dotenv()

# ============================================================
# CẤU HÌNH API NỘI BỘ  (E01)
# ============================================================
_BACKEND_BASE = os.getenv("SOPE_BACKEND_API_URL", "http://localhost:8080/api").rstrip("/")
_SERVICE_KEY = os.getenv("SOPE_SERVICE_KEY", "")          # khóa dịch vụ nội bộ
_API_TIMEOUT = float(os.getenv("SOPE_API_TIMEOUT", "10"))  # giây

def _service_headers() -> Dict[str, str]:
    """Tạo header với service key nếu được cấu hình."""
    headers: Dict[str, str] = {"Accept": "application/json"}
    if _SERVICE_KEY:
        headers["X-Service-Key"] = _SERVICE_KEY
    return headers


# ============================================================
# LẤY DỮ LIỆU TỪ BACKEND API  (E01)
# ============================================================

def fetch_all_products() -> List[Dict[str, Any]]:
    """
    Lấy toàn bộ sản phẩm từ backend qua REST API (phân trang).
    Trả về list rỗng nếu backend không phản hồi hoặc timeout.
    Không kết nối MySQL trực tiếp.
    """
    url = f"{_BACKEND_BASE}/products"
    all_products: List[Dict[str, Any]] = []
    page = 0
    while True:
        try:
            resp = requests.get(
                url,
                params={"page": page, "size": 100, "sortBy": "id", "sortDir": "asc"},
                headers=_service_headers(),
                timeout=_API_TIMEOUT,
            )
        except requests.exceptions.Timeout:
            print(f"[recommendation] Timeout khi lấy sản phẩm trang {page}.")
            break
        except requests.exceptions.RequestException as exc:
            print(f"[recommendation] Lỗi kết nối backend khi lấy sản phẩm: {exc}")
            break

        if resp.status_code != 200:
            print(f"[recommendation] Backend trả lỗi {resp.status_code} khi lấy sản phẩm.")
            break

        payload = resp.json()
        if isinstance(payload, dict):
            items = payload.get("content", [])
        elif isinstance(payload, list):
            items = payload
        else:
            items = []

        if not isinstance(items, list):
            break
        all_products.extend(items)

        if not isinstance(payload, dict) or payload.get("last", True):
            break
        total_pages = int(payload.get("totalPages", page + 1))
        page += 1
        if page >= total_pages:
            break

    return all_products


def fetch_user_interactions() -> pd.DataFrame:
    """
    Lấy dữ liệu tương tác người dùng – sản phẩm từ backend API.
    Endpoint mong đợi: GET /api/reviews
    Trả về DataFrame với cột [user_id, product_id, rating].
    Trả DataFrame rỗng nếu backend không có hoặc lỗi.
    """
    url = f"{_BACKEND_BASE}/reviews"
    all_rows: List[Dict[str, Any]] = []
    page = 0
    while True:
        try:
            resp = requests.get(
                url,
                params={"page": page, "size": 200, "sortBy": "id", "sortDir": "asc"},
                headers=_service_headers(),
                timeout=_API_TIMEOUT,
            )
        except requests.exceptions.Timeout:
            print(f"[recommendation] Timeout khi lấy reviews trang {page}.")
            break
        except requests.exceptions.RequestException as exc:
            print(f"[recommendation] Lỗi kết nối backend khi lấy reviews: {exc}")
            break

        if resp.status_code == 404:
            print("[recommendation] Endpoint /api/reviews chưa có; CF sẽ trả rỗng.")
            break
        if resp.status_code != 200:
            print(f"[recommendation] Backend trả lỗi {resp.status_code} khi lấy reviews.")
            break

        payload = resp.json()
        if isinstance(payload, dict):
            items = payload.get("content", [])
        elif isinstance(payload, list):
            items = payload
        else:
            items = []

        if not isinstance(items, list):
            break

        for item in items:
            # Hỗ trợ cả hai cấu trúc JSON backend có thể trả
            user_id = (
                item.get("reviewerName")
                or item.get("reviewer_name")
                or item.get("userId")
                or item.get("user_id")
            )
            product_id = item.get("productId") or item.get("product_id")
            rating = item.get("ratingStars") or item.get("rating_stars") or item.get("rating")
            if user_id is not None and product_id is not None and rating is not None:
                all_rows.append(
                    {"user_id": user_id, "product_id": int(product_id), "rating": float(rating)}
                )

        if not isinstance(payload, dict) or payload.get("last", True):
            break
        total_pages = int(payload.get("totalPages", page + 1))
        page += 1
        if page >= total_pages:
            break

    if not all_rows:
        return pd.DataFrame(columns=["user_id", "product_id", "rating"])
    return pd.DataFrame(all_rows)


# ============================================================
# E02 – TẠO MÔ TẢ SẢN PHẨM TỔNG HỢP CHO SO SÁNH
# ============================================================

def _normalize_spec_text(value: Any) -> str:
    """Chuẩn hóa unicode, bỏ dấu tiếng Việt, lowercase – dùng nội bộ."""
    text = str(value or "").lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip()


def _specs_to_flat_text(specs: Any) -> str:
    """Chuyển dict specs thành chuỗi 'key: value' cách nhau bởi dấu chấm phẩy."""
    if not isinstance(specs, dict):
        return ""
    parts = []
    for k, v in specs.items():
        if v:
            parts.append(f"{k} {v}")
    return " ".join(parts)


def _format_price(price: Any) -> str:
    """
    Chuyển giá số thành chuỗi triệu/nghìn để dùng trong TF-IDF.
    Dùng phép chia nguyên (//) để tránh float làm tròn sai.
    Ví dụ: 22990000 → '22 trieu', 15500000 → '15 trieu',
           990000 → '990 nghin', None → ''
    """
    if price is None:
        return ""
    try:
        p = int(str(price).replace(",", "").replace(".", "").strip())
    except (ValueError, TypeError):
        return str(price)
    if p >= 1_000_000:
        trieu = p // 1_000_000   # luôn floor xuống
        du    = p % 1_000_000
        if du == 0:
            return f"{trieu} trieu"
        elif du == 500_000:
            return f"{trieu}.5 trieu"  # chỉ khi đúng 15.5M, 20.5M...
        else:
            return f"{trieu} trieu"    # 22.99M, 23.9M... → floor
    if p >= 1_000:
        return f"{p // 1_000} nghin"
    return str(p)


def build_product_description(product: Dict[str, Any]) -> str:
    """
    [E02] Ghép tên, hãng, loại, thông số, mô tả và khoảng giá thành một
    chuỗi text thuần duy nhất, dùng làm input cho TF-IDF vectorizer
    trong hệ thống gợi ý content-based.

    Ví dụ đầu ra:
        "iPhone 15 Apple phone Apple A16 Bionic 6GB RAM 128GB 15 trieu
         12 trieu man hinh 6.1 inch OLED camera 48MP pin 3877mAh
         dien thoai cao cap Apple A16 Bionic 5nm chinh hang"
    """
    parts: List[str] = []

    # Tên sản phẩm (quan trọng nhất – thêm 2 lần để tăng trọng số)
    name = _normalize_spec_text(product.get("name", ""))
    if name:
        parts.append(name)
        parts.append(name)

    # Thương hiệu
    brand = _normalize_spec_text(product.get("brand", ""))
    if brand:
        parts.append(brand)

    # Danh mục / loại sản phẩm
    category = _normalize_spec_text(product.get("category", ""))
    if category:
        parts.append(category)

    # Thông số kỹ thuật (specs dict)
    specs_text = _normalize_spec_text(_specs_to_flat_text(product.get("specs")))
    if specs_text:
        parts.append(specs_text)

    # Mô tả ngắn
    short_desc = _normalize_spec_text(product.get("shortDescription", ""))
    if short_desc:
        parts.append(short_desc)

    # Khoảng giá (giá hiện tại và giá cũ nếu có)
    price_str = _format_price(product.get("price"))
    old_price_str = _format_price(product.get("oldPrice"))
    if price_str:
        parts.append(price_str)
    if old_price_str and old_price_str != price_str:
        parts.append(old_price_str)

    return " ".join(parts)


# ============================================================
# E04 – LỌC SẢN PHẨM GỢI Ý HỢP LÝ
# ============================================================

# Giới hạn tối đa top_n được phép trả về
_MAX_RECOMMENDATIONS = int(os.getenv("SOPE_MAX_RECOMMENDATIONS", "10"))


def filter_recommendable(
    products: List[Dict[str, Any]],
    *,
    exclude_id: Optional[int] = None,
    same_category: Optional[str] = None,
    top_n: int = 5,
) -> List[int]:
    """
    E04: Giữ lại các product_id hợp lệ để gợi ý:
      - Cùng loại (category) với sản phẩm đang xem (nếu truyền same_category).
      - Đang bán (status == 'active' / available == True / không có flag ngưng bán).
      - Còn hàng (stockQuantity > 0 hoặc không có field tồn kho → cho qua).
      - Không gợi ý chính sản phẩm đang xem (exclude_id).
      - Giới hạn số lượng tối đa _MAX_RECOMMENDATIONS.
    Trả list product_id (int) đã lọc.
    """
    safe_top_n = min(top_n, _MAX_RECOMMENDATIONS)
    result: List[int] = []

    for p in products:
        pid = p.get("id")
        if pid is None:
            continue
        pid = int(pid)

        # Loại chính sản phẩm đang xem
        if exclude_id is not None and pid == exclude_id:
            continue

        # Kiểm tra cùng loại
        if same_category:
            cat = str(p.get("category") or "").lower().strip()
            if cat != same_category.lower().strip():
                continue

        # Kiểm tra đang bán
        status = str(p.get("status") or "").lower()
        available = p.get("available")
        active = p.get("active")
        is_selling = p.get("isSelling")
        if status and status not in ("", "active", "selling", "available", "published", "1"):
            continue  # ngưng bán, ẩn, draft...
        if available is not None and not available:
            continue
        if active is not None and not active:
            continue
        if is_selling is not None and not is_selling:
            continue

        # Kiểm tra còn hàng – ưu tiên field đầu tiên khác None
        stock = None
        for stock_field in ("stockQuantity", "stock", "quantity"):
            val = p.get(stock_field)
            if val is not None:
                stock = val
                break
        if stock is not None:
            try:
                if int(stock) <= 0:
                    continue  # hết hàng
            except (ValueError, TypeError):
                pass  # không parse được → cho qua

        result.append(pid)
        if len(result) >= safe_top_n:
            break

    return result


# ============================================================
# CF – COLLABORATIVE FILTERING  (E01: thay MySQL bằng API)
# ============================================================

def build_recommendation_engine():
    """
    Xây dựng ma trận User-Item và ma trận tương đồng sản phẩm
    bằng Collaborative Filtering.
    Dữ liệu lấy qua REST API (không dùng MySQL).
    """
    df = fetch_user_interactions()
    if df.empty:
        print("[recommendation] Không có dữ liệu interaction; CF trả rỗng.")
        empty_matrix = pd.DataFrame()
        return empty_matrix, pd.DataFrame()

    print("========== Interaction Data ==========")
    print(df.head(10))
    print("Số reviewer:", df["user_id"].nunique())
    print("Số sản phẩm:", df["product_id"].nunique())
    print("======================================")

    user_item_matrix = df.pivot_table(
        index="user_id",
        columns="product_id",
        values="rating",
        aggfunc="mean",
        fill_value=0,
    )
    print("User-Item Matrix:", user_item_matrix.shape)

    item_similarity = cosine_similarity(user_item_matrix.T)
    item_similarity_df = pd.DataFrame(
        item_similarity,
        index=user_item_matrix.columns,
        columns=user_item_matrix.columns,
    )
    return user_item_matrix, item_similarity_df


def get_recommendations(user_id, top_n: int = 5) -> List[int]:
    """
    CF: Gợi ý sản phẩm cho người dùng dựa trên lịch sử rating.
    Trả list rỗng nếu chưa có dữ liệu (cold start).
    """
    user_item_matrix, item_similarity_df = build_recommendation_engine()

    if user_item_matrix.empty or user_id not in user_item_matrix.index:
        return []

    user_ratings = user_item_matrix.loc[user_id]
    similar_scores = item_similarity_df.dot(user_ratings) / np.array(
        [np.abs(item_similarity_df).sum(axis=1)]
    ).ravel()
    similar_scores = pd.Series(similar_scores, index=item_similarity_df.columns)

    already_interacted = user_ratings[user_ratings > 0].index
    recommendations = similar_scores.drop(already_interacted).sort_values(ascending=False)

    return recommendations.head(top_n).index.tolist()


def get_similar_products(product_id: int, top_n: int = 5) -> List[int]:
    """
    CF: Tìm sản phẩm tương tự theo ma trận tương đồng item-item.
    """
    _, item_similarity_df = build_recommendation_engine()

    if item_similarity_df.empty or product_id not in item_similarity_df.columns:
        print(f"[recommendation] CF: Không có product_id={product_id}")
        return []

    similar_items = item_similarity_df[product_id].sort_values(ascending=False)
    return similar_items.index.tolist()[1 : top_n + 1]


# ============================================================
# CBF – CONTENT-BASED FILTERING  (E01 + E02)
# ============================================================

# ============================================================
# E05 – CACHE MA TRẬN CBF IN-MEMORY
# Chỉ tính lại khi tập product_id thay đổi (danh mục cập nhật)
# ============================================================

_CBF_CACHE_TTL = int(os.getenv("SOPE_CBF_CACHE_TTL", "3600"))  # giây, mặc định 1h

_cbf_cache: Dict[str, Any] = {
    "matrix":      None,   # pd.DataFrame | None
    "product_ids": None,   # frozenset[int] | None – khóa để kiểm tra thay đổi
    "expires_at":  0.0,    # timestamp hết hạn
    "raw_products": None,  # list sản phẩm gốc, dùng cho E04 filter
}


def _cbf_cache_key(products: List[Dict[str, Any]]) -> frozenset:
    """Tạo khóa cache từ tập product_id hiện tại."""
    return frozenset(int(p["id"]) for p in products if p.get("id") is not None)


def build_content_based_engine() -> pd.DataFrame:
    """
    Xây dựng ma trận tương đồng content-based.
    [E01] Lấy danh sách sản phẩm từ backend API (không dùng MySQL).
    [E02] Dùng build_product_description() để tạo "hồ sơ" sản phẩm.
    [E03] Chuẩn hóa specs trước khi tính TF-IDF.
    [E05] Kiểm tra cache: chỉ tính lại nếu danh mục sản phẩm thay đổi hoặc cache hết hạn.
    """
    products = fetch_all_products()
    if not products:
        print("[recommendation] CBF: Không lấy được sản phẩm từ backend.")
        # Trả cache cũ nếu vẫn còn
        if _cbf_cache["matrix"] is not None and not _cbf_cache["matrix"].empty:
            print("[recommendation] CBF: Dùng lại cache cũ.")
            return _cbf_cache["matrix"]
        return pd.DataFrame()

    now = time.time()
    current_key = _cbf_cache_key(products)

    # E05: Trả cache nếu không có gì thay đổi và chưa hết hạn
    if (
        _cbf_cache["matrix"] is not None
        and not _cbf_cache["matrix"].empty
        and _cbf_cache["product_ids"] == current_key
        and now < _cbf_cache["expires_at"]
    ):
        print(f"[recommendation] CBF: Dùng cache (còn {int(_cbf_cache['expires_at'] - now)}s).")
        return _cbf_cache["matrix"]

    print(f"[recommendation] CBF: Tính lại ma trận ({len(products)} sản phẩm)...")

    # E03: Chuẩn hóa specs trước khi tạo profile
    normalized_products = [normalize_product_specs(p) for p in products]

    # Tạo profile mô tả cho từng sản phẩm (E02 + E03)
    records = []
    for product in normalized_products:
        pid = product.get("id")
        if pid is None:
            continue
        description = build_product_description(product)
        if description.strip():
            records.append({"product_id": int(pid), "description": description})

    if not records:
        print("[recommendation] CBF: Không có sản phẩm nào có mô tả.")
        return pd.DataFrame()

    product_profiles = pd.DataFrame(records).set_index("product_id")
    print(f"Số sản phẩm có profile: {len(product_profiles)}")

    # TF-IDF vectorize
    tfidf = TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        min_df=1,
        sublinear_tf=True,
    )
    tfidf_matrix = tfidf.fit_transform(product_profiles["description"])
    cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
    cbf_similarity_df = pd.DataFrame(
        cosine_sim,
        index=product_profiles.index,
        columns=product_profiles.index,
    )

    # E05: Lưu vào cache
    _cbf_cache["matrix"]       = cbf_similarity_df
    _cbf_cache["product_ids"]  = current_key
    _cbf_cache["expires_at"]   = now + _CBF_CACHE_TTL
    _cbf_cache["raw_products"] = products  # dùng cho filter E04
    print(f"[recommendation] CBF: Cache cập nhật (TTL={_CBF_CACHE_TTL}s).")

    return cbf_similarity_df


def invalidate_cbf_cache() -> None:
    """
    E05: Buộc tính lại ma trận lần tiếp theo
    (gọi khi backend thông báo danh mục đã thay đổi).
    """
    _cbf_cache["product_ids"] = None
    _cbf_cache["expires_at"]  = 0.0
    print("[recommendation] CBF cache đã bị xóa, sẽ tính lại lần sau.")


def get_content_based_similar_products(
    product_id: int,
    top_n: int = 5,
    products_ref: Optional[List[Dict[str, Any]]] = None,
) -> List[int]:
    """
    CBF: Gợi ý sản phẩm tương tự dựa trên mô tả tổng hợp.
    [E05] Dùng cache matrix, không tính lại nếu danh mục chưa đổi.
    [E04] Lọc kết quả: cùng loại, đang bán, còn hàng.
    """
    cbf_similarity_df = build_content_based_engine()

    if cbf_similarity_df.empty:
        print("[recommendation] CBF: Ma trận rỗng, không thể gợi ý.")
        return []

    if product_id not in cbf_similarity_df.columns:
        print(f"[recommendation] CBF: Không có product_id={product_id} trong ma trận.")
        return []

    # Lấy các ứng viên (bỏ chính sản phẩm)
    similar_items = cbf_similarity_df[product_id].sort_values(ascending=False)
    candidate_ids = similar_items.iloc[1:].index.tolist()

    # Dùng raw_products từ cache nếu có, hoặc products_ref từ caller
    ref = products_ref or _cbf_cache.get("raw_products") or []

    if ref:
        current_category: Optional[str] = None
        for p in ref:
            if p.get("id") == product_id or int(p.get("id", -1)) == product_id:
                current_category = str(p.get("category") or "").lower().strip()
                break
        id_to_product = {int(p["id"]): p for p in ref if p.get("id") is not None}
        ordered = [id_to_product[cid] for cid in candidate_ids if cid in id_to_product]
        recommendations = filter_recommendable(
            ordered,
            exclude_id=product_id,
            same_category=current_category,
            top_n=top_n,
        )
    else:
        safe_n = min(top_n, _MAX_RECOMMENDATIONS)
        recommendations = [cid for cid in candidate_ids if cid != product_id][:safe_n]

    print(f"[recommendation] CBF top-{top_n} (E04+E05): {recommendations}")
    return recommendations


# ============================================================
# E06 – COLD START: GỢI Ý SẢN PHẨM PHỔ BIẾN / ĐÁNH GIÁ CAO
# ============================================================

def get_cold_start_recommendations(
    top_n: int = 5,
    category: Optional[str] = None,
    exclude_ids: Optional[List[int]] = None,
) -> List[int]:
    """
    E06: Fallback cho người dùng mới hoặc chưa có lịch sử tương tác.
    Ưu tiên 1: sản phẩm có rating trung bình cao nhất.
    Ưu tiên 2: nếu không có review, dùng sản phẩm mới nhất (id lớn nhất).
    Có thể lọc theo danh mục và loại trừ exclude_ids.
    """
    exclude_set = set(exclude_ids or [])
    products = _cbf_cache.get("raw_products") or fetch_all_products()

    if not products:
        return []

    # Lọc: đang bán, còn hàng, đúng danh mục
    candidates = []
    for p in products:
        pid = p.get("id")
        if pid is None:
            continue
        pid = int(pid)
        if pid in exclude_set:
            continue

        # Lọc danh mục (tùy chọn)
        if category:
            cat = str(p.get("category") or "").lower().strip()
            if cat != category.lower().strip():
                continue

        # Kiểm tra đang bán
        status = str(p.get("status") or "").lower()
        if status and status not in ("", "active", "selling", "available", "published", "1"):
            continue
        if p.get("available") is not None and not p["available"]:
            continue

        # Kiểm tra còn hàng
        stock = None
        for sf in ("stockQuantity", "stock", "quantity"):
            v = p.get(sf)
            if v is not None:
                stock = v
                break
        if stock is not None:
            try:
                if int(stock) <= 0:
                    continue
            except (ValueError, TypeError):
                pass

        # Điểm phổ biến: uu tiên averageRating, rồi reviewCount, rồi id mới
        avg_rating = float(p.get("averageRating") or p.get("avgRating") or 0)
        review_cnt = int(p.get("reviewCount") or p.get("totalReviews") or 0)
        candidates.append((avg_rating, review_cnt, pid, p))

    if not candidates:
        return []

    # Sắp xếp: rating cao → review nhiều → id mới (mới ra hàng)
    candidates.sort(key=lambda x: (-x[0], -x[1], -x[2]))

    safe_n = min(top_n, _MAX_RECOMMENDATIONS)
    result = [c[2] for c in candidates[:safe_n]]
    print(f"[recommendation] E06 cold start top-{top_n}: {result}")
    return result


def get_recommendations_with_fallback(
    user_id: Any,
    top_n: int = 5,
    category: Optional[str] = None,
) -> List[int]:
    """
    E06: Gợi ý CF; nếu cold start (chưa có lịch sử) thì fallback sang cold start.
    """
    cf_result = get_recommendations(user_id, top_n)
    if cf_result:
        return cf_result
    print(f"[recommendation] CF cold start user={user_id}, dùng cold start fallback.")
    return get_cold_start_recommendations(top_n=top_n, category=category)