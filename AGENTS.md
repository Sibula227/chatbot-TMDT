# AGENTS.md - Quy tắc riêng cho chatbot-TMDT

## 1. Vai trò của thư mục này

Bạn đang làm việc trong module `chatbot-TMDT/` của dự án SOPE.

Module này là chatbot thương mại điện tử viết bằng Python, có chức năng chính là:

- Nhận câu hỏi/yêu cầu từ người dùng.
- Xử lý hội thoại chatbot.
- Gợi ý/recommend sản phẩm phù hợp.
- Đọc dữ liệu sản phẩm từ thư mục `data/` nếu có.
- Gọi mô hình AI/LLM hoặc model cục bộ nếu dự án đang cấu hình.
- Kiểm tra model qua `check_model.py`.
- Chạy chatbot chính qua `main.py`.
- Xử lý logic gợi ý sản phẩm trong `recommendation.py`.

Cấu trúc hiện tại:

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

---

## 2. Quy tắc bắt buộc trước khi code

Trước khi sửa code, phải:

1. Đọc `../CONTEXT.md` nếu tồn tại.
2. Đọc `CONTEXT.md` trong thư mục `chatbot-TMDT/` nếu tồn tại.
3. Kiểm tra `README.md` để hiểu cách chạy nếu có.
4. Kiểm tra `main.py` để hiểu luồng chạy chính.
5. Kiểm tra `recommendation.py` nếu yêu cầu liên quan gợi ý sản phẩm.
6. Kiểm tra `check_model.py` nếu yêu cầu liên quan kiểm tra model.
7. Kiểm tra thư mục `data/` nếu yêu cầu liên quan dữ liệu sản phẩm.
8. Kiểm tra `requirements.txt` trước khi thêm thư viện mới.
9. Không sửa `.env` nếu không được yêu cầu rõ.
10. Không sửa hoặc dùng file trong `__pycache__/`.

Không viết lại toàn bộ chatbot nếu chỉ cần sửa một hàm hoặc một lỗi nhỏ.

---

## 3. Vai trò từng file/thư mục

### `main.py`

File chạy chính của chatbot.

Khi sửa `main.py`:

- Không nhồi quá nhiều logic recommendation vào `main.py`.
- Nếu logic liên quan gợi ý sản phẩm, ưu tiên đặt trong `recommendation.py`.
- `main.py` chỉ nên điều phối luồng: nhận input, gọi xử lý, gọi recommendation/model, in hoặc trả kết quả.
- Không hard-code dữ liệu sản phẩm trực tiếp trong `main.py`.
- Nếu thay đổi cách chạy chatbot, phải cập nhật `README.md` hoặc ghi rõ trong `CONTEXT.md`.

### `recommendation.py`

File xử lý gợi ý/recommend sản phẩm.

Khi sửa `recommendation.py`:

- Đây là nơi ưu tiên đặt logic đề xuất sản phẩm.
- Không tạo file recommendation mới nếu file này đã đủ dùng.
- Không tạo hàm trùng chức năng với hàm đã có.
- Không bịa sản phẩm, giá, tồn kho, mô tả.
- Chỉ gợi ý dựa trên dữ liệu thật từ `data/` hoặc nguồn backend/API nếu có.
- Nếu dữ liệu thiếu, phải trả thông báo rõ ràng thay vì tự đoán.
- Nếu thêm thuật toán mới, phải giữ hàm cũ nếu đang được `main.py` gọi.
- Nếu đổi tên hàm trong `recommendation.py`, phải kiểm tra tất cả nơi gọi hàm đó.

### `check_model.py`

File dùng để kiểm tra model hoặc kiểm tra khả năng gọi AI/LLM.

Khi sửa `check_model.py`:

- Không đưa API key trực tiếp vào code.
- Lấy thông tin nhạy cảm từ `.env`.
- Không log API key, token, secret.
- Nếu model lỗi, cần báo lỗi rõ: thiếu key, sai model, lỗi mạng, lỗi package, hoặc lỗi dữ liệu.
- Không biến `check_model.py` thành file chạy chatbot chính.

### `data/`

Thư mục chứa dữ liệu sản phẩm hoặc dữ liệu phục vụ recommendation.

Khi dùng `data/`:

- Không tự ý xóa dữ liệu.
- Không tự ý đổi cấu trúc dữ liệu nếu chưa kiểm tra code đang đọc dữ liệu đó.
- Nếu dữ liệu là CSV/JSON/Excel, phải kiểm tra tên cột/key trước khi xử lý.
- Không load toàn bộ dữ liệu lớn vào prompt LLM nếu chỉ cần một phần nhỏ.
- Nếu thêm dữ liệu mẫu, phải ghi rõ là dữ liệu mẫu.
- Nếu sửa cấu trúc dữ liệu, phải cập nhật logic đọc dữ liệu trong `recommendation.py`.

