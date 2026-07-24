"""
normalize_specs.py – SOPE Chatbot
Cập nhật: 2026-07-13 | Task E03
Chuẩn hóa thông số kỹ thuật sản phẩm: RAM, dung lượng, chip, pin, màn hình
và đơn vị để thuật toán TF-IDF/CF hiểu đồng nhất.
"""

import re
import unicodedata
from typing import Any, Dict, Optional

# ============================================================
# BẢNG ALIAS – ánh xạ từ gốc → dạng chuẩn
# ============================================================

# Chip / CPU
_CHIP_ALIASES: Dict[str, str] = {
    # Apple
    "a13 bionic": "apple a13",
    "a14 bionic": "apple a14",
    "a15 bionic": "apple a15",
    "a16 bionic": "apple a16",
    "a17 pro": "apple a17",
    "a18": "apple a18",
    "a18 pro": "apple a18",
    "m1": "apple m1",
    "m2": "apple m2",
    "m3": "apple m3",
    "m4": "apple m4",
    # Qualcomm
    "snapdragon 8 gen 1": "snapdragon 8gen1",
    "snapdragon 8 gen 2": "snapdragon 8gen2",
    "snapdragon 8 gen 3": "snapdragon 8gen3",
    "snapdragon 8 gen 4": "snapdragon 8gen4",
    "snapdragon 7 gen 1": "snapdragon 7gen1",
    "snapdragon 7 gen 2": "snapdragon 7gen2",
    "snapdragon 7 gen 3": "snapdragon 7gen3",
    "sd 888": "snapdragon 888",
    "sd 870": "snapdragon 870",
    # Samsung Exynos
    "exynos 2200": "exynos 2200",
    "exynos 2400": "exynos 2400",
    # MediaTek
    "dimensity 9300": "dimensity 9300",
    "dimensity 9200": "dimensity 9200",
    "dimensity 8300": "dimensity 8300",
    "helio g99": "helio g99",
    "helio g96": "helio g96",
    # Intel
    "core i3": "intel i3",
    "core i5": "intel i5",
    "core i7": "intel i7",
    "core i9": "intel i9",
    "core ultra 5": "intel ultra5",
    "core ultra 7": "intel ultra7",
    # AMD
    "ryzen 5": "amd ryzen5",
    "ryzen 7": "amd ryzen7",
    "ryzen 9": "amd ryzen9",
}

# RAM: chuẩn hóa thành "Xgb ram"
_RAM_PATTERN = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(?:gb|gb ram|gb bộ nhớ ram|g\b)",
    re.IGNORECASE,
)

# Storage: chuẩn hóa thành "Xgb" hoặc "Xtb"
_STORAGE_PATTERN = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(?:tb|terabyte)",
    re.IGNORECASE,
)
_STORAGE_GB_PATTERN = re.compile(
    r"(\d+)\s*(?:gb|gigabyte)(?!\s*ram)",
    re.IGNORECASE,
)

# Pin: chuẩn hóa thành "XmAh"
_BATTERY_PATTERN = re.compile(
    r"(\d[\d,\.]*)\s*(?:mah|mah pin|milli?ampere)",
    re.IGNORECASE,
)

# Màn hình: chuẩn hóa kích thước "X inch"
_SCREEN_SIZE_PATTERN = re.compile(
    r'(\d+(?:[.,]\d+)?)\s*(?:"|inch|in\b)',
    re.IGNORECASE,
)

# Tần số màn hình: "X Hz"
_REFRESH_RATE_PATTERN = re.compile(
    r"(\d+)\s*hz",
    re.IGNORECASE,
)

# Camera: chuẩn hóa thành "XMP"
_CAMERA_PATTERN = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(?:mp|megapixel|mega pixel)",
    re.IGNORECASE,
)

# Trọng lượng: chuẩn hóa thành "Xg" hoặc "Xkg"
_WEIGHT_G_PATTERN = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(?:gram|g\b)(?!\s*ram|\s*b)",
    re.IGNORECASE,
)
_WEIGHT_KG_PATTERN = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(?:kg|kilogram)",
    re.IGNORECASE,
)


