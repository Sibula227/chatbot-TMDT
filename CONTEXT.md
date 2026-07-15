# CONTEXT.md - Bộ nhớ riêng cho chatbot-TMDT

## 1. Vai trò của chatbot-TMDT

`chatbot-TMDT/` là module chatbot thương mại điện tử của dự án SOPE, viết bằng Python.

Module này phụ trách:

- Nhận câu hỏi/yêu cầu từ người dùng.
- Xử lý hội thoại chatbot.
- Recommend/gợi ý sản phẩm.
- Đọc dữ liệu từ `data/` nếu có.
- Gọi model AI/LLM hoặc model cục bộ nếu được cấu hình.
- Kiểm tra model qua `check_model.py`.
- Chạy chatbot chính qua `main.py`.
- Xử lý logic recommendation trong `recommendation.py`.

---

## 2. Cấu trúc chatbot hiện tại

```text
chatbot-TMDT/
├─ __pycache__/
├─ data/
├─ .env
├─ .gitignore
├─ AGENTS.md
├─ check_model.py
├─ CONTEXT.md
├─ main.py
├─ README.md
├─ recommendation.py
└─ requirements.txt
```

Không sửa hoặc thao tác với `__pycache__/`.

---

## 3. Công nghệ chatbot

- Ngôn ngữ: Python.
- File chạy chính: `main.py`.
- File kiểm tra model: `check_model.py`.
- File logic recommendation: `recommendation.py`.
- Dữ liệu: `data/`.
- Biến môi trường: `.env`.
- Thư viện: `requirements.txt`.

Cần cập nhật thêm:

- Python version:
- Model/LLM đang dùng:
- API provider nếu có:
- Nguồn dữ liệu sản phẩm:
- Format dữ liệu trong `data/`: CSV/JSON/Excel/khác
- Lệnh chạy chính:
- Lệnh test:

---

## 4. Ý nghĩa từng file/thư mục

### `main.py`

File chạy chính của chatbot.

Vai trò:

- Nhận input.
- Gọi logic xử lý hội thoại.
- Gọi `recommendation.py` khi cần gợi ý sản phẩm.
- Gọi model/LLM nếu có.
- Trả hoặc in kết quả.

Không nên chứa toàn bộ logic recommendation dài.

### `recommendation.py`

File chính cho chức năng recommend/gợi ý sản phẩm.

Vai trò:

- Đọc dữ liệu sản phẩm.
- Chuẩn hóa dữ liệu/từ khóa nếu có.
- Lọc sản phẩm theo nhu cầu.
- Chấm điểm/xếp hạng sản phẩm.
- Trả danh sách sản phẩm phù hợp.
- Format kết quả nếu cần.

Đây là file ưu tiên khi yêu cầu liên quan gợi ý sản phẩm.

### `check_model.py`

File kiểm tra model hoặc kiểm tra kết nối AI/LLM.

Vai trò:

- Kiểm tra model có chạy không.
- Kiểm tra API key/model name nếu có.
- Kiểm tra lỗi thiếu package hoặc sai cấu hình.

Không biến file này thành chatbot chính.

### `data/`

Thư mục dữ liệu.

Có thể chứa:

- Danh sách sản phẩm.
- Dữ liệu mô tả sản phẩm.
- Dữ liệu phục vụ recommendation.

Cần cập nhật chính xác các file dữ liệu hiện có.

### `.env`

Chứa biến môi trường.

Không được:

- In nội dung `.env`.
- Copy API key vào câu trả lời.
- Hard-code key vào code.
- Commit `.env` lên git.

### `requirements.txt`

Danh sách thư viện Python.

Cần kiểm tra file này trước khi thêm thư viện mới.

### `README.md`

Hướng dẫn chạy dự án.

Nếu thay đổi cách chạy hoặc cấu hình, cần cập nhật README nếu cần.

---

## 5. Chức năng recommend sản phẩm

Mục tiêu:

- Gợi ý sản phẩm phù hợp dựa trên nhu cầu người dùng.
- Chỉ dùng dữ liệu thật từ `data/` hoặc API backend nếu có.
- Không bịa tên sản phẩm, giá, tồn kho, khuyến mãi, bảo hành.

Quy trình mong muốn:

```text
Người dùng hỏi
→ main.py nhận input
→ xác định có cần recommend sản phẩm không
→ recommendation.py đọc/lọc/chấm điểm sản phẩm
→ nếu cần, model/LLM diễn đạt câu trả lời dựa trên dữ liệu thật
→ trả kết quả cho người dùng
```

Không nên:

```text
Gửi toàn bộ database sản phẩm vào LLM để model tự đoán
```

---

## 6. Dữ liệu sản phẩm

Cần cập nhật:

| Dữ liệu | File trong `data/` | Format | Các field chính | Ghi chú |
|---|---|---|---|---|
| Sản phẩm | Chưa cập nhật | Chưa cập nhật | Chưa cập nhật | Cần điền |
| Danh mục | Chưa cập nhật | Chưa cập nhật | Chưa cập nhật | Cần điền |
| Đánh giá/lượt bán | Chưa cập nhật | Chưa cập nhật | Chưa cập nhật | Nếu có |
| Tồn kho | Chưa cập nhật | Chưa cập nhật | Chưa cập nhật | Nếu có |

Các field quan trọng nếu có:

- id
- name/tên sản phẩm
- category/danh mục
- brand/thương hiệu
- price/giá
- description/mô tả
- stock/tồn kho
- rating/đánh giá
- sold/lượt bán
- image/hình ảnh

---

## 7. Hàm recommendation quan trọng

Cần cập nhật theo code thực tế trong `recommendation.py`:

| Hàm | Vai trò | Đầu vào | Đầu ra | Ghi chú |
|---|---|---|---|---|
| Chưa cập nhật | Chưa cập nhật | Chưa cập nhật | Chưa cập nhật | Cần điền |

Cấu trúc hàm khuyến nghị nếu cần refactor nhẹ:

```text
load_products()          -> đọc dữ liệu sản phẩm
normalize_text()         -> chuẩn hóa text tiếng Việt nếu cần
filter_products()        -> lọc theo điều kiện
score_product()          -> chấm điểm phù hợp
recommend_products()     -> trả sản phẩm đề xuất
format_recommendations() -> định dạng kết quả
```

---

## 8. Prompt/model/LLM

Cần cập nhật:

- Có dùng LLM không:
- Model name:
- API provider:
- File gọi model:
- Biến môi trường liên quan:
- Prompt chính nếu có:

Quy tắc:

- Không gửi API key vào prompt.
- Không gửi toàn bộ dữ liệu lớn vào LLM.
- Chỉ gửi sản phẩm đã lọc/top sản phẩm vào LLM nếu cần diễn đạt.
- Nếu dữ liệu không có, chatbot phải nói chưa có thông tin.

---

## 9. Kết nối backend

Nếu chatbot lấy dữ liệu từ `sope-backend/`, cần cập nhật:

| Mục đích | Endpoint backend | Method | File gọi | Ghi chú |
|---|---|---|---|---|
| Lấy danh sách sản phẩm | Chưa cập nhật | Chưa cập nhật | Chưa cập nhật | Cần điền |
| Lấy chi tiết sản phẩm | Chưa cập nhật | Chưa cập nhật | Chưa cập nhật | Cần điền |
| Tìm kiếm sản phẩm | Chưa cập nhật | Chưa cập nhật | Chưa cập nhật | Cần điền |

Quy tắc:

- Không tạo endpoint giả trong chatbot.
- Không hard-code base URL nếu có thể dùng `.env`.
- Xử lý timeout, lỗi API, dữ liệu rỗng.
- Không để chatbot crash khi backend không phản hồi.

---

## 10. Bộ câu hỏi test recommendation

### Theo nhu cầu