### `.env`

File chứa biến môi trường, API key, secret, cấu hình model.

Không được:

- In nội dung `.env` ra terminal.
- Copy API key vào câu trả lời.
- Đưa `.env` vào git.
- Hard-code key từ `.env` vào code.
- Sửa `.env` nếu chưa được yêu cầu.

### `requirements.txt`

File quản lý thư viện Python.

Khi cần thêm thư viện:

- Kiểm tra `requirements.txt` trước.
- Không thêm thư viện mới nếu thư viện hiện có đã xử lý được.
- Nếu thêm thư viện, phải ghi rõ lý do.
- Sau khi thêm thư viện, hướng dẫn chạy:

```bash
pip install -r requirements.txt
```

### `README.md`

File hướng dẫn dự án.

Nếu thay đổi cách chạy, cấu hình, dữ liệu hoặc API, cần cập nhật README nếu người dùng yêu cầu hoặc ghi lại trong `CONTEXT.md`.

---

## 4. Quy tắc riêng cho chức năng recommend sản phẩm

Chức năng recommend sản phẩm phải ưu tiên tính đúng dữ liệu, không bịa.

Khi người dùng hỏi gợi ý sản phẩm, cần xử lý theo hướng:

1. Hiểu nhu cầu người dùng.
2. Xác định tiêu chí nếu có:
   - Tên sản phẩm.
   - Danh mục.
   - Khoảng giá.
   - Thương hiệu.
   - Nhu cầu sử dụng.
   - Mô tả.
   - Tồn kho.
   - Đánh giá/lượt bán nếu dữ liệu có.
3. Lọc dữ liệu sản phẩm thật.
4. Xếp hạng sản phẩm phù hợp.
5. Trả kết quả ngắn gọn, dễ hiểu.
6. Nếu thiếu tiêu chí, hỏi lại người dùng.
7. Nếu không có sản phẩm phù hợp, nói rõ không tìm thấy.

Không được:

- Bịa sản phẩm.
- Bịa giá.
- Bịa tồn kho.
- Bịa khuyến mãi.
- Bịa bảo hành.
- Gợi ý sản phẩm không có trong dữ liệu.
- Trả lời chắc chắn khi dữ liệu không đủ.

Nếu dữ liệu sản phẩm không có trường cần thiết, ví dụ không có tồn kho hoặc đánh giá, phải nói rõ thay vì đoán.

---

## 5. Quy tắc thiết kế code recommendation

Khi sửa hoặc thêm logic trong `recommendation.py`, ưu tiên cấu trúc rõ ràng:

```text
load_products()          -> đọc dữ liệu sản phẩm
normalize_text()         -> chuẩn hóa tiếng Việt/chữ thường nếu cần
filter_products()        -> lọc theo điều kiện
score_product()          -> chấm điểm độ phù hợp
recommend_products()     -> trả danh sách sản phẩm đề xuất
format_recommendations() -> định dạng câu trả lời nếu cần
```

Không bắt buộc phải có đúng các hàm trên, nhưng nếu code hiện tại chưa rõ, có thể refactor nhẹ theo hướng này.

Nguyên tắc:

- Mỗi hàm chỉ nên làm một việc.
- Không lặp code lọc sản phẩm ở nhiều nơi.
- Không hard-code quá nhiều điều kiện trong luồng chính.
- Không làm thuật toán quá phức tạp nếu dữ liệu nhỏ.
- Nếu dữ liệu lớn, cần tối ưu đọc/lọc để tránh chậm.
- Nếu dùng tiếng Việt, nên chuẩn hóa chữ hoa/thường và dấu nếu cần.

---

## 6. Quy tắc xử lý tiếng Việt

Vì người dùng có thể hỏi bằng tiếng Việt:

- Cần xử lý chữ hoa/chữ thường.
- Cần xử lý từ khóa gần đúng nếu có thể.
- Không để lỗi encoding tiếng Việt.
- Khi đọc file dữ liệu, ưu tiên encoding `utf-8`.
- Nếu xử lý bỏ dấu tiếng Việt, phải cẩn thận để không làm sai tên sản phẩm khi hiển thị.
- Kết quả trả lời nên bằng tiếng Việt.

---

## 7. Quy tắc khi dùng AI/LLM

Nếu chatbot dùng AI/LLM:

- Không gửi toàn bộ dữ liệu sản phẩm vào model nếu không cần.
- Chỉ gửi danh sách sản phẩm đã được lọc hoặc top sản phẩm liên quan.
- Tách rõ dữ liệu thật và hướng dẫn trả lời.
- Yêu cầu model chỉ trả lời dựa trên dữ liệu được cung cấp.
- Nếu dữ liệu không có, model phải nói không có thông tin.
- Không gửi API key, token, secret vào prompt.
- Không gửi thông tin nhạy cảm của người dùng vào prompt nếu không cần.