# ============================================================
# HÀM TIỆN ÍCH
# ============================================================

def _base_normalize(text: Any) -> str:
    """Bỏ dấu tiếng Việt, lowercase, chuẩn hóa khoảng trắng."""
    s = str(text or "").lower().strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.replace("đ", "d")
    return re.sub(r"\s+", " ", s).strip()


def _normalize_number(raw: str) -> str:
    """Chuyển '8,0' hoặc '8.0' → '8'; '12,5' → '12'."""
    try:
        val = float(raw.replace(",", "."))
        return str(int(val)) if val == int(val) else str(round(val, 1))
    except ValueError:
        return raw


# ============================================================
# CÁC HÀM CHUẨN HÓA TỪNG LOẠI THÔNG SỐ  (E03)
# ============================================================

def normalize_chip(value: Any) -> str:
    """
    Chuẩn hóa tên chip/CPU về dạng thống nhất.
    Ví dụ: 'Apple A16 Bionic (5nm)' → 'apple a16'
           'Snapdragon 8 Gen 2' → 'snapdragon 8gen2'
           'Intel Core i7-1355U' → 'intel i7'
    """
    text = _base_normalize(value)
    # Bỏ thông tin trong ngoặc đơn: (5nm), (4nm)...
    text = re.sub(r"\(.*?\)", "", text).strip()
    # Áp dụng alias
    for pattern, canonical in _CHIP_ALIASES.items():
        if pattern in text:
            return canonical
    return text


def normalize_ram(value: Any) -> str:
    """
    Chuẩn hóa RAM về dạng 'Xgb ram'.
    Ví dụ: '8 GB' → '8gb ram', '12GB RAM' → '12gb ram'
    """
    text = _base_normalize(value)
    m = _RAM_PATTERN.search(text)
    if m:
        num = _normalize_number(m.group(1))
        return f"{num}gb ram"
    return text


def normalize_storage(value: Any) -> str:
    """
    Chuẩn hóa dung lượng lưu trữ.
    Ví dụ: '256 GB' → '256gb', '1 TB' → '1tb', '512GB SSD' → '512gb'
    """
    text = _base_normalize(value)
    # TB trước
    m = _STORAGE_PATTERN.search(text)
    if m:
        num = _normalize_number(m.group(1))
        return f"{num}tb"
    # GB
    m = _STORAGE_GB_PATTERN.search(text)
    if m:
        num = _normalize_number(m.group(1))
        return f"{num}gb"
    return text


def normalize_battery(value: Any) -> str:
    """
    Chuẩn hóa dung lượng pin.
    Ví dụ: '4,500 mAh' → '4500mah', '5000 mAh' → '5000mah'
    """
    text = _base_normalize(value)
    m = _BATTERY_PATTERN.search(text)
    if m:
        raw = m.group(1).replace(",", "").replace(".", "")
        return f"{raw}mah"
    return text


def normalize_screen(value: Any) -> str:
    """
    Chuẩn hóa thông số màn hình.
    Ví dụ: '6.1" Super Retina XDR OLED' → '6.1inch oled'
           '15,6 inch FHD IPS 144Hz'    → '15.6inch fhd ips 144hz'
    """
    text = _base_normalize(value)
    # Kích thước
    text = _SCREEN_SIZE_PATTERN.sub(lambda m: f"{m.group(1).replace(',', '.')}inch ", text)
    # Tần số
    text = _REFRESH_RATE_PATTERN.sub(lambda m: f"{m.group(1)}hz ", text)
    # Dọn khoảng trắng thừa
    return re.sub(r"\s+", " ", text).strip()


def normalize_camera(value: Any) -> str:
    """
    Chuẩn hóa độ phân giải camera.
    Ví dụ: '50 MP' → '50mp', '12.2 Megapixel' → '12mp'
    """
    text = _base_normalize(value)
    m = _CAMERA_PATTERN.search(text)
    if m:
        num = _normalize_number(m.group(1))
        return f"{num}mp"
    return text


