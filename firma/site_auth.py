"""Reuse TVS's AES-GCM admin cookie and recheck membership on every request."""
import base64
import hmac
import json
import os
import re
import time
from contextvars import ContextVar
from urllib.parse import parse_qsl, urlencode

import httpx
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from starlette.requests import Request
from starlette.responses import JSONResponse

TOKEN = ContextVar('tvs_boutique_token', default=None)
ORIGIN = 'https://www.tvstextile.com'
COOKIE = '__Host-tvs-admin'


def config():
    url = os.getenv('SUPABASE_URL', '').rstrip('/')
    key = os.getenv('SUPABASE_PUBLISHABLE_KEY') or os.getenv('SUPABASE_ANON_KEY', '')
    if not re.fullmatch(r'https://[a-z0-9]+\.supabase\.co', url) or not key:
        raise ValueError('Supabase configuration missing')
    return url, key


def unseal(cookie_header):
    values = [p.strip().split('=', 1)[1] for p in cookie_header.split(';')
              if p.strip().startswith(COOKIE + '=')]
    if len(values) != 1 or len(values[0]) > 6000:
        raise ValueError('Invalid cookie')
    value = values[0]
    if not re.fullmatch(r'[A-Za-z0-9_-]+', value):
        raise ValueError('Invalid cookie')
    key = base64.b64decode(os.environ.get('ADMIN_SESSION_KEY', ''), validate=True)
    if len(key) != 32:
        raise ValueError('Invalid session configuration')
    raw = base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))
    data = json.loads(AESGCM(key).decrypt(raw[:12], raw[28:] + raw[12:28], None))
    if (not isinstance(data, dict) or not isinstance(data.get('exp'), (float, int))
            or data['exp'] <= time.time() * 1000
            or not isinstance(data.get('token'), str) or not data['token']
            or not isinstance(data.get('csrf'), str) or not data['csrf']):
        raise ValueError('Invalid session')
    return data


async def verify_admin(token):
    url, key = config()
    headers = {'apikey': key, 'Authorization': 'Bearer ' + token}
    async with httpx.AsyncClient(timeout=5, follow_redirects=False, trust_env=False) as client:
        user = await client.get(url + '/auth/v1/user', headers=headers)
        if user.status_code != 200 or not user.json().get('id'):
            return False
        role = await client.post(url + '/rest/v1/rpc/cms_is_admin', headers=headers, json={})
        return role.status_code == 200 and role.json() is True


class AdminGateway:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        request = Request(scope)

        async def error(status, message):
            response = JSONResponse({'detail': message}, status_code=status, headers={
                'Cache-Control': 'no-store', 'X-Robots-Tag': 'noindex, nofollow',
                'X-Content-Type-Options': 'nosniff', 'X-Frame-Options': 'DENY'})
            await response(scope, receive, send)

        try:
            # Join duplicate Cookie headers so unseal rejects duplicate session cookies.
            session = unseal(';'.join(request.headers.getlist('cookie')))
        except Exception:
            return await error(401, 'Yönetici girişi gerekiyor.')
        if request.method not in ('GET', 'HEAD'):
            if (request.headers.get('origin') != ORIGIN
                    or request.headers.get('sec-fetch-site', 'same-origin') != 'same-origin'
                    or not hmac.compare_digest(request.headers.get('x-csrf-token', '').encode(), session['csrf'].encode())):
                return await error(403, 'Geçersiz istek kaynağı. Sayfayı yenileyin.')
        try:
            if not await verify_admin(session['token']):
                return await error(401, 'Yönetici yetkiniz doğrulanamadı. Yeniden giriş yapın.')
        except Exception:
            return await error(503, 'Yönetici doğrulama servisine ulaşılamadı.')
        pairs = parse_qsl(scope.get('query_string', b'').decode(), keep_blank_values=True)
        routes = [value for key, value in pairs if key == 'route']
        path = request.url.path
        if path.startswith('/admin/butik-api/'):
            route = path.removeprefix('/admin/butik-api/')
        elif path in ('/api/boutiques', '/api/boutiques.py') and len(routes) == 1:
            route = routes[0]
        else:
            return await error(404, 'İşlem bulunamadı.')
        if not re.fullmatch(r'(?:health|session|settings|search|enrich|leads(?:/[a-zA-Z0-9-]{1,64})?|history|backup|restore|export(?:/pdf)?|translation/settings|translate)', route):
            return await error(404, 'İşlem bulunamadı.')
        mapped = dict(scope, path='/api/' + route, raw_path=('/api/' + route).encode(),
                      query_string=urlencode([(k, v) for k, v in pairs if k != 'route']).encode(),
                      state={**scope.get('state', {}), 'tvs_admin_verified': True})
        context = TOKEN.set(session['token'])
        try:
            await self.app(mapped, receive, send)
        finally:
            TOKEN.reset(context)
