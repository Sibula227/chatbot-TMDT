# TIMEOUT_FIX_REPORT

1. Nguyên nhân chính xác

- Một số chỗ trong code (ví dụ `load_products_from_backend` trong `main.py` và `fetch_all_products` trong `recommendation.py`) dùng `timeout=5.0` hoặc đọc `SOPE_API_TIMEOUT=10` cứng, dẫn tới `requests` read timeout=5s quá ngắn so với thời gian phản hồi thực tế (~7s) của endpoint `/api/products` trên backend.

2. Các file đã sửa

- `timeout_config.py` (mới): helper đọc biến môi trường, trả tuple và httpx.Timeout
- `main.py`: dùng `requests_timeout_tuple()` cho `requests.get`, dùng `httpx_timeout()` cho `httpx.AsyncClient` calls; thay đổi nơi có `timeout=5.0` và `timeout=float(os.getenv(...))`.
- `recommendation.py`: import `requests_timeout_tuple` và sử dụng cho mọi `requests.get(..., timeout=...)`; log timeout rõ connect/read.
- `.env.example`: thêm `SOPE_CONNECT_TIMEOUT=5` và đặt `SOPE_API_TIMEOUT=20`.
- `test_timeout.py`: tests mới kiểm tra cấu hình và rằng `requests.get` nhận tuple timeout.

3. Các dòng timeout cũ

- `main.py`: `timeout=5.0` trong `load_products_from_backend` (được thay thế).
- `main.py`: `timeout=float(os.getenv("SOPE_API_TIMEOUT", "10"))` khi post chat (đã thay bằng `httpx_timeout()`).
- `recommendation.py`: `_API_TIMEOUT = float(os.getenv("SOPE_API_TIMEOUT", "10"))` dùng trực tiếp cho `requests.get` (đã chuyển để dùng `requests_timeout_tuple()`).

4. Cấu hình timeout mới

- `SOPE_CONNECT_TIMEOUT`: default 5 (connect timeout)
- `SOPE_API_TIMEOUT`: default 20 (read timeout)
- Trong code: `requests.get(..., timeout=(SOPE_CONNECT_TIMEOUT, SOPE_API_TIMEOUT))` và `httpx.AsyncClient(..., timeout=httpx.Timeout(connect=..., read=...))`.

5. Có thêm retry hay không

- Không thêm retry tự động. Lý do: tránh phức tạp về tổng thời gian chờ và duplicate side-effects; có thể thêm sau nếu muốn (chỉ cho GET và tối đa 1 retry).

6. Cách xử lý ConnectTimeout

- Với `requests`, nếu kết nối không thành công trong `SOPE_CONNECT_TIMEOUT`, `requests.exceptions.ConnectTimeout`/`requests.exceptions.Timeout` sẽ được ném. Code hiện tại bắt `requests.exceptions.Timeout` ở các chỗ lấy dữ liệu và ghi log, không crash toàn bộ service.

7. Cách xử lý ReadTimeout

- Với `requests`, nếu read vượt quá `SOPE_API_TIMEOUT`, `requests.exceptions.ReadTimeout` được log cụ thể (từ `requests.exceptions.Timeout`) và hàm fallback trả cache cũ hoặc danh sách rỗng.
- Với `httpx`, `httpx.Timeout` cấu hình connect/read; code bắt Exception xung quanh async calls và in tên exception, không trả exception không bắt.

8. Cách xử lý HTTP error

- Giữ nguyên hành vi: nếu status != 200 thì ghi log và thực hiện fallback hiện có (trả cache hoặc danh sách rỗng).

9. Test đã thêm

- `test_timeout.py`:
  - `test_defaults`: kiểm tra giá trị mặc định 5 và 20.
  - `test_env_override_valid`: kiểm tra override env.
  - `test_env_invalid_values_fallback`: kiểm tra giá trị không hợp lệ fallback về default.
  - `test_fetch_all_products_uses_timeout_tuple`: mock `requests.get` và kiểm tra tham số `timeout` là tuple `(connect, read)`.

10. Kết quả compile

- `python -m compileall main.py recommendation.py normalize_specs.py` thành công.

11. Kết quả import

- `python -c "import main; print('IMPORT_OK')"` in ra `IMPORT_OK`.

12. Kết quả test

- Chạy `python -m unittest test_timeout.py` : tất cả tests pass.

13. Kết quả đo backend production

- Tài liệu ghi chú: production `/api/products` trả ~7s, nhỏ hơn `SOPE_API_TIMEOUT=20` mới.

14. Git diff tóm tắt

- Thêm: `timeout_config.py`, `test_timeout.py`, `TIMEOUT_FIX_REPORT.md`
- Sửa: `main.py`, `recommendation.py`, `.env.example`

15. Các biến cần đặt trên Render

- `SOPE_CONNECT_TIMEOUT=5`
- `SOPE_API_TIMEOUT=20`
- `SOPE_BACKEND_API_URL=https://sope-backend-wezh.onrender.com/api`

16. Lệnh commit đề xuất

```bash
git add timeout_config.py recommendation.py main.py .env.example test_timeout.py TIMEOUT_FIX_REPORT.md
git commit -m "Fix timeouts: use SOPE_CONNECT_TIMEOUT and SOPE_API_TIMEOUT; add tests and config"
```

17. Lệnh kiểm tra sau deploy

```bash
# kiểm tra service chạy
curl -sS https://chatbot-tmdt.onrender.com/health

# kiểm tra product API từ chatbot (nội bộ)
curl -sS "https://chatbot-tmdt.onrender.com/api/ai/recommend/popular" | jq .
```

18. Các vấn đề chưa giải quyết

- Không thêm retry: nếu muốn đề xuất thêm retry 1 lần cho GET /products, tôi có thể triển khai với backoff 0.5s.
- Không thay đổi logging framework (hiện dùng print); có thể migrate sang `logging` để cấu hình level/handler.
