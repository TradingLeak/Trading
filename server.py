#!/usr/bin/env python3
"""
Exness Terminal — Backend proxy server (optional, for real Exness API)

Exness không cung cấp API giá công khai miễn phí. Để dùng giá thật từ
tài khoản Exness của bạn, chạy server này kèm Personal API Key, sau đó
trỏ frontend tới http://localhost:8000/api/...

Cách lấy API Key:
  1. Đăng nhập exness.com → Personal Area → Settings → API
  2. Tạo Personal API Key (bật quyền đọc giá / giao dịch nếu cần)
  3. export EXNESS_API_KEY=... EXNESS_API_SECRET=... EXNESS_ACCOUNT=...
  4. python3 server.py

Server này:
  - Serve file index.html tại http://localhost:8000
  - Proxy /api/price?symbol=XAUUSD → Exness REST (khi có key)
  - Fallback sang Stooq/Binance public feed khi chưa có key
  - Thêm CORS header để frontend gọi được từ mọi origin

Chạy:  python3 server.py  →  mở http://localhost:8000
"""
import os, json, urllib.request, urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler

EXNESS_KEY = os.environ.get("EXNESS_API_KEY", "")
EXNESS_SECRET = os.environ.get("EXNESS_API_SECRET", "")
EXNESS_ACCOUNT = os.environ.get("EXNESS_ACCOUNT", "")
EXNESS_BASE = os.environ.get("EXNESS_API_BASE", "https://api.exness.com/v1")

# Map symbol Exness -> Stooq / Binance fallback
FALLBACK = {
    "XAUUSD": ("xauusd", None), "EURUSD": ("eurusd", None), "GBPUSD": ("gbpusd", None),
    "USDJPY": ("usdjpy", None), "BTCUSD": ("btcusd", "BTCUSDT"), "ETHUSD": ("ethusd", "ETHUSDT"),
}

def fetch_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())

def get_price(symbol: str):
    symbol = symbol.upper()
    # 1) Try Exness REST API if key present
    if EXNESS_KEY:
        try:
            # NOTE: endpoint thực tế phụ thuộc loại API Exness cấp cho bạn
            # (Personal API / MT5 bridge). Điều chỉnh path cho khớp tài khoản.
            url = f"{EXNESS_BASE}/symbols/{symbol}/tick"
            headers = {"Authorization": f"Bearer {EXNESS_KEY}", "X-Account-Id": EXNESS_ACCOUNT}
            data = fetch_json(url, headers)
            return {"symbol": symbol, "source": "exness", "data": data}
        except Exception as e:
            return {"symbol": symbol, "source": "exness-error", "error": str(e)}
    # 2) Fallback: Stooq daily CSV (last close)
    stooq, binance = FALLBACK.get(symbol, (symbol.lower(), None))
    try:
        url = f"https://stooq.com/q/d/l/?s={stooq}&i=d"
        with urllib.request.urlopen(url, timeout=10) as r:
            text = r.read().decode()
        lines = text.strip().split("\n")
        last = lines[-1].split(",")
        return {"symbol": symbol, "source": "stooq", "date": last[0], "close": float(last[4])}
    except Exception as e:
        return {"symbol": symbol, "source": "error", "error": str(e)}

class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204); self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/price":
            qs = urllib.parse.parse_qs(parsed.query)
            symbol = qs.get("symbol", ["XAUUSD"])[0]
            body = json.dumps(get_price(symbol)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/api/health":
            body = json.dumps({"ok": True, "exness_configured": bool(EXNESS_KEY)}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print(f"Exness Terminal → http://localhost:{port}")
    print(f"Exness API key: {'CONFIGURED' if EXNESS_KEY else 'not set (using public fallback)'}")
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