Ưu tiên mô hình xử lý:

```text
Người dùng hỏi
→ Python lọc sản phẩm liên quan trong recommendation.py
→ Chỉ gửi kết quả lọc/top sản phẩm vào LLM nếu cần diễn đạt tự nhiên
→ Chatbot trả lời dựa trên dữ liệu thật
```

Không nên:

```text
Gửi toàn bộ database sản phẩm vào LLM
→ Nhờ LLM tự tìm và tự đoán
```

---

## 8. Quy tắc khi gọi backend

Nếu chatbot lấy dữ liệu từ `sope-backend/`:

- Kiểm tra endpoint backend thật trước.
- Không tạo endpoint giả trong chatbot.
- Không hard-code base URL nếu có thể dùng `.env`.
- Xử lý lỗi backend không phản hồi.
- Xử lý lỗi timeout.
- Xử lý lỗi dữ liệu rỗng.
- Không để chatbot crash khi API lỗi.
- Không lấy hoặc trả thông tin nhạy cảm nếu không cần.

Nếu cần sửa backend, phải nói rõ:

- Vì sao lỗi nằm ở backend.
- Endpoint nào cần sửa.
- Chatbot đang cần dữ liệu gì.
- Frontend có bị ảnh hưởng không.

---

## 9. Quy tắc bảo mật

Không được:

- Lộ API key.
- Lộ token.
- Lộ secret.
- Lộ mật khẩu.
- Lộ nội dung `.env`.
- Log dữ liệu nhạy cảm.
- Đưa dữ liệu nhạy cảm vào prompt.
- Đưa `.env` vào git.

Nếu cần đọc biến môi trường trong Python, ưu tiên dùng `os.getenv()` hoặc thư viện đã có trong dự án.

---

## 10. Quy tắc kiểm tra sau khi sửa

Sau khi sửa code chatbot, nếu phù hợp, hãy chạy hoặc đề xuất:

```bash
python check_model.py
python main.py
python -m compileall .
pip install -r requirements.txt
```

Nếu dự án dùng môi trường ảo:

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

Khi báo lại, phải nêu rõ:

- Đã test file nào.
- Lệnh test nào.
- Input mẫu nào.
- Kết quả mong đợi.
- Lỗi còn lại nếu có.

---

## 11. Bộ câu hỏi test recommendation

Sau khi sửa chức năng recommend sản phẩm, cần kiểm tra bằng các câu hỏi mẫu:

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

## 12. Những việc không được tự ý làm

Không tự ý:

- Viết lại toàn bộ chatbot.
- Xóa `data/`.
- Xóa `.env`.
- Sửa `.env` nếu không được yêu cầu.
- Sửa file trong `__pycache__/`.
- Tạo file recommendation mới khi đã có `recommendation.py`.
- Bịa dữ liệu sản phẩm.
- Hard-code API key.
- Thêm nhiều thư viện mới không cần thiết.
- Đổi cách chạy chính nếu không cập nhật tài liệu.
- Sửa backend/frontend nếu chưa xác định cần thiết.

---

## 13. Cập nhật CONTEXT.md

Sau khi sửa chatbot, phải cập nhật:

1. `chatbot-TMDT/CONTEXT.md`
2. `../CONTEXT.md` nếu thay đổi ảnh hưởng toàn dự án.

Nội dung cập nhật gồm:

- Người dùng yêu cầu gì.
- File đã sửa.
- Hàm/logic recommendation đã thay đổi nếu có.
- Dữ liệu `data/` có bị ảnh hưởng không.
- Model/API có bị ảnh hưởng không.
- Lệnh đã chạy hoặc cách kiểm tra.
- Lỗi gặp phải nếu có.
- Cách tránh lặp lại lỗi.
- Việc cần làm tiếp theo.

Không chép code dài vào `CONTEXT.md`.
Chỉ ghi tóm tắt ngắn gọn, đủ để lần sau Codex hiểu và làm tiếp.

---

## 14. Cách trả lời người dùng sau khi hoàn thành

Sau khi làm xong, trả lời bằng tiếng Việt theo mẫu:

### Đã hoàn thành

- Đã làm:
- File đã sửa:
- Chức năng bị ảnh hưởng:
- Cách kiểm tra:
- Đã cập nhật `CONTEXT.md`:

### Lưu ý

- Nêu ngắn gọn lỗi hoặc rủi ro nếu có.
- Nêu việc nên làm tiếp theo nếu cần.

Không trả lời quá dài nếu nhiệm vụ nhỏ.
