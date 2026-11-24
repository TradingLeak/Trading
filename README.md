# Trading — Biểu đồ thị trường

Website biểu đồ kiểu TradingView/OpenMarket bằng tiếng Việt, không có chức năng đặt hoặc quản lý lệnh.

## Website

[https://tradingleak.github.io/Trading/](https://tradingleak.github.io/Trading/)

GitHub Actions triển khai website khi thay đổi được đưa vào `main`. Để chạy tại máy:

```bash
python3 -m http.server 8000
# Mở http://localhost:8000
```

Biểu đồ sử dụng Lightweight Charts từ CDN nên cần kết nối internet.

## Tính năng

- Biểu đồ nến, bar, line, area và Heikin Ashi; khung thời gian 1m–1W.
- Chỉ báo MA, EMA, Bollinger Bands, RSI, MACD và khối lượng.
- Danh sách mã, tìm kiếm, dải ticker và bảng thông số tham khảo.
- Các công cụ vẽ chỉ là giao diện demo, chưa hỗ trợ vẽ trên biểu đồ.

## Nguồn dữ liệu và giới hạn

Website **chưa kết nối với Exness**. Không nhập API key hoặc thông tin tài khoản vào website. Nút Exness API chỉ hiển thị thông tin và cho phép xóa key đã lưu ở phiên bản trước trong trình duyệt hiện tại.

Biểu đồ thử tải dữ liệu lịch sử từ Binance cho crypto hoặc Stooq cho các mã khác; khi không thể tải sẽ dùng dữ liệu mô phỏng. Nến intraday được suy ra từ dữ liệu ngày của Stooq là mô phỏng. Danh sách theo dõi, ticker và các tick cập nhật trên biểu đồ cũng là mô phỏng, không phải báo giá trực tiếp. Thông số trong bảng chỉ mang tính tham khảo, không xác nhận là thông số Exness hiện tại. Không sử dụng dữ liệu này để ra quyết định đầu tư.

`server.py` là thử nghiệm độc lập, không được frontend hay GitHub Pages sử dụng và chưa được xác nhận hoạt động với API Exness.
