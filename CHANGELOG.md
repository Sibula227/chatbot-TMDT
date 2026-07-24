# CHANGELOG – chatbot-TMDT (SOPE)

Tất cả thay đổi đáng chú ý của dự án được ghi tại đây.
Định dạng theo [Keep a Changelog](https://keepachangelog.com/vi/1.0.0/).

---

## [Unreleased]

### Added
- **F09** – Cấu hình rate limiting: biến `SOPE_RATE_LIMIT_MAX_REQUESTS` và `SOPE_RATE_LIMIT_WINDOW_SEC` để giới hạn request spam mỗi user.
- **E03+** – Chuẩn hóa camera (MP) và trọng lượng (g/kg) trong `normalize_specs.py` cho vector TF-IDF chính xác hơn.
- **F04+** – Mở rộng `PRODUCT_INTENT_TERMS`: thêm Asus, Lenovo, Honor, OnePlus, Nothing Phone, tai nghe, sạc, phụ kiện.
- **policy.json** – Thêm chính sách tài khoản (đăng nhập, đăng ký, quên mật khẩu, OTP).
- **README** – Bảng biến môi trường đầy đủ và hướng dẫn test nhanh trên Windows (PowerShell).

### Changed
- **F06** – `format_order_reply` hiển thị icon emoji theo trạng thái đơn (⏳ pending, 🚚 shipping, 📬 delivered, ❌ cancelled…).
- **F08** – `sanitize_reply` che thêm email và số điện thoại VN để tránh rò rỉ PII.
- **env** – `.env.example` đồng bộ thêm 2 biến rate limiting F09.

### Tests
- `test_day14.py` – Bổ sung test `normalize_camera`, `normalize_weight`, và `sanitize_reply` PII (email + SĐT).

---

## [0.3.0] – 2026-07-15

### Added
- **E08** – Gợi ý cá nhân hóa từ lịch sử hành vi người dùng; ghi lý do gợi ý, tránh lặp, đa dạng hóa kết quả.
- **F08** – Bảo vệ chatbot: phát hiện prompt injection, giới hạn độ dài tin nhắn/reply, sanitize API key & JWT.

### Changed
- **E05** – Cache ma trận TF-IDF in-memory; chỉ tính lại khi danh mục sản phẩm thay đổi.
- **E06** – Cold start: gợi ý sản phẩm phổ biến/đánh giá cao khi chưa có lịch sử.

---

## [0.2.0] – 2026-07-13

### Added
- **E03** – Chuẩn hóa thông số: RAM, dung lượng, chip, pin, màn hình, tần số.
- **F05** – Load chính sách từ `policy.json`; hỗ trợ override qua API endpoint.
- **F06** – Tra cứu đơn hàng qua backend API; bảo vệ quyền riêng tư theo `user_id`.

### Changed
- **E01** – Bỏ kết nối MySQL trực tiếp; lấy dữ liệu qua REST API nội bộ với service key.

---

## [0.1.0] – 2026-07-12

### Added
- Khởi tạo dự án FastAPI chatbot SOPE.
- Tích hợp Gemini AI để sinh phản hồi tự nhiên.
- Endpoint `/api/chat` nhận `user_id` + `message`.
- Endpoint `/health` cho Docker healthcheck.
- `recommendation.py` – gợi ý sản phẩm CBF (Content-Based Filtering) với TF-IDF + cosine similarity.
- Dockerfile với Python 3.12, non-root user, healthcheck.
- `.env.example` và `.gitignore` chuẩn.
