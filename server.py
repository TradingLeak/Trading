#!/usr/bin/env python3
"""Read-only Exness candle proxy. Credentials remain on the server.

See README.md for deployment, limitations and configuration.
"""
import base64
import hashlib
import json
import math
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlsplit

import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from flask import Flask, jsonify, request

app = Flask(__name__)
FRONTEND_ORIGIN = os.environ.get('FRONTEND_ORIGIN', 'https://tradingleak.github.io')
ACCOUNT = os.environ.get('EXN_ACCOUNT_ID', '')
KEY_ID = os.environ.get('EXN_API_KEY', '')
PRIVATE_KEY = os.environ.get('EXN_PRIVATE_KEY', '')
GATEWAY = os.environ.get('EXN_DISCOVERY_BASE_URL', '')
ALLOWED_SUFFIXES = tuple(x.strip().lower().lstrip('.') for x in os.environ.get('EXN_ALLOWED_HOST_SUFFIXES', 'exness.com').split(',') if x.strip())
SYMBOLS = frozenset('XAUUSD XAGUSD EURUSD GBPUSD USDJPY USDCHF AUDUSD USDCAD EURGBP EURJPY BTCUSD ETHUSD LTCUSD XRPUSD US30 NAS100 SPX500 GER40 UK100 JPN225 XBRUSD XTIUSD'.split())
TIMEFRAMES = {'1m': ('M1', 60), '5m': ('M5', 300), '15m': ('M15', 900), '1h': ('H1', 3600), '4h': ('H4', 14400), '1d': ('D1', 86400), '1w': ('W1', 604800)}
CACHE_SECONDS = 30
_lock = threading.Lock()
_cache = {}
_access_point = None
_last_request = 0.0


def b64(value):
    return base64.urlsafe_b64encode(value).decode('ascii').rstrip('=')


