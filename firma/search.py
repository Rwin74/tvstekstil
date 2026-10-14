import html
import re
import time
from concurrent.futures import ThreadPoolExecutor

import httpx

from .buyers import normalized, product_terms, evaluate, prefilter, boutique_site_reason
from .models import COUNTRIES, Lead, SearchRequest, domain_key
from .store import now


class ServiceError(Exception):
    pass


def plain(text):
    return html.unescape(re.sub(r"<[^>]+>", "", text or "")).strip()


SECTORS = {
    "fr": {"fashion":"boutique vêtements multimarque", "home":"boutique linge de maison", "baby":"boutique bébé enfant", "accessories":"boutique accessoires mode"},
    "tr": {"fashion":"çok markalı giyim butik", "home":"butik ev tekstili mağazası", "baby":"bebek çocuk giyim butik", "accessories":"butik moda aksesuar çanta"},
    "en": {"fashion":"independent multibrand clothing boutique", "home":"independent home textiles boutique", "baby":"baby children clothing boutique", "accessories":"independent fashion accessories boutique"},
    "de": {"fashion":"Multibrand Mode Boutique", "home":"Heimtextilien Boutique Geschäft", "baby":"Kinderkleidung Baby Boutique", "accessories":"Mode Accessoires Boutique"},
    "it": {"fashion":"boutique multimarca abbigliamento", "home":"negozio tessili casa indipendente", "baby":"boutique abbigliamento bambini", "accessories":"boutique accessori moda"},
    "es": {"fashion":"boutique multimarca ropa", "home":"tienda textiles hogar independiente", "baby":"boutique ropa bebé niños", "accessories":"boutique accesorios moda"},
    "nl": {"fashion":"multibrand kleding boetiek", "home":"woontextiel winkel", "baby":"babykleding kinder boetiek", "accessories":"mode accessoires boetiek"},
}
RETAIL_WORD = {"fr":"boutique", "tr":"butik", "en":"boutique", "de":"Boutique", "it":"boutique", "es":"boutique", "nl":"boetiek"}
# Most exclusion happens after retrieval, so precise product queries stay usable.


def build_queries(req):
    if req.mode == "prospects" or (req.mode == "city" and not req.product):
        sectors = ["fashion","home","baby"] if req.sector == "all" else [req.sector]
        bases = [SECTORS[req.language][s] for s in sectors]
    else:
        phrase = req.query if req.mode == "general" else req.product
        phrase = re.sub(r'[^\w\s\-À-ÿ]', ' ', product_terms(phrase, req.language))
        bases = [phrase + " " + RETAIL_WORD[req.language]]
    return [" ".join(x for x in (base,req.city,COUNTRIES[req.country] if not req.city else "") if x) for base in bases]


def build_query(req):
    return build_queries(req)[0]


def fetch_results(query, req, settings, timeout=18):
    try:
        with httpx.Client(timeout=timeout, follow_redirects=False) as client:
            if settings.provider == "brave":
                response = client.get("https://api.search.brave.com/res/v1/web/search", headers={"X-Subscription-Token":settings.api_key,"Accept":"application/json"}, params={"q":query,"country":req.country,"search_lang":req.language,"count":10,"offset":req.page-1})
            else:
                params = {"engine":"google","q":query,"hl":req.language,"start":(req.page-1)*10,"api_key":settings.api_key}
                if req.country != "ALL":
                    params["gl"] = req.country.lower()
                response = client.get("https://serpapi.com/search.json",params=params)
            if response.status_code in (401,403):
                raise ServiceError("Arama anahtarı reddedildi. Anahtarı ve servis yetkilerini kontrol edin.")
            if response.status_code == 429:
                raise ServiceError("Arama servisinin kotası doldu. Bir süre sonra tekrar deneyin.")
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError,ValueError) as exc:
        raise ServiceError("Arama servisine ulaşılamadı. Bağlantıyı ve servis ayarlarını kontrol edin.") from exc
    if payload.get("search_information",{}).get("organic_results_state") == "Fully empty" and "returned any results" in str(payload.get("error","")):
        return []
    if payload.get("error"):
        raise ServiceError("Arama servisi isteği tamamlayamadı. Servis hesabınızı ve kotanızı kontrol edin.")
    raw = payload.get("web",{}).get("results",[]) if settings.provider == "brave" else payload.get("organic_results",[])
    return [{"url":x.get("url" if settings.provider == "brave" else "link",""),"title":plain(x.get("title",""))[:200],"snippet":plain(x.get("description",x.get("snippet","")))[:4000]} for x in raw[:20]]