def normalize_weight(value: Any) -> str:
    """
    Chuẩn hóa trọng lượng thiết bị.
    Ví dụ: '172 gram' → '172g', '1.5 kg' → '1.5kg'
    """
    text = _base_normalize(value)
    # Ưu tiên kg
    m = _WEIGHT_KG_PATTERN.search(text)
    if m:
        num = _normalize_number(m.group(1))
        return f"{num}kg"
    # Sau đó gram
    m = _WEIGHT_G_PATTERN.search(text)
    if m:
        num = _normalize_number(m.group(1))
        return f"{num}g"
    return text


# Tên key thường gặp cho từng loại thông số
_RAM_KEYS = {"ram", "bo nho ram", "bo nho trong ram", "ram memory"}
_STORAGE_KEYS = {
    "bo nho trong", "dung luong luu tru", "o cung", "ssd", "storage",
    "internal storage", "rom", "emmc", "ufs",
}
_CHIP_KEYS = {
    "chip xu ly", "cpu", "bo xu ly", "chip", "processor",
    "cong nghe cpu", "vi xu ly",
}
_BATTERY_KEYS = {"pin", "dung luong pin", "battery", "capacity"}
_SCREEN_KEYS = {
    "man hinh", "kich thuoc man hinh", "display", "screen",
    "kich co man hinh",
}
_CAMERA_KEYS = {
    "camera", "camera sau", "camera chinh", "do phan giai camera",
    "camera truoc", "selfie", "rear camera", "front camera",
}
_WEIGHT_KEYS = {
    "trong luong", "can nang", "weight", "kl", "khoi luong",
}


def _key_type(raw_key: Any) -> Optional[str]:
    """Xác định loại spec dựa trên tên key đã normalize."""
    k = _base_normalize(raw_key)
    if k in _CHIP_KEYS:
        return "chip"
    if k in _RAM_KEYS:
        return "ram"
    if k in _STORAGE_KEYS:
        return "storage"
    if k in _BATTERY_KEYS:
        return "battery"
    if k in _SCREEN_KEYS:
        return "screen"
    if k in _CAMERA_KEYS:
        return "camera"
    if k in _WEIGHT_KEYS:
        return "weight"
    return None


def normalize_specs_dict(specs: Any) -> Dict[str, str]:
    """
    [E03] Chuẩn hóa toàn bộ dict specs của một sản phẩm.
    Trả về dict mới với cùng key nhưng value đã được chuẩn hóa.
    Giữ nguyên các key không nhận ra.

    Ví dụ:
        {"RAM": "8 GB", "Chip xử lý": "Apple A16 Bionic", "Pin": "3877 mAh"}
        → {"RAM": "8gb ram", "Chip xử lý": "apple a16", "Pin": "3877mah"}
    """
    if not isinstance(specs, dict):
        return {}

    result: Dict[str, str] = {}
    for raw_key, raw_val in specs.items():
        if not raw_val:
            continue
        spec_type = _key_type(raw_key)
        if spec_type == "chip":
            result[raw_key] = normalize_chip(raw_val)
        elif spec_type == "ram":
            result[raw_key] = normalize_ram(raw_val)
        elif spec_type == "storage":
            result[raw_key] = normalize_storage(raw_val)
        elif spec_type == "battery":
            result[raw_key] = normalize_battery(raw_val)
        elif spec_type == "screen":
            result[raw_key] = normalize_screen(raw_val)
        elif spec_type == "camera":
            result[raw_key] = normalize_camera(raw_val)
        elif spec_type == "weight":
            result[raw_key] = normalize_weight(raw_val)
        else:
            # Giữ nguyên, chỉ lowercase
            result[raw_key] = _base_normalize(raw_val)
    return result


def normalize_product_specs(product: Dict[str, Any]) -> Dict[str, Any]:
    """
    Trả về bản copy của product dict với field 'specs' đã được chuẩn hóa.
    Không sửa đổi product gốc.
    """
    normalized = dict(product)
    if "specs" in product:
        normalized["specs"] = normalize_specs_dict(product["specs"])
    return normalized
