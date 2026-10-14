import csv
import hashlib
import hmac
import io
import json
import logging
import time
from typing import Literal
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from . import vault
from .config import ROOT, Settings
from .enrich import enrich
from .models import EnrichRequest, Lead, LeadUpdate, SearchRequest
from .search import ServiceError, search, build_queries
from .buyers import evaluate, boutique_site_reason, prefilter
from .store import Conflict, Store, now
from . import translation
from .pdf_export import build_pdf


class Login(BaseModel):
    password: str = Field(max_length=500)


class TranslationSettings(BaseModel):
    provider: Literal['azure','google']
    key: str = Field(min_length=8,max_length=500)
    region: str = Field(default='',max_length=60,pattern=r'^[a-z0-9-]*$')


class PdfRequest(BaseModel):
    ids: list[str] = Field(default_factory=list,max_length=500)


class SearchSettings(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    provider: Literal["serpapi", "brave"]
    key: str = Field(min_length=8, max_length=300)


class Backup(BaseModel):
    format: Literal["firma-atlas-v1"]
    leads: list[dict] = Field(max_length=10000)


def session_token(settings, expires=None):
    stamp = str(expires or int(time.time()) + 43200)
    signature = hmac.new((settings.secret + settings.password).encode(), stamp.encode(), hashlib.sha256).hexdigest()
    return stamp + "." + signature


def authenticated(request, settings):
    if getattr(request.state, 'tvs_admin_verified', False):
        return True
    if not settings.cloud:
        return True
    token = request.cookies.get("firma_session", "")
    try:
        stamp = int(token.split(".")[0])
        return stamp > time.time() and hmac.compare_digest(token, session_token(settings, stamp))
    except (ValueError, IndexError):
        return False


def create_app(settings=None, *, site_store=None):
    settings = settings or Settings.from_env()
    if site_store is None:
        settings.validate()
    elif not settings.cloud:
        raise RuntimeError('Site integration requires cloud mode')
    vault.load(settings)
    app = FastAPI(title="Firma Atlas", docs_url=None, redoc_url=None, openapi_url=None)
    store = site_store if site_store is not None else Store(settings)
    app.state.store, app.state.settings = store, settings

    @app.middleware("http")
    async def security(request, call_next):
        path = request.url.path
        if site_store is not None and not getattr(request.state, 'tvs_admin_verified', False):
            return JSONResponse({'detail': 'Yönetici girişi gerekiyor.'}, status_code=401)
        if not settings.cloud and request.url.hostname not in ("localhost", "127.0.0.1", "testserver"):
            return JSONResponse({"detail": "Geçersiz yerel adres."}, status_code=403)
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            origin = request.headers.get("origin")
            if request.headers.get("x-app-request") != "FirmaAtlas" or (origin and urlsplit(origin).netloc != request.headers.get("host")):
                return JSONResponse({"detail": "Geçersiz istek kaynağı."}, status_code=403)
            try:
                length = int(request.headers.get("content-length", "0"))
            except ValueError:
                length = 20_000_001
            if length > (4_000_000 if site_store is not None else 20_000_000):
                return JSONResponse({"detail": "Dosya çok büyük. Web sürümünde en fazla 4 MB aktarılabilir."}, status_code=413)
            # Bound chunked requests too, before parsing any JSON.
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > (4_000_000 if site_store is not None else 20_000_000):
                    return JSONResponse({"detail": "Dosya çok büyük. Web sürümünde en fazla 4 MB aktarılabilir."}, status_code=413)
            request._body = bytes(body)
        if path.startswith("/api/") and path not in ("/api/session", "/api/login", "/api/health") and not authenticated(request, settings):
            return JSONResponse({"detail": "Oturum açmanız gerekiyor."}, status_code=401)
        try:
            response = await call_next(request)
        except Exception:
            logging.getLogger("firma").exception("İstek işlenemedi: %s", path)
            response = JSONResponse({"detail": "İşlem tamamlanamadı. Veritabanı bağlantısını kontrol edip tekrar deneyin."}, status_code=500)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Never reflect input (passwords/API keys included) in errors.
        return JSONResponse({"detail": "Bilgileri kontrol edin. Zorunlu alan, adres veya değer biçimi geçersiz."}, status_code=422)

    @app.exception_handler(Conflict)
    async def conflict(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(ServiceError)
    async def service_error(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=502)

    @app.get("/api/health")
    def health():
        return {"ok": True, "version": "2.2.0"}

    @app.get("/api/session")
    def session(request: Request):
        return {"authenticated": authenticated(request, settings), "cloud": settings.cloud}

    @app.post("/api/login")
    def login(payload: Login, request: Request):
        ip = request.client.host if request.client else "unknown"
        bucket = f"{int(time.time() // 3600)}:login:{hashlib.sha256(ip.encode()).hexdigest()}"
        if not store.rate_limit(bucket, 30):
            raise HTTPException(429, "Çok fazla giriş denemesi. Daha sonra tekrar deneyin.")
        if settings.cloud and not hmac.compare_digest(payload.password.encode(), settings.password.encode()):
            raise HTTPException(401, "Parola yanlış.")
        response = JSONResponse({"ok": True})
        response.set_cookie("firma_session", session_token(settings), httponly=True, secure=settings.cloud, samesite="strict", max_age=43200)
        return response

    @app.post("/api/logout")
    def logout():
        response = JSONResponse({"ok": True})
        response.delete_cookie("firma_session")
        return response

    @app.get("/api/settings")
    def get_settings():
        return {"provider": settings.provider, "configured": bool(settings.api_key), "cloud": settings.cloud, "storage": "PostgreSQL" if store.pg else "Bu bilgisayar", "version": "2.2.0"}

    @app.put("/api/settings")
    def set_settings(payload: SearchSettings):
        if settings.cloud:
            raise HTTPException(403, "Canlı site anahtarlarını Vercel ortam değişkenlerinden yönetin.")
        try:
            vault.save(settings, payload.provider, payload.key.strip())
        except (OSError, RuntimeError) as exc:
            raise HTTPException(400, str(exc))
        return get_settings()

    @app.post("/api/search")
    def run_search(payload: SearchRequest):
        fingerprint = hashlib.sha256(settings.api_key.encode()).hexdigest()
        cache_key = hashlib.sha256(("boutique-only-v3:" + settings.provider + fingerprint + payload.model_dump_json()).encode()).hexdigest()
        if settings.api_key:
            cached = store.cached(cache_key)
            if cached:
                return dict(cached,cached=True,requests_used=0)
        if not store.rate_limit(f"{int(time.time() // 3600)}:search", 120, len(build_queries(payload))):
            raise HTTPException(429, "Saatlik 120 canlı arama sınırına ulaşıldı.")
        result = search(payload, settings)
        if not result.get("warnings"):
            store.cache(cache_key,result)
        store.add_history({"request": payload.model_dump(), "query": result["query"], "count": len(result["results"]), "provider": result["provider"],"excluded":len(result["excluded"]),"requests_used":result["requests_used"]})
        return result

    @app.post("/api/enrich")
    def enrich_site(payload: EnrichRequest):
        if not store.rate_limit(f"{int(time.time() // 3600)}:enrich", 120):
            raise HTTPException(429, "Saatlik site inceleme sınırına ulaşıldı.")
        result = enrich(payload.url, payload.product,include_pages=True)
        pages = result.pop("pages")
        reason = boutique_site_reason(payload.url, pages, payload.product)
        result["assessment"] = {"accepted":False,"reason":reason} if reason else evaluate(payload.url,"","",payload.product,pages)
        result["assessment"]["assessed_at"] = now()
        return result

    @app.get("/api/leads")
    def leads():
        visible = store.list()
        return {"leads": visible, "hidden_count":len(store.list(include_legacy=True))-len(visible)}

    @app.post("/api/leads", status_code=201)
    def save_lead(payload: Lead):
        if payload.is_demo:
            raise HTTPException(422,"Yalnızca gerçek işletme kayıtları eklenebilir.")
        if payload.website and prefilter(payload.website, payload.name, payload.evidence):
            raise HTTPException(422,"Bu adres bir butik olarak kabul edilmedi: " + prefilter(payload.website,payload.name,payload.evidence))
        return store.save(payload)

    @app.put("/api/leads/{lead_id}")
    def update_lead(lead_id: str, payload: LeadUpdate):
        if payload.lead.is_demo:
            raise HTTPException(422,"Yalnızca gerçek işletme kayıtları düzenlenebilir.")
        return store.save(payload.lead, lead_id, payload.version)

    @app.delete("/api/leads/{lead_id}")
    def delete_lead(lead_id: str, version: int):
        store.delete(lead_id, version)
        return {"ok": True}

    @app.get("/api/history")
    def history():
        return {"history": store.history()}

    @app.get("/api/backup")
    def backup():
        body = json.dumps({"format": "firma-atlas-v1", "exported_at": now(), "leads": store.list(include_legacy=True)}, ensure_ascii=False, indent=2)
        return Response(body, media_type="application/json", headers={"Content-Disposition": 'attachment; filename="firma-atlas-yedek.json"'})

    @app.post("/api/restore")
    def restore(payload: Backup):
        rows = []
        try:
            for item in payload.leads:
                rows.append(Lead.model_validate({k: v for k, v in item.items() if k not in ("id", "created_at", "updated_at", "version")}))
        except ValidationError:
            raise HTTPException(422, "Yedekte geçersiz firma bilgisi var. Hiçbir kayıt aktarılmadı.")
        added, skipped = store.restore(rows)
        return {"added": added, "skipped": skipped}

    @app.get("/api/export")
    def export_csv():
        fields = {"name": "Firma adı", "website": "Web sitesi", "product": "Ürün", "fit": "Ürün uygunluğu", "email": "E-posta", "phone": "Telefon", "whatsapp": "WhatsApp", "instagram": "Instagram", "contact_person": "Yetkili", "city": "Şehir", "target_city": "Aranan şehir", "country": "Ülke", "status": "Durum", "notes": "Notlar", "source_url": "Kaynak", "evidence": "Kanıt", "priority": "Alıcı önceliği", "buyer_type": "Alıcı türü", "opportunity": "Alıcı sinyali", "assessment": "İnceleme düzeyi", "supplier_evidence": "Tedarikçi başvuru kanıtı", "supplier_source": "Başvuru kaynağı"}
        statuses = {"research": "Araştırılacak", "qualified": "Uygun", "contacted": "İletişime geçildi", "replied": "Yanıt geldi", "not_suitable": "Uygun değil", "unknown": "Belirsiz", "possible": "Olası eşleşme", "confirmed": "Doğrulandı", "no": "Uygun değil"}
        out = io.StringIO(newline="")
        writer = csv.writer(out, delimiter=";")
        writer.writerow(fields.values())
        for lead in store.list():
            row = []
            for field in fields:
                value = str(lead.get(field, ""))
                if field in ("status", "fit"):
                    value = statuses.get(value, value)
                if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")):
                    value = "'" + value
                row.append(value)
            writer.writerow(row)
        return Response("\ufeff" + out.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": 'attachment; filename="firma-atlas-firmalar.csv"'})

    @app.get('/api/translation/settings')
    def translation_settings():
        c=translation.settings_for(settings)
        return {'provider':c['provider'],'configured':bool(c['key']),'region':c.get('region',''),'cloud':settings.cloud}

    @app.put('/api/translation/settings')
    def set_translation_settings(payload:TranslationSettings):
        if settings.cloud: raise HTTPException(403,'Çeviri bağlantısını Vercel ortam değişkenlerinden yönetin.')
        if not payload.key.strip(): raise HTTPException(422,'Çeviri anahtarı boş olamaz.')
        try: translation.save_settings(settings,payload.provider,payload.key.strip(),payload.region)
        except (OSError,RuntimeError): raise HTTPException(400,'Çeviri anahtarı güvenli kasaya kaydedilemedi.')
        return translation_settings()

    @app.post('/api/translate')
    def translate_lead(payload:Lead):
        if not store.rate_limit(f'{int(time.time()//3600)}:translation',60): raise HTTPException(429,'Saatlik çeviri sınırına ulaşıldı.')
        result=translation.translate(payload.model_dump(),translation.settings_for(settings))
        try: Lead.model_validate({**payload.model_dump(),**result})
        except ValidationError: raise HTTPException(422,'Çeviri izin verilen alan uzunluğunu aşıyor.')
        return {'translations':result}

    @app.post('/api/export/pdf')
    def export_pdf(payload:PdfRequest):
        rows=store.list()
        if payload.ids:
            chosen=set(payload.ids)
            rows=[r for r in rows if r['id'] in chosen]
            if len(rows)!=len(chosen): raise HTTPException(409,'Bazı kayıtlar değişti veya gizlendi. Listeyi yenileyin.')
        if not rows: raise HTTPException(422,'PDF için önce firma kaydedin.')
        if len(rows)>500: raise HTTPException(422,'Bir PDF en fazla 500 firma içerebilir. Listeyi filtreleyin.')
        if sum(len(json.dumps(row,ensure_ascii=False)) for row in rows)>2_000_000:
            raise HTTPException(422,'PDF içeriği çok büyük. Firma listesini filtreleyerek daha küçük gruplar halinde indirin.')
        pdf = build_pdf(rows)
        if site_store is not None and len(pdf) > 4_000_000:
            raise HTTPException(422, 'PDF çok büyük. Listeyi filtreleyerek daha küçük gruplar halinde indirin.')
        return Response(pdf,media_type='application/pdf',headers={'Content-Disposition':'attachment; filename="firma-atlas-butikler.pdf"','Cache-Control':'no-store'})

    @app.get("/")
    def index():
        return FileResponse(ROOT / "admin" / "butik" / "index.html")

    if site_store is None:
        app.mount("/assets", StaticFiles(directory=ROOT / "admin" / "butik"), name="assets")
    return app