def probe_site(url, product):
    from .enrich import enrich
    return enrich(url, product, budget=8, include_pages=True)


def search(req: SearchRequest, settings):
    if not settings.api_key:
        raise ServiceError("Canlı butik keşfi için Ayarlar bölümüne SerpApi veya Brave anahtarınızı ekleyin.")
    queries = build_queries(req)
    raw, warnings = [], []
    successful, more = 0, False
    deadline = time.monotonic() + 36
    attempted = 0
    for i, query in enumerate(queries):
        if i:
            time.sleep(1.05)
        try:
            if time.monotonic() >= deadline-1:
                warnings.append("Araştırma süre sınırına ulaştı; tamamlanan kategoriler gösteriliyor.")
                break
            attempted += 1
            batch = fetch_results(query, req, settings,timeout=min(18,deadline-time.monotonic()))
            raw.extend(batch)
            more = more or len(batch) >= 10
            successful += 1
        except ServiceError as exc:
            if not successful:
                raise
            warnings.append(str(exc))
            break
    candidates, excluded, seen = [], [], set()
    for item in raw:
        try:
            key = domain_key(item["url"])
            reason = prefilter(item["url"], item["title"], item["snippet"])
        except ValueError:
            key, reason = item["url"], "Geçersiz web adresi"
        if key in seen:
            continue
        seen.add(key)
        if reason:
            excluded.append({"name":item["title"],"url":item["url"],"reason":reason})
        else:
            candidates.append(item)
    product = req.query if req.mode == "general" else req.product
    candidates.sort(key=lambda x: evaluate(x["url"],x["title"],x["snippet"],product).get("priority",0),reverse=True)
    def inspect(item):
        try:
            return probe_site(item["url"], product)
        except (ServiceError,ValueError):
            return None
    with ThreadPoolExecutor(max_workers=6) as pool:
        inspected = list(pool.map(inspect,candidates[:6]))
    rows = []
    for i, item in enumerate(candidates):
        probe = inspected[i] if i < len(inspected) else None
        pages = probe.get("pages",[]) if probe else []
        strict_reason = boutique_site_reason(item["url"], pages, product)
        if strict_reason:
            excluded.append({"name":item["title"],"url":item["url"],"reason":strict_reason})
            continue
        assessment = evaluate(item["url"],item["title"],item["snippet"],product,pages)
        if not assessment.pop("accepted"):
            excluded.append({"name":item["title"],"url":item["url"],"reason":assessment["reason"]})
            continue
        contact = probe["data"] if probe else {}
        if assessment["buyer_type"] == "retailer":
            assessment["buyer_type"] = "boutique"
        assessment["reasons"].append("Kendi sitesinde butik kimliği ve satış / mağaza bilgisi birlikte bulundu")
        sources = [{"field":"buyer_assessment","value":"; ".join(assessment["reasons"]),"url":item["url"],"checked_at":now()}] + contact.get("sources",[])
        try:
            row = Lead(name=item["title"] or domain_key(item["url"]),website=item["url"],product=product,target_city=req.city,country=req.country if req.country != "ALL" else "",evidence=item["snippet"],source_url=item["url"],sources=sources[:20],email=contact.get("email",""),phone=contact.get("phone",""),whatsapp=contact.get("whatsapp",""),instagram=contact.get("instagram",""),assessed_at=now(),discovery_mode=req.mode,**assessment)
            rows.append(row.model_dump())
        except ValueError:
            excluded.append({"name":item["title"],"url":item["url"],"reason":"İşletme bilgileri doğrulanamadı"})
    rows.sort(key=lambda r:r["priority"],reverse=True)
    return {"results":rows,"query":f"{product or 'Potansiyel butik keşfi'} · {req.city} · {COUNTRIES[req.country]}","queries":queries,"provider":settings.provider,"page":req.page,"has_more":more and req.page<5,"excluded":excluded,"scanned":len(seen),"site_checks":len(inspected),"requests_used":attempted,"warnings":warnings,"cached":False}