def signing_key(text):
    text = text.strip()
    if text.startswith('-----BEGIN PRIVATE KEY-----'):
        key = serialization.load_pem_private_key(text.encode(), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise ValueError('Expected Ed25519 key')
        return key
    if not re.fullmatch(r'[0-9a-fA-F]{128}', text):
        raise ValueError('Invalid private key format')
    raw = bytes.fromhex(text)
    key = Ed25519PrivateKey.from_private_bytes(raw[:32])
    public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    if public != raw[32:]:
        raise ValueError('Invalid private key')
    return key


def checked_base(value):
    url = urlsplit(value)
    host = (url.hostname or '').lower()
    if (url.scheme != 'https' or url.username or url.password or url.port not in (None, 443)
            or url.path not in ('', '/') or url.query or url.fragment
            or not any(host == suffix or host.endswith('.' + suffix) for suffix in ALLOWED_SUFFIXES)):
        raise ValueError('Invalid upstream host')
    return 'https://' + host


def signed_get(base, path):
    global _last_request
    delay = 1.0 - (time.monotonic() - _last_request)
    if delay > 0:
        time.sleep(delay)
    stamp = int(time.time() * 1000)
    payload = json.dumps({'api_key': KEY_ID, 'idempotency_key': '', 'timestamp': stamp,
                          'sign_version': 1, 'method': 'GET', 'path': path,
                          'body_hash': b64(hashlib.sha256(b'').digest())}, separators=(',', ':')).encode()
    headers = {'EXN-API-KEY': KEY_ID, 'EXN-IDEMPOTENCY-KEY': '', 'EXN-TIMESTAMP': str(stamp),
               'EXN-SIGN-VERSION': '1', 'EXN-DATA': b64(payload),
               'EXN-SIGN': b64(signing_key(PRIVATE_KEY).sign(payload)), 'User-Agent': 'Trading-ReadOnly/1.0'}
    _last_request = time.monotonic()
    response = requests.get(checked_base(base) + path, headers=headers, timeout=12, allow_redirects=False)
    if response.status_code != 200:
        raise UpstreamError(response.status_code)
    return response.json()


class UpstreamError(Exception):
    def __init__(self, status):
        self.status = status


def candles(symbol, tf):
    global _access_point
    if not re.fullmatch(r'[1-9][0-9]{0,19}', ACCOUNT) or int(ACCOUNT) > 2**64 - 1:
        raise ValueError('Account not configured')
    if not KEY_ID or not PRIVATE_KEY or not GATEWAY:
        raise ValueError('Credentials not configured')
    if _access_point is None:
        discovery = signed_get(GATEWAY, '/v1/trading/access-point?' + urlencode({'account_id': ACCOUNT}))
        _access_point = checked_base(discovery['access_point'])
    wire_tf, seconds = TIMEFRAMES[tf]
    now = datetime.now(timezone.utc)
    # 300 candles maximum; the exclusive end includes the current candle.
    start = now - timedelta(seconds=seconds * 300)
    iso = lambda dt: dt.isoformat(timespec='seconds').replace('+00:00', 'Z')
    query = urlencode({'instrument': symbol, 'timeframe': wire_tf, 'from': iso(start),
                       'to': iso(now), 'price_type': 'bid'})
    try:
        result = signed_get(_access_point, f'/v1/market-data/accounts/{ACCOUNT}/candles?{query}')
    except UpstreamError as exc:
        if exc.status in (401, 403, 404, 502, 503):
            _access_point = None
        raise
    rows = []
    for c in result.get('candles', []):
        timestamp = datetime.fromisoformat(c['time'].replace('Z', '+00:00'))
        if timestamp.tzinfo is None:
            raise ValueError('Naive candle timestamp')
        row = {'time': int(timestamp.timestamp())}
        for name in ('open', 'high', 'low', 'close'):
            row[name] = float(c[name])
        row['volume'] = float(c.get('volume') or 0)
        if not all(math.isfinite(row[n]) for n in ('open', 'high', 'low', 'close', 'volume')):
            raise ValueError('Invalid candle')
        rows.append(row)
    rows.sort(key=lambda x: x['time'])
    if not rows or any(a['time'] >= b['time'] for a, b in zip(rows, rows[1:])):
        raise ValueError('No usable candles')
    return {'symbol': symbol, 'timeframe': tf, 'source': 'exness', 'price_type': 'bid',
            'retrieved_at': iso(now), 'candles': rows}


@app.after_request
def cors(response):
    if request.headers.get('Origin') == FRONTEND_ORIGIN:
        response.headers['Access-Control-Allow-Origin'] = FRONTEND_ORIGIN
        response.headers['Vary'] = 'Origin'
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@app.get('/api/health')
def health():
    return jsonify(status='configured' if all((ACCOUNT, KEY_ID, PRIVATE_KEY, GATEWAY)) else 'not_configured',
                   note='Configuration only; not a connectivity test')


@app.get('/api/candles')
def candle_endpoint():
    symbol, tf = request.args.get('symbol', ''), request.args.get('timeframe', '')
    if symbol not in SYMBOLS or tf not in TIMEFRAMES:
        return jsonify(error='Unsupported symbol or timeframe'), 400
    # A busy proxy rejects excess requests instead of accumulating an unbounded queue.
    if not _lock.acquire(blocking=False):
        return jsonify(error='Backend busy; retry shortly'), 429
    try:
        entry = _cache.get((symbol, tf))
        if entry and time.monotonic() - entry[0] < CACHE_SECONDS:
            return jsonify(entry[1])
        try:
            data = candles(symbol, tf)
        except UpstreamError as exc:
            return jsonify(error='Exness request failed', upstream_status=exc.status), 502
        except (ValueError, KeyError, TypeError, requests.RequestException):
            return jsonify(error='Exness unavailable or server configuration invalid'), 503
        _cache[(symbol, tf)] = (time.monotonic(), data)
        return jsonify(data)
    finally:
        _lock.release()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '8000')), debug=False)
