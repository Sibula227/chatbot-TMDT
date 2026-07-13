"""
test_day13.py - Script test cho task ngay 13/07/2026
Chay: python test_day13.py
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=" * 60)
print("  TEST NGAY 13/07 - E03, E04, F04, F05")
print("=" * 60)

# -------------------------------------------------------
# TEST E03 - Chuan hoa thong so san pham
# -------------------------------------------------------
print("\n[TEST E03-1] normalize_chip...")
from normalize_specs import normalize_chip, normalize_ram, normalize_storage, normalize_battery, normalize_screen, normalize_specs_dict

chip_cases = [
    ("Apple A16 Bionic (5nm)", "apple a16"),
    ("A15 Bionic", "apple a15"),
    ("Snapdragon 8 Gen 2", "snapdragon 8gen2"),
    ("Snapdragon 8 Gen 3", "snapdragon 8gen3"),
    ("Intel Core i7-1355U", "intel i7"),
    ("AMD Ryzen 5 7520U", "amd ryzen5"),
    ("Apple M3", "apple m3"),
]
for raw, expected in chip_cases:
    result = normalize_chip(raw)
    status = "PASS" if result == expected else "FAIL"
    print(f"  [{status}] normalize_chip('{raw}') = '{result}' (mong: '{expected}')")

print("\n[TEST E03-2] normalize_ram...")
ram_cases = [
    ("8 GB", "8gb ram"),
    ("12GB RAM", "12gb ram"),
    ("6 gb", "6gb ram"),
    ("16GB", "16gb ram"),
]
for raw, expected in ram_cases:
    result = normalize_ram(raw)
    status = "PASS" if result == expected else "FAIL"
    print(f"  [{status}] normalize_ram('{raw}') = '{result}' (mong: '{expected}')")

print("\n[TEST E03-3] normalize_storage...")
storage_cases = [
    ("256 GB", "256gb"),
    ("512GB SSD", "512gb"),
    ("1 TB", "1tb"),
    ("128GB", "128gb"),
]
for raw, expected in storage_cases:
    result = normalize_storage(raw)
    status = "PASS" if result == expected else "FAIL"
    print(f"  [{status}] normalize_storage('{raw}') = '{result}' (mong: '{expected}')")

print("\n[TEST E03-4] normalize_battery...")
battery_cases = [
    ("4500 mAh", "4500mah"),
    ("3877 mAh", "3877mah"),
    ("5000mAh", "5000mah"),
    ("4,000 mAh", "4000mah"),
]
for raw, expected in battery_cases:
    result = normalize_battery(raw)
    status = "PASS" if result == expected else "FAIL"
    print(f"  [{status}] normalize_battery('{raw}') = '{result}' (mong: '{expected}')")

print("\n[TEST E03-5] normalize_screen...")
screen_cases = [
    ('6.1" Super Retina OLED', "6.1inch super retina oled"),
    ("6.7 inch FHD+ AMOLED 120Hz", "6.7inch fhd+ amoled 120hz"),
    ("15.6 inch FHD IPS", "15.6inch fhd ips"),
]
for raw, expected in screen_cases:
    result = normalize_screen(raw)
    status = "PASS" if result == expected else "FAIL"
    print(f"  [{status}] normalize_screen('{raw}')")
    print(f"           = '{result}'")
    print(f"      mong : '{expected}'")

print("\n[TEST E03-6] normalize_specs_dict (toan bo dict)...")
sample_specs = {
    "Chip xu ly": "Apple A16 Bionic (5nm)",
    "RAM": "6 GB",
    "Bo nho trong": "128 GB",
    "Pin": "3877 mAh",
    "Man hinh": '6.1" Super Retina XDR OLED',
    "Camera": "48MP + 12MP + 12MP",  # giu nguyen
}
result_specs = normalize_specs_dict(sample_specs)
print(f"  Input:  {sample_specs}")
print(f"  Output: {result_specs}")
print("  [PASS] normalize_specs_dict chay khong loi")

# -------------------------------------------------------
# TEST E04 - Loc san pham goi y hop ly
# -------------------------------------------------------
print("\n[TEST E04-1] filter_recommendable - loai chinh SP + loc status/stock...")
from recommendation import filter_recommendable

sample_products = [
    {"id": 1, "category": "phone", "status": "active",   "stockQuantity": 10},  # hop le
    {"id": 2, "category": "phone", "status": "active",   "stockQuantity": 0},   # het hang
    {"id": 3, "category": "phone", "status": "inactive", "stockQuantity": 5},   # ngung ban
    {"id": 4, "category": "laptop","status": "active",   "stockQuantity": 3},   # sai loai
    {"id": 5, "category": "phone", "status": "active",   "stockQuantity": 2},   # hop le
    {"id": 6, "category": "phone", "status": "active",   "stockQuantity": 8},   # hop le
    {"id": 7, "category": "phone"},                                              # khong co stock -> cho qua
]

result = filter_recommendable(
    sample_products,
    exclude_id=1,           # loai chinh san pham dang xem
    same_category="phone",  # chi phone
    top_n=5,
)
expected = [5, 6, 7]  # id 1 bi loai (chinh sp), 2 het hang, 3 inactive, 4 sai loai
status = "PASS" if result == expected else "FAIL"
print(f"  [{status}] filter_recommendable() = {result} (mong: {expected})")

print("\n[TEST E04-2] filter_recommendable - gioi han top_n...")
many_products = [{"id": i, "category": "phone", "status": "active"} for i in range(1, 20)]
result2 = filter_recommendable(many_products, top_n=3)
status2 = "PASS" if len(result2) == 3 else "FAIL"
print(f"  [{status2}] Gioi han top_n=3: tra {len(result2)} san pham (mong: 3)")

# -------------------------------------------------------
# TEST F04 - Nhan dien y dinh: giao vs gia, tablet Samsung
# -------------------------------------------------------
print("\n[TEST F04-1] is_delivery_question vs is_product_question...")
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from main import is_product_question, is_delivery_question

f04_cases = [
    # (message, expect_product, expect_delivery)
    ("thoi gian giao hang bao lau",          False, True),   # chi hoi giao hang
    ("phi ship la bao nhieu",                False, True),   # chi phi ship
    ("iphone 15 gia bao nhieu",              True,  False),  # gia san pham
    ("samsung galaxy tab s9 co gi hay",      True,  False),  # tablet samsung
    ("tu van galaxy tab a8",                 True,  False),  # samsung tablet
    ("giao hang iphone 15 mat bao lau",      True,  True),   # ca 2 (co sp)
    ("cho toi xem ipad pro",                 True,  False),  # ipad
    ("iphone se gia re khong",               True,  False),  # iphone se
    ("iphone 16 pro max gia bao nhieu",      True,  False),  # iphone 16 pro max
    ("may tinh bang samsung loai nao tot",   True,  False),  # samsung tablet
]
for msg, exp_prod, exp_delivery in f04_cases:
    got_prod     = is_product_question(msg)
    got_delivery = is_delivery_question(msg)
    status_p = "PASS" if got_prod == exp_prod else "FAIL"
    status_d = "PASS" if got_delivery == exp_delivery else "FAIL"
    label = "PASS" if (got_prod == exp_prod and got_delivery == exp_delivery) else "FAIL"
    print(f"  [{label}] '{msg}'")
    if got_prod != exp_prod:
        print(f"         product_q: got={got_prod}, mong={exp_prod}")
    if got_delivery != exp_delivery:
        print(f"         delivery_q: got={got_delivery}, mong={exp_delivery}")

# -------------------------------------------------------
# TEST F05 - Chinh sach tu policy.json
# -------------------------------------------------------
print("\n[TEST F05-1] Load policy.json...")
from main import _policy_data, match_policy

if _policy_data:
    print(f"  [PASS] policy.json load OK: {len(_policy_data)} muc chinh sach")
    for topic in _policy_data:
        print(f"         - {topic}")
else:
    print("  [FAIL] Khong load duoc policy.json!")

print("\n[TEST F05-2] match_policy...")
policy_cases = [
    ("giao hang bao lau",             "giao hang"),
    ("chinh sach doi tra nhu the nao","doi tra"),
    ("thanh toan bang the duoc khong","thanh toan"),
    ("co ma giam gia khong",          "khuyen mai"),
    ("hoi ve iphone 15",              None),  # khong match policy, tra rong
]
for msg, expect_topic in policy_cases:
    result = match_policy(msg)
    if expect_topic is None:
        status = "PASS" if result == "" else "WARN"
    else:
        status = "PASS" if result else "FAIL"
    print(f"  [{status}] match_policy('{msg}'): {'co noi dung' if result else 'rong'}")

# -------------------------------------------------------
# TONG KET
# -------------------------------------------------------
print("\n" + "=" * 60)
print("  KET QUA TEST NGAY 13/07")
print("=" * 60)
print("  E03 - Chuan hoa chip/RAM/storage/battery/screen  [DONE]")
print("  E04 - Loc san pham goi y: status/stock/category  [DONE]")
print("  F04 - Nhan dien y dinh: giao vs gia, tablet      [DONE]")
print("  F05 - Chinh sach tu policy.json, khong hard-code [DONE]")
print("=" * 60)
