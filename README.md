# Trading — Exness Terminal (TradingView Style)

Website giao diện giao dịch kiểu **TradingView / OpenMarket**, kết nối dữ liệu giá theo chuẩn **Exness** (spread, contract size, đòn bẩy tới 1:2000).

![Terminal](https://img.shields.io/badge/Exness-Terminal-2962ff) ![Chart](https://img.shields.io/badge/Lightweight-Charts-26a69a)

## Tính năng

| Hạng mục | Chi tiết |
|---|---|
| **Chart** | Nến Nhật, Bar, Line, Area, Heikin Ashi — thư viện Lightweight Charts của TradingView |
| **Khung thời gian** | 1m · 5m · 15m · 1H · 4H · 1D · 1W |
| **Chỉ báo** | MA20, MA50, EMA20, Bollinger Bands, RSI 14, MACD (12,26,9) + Volume |
| **Watchlist** | 22 symbol Forex / Kim loại / Crypto / Chỉ số, sparkline, % thay đổi |
| **Ticker tape** | Dải giá chạy ngang đầu trang |
| **Sổ lệnh** | Order book Ask/Bid theo spread Exness, click để đặt Limit |
| **Đặt lệnh** | Mua/Bán, Market/Limit/Stop, Lot, đòn bẩy, TP/SL, tính margin |
| **Quản lý lệnh** | Vị thế đang mở (P/L realtime), Lệnh chờ, Lịch sử, Equity |
| **Công cụ vẽ** | Thanh công cụ kiểu TradingView (trend, fib, rect, text, magnet) |
| **Exness API** | Panel nhập Personal API Key, lưu local, kiểm tra kết nối |

## Chạy ngay (không cần cài đặt)

Mở trực tiếp file `index.html` bằng trình duyệt, hoặc:

```bash
# Python (có sẵn trên hầu hết máy)
python3 -m http.server 8000
# → mở http://localhost:8000
```

> Frontend tải thư viện chart từ CDN nên cần kết nối Internet khi mở.

## Nguồn dữ liệu giá

Exness **không** cung cấp API giá công khai miễn phí — API chính thức yêu cầu **Personal API Key** từ tài khoản của bạn. Terminal này dùng chiến lược 3 tầng:

1. **Crypto (BTC/ETH/LTC/XRP):** Binance Public API — giá thật, CORS mở, realtime.
2. **Forex / Kim loại / Chỉ số (XAUUSD, EURUSD, US30...):** Stooq Public Feed — giá thật (daily + mở rộng intraday).
3. **Fallback:** Mô phỏng Exness demo (random-walk theo volatility thật) nếu mạng/feed lỗi — chart vẫn luôn hoạt động.

Badge ở header hiển thị trạng thái: `LIVE` (feed thật) hoặc `DEMO` (mô phỏng). Panel trái dưới hiển thị nguồn feed hiện tại.

## Kết nối Exness API thật

### Bước 1 — Lấy API Key
1. Đăng nhập [exness.com](https://www.exness.com) → **Personal Area**
2. Vào **Settings → API** → tạo **Personal API Key**
3. Bật quyền đọc giá (và giao dịch nếu muốn đặt lệnh thật)

### Bước 2 — Nhập vào Terminal
- Click nút **Exness API** ở header → dán Key / Secret / Account ID (MT5) → **Lưu & Kết nối**
- Key chỉ lưu trong `localStorage` của trình duyệt, không gửi đi đâu khác.

### Bước 3 — (Tuỳ chọn) Chạy backend proxy
Nếu muốn gọi Exness REST qua server (tránh lộ key ở frontend):

```bash
export EXNESS_API_KEY="key_của_bạn"
export EXNESS_API_SECRET="secret_của_bạn"
export EXNESS_ACCOUNT="12345678"
python3 server.py
# → http://localhost:8000  (kèm /api/price?symbol=XAUUSD)
```

Xem chi tiết trong `server.py`.

## Thông số Exness (mô phỏng)

Mỗi symbol có: digits, spread (points), contract size, min lot, max leverage — xem tab **Thông số Exness** ở panel dưới hoặc bảng trong code (`SYMBOLS` trong `index.html`).

Ví dụ: XAUUSD — digits 2, spread 35 pts, contract 100 oz, leverage tới 1:2000.

## Số dư Demo

Mặc định **$10,000** tiền ảo. Đặt lệnh → P/L tính theo công thức Exness: `(giá hiện tại − giá vào) × contract × lot`. Nút **Reset Demo** để chơi lại.

## Cấu trúc repo

```
index.html   — toàn bộ frontend (HTML/CSS/JS, không cần build)
server.py    — backend proxy tuỳ chọn cho Exness API
README.md    — tài liệu này
```

## Lưu ý pháp lý

Đây là công cụ hiển thị & demo. Giao dịch Forex/CFD có rủi ro cao — chỉ dùng tiền thật khi đã hiểu rõ rủi ro và tuân thủ quy định tại quốc gia của bạn.