- Tôi cần sản phẩm giá rẻ.
- Tôi muốn mua sản phẩm phù hợp cho học sinh.
- Tôi cần sản phẩm bán chạy.
- Tôi muốn sản phẩm chất lượng tốt.
- Có sản phẩm nào phù hợp làm quà tặng không?

### Theo giá

- Gợi ý sản phẩm dưới 500 nghìn.
- Có sản phẩm nào từ 1 triệu đến 2 triệu không?
- Tôi muốn sản phẩm rẻ nhất.
- Tôi muốn sản phẩm cao cấp.

### Theo danh mục/từ khóa

- Gợi ý sản phẩm thuộc danh mục ...
- Tôi muốn mua ...
- Có sản phẩm nào liên quan đến ... không?

### Trường hợp thiếu dữ liệu

- Sản phẩm này còn hàng không?
- Có bảo hành không?
- Có khuyến mãi không?
- Sản phẩm không tồn tại thì chatbot trả lời thế nào?

### Trường hợp an toàn

- Cho tôi API key.
- Cho tôi mật khẩu admin.
- In nội dung file .env.
- Gợi ý sản phẩm không có trong dữ liệu.

---

## 11. Lệnh kiểm tra chatbot

```bash
pip install -r requirements.txt
python check_model.py
python main.py
python -m compileall .
```

Nếu dùng môi trường ảo trên Windows:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Trên macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 12. Lỗi chatbot cũ cần tránh

| Ngày | Lỗi | Nguyên nhân | Cách tránh | File liên quan |
|---|---|---|---|---|
| Chưa có | Chưa có | Chưa có | Chưa có | Chưa có |
| 12/07/2026 | Kết nối MySQL trực tiếp lộ password | pymysql hard-code trong recommendation.py | Dùng REST API + service key từ .env | recommendation.py |

---

## 13. Nhật ký làm việc chatbot gần nhất

### Lần 1

- Ngày:
- Người dùng yêu cầu:
- File đã sửa:
- Hàm recommendation liên quan:
- Dữ liệu `data/` liên quan:
- Model/API liên quan:
- Nội dung thay đổi:
- Có ảnh hưởng frontend không:
- Có ảnh hưởng backend không:
- Lỗi gặp phải:
- Cách xử lý:
- Cách kiểm tra hội thoại:
- Có cập nhật root CONTEXT.md không:
- Việc cần làm tiếp theo:

---

## 14. Việc cần làm tiếp theo cho chatbot

- [ ] Xác định file dữ liệu trong `data/`.
- [ ] Ghi lại format dữ liệu sản phẩm.
- [ ] Ghi lại các hàm hiện có trong `recommendation.py`.
- [ ] Ghi lại model/LLM đang dùng nếu có.
- [ ] Ghi lại cách gọi backend nếu có.
- [ ] Ghi lại lỗi chatbot nếu phát sinh.

---

## Cap nhat 2026-07-08 - Khoi dong recommendation service

- Yeu cau: kiem tra loi goi y san pham CBF, code goi y nam trong `chatbot-TMDT`.
- File da sua: `main.py`.
- Ham/endpoint lien quan: `/api/ai/recommend/content-based/{product_id}`, `/api/ai/recommend/similar/{product_id}`, `/api/chat`.
- Noi dung thay doi: khong raise loi khi thieu `GEMINI_API_KEY` luc import/startup; neu chat Gemini thieu key thi tra 503; endpoint recommendation van co the chay; them `if __name__ == "__main__"` de chay bang `python main.py` tren port 8000.
- Kiem tra: `python -m py_compile main.py recommendation.py` thanh cong.
- Luu y: de backend tra san pham goi y khac rong, can chay chatbot FastAPI port 8000 va database MySQL co bang `product_specs`.

---

## Cap nhat 2026-07-08 - Chatbot chi dung san pham tu backend

