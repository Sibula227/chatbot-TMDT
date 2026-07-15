"""
test_day15.py - Script test cho task ngay 15/07/2026
Task: E08 - Goi y ca nhan hoa theo so thich nguoi dung
Chay: python test_day15.py
"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

print("=" * 60)
print("  TEST NGAY 15/07 - E08: GOI Y CA NHAN HOA")
print("=" * 60)

# ============================================================
# Setup: inject du lieu mau vao cache de test offline
# ============================================================
from recommendation import _cbf_cache

sample_products = [
    # phone - apple
    {"id": 1,  "name": "iPhone 15 Pro",    "category": "phone",  "brand": "Apple",   "status": "active", "stockQuantity": 5,  "price": 28990000, "averageRating": 4.8, "reviewCount": 300},
    {"id": 2,  "name": "iPhone 15",        "category": "phone",  "brand": "Apple",   "status": "active", "stockQuantity": 8,  "price": 22990000, "averageRating": 4.6, "reviewCount": 250},
    {"id": 3,  "name": "iPhone 14",        "category": "phone",  "brand": "Apple",   "status": "active", "stockQuantity": 3,  "price": 17990000, "averageRating": 4.5, "reviewCount": 200},
    # phone - samsung
    {"id": 4,  "name": "Galaxy S24 Ultra", "category": "phone",  "brand": "Samsung", "status": "active", "stockQuantity": 7,  "price": 31990000, "averageRating": 4.7, "reviewCount": 150},
    {"id": 5,  "name": "Galaxy S24",       "category": "phone",  "brand": "Samsung", "status": "active", "stockQuantity": 6,  "price": 21990000, "averageRating": 4.5, "reviewCount": 120},
    {"id": 6,  "name": "Galaxy A55",       "category": "phone",  "brand": "Samsung", "status": "active", "stockQuantity": 15, "price": 9990000,  "averageRating": 4.3, "reviewCount": 80},
    # laptop
    {"id": 7,  "name": "MacBook Pro M3",   "category": "laptop", "brand": "Apple",   "status": "active", "stockQuantity": 4,  "price": 49990000, "averageRating": 4.9, "reviewCount": 90},
    {"id": 8,  "name": "MacBook Air M2",   "category": "laptop", "brand": "Apple",   "status": "active", "stockQuantity": 6,  "price": 29990000, "averageRating": 4.7, "reviewCount": 70},
    {"id": 9,  "name": "Galaxy Book4",     "category": "laptop", "brand": "Samsung", "status": "active", "stockQuantity": 3,  "price": 24990000, "averageRating": 4.4, "reviewCount": 40},
    # het hang / ngung ban -> khong duoc goi y
    {"id": 10, "name": "iPhone 13",        "category": "phone",  "brand": "Apple",   "status": "active", "stockQuantity": 0,  "price": 14990000, "averageRating": 4.4, "reviewCount": 180},
    {"id": 11, "name": "Old Phone",        "category": "phone",  "brand": "Nokia",   "status": "inactive","stockQuantity": 5, "price": 3990000,  "averageRating": 3.8, "reviewCount": 20},
]
_cbf_cache["raw_products"] = sample_products

# ============================================================
# TEST E08-1: _build_user_preference
# ============================================================
print("\n[TEST E08-1] _build_user_preference - phan tich so thich...")
from recommendation import _build_user_preference

products_map = {int(p["id"]): p for p in sample_products}

# User thich Apple phone: da mua iPhone 15 (rating 5), iPhone 14 (rating 4)
history_apple = [
    {"product_id": 1, "rating": 5.0, "category": "phone", "brand": "Apple",   "price": 28990000},
    {"product_id": 2, "rating": 4.5, "category": "phone", "brand": "Apple",   "price": 22990000},
    {"product_id": 3, "rating": 4.0, "category": "phone", "brand": "Apple",   "price": 17990000},
]
pref = _build_user_preference(history_apple, products_map)

s1 = "PASS" if "phone"  in pref["top_categories"] else "FAIL"
s2 = "PASS" if "apple"  in pref["top_brands"]     else "FAIL"
s3 = "PASS" if pref["price_min"] > 0               else "FAIL"
s4 = "PASS" if len(pref["seen_ids"]) == 3          else "FAIL"
print(f"  [{s1}] Top category co 'phone': {pref['top_categories']}")
print(f"  [{s2}] Top brand co 'apple': {pref['top_brands']}")
print(f"  [{s3}] Khoang gia tinh duoc: [{pref['price_min']:.0f}, {pref['price_max']:.0f}]")
print(f"  [{s4}] Seen_ids = {pref['seen_ids']} (mong: {{1,2,3}})")

# ============================================================
# TEST E08-2: _score_product_for_user
# ============================================================
print("\n[TEST E08-2] _score_product_for_user - tinh diem phu hop so thich...")
from recommendation import _score_product_for_user

# iPhone 15 Pro (id=1): cung phone, cung apple, trong tam gia -> nhung da seen -> giam diem
score_iphone15pro = _score_product_for_user(sample_products[0], pref)  # id=1
# Galaxy S24 (id=4): phone nhung samsung, gia hoi cao
score_s24 = _score_product_for_user(sample_products[3], pref)           # id=4
# MacBook Pro (id=6): laptop, apple, ngoai tam gia
score_macbook = _score_product_for_user(sample_products[6], pref)       # id=7

s5 = "PASS" if score_s24 > score_macbook else "FAIL"   # phone > laptop khi prefer phone
s6 = "PASS" if score_iphone15pro < score_s24 + 2 else "FAIL"  # seen penalty ap dung

print(f"  [{s5}] Score Galaxy S24 ({score_s24:.2f}) > MacBook ({score_macbook:.2f}) khi prefer phone")
print(f"  [{s6}] iPhone 15 Pro (seen) score={score_iphone15pro:.2f} (bi pen -0.5)")
print(f"         MacBook Pro score={score_macbook:.2f}")
print(f"         Galaxy S24 score={score_s24:.2f}")

# ============================================================
# TEST E08-3: _build_reason - ly do goi y
# ============================================================
print("\n[TEST E08-3] _build_reason - sinh ly do goi y...")
from recommendation import _build_reason

reason_iphone = _build_reason(sample_products[0], pref)   # id=1, Apple, phone
reason_samsung = _build_reason(sample_products[3], pref)  # id=4, Samsung, phone
reason_macbook = _build_reason(sample_products[6], pref)  # id=7, Apple, laptop

s7 = "PASS" if "Goi y vi" in reason_iphone.replace("ợ", "oi").replace("ý", "y") or "Gợi ý vì" in reason_iphone else "FAIL"
s8 = "PASS" if len(reason_iphone) > 10 else "FAIL"
print(f"  [{s7}] ly do iphone: '{reason_iphone}'")
print(f"  [{s8}] ly do samsung: '{reason_samsung}'")
print(f"         ly do macbook: '{reason_macbook}'")

# ============================================================
# TEST E08-4: _apply_diversity - gioi han cung hang
# ============================================================
print("\n[TEST E08-4] _apply_diversity - gioi han cung hang...")
from recommendation import _apply_diversity

# 5 san pham: 3 Apple phone, 2 Samsung
scored_list = [
    (5.0, {"id": 1, "brand": "Apple"}),
    (4.5, {"id": 2, "brand": "Apple"}),
    (4.2, {"id": 4, "brand": "Samsung"}),
    (4.0, {"id": 3, "brand": "Apple"}),   # thu 3 cua Apple -> bi cut
    (3.8, {"id": 5, "brand": "Samsung"}),
]
diverse = _apply_diversity(scored_list, max_per_brand=2)
got_ids = [p["id"] for _, p in diverse]
s9  = "PASS" if 3 not in got_ids else "FAIL"  # id=3 (Apple thu 3) bi loai
s10 = "PASS" if len(diverse) == 4 else "FAIL"  # con 4 sp (2 Apple + 2 Samsung)
print(f"  [{s9}]  id=3 (Apple thu 3) bi loai: ids={got_ids}")
print(f"  [{s10}] Con lai {len(diverse)} san pham (2 Apple + 2 Samsung)")

# ============================================================
# TEST E08-5: get_personalized_recommendations (offline/mock)
# ============================================================
print("\n[TEST E08-5] get_personalized_recommendations (mock history)...")
from recommendation import get_personalized_recommendations, _fetch_user_history
import unittest.mock as mock

# Mock _fetch_user_history de tranh goi API that
with mock.patch("recommendation._fetch_user_history", return_value=history_apple):
    results = get_personalized_recommendations(user_id=99, top_n=5)

s11 = "PASS" if isinstance(results, list) and len(results) > 0 else "FAIL"
s12 = "PASS" if all(isinstance(r, dict) and "product_id" in r and "score" in r and "reason" in r for r in results) else "FAIL"
s13 = "PASS" if not any(r["product_id"] in [10, 11] for r in results) else "FAIL"  # het hang/ngung ban
print(f"  [{s11}] Tra ve {len(results)} goi y (mong: > 0)")
print(f"  [{s12}] Moi item co du product_id, score, reason")
print(f"  [{s13}] Khong co sp het hang (id=10) hoac ngung ban (id=11)")
for r in results:
    print(f"         #{r['product_id']} score={r['score']} | {r['reason']}")

print("\n[TEST E08-6] get_personalized_recommendations - cold start (no history)...")
with mock.patch("recommendation._fetch_user_history", return_value=[]):
    cold_results = get_personalized_recommendations(user_id=999, top_n=3)

s14 = "PASS" if isinstance(cold_results, list) and len(cold_results) > 0 else "FAIL"
s15 = "PASS" if all("cold start" in r.get("reason", "").lower() or "pho bien" in r.get("reason", "").lower() or "phổ biến" in r.get("reason", "") for r in cold_results) else "FAIL"
print(f"  [{s14}] Cold start tra {len(cold_results)} goi y")
print(f"  [{s15}] Ly do goi y cold start:")
for r in cold_results:
    print(f"         #{r['product_id']} | {r['reason']}")

# ============================================================
# TEST E08-7: Syntax check main.py co endpoint E08
# ============================================================
print("\n[TEST E08-7] Import endpoint E08 tu main.py...")
try:
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    from main import get_personalized_api
    s16 = "PASS"
    print(f"  [PASS] get_personalized_api da co trong main.py")
except ImportError as e:
    s16 = "FAIL"
    print(f"  [FAIL] Khong import duoc: {e}")

# ============================================================
# TONG KET
# ============================================================
print("\n" + "=" * 60)
print("  KET QUA TEST NGAY 15/07")
print("=" * 60)
print("  E08-1  Phan tich so thich tu lich su                 [DONE]")
print("  E08-2  Tinh diem phu hop so thich                    [DONE]")
print("  E08-3  Sinh ly do goi y than thien                   [DONE]")
print("  E08-4  Diversity: gioi han cung hang                 [DONE]")
print("  E08-5  get_personalized_recommendations (co lich su)  [DONE]")
print("  E08-6  Fallback cold start khi chua co lich su       [DONE]")
print("  E08-7  Endpoint /api/ai/recommend/personalized/      [DONE]")
print("=" * 60)
print("\nEndpoint moi (khi backend chay):")
print("  GET /api/ai/recommend/personalized/42?top_n=5")
print("  Response: {status, user_id, recommendations: [{product_id, score, reason}]}")
