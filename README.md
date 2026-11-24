# Trading — Biểu đồ thị trường

Website tiếng Việt trên [GitHub Pages](https://tradingleak.github.io/Trading/) chỉ hiển thị biểu đồ; không đặt lệnh. Có thể kết nối **backend chỉ đọc** để lấy nến giá bid từ Exness.

## Tình trạng hiện tại

`api-config.js` mặc định để trống, vì vậy GitHub Pages **chưa kết nối Exness**. Cần triển khai backend và cấu hình URL như bên dưới. Trên backend, `/api/health` chỉ cho biết đã cấu hình biến môi trường hay chưa, **không chứng minh kết nối thành công**.

Khi kết nối thành công, biểu đồ mã đang chọn dùng nến bid Exness và làm mới mỗi 30 giây khi tab đang mở. Đây là polling nến lịch sử, **không phải tick WebSocket trực tiếp**; có thể trễ và dữ liệu ngừng thay đổi khi thị trường đóng. Các mã khác trong watchlist/ticker vẫn mô phỏng. Không phải mã nào trong danh sách cũng được Exness hoặc tài khoản của bạn hỗ trợ; ví dụ API có thể không hỗ trợ chỉ số. Nếu backend lỗi hoặc mã không được hỗ trợ, biểu đồ chuyển sang Binance/Stooq hoặc mô phỏng và ghi rõ nguồn dự phòng. Nến intraday suy ra từ dữ liệu ngày của Stooq cũng là mô phỏng. Thông số chỉ để tham khảo, không sử dụng dữ liệu này để ra quyết định đầu tư.

## Bảo mật

- Thu hồi ngay cặp khóa từng gửi trong chat và tạo cặp mới; không dán khóa mới vào chat, Git, `api-config.js`, HTML hoặc biến môi trường GitHub Actions của trang tĩnh.
- Chỉ đặt khóa trong **biến môi trường riêng tư của dịch vụ backend**, dùng tài khoản demo trước và quyền **Trading read-only** nếu được hỗ trợ. Không bật quyền giao dịch cho ứng dụng này. Kiểm tra điều kiện, giới hạn API và IP allowlist của Exness.
- Backend công khai trả nến giá, không trả thông tin tài khoản hay khóa, nhưng bất kỳ ai cũng có thể gọi endpoint và tiêu thụ hạn mức Exness. CORS không phải cơ chế xác thực; hãy bổ sung rate limit tại nhà cung cấp/reverse proxy, theo dõi lưu lượng và chi phí, và chỉ công khai nếu chấp nhận điều này. Không có tính năng đăng nhập người dùng.
- Chỉ chạy một instance/một worker để cache và giới hạn tốc độ process hoạt động như thiết kế. Không log biến môi trường, header, khóa hoặc phản hồi có dữ liệu nhạy cảm.

## Triển khai backend

Chọn dịch vụ hosting Python hỗ trợ process chạy liên tục, HTTPS công khai, biến môi trường riêng tư và kết nối ra máy chủ Exness (GitHub Pages không chạy Python). Kết nối repo với dịch vụ đó, cài `requirements.txt`, dùng `Procfile` hoặc lệnh:

```sh
gunicorn --workers 1 --threads 4 --timeout 45 --bind 0.0.0.0:$PORT server:app
```

Thiết lập trong phần **environment/secrets của hosting backend** (không commit giá trị thật):

| Biến | Ý nghĩa |
| --- | --- |
| `EXN_API_KEY` | API key mới của Exness |
| `EXN_PRIVATE_KEY` | Private key 128 ký tự hex hoặc PEM Ed25519 |
| `EXN_ACCOUNT_ID` | ID tài khoản Exness có quyền API |
| `EXN_DISCOVERY_BASE_URL` | URL HTTPS Gateway từ DNS widget của Exness Key Management; không tự đoán |
| `FRONTEND_ORIGIN` | `https://tradingleak.github.io` (không có `/Trading`); mặc định như vậy |
| `EXN_ALLOWED_HOST_SUFFIXES` | Danh sách hậu tố host tin cậy, phân cách bằng dấu phẩy; mặc định `exness.com`. Nếu Gateway/Access Point chính thức của bạn dùng hậu tố khác, xác nhận với Exness và cấu hình rõ ràng |

Chỉ cung cấp URL và ID qua cấu hình riêng tư; không chia sẻ key. API dùng discovery có chữ ký Ed25519, sau đó gọi `/v1/market-data/accounts/{id}/candles` bằng Access Point. Chỉ GET, không có endpoint giao dịch. Cache trong bộ nhớ 30 giây, chỉ xử lý một cache miss mỗi lần và giới hạn một yêu cầu upstream mỗi giây trên một process, nhưng không thay thế rate limit ngoài. Truy cập `https://<backend>/api/health` để xem trạng thái cấu hình, sau đó `https://<backend>/api/candles?symbol=XAUUSD&timeframe=1h` để kiểm tra dữ liệu thật; lỗi sẽ không trả key hoặc signed headers. Hạn mức và tên instrument phụ thuộc tài khoản.

## Kết nối website GitHub Pages

Sau khi backend chạy HTTPS, điền **duy nhất URL gốc công khai**, không có dấu `/` cuối, vào `api-config.js`, ví dụ `window.EXNESS_BACKEND_URL = 'https://your-backend.example';`. Đây không phải nơi chứa key. Commit và merge thay đổi vào `main`; workflow Pages sẽ cập nhật website. Mở website, chọn XAUUSD và kiểm tra nhãn nguồn Exness cùng thời điểm cập nhật. Nếu ghi dự phòng hoặc DEMO, xem cấu hình, logs an toàn và kiểm tra endpoint backend.

## Kiểm thử cục bộ

```sh
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v
```

Test dùng khóa giả và máy chủ Exness giả; không xác nhận được tài khoản hay kết nối thực. Frontend có thể mở bằng `python3 -m http.server 8000`; biểu đồ cần CDN. `python3 server.py` chỉ chạy API backend, không serve frontend; để frontend truy cập backend cần HTTPS và cấu hình CORS phù hợp.

## Tham khảo

- [Exness: Request signing](https://www.exness-api.com/authentication/request-signing)
- [Exness: Access Point / Host Discovery](https://www.exness-api.com/trading/get-started/access-point-host-discovery)
- [Exness: Key Management](https://www.exness-api.com/authentication/api-key-and-host-setup)