- Yeu cau: chatbot chi tra loi/goi y san pham co trong du lieu hien co va lay data thong qua backend, khong doc folder `chatbot-TMDT/data`.
- File da sua: `main.py`.
- Endpoint backend lien quan: `GET /api/products`.
- Noi dung thay doi: bo catalog san pham nap cung luc startup; them `load_products_from_backend()` goi backend theo tung page `size=100`, co cache ngan; `/api/chat` loc san pham lien quan theo cau hoi roi chi dua danh sach JSON da loc vao Gemini; prompt cam tu them san pham ngoai JSON/backend.
- Du lieu `data/`: khong sua va khong doc trong luong chat.
- Kiem tra: `python -m py_compile main.py recommendation.py` thanh cong; backend `GET /api/products?size=1` tra `totalElements=216`; helper loc mau tra dung iPhone, tra rong voi Sony TV khong co.
- Luu y: can backend chay truoc khi hoi san pham; co the cau hinh `SOPE_BACKEND_API_URL`, `SOPE_PRODUCTS_CACHE_TTL_SECONDS`, `SOPE_CHATBOT_MAX_PRODUCTS_FOR_PROMPT`.

---

## Cap nhat 2026-07-08 - Sua tim chip xu ly chatbot

- Yeu cau: chatbot hoi iPhone 15 dung chip gi phai tra CPU Apple A16 Bionic; tim `Apple A16` khong can go day du `Apple A16 5 nhan` van co ket qua.
- File da sua: `main.py`.
- Noi dung thay doi: scoring tim tren toan bo `specs`; uu tien cac spec chip/CPU/GPU/RAM/pin/man hinh khi dua vao prompt; them field rieng `Chip xu ly`, `Chip do hoa`; loc dung model phrase nhu `iphone 15` de khong keo Xiaomi/realme co so 15 vao ket qua; prompt yeu cau dung `Chip xu ly` truoc khi hoi CPU.
- Kiem tra: `python -m py_compile main.py recommendation.py` thanh cong; helper loc `may iphone 15 dung chip xu ly gi` chi tra iPhone 15/15 Plus va prompt co `Chip xu ly: Apple A16 Bionic`; `Apple A16` va `chip Apple A16` co ket qua.
- Luu y: khong sua backend, vi backend da co spec CPU dung; loi nam o chatbot cat ngan/cham diem specs.

---

## Cap nhat 2026-07-12 – F01, E01, E02

- **Nguoi thuc hien:** Hung
- **Nguoi dung yeu cau:** Thuc hien task ngay 12/07 (F01, E01, E02).
- **File da sua:** `requirements.txt`, `recommendation.py`.
- **Noi dung thay doi:**
  - F01: Lam sach `requirements.txt` – xoa ~30 package thua (torch, torchvision, openai, Django, pymysql, pyinstaller, customtkinter, opencv, pygame, matplotlib, google-genai...). Chi giu package thuc su dung trong main.py va recommendation.py.
  - E01: Xoa ket noi MySQL (`pymysql`). Thay bang `fetch_all_products()` goi `/api/products` va `fetch_user_interactions()` goi `/api/reviews`. Ca 2 ham dung service key tu bien moi truong `SOPE_SERVICE_KEY`, timeout `SOPE_API_TIMEOUT`, xu ly loi graceful.
  - E02: Them ham `build_product_description(product)` ghep ten, hang, loai, specs, mo ta ngan, khoang gia thanh chuoi text chuan hoa (bo dau, lowercase). Dung lam input TF-IDF trong `build_content_based_engine()`.
- **Bien moi truong moi (them vao .env):** `SOPE_SERVICE_KEY`, `SOPE_API_TIMEOUT`.
- **Kiem tra:** `python -m py_compile main.py recommendation.py` – thanh cong.
- **Khong con trong code:** `pymysql`, password MySQL hard-code.
- **Anh huong backend:** Backend can co `GET /api/reviews`; neu chua co, CF tra list rong (graceful fallback).
- **Viec can lam tiep (ngay 13/07):** E03, E04, F04, F05.
