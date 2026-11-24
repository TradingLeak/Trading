import base64
import json
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit, parse_qs

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import server


def decode(s):
    return base64.urlsafe_b64decode(s + '=' * (-len(s) % 4))


class Response:
    status_code = 200
    def __init__(self, body): self.body = body
    def json(self): return self.body


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.key = Ed25519PrivateKey.generate()
        seed = self.key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
        public = self.key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        self.patches = [patch.object(server, 'ACCOUNT', '123456'), patch.object(server, 'KEY_ID', 'exnsk-test'),
                        patch.object(server, 'PRIVATE_KEY', (seed + public).hex()),
                        patch.object(server, 'GATEWAY', 'https://gateway.exness.com'),
                        patch.object(server, '_access_point', None), patch.object(server, '_cache', {}),
                        patch.object(server, '_last_request', 0.0), patch.object(server.time, 'sleep')]
        for p in self.patches: p.start()
        self.addCleanup(lambda: [p.stop() for p in reversed(self.patches)])
        self.client = server.app.test_client()
        self.calls = []

    def fake_get(self, url, *, headers, timeout, allow_redirects):
        self.assertFalse(allow_redirects)
        parsed = urlsplit(url)
        path = parsed.path + ('?' + parsed.query if parsed.query else '')
        payload_bytes = decode(headers['EXN-DATA'])
        self.key.public_key().verify(decode(headers['EXN-SIGN']), payload_bytes)
        payload = json.loads(payload_bytes)
        self.assertEqual(payload['method'], 'GET')
        self.assertEqual(payload['path'], path)
        self.assertEqual(payload['idempotency_key'], '')
        self.assertEqual(headers['EXN-IDEMPOTENCY-KEY'], '')
        self.assertEqual(payload['body_hash'], '47DEQpj8HBSa-_TImW-5JCeuQeRkm5NMpJWZG3hSuFU')
        self.calls.append(path)
        if parsed.path == '/v1/trading/access-point':
            self.assertEqual(parse_qs(parsed.query)['account_id'], ['123456'])
            return Response({'access_point': 'https://ap.exness.com'})
        self.assertEqual(parsed.path, '/v1/market-data/accounts/123456/candles')
        query = parse_qs(parsed.query)
        self.assertEqual(query['instrument'], ['XAUUSD'])
        self.assertEqual(query['price_type'], ['bid'])
        self.assertEqual(query['timeframe'], ['H1'])
        return Response({'candles': [{'time':'2026-11-24T00:00:00Z','open':100,'high':102,'low':99,'close':101,'volume':12}]})

    def test_signed_discovery_candles_cache_and_cors(self):
        with patch.object(server.requests, 'get', side_effect=self.fake_get):
            response = self.client.get('/api/candles?symbol=XAUUSD&timeframe=1h', headers={'Origin':'https://tradingleak.github.io'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['candles'][0]['close'], 101)
            self.assertEqual(response.json['source'], 'exness')
            self.assertEqual(response.headers['Access-Control-Allow-Origin'], 'https://tradingleak.github.io')
            self.assertEqual(self.client.get('/api/candles?symbol=XAUUSD&timeframe=1h').status_code, 200)
            self.assertEqual(len(self.calls), 2)

    def test_reject_invalid_requests_and_origins(self):
        self.assertEqual(self.client.get('/api/candles?symbol=../../foo&timeframe=1h').status_code, 400)
        self.assertEqual(self.client.get('/api/candles?symbol=XAUUSD&timeframe=BAD').status_code, 400)
        response = self.client.get('/api/health', headers={'Origin': 'https://evil.example'})
        self.assertNotIn('Access-Control-Allow-Origin', response.headers)
        with self.assertRaises(ValueError): server.checked_base('https://exness.com.evil.example')
        with self.assertRaises(ValueError): server.checked_base('https://user:secret@exness.com')

    def test_no_credentials_leaked_on_error(self):
        with patch.object(server, 'PRIVATE_KEY', 'bad'):
            response = self.client.get('/api/candles?symbol=XAUUSD&timeframe=1h')
            self.assertEqual(response.status_code, 503)
            self.assertNotIn('exnsk-test', response.get_data(as_text=True))
            self.assertNotIn('bad', response.get_data(as_text=True))

    def test_upstream_error_and_busy_are_safe(self):
        class BadResponse:
            status_code = 401
        with patch.object(server.requests, 'get', return_value=BadResponse()):
            response = self.client.get('/api/candles?symbol=XAUUSD&timeframe=1h')
            self.assertEqual(response.status_code, 502)
            self.assertEqual(response.json['upstream_status'], 401)
            self.assertNotIn('exnsk-test', response.get_data(as_text=True))
        server._lock.acquire()
        try:
            self.assertEqual(self.client.get('/api/candles?symbol=XAUUSD&timeframe=1h').status_code, 429)
        finally:
            server._lock.release()

    def test_health_is_not_connectivity_check(self):
        response = self.client.get('/api/health')
        self.assertEqual(response.json['status'], 'configured')
        self.assertIn('not a connectivity test', response.json['note'])

if __name__ == '__main__': unittest.main()
