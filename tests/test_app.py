import concurrent.futures
import csv
import io
import json
import os
import socket
import time
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient

from firma.app import create_app, session_token
from firma.config import Settings
from firma.enrich import extract, fetch, resolve_public
from firma.models import Lead, SearchRequest, domain_key
from firma.search import ServiceError, build_query, search
from firma.store import Conflict, Store

HEADERS = {"X-App-Request": "FirmaAtlas"}


@pytest.fixture
def client(tmp_path):
    app = create_app(Settings(tmp_path))
    with TestClient(app, headers=HEADERS) as c:
        yield c


def example(**kwargs):
    return {"name": "Örnek Tekstil", "website": "https://ornek.example/", "product": "müslin nevresim", **kwargs}


def test_health_assets_and_headers(client):
    assert client.get("/api/health").json()["ok"]
    page = client.get("/")
    assert page.status_code == 200 and "Firma Atlas" in page.text
    assert "frame-ancestors 'none'" in page.headers["content-security-policy"]
    assert client.get("/assets/app.js").status_code == 200
    assert client.get("/assets/style.css").status_code == 200
    assert client.get("/assets/../.env").status_code == 404


@pytest.mark.parametrize("mode,fields", [("product", {"product":"müslin nevresim"}), ("city", {"city":"Lyon"}), ("general", {"query":"müslin nevresim"}), ("prospects", {})])
def test_all_search_modes(client, mode, fields):
    from retail_fixtures import fetch_results, probe_site
    client.app.state.settings.api_key="fixture-key"
    with patch("firma.search.fetch_results",side_effect=fetch_results),patch("firma.search.probe_site",side_effect=probe_site),patch("firma.search.time.sleep"):
        r=client.post("/api/search",json={"mode":mode,**fields})
    assert r.status_code == 200, r.text
    assert len(r.json()["results"]) == 2
    assert all(not x["is_demo"] for x in r.json()["results"])
    assert len(r.json()["excluded"]) == 5
    assert len(client.get("/api/history").json()["history"]) == 1


def test_demo_removed(client):
    assert client.post("/api/search",json={"product":"müslin", "demo":True}).status_code == 422
    assert "demo-toggle" not in client.get("/").text


@pytest.mark.parametrize("payload", [{}, {"mode":"city"}, {"mode":"general"}, {"product":"x"}, {"product":"cotton","country":"XX"}, {"product":"cotton","page":0}, {"product":"cotton","page":6}, {"product":"cotton","extra":"bad"}])
def test_search_validation(client, payload):
    assert client.post("/api/search", json=payload).status_code == 422


def test_missing_key_not_fake_success(client):
    r = client.post("/api/search", json={"product":"cotton"})
    assert r.status_code == 502
    assert "anahtar" in r.json()["detail"]
    assert client.get("/api/history").json()["history"] == []


def test_query_localization():
    q = build_query(SearchRequest(product="müslin nevresim", city="Lyon", language="fr"))
    assert q == "linge de lit mousseline boutique Lyon"
    assert "muslin bedding" in build_query(SearchRequest(product="müslin nevresim", language="en"))


def test_crud_duplicate_and_optimistic_lock(client):
    created = client.post("/api/leads", json=example())
    assert created.status_code == 201
    row = created.json()
    assert row["version"] == 1
    assert client.post("/api/leads", json=example(website="https://www.ornek.example/contact")).status_code == 409
    updated = client.put(f'/api/leads/{row["id"]}', json={"version":1,"lead":example(status="contacted",phone="+33 123 456 789")})
    assert updated.status_code == 200 and updated.json()["version"] == 2
    assert client.put(f'/api/leads/{row["id"]}', json={"version":1,"lead":example()}).status_code == 409
    assert client.delete(f'/api/leads/{row["id"]}?version=1').status_code == 409
    assert client.delete(f'/api/leads/{row["id"]}?version=2').status_code == 200
    assert client.get("/api/leads").json()["leads"] == []


def test_legacy_example_creation_rejected(client):
    assert client.post("/api/leads", json=example(is_demo=True)).status_code == 422
    assert client.post("/api/leads", json=example()).status_code == 201


@pytest.mark.parametrize("field,value", [("website","javascript:alert(1)"),("website","https://user:pass@x.com"),("website","https://x.com:22"),("instagram","data:text/html,bad"),("email","not-an-email"),("fit","yes"),("status","done"),("name","")])
def test_lead_validation(client, field, value):
    assert client.post("/api/leads", json=example(**{field:value})).status_code == 422


def test_csv_formula_injection_and_unicode(client):
    client.post("/api/leads", json=example(name="=HYPERLINK(1)", notes="\t=cmd", phone="+33123456789"))
    result = client.get("/api/export")
    assert result.content.startswith(b"\xef\xbb\xbf")
    rows = list(csv.reader(io.StringIO(result.content.decode("utf-8-sig")), delimiter=";"))
    assert rows[1][0].startswith("'=")
    assert rows[1][5].startswith("'+")
    assert rows[1][13].startswith("'=")
    assert "müslin nevresim" in rows[1]


def test_backup_roundtrip_and_atomic_validation(client, tmp_path):
    client.post("/api/leads", json=example(notes="Türkçe: ı İ ş Ş ğ ü ö ç", sources=[{"url":"https://ornek.example/contact","field":"email","value":"hello@ornek.example"}]))
    backup = client.get("/api/backup").json()
    dest = TestClient(create_app(Settings(tmp_path / "restored")), headers=HEADERS)
    assert dest.post("/api/restore", json=backup).json() == {"added":1,"skipped":0}
    assert dest.post("/api/restore", json=backup).json() == {"added":0,"skipped":1}
    restored = dest.get("/api/leads").json()["leads"][0]
    assert restored["notes"] == backup["leads"][0]["notes"]
    assert restored["sources"] == backup["leads"][0]["sources"]
    invalid = {"format":"firma-atlas-v1","leads":[example(website="https://second.example"),example(name="")]}
    assert dest.post("/api/restore", json=invalid).status_code == 422
    assert len(dest.get("/api/leads").json()["leads"]) == 1


def test_persistence_between_app_instances(tmp_path):
    s = Settings(tmp_path)
    one = TestClient(create_app(s), headers=HEADERS)
    one.post("/api/leads", json=example())
    two = TestClient(create_app(s), headers=HEADERS)
    assert len(two.get("/api/leads").json()["leads"]) == 1


def test_csrf_and_host_rejection(client):
    assert client.post("/api/leads", json=example(), headers={"X-App-Request":""}).status_code == 403
    assert client.post("/api/leads", json=example(), headers={"Origin":"https://evil.example"}).status_code == 403
    assert client.get("/api/leads", headers={"Host":"evil.example"}).status_code == 403
    assert client.post("/api/leads", json=example(), headers={"content-length":"20000001"}).status_code == 413


def test_cloud_fails_closed(tmp_path):
    with pytest.raises(RuntimeError):
        create_app(Settings(tmp_path, cloud=True))
    with pytest.raises(RuntimeError):
        create_app(Settings(tmp_path, cloud=True, database_url="postgresql://example"))


def test_cloud_auth_cookie_and_expiry(tmp_path):
    s = Settings(tmp_path, cloud=True, database_url="postgresql://unused", password="strong-test-password", secret="s" * 40)
    app = create_app(s)
    # Auth uses production settings; database replaced with local test storage.
    app.state.store.pg = False
    c = TestClient(app, headers=HEADERS, base_url="https://testserver")
    assert c.get("/api/leads").status_code == 401
    assert c.get("/api/session").json()["authenticated"] is False
    assert c.post("/api/login", json={"password":"wrong"}).status_code == 401
    login = c.post("/api/login", json={"password":s.password})
    assert login.status_code == 200
    assert "HttpOnly" in login.headers["set-cookie"] and "Secure" in login.headers["set-cookie"]
    assert c.get("/api/leads").status_code == 200
    assert c.put("/api/settings", json={"provider":"brave","key":"secret-key"}).status_code == 403
    assert c.post("/api/logout").status_code == 200
    assert c.get("/api/leads").status_code == 401
    c.cookies.set("firma_session", session_token(s, int(time.time())-1))
    assert c.get("/api/leads").status_code == 401


def test_rate_limit_and_concurrent_duplicates(tmp_path):
    store = Store(Settings(tmp_path))
    assert store.rate_limit("999999:search", 2)
    assert store.rate_limit("999999:search", 2)
    assert not store.rate_limit("999999:search", 2)
    def write(_):
        try:
            store.save(Lead(**example()))
            return True
        except Conflict:
            return False
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        assert sum(pool.map(write, range(8))) == 1
    assert len(store.list()) == 1


@pytest.mark.parametrize("ip", ["127.0.0.1","10.1.2.3","172.16.0.1","192.168.1.1","169.254.169.254","::1","fc00::1","::ffff:127.0.0.1","0.0.0.0"])
def test_ssrf_private_addresses(ip):
    with patch("socket.getaddrinfo", return_value=[(socket.AF_INET,socket.SOCK_STREAM,6,"",(ip,443))]):
        with pytest.raises(ServiceError): resolve_public("public.test",443)


def test_mixed_dns_and_redirect_blocked():
    with patch("socket.getaddrinfo", return_value=[(2,1,6,"",("8.8.8.8",443)),(2,1,6,"",("127.0.0.1",443))]):
        with pytest.raises(ServiceError): resolve_public("public.test",443)
    with pytest.raises(ServiceError): fetch("https://other.test/",time.monotonic()+3,"expected.test")


def test_extract_published_contacts_and_sources():
    html = '''<html><script>secret@not-contact.test</script><body><h1>Müslin nevresim</h1><footer><a href="mailto:hello@shop.test?subject=hello">Mail</a><a href="tel:+33123456789">Call</a><a href="https://wa.me/33123456789">WhatsApp</a><a href="https://www.instagram.com/shop/">Instagram</a><a href="/contact">Contact</a></footer></body></html>'''
    data, links = extract(html,"https://shop.test/","müslin nevresim")
    assert data["email"] == "hello@shop.test"
    assert data["phone"] == "+33123456789"
    assert data["whatsapp"] == "+33123456789"
    assert data["instagram"] == "https://www.instagram.com/shop/"
    assert data["fit"] == "possible"
    assert len(data["sources"]) == 5
    assert links == ["https://shop.test/contact"]
    assert "contact_person" not in data


def test_empty_site_no_invented_contacts():
    data, links = extract("<h1>Hello</h1>","https://shop.test/","müslin")
    assert data["email"] == data["phone"] == data["whatsapp"] == data["instagram"] == ""
    assert data["fit"] == "unknown" and data["sources"] == []


def test_robot_denial_and_demo_enrich(client):
    with patch("firma.enrich.fetch", return_value=(200,"User-agent: *\nDisallow: /","https://shop.test/robots.txt","text/plain")) as mocked:
        result = client.post("/api/enrich", json={"url":"https://shop.test/"})
        assert result.status_code == 200 and result.json()["warnings"]
        assert mocked.call_count == 1
    assert client.post("/api/enrich", json={"url":"https://firma-1.example/"}).status_code == 502


@pytest.mark.parametrize("provider", ["serpapi", "brave"])
def test_provider_adapter_and_dedup(provider, tmp_path):
    raw = [{"title":"<b>Shop boutique</b>","link":"https://shop.test/a","url":"https://shop.test/a","snippet":"Linge de lit mousseline","description":"Linge de lit mousseline"},{"title":"Shop 2","link":"https://www.shop.test/b","url":"https://www.shop.test/b"},{"title":"Unsafe","link":"javascript:alert(1)","url":"javascript:alert(1)"}]
    payload = {"organic_results":raw} if provider == "serpapi" else {"web":{"results":raw}}
    response = httpx.Response(200,json=payload,request=httpx.Request("GET","https://service.test"))
    site = {"data":{},"pages":[{"url":"https://shop.test/a","title":"Shop boutique","text":"Boutique linge de lit mousseline. Ajouter au panier. Livraison."}]}
    with patch("httpx.Client.get", return_value=response) as call, patch("firma.search.probe_site",return_value=site):
        result = search(SearchRequest(product="müslin nevresim",city="Lyon"),Settings(tmp_path,provider=provider,api_key="test-secret"))
        assert len(result["results"]) == 1
        assert result["results"][0]["name"] == "Shop boutique"
        assert result["results"][0]["fit"] == "possible"
        assert result["results"][0]["city"] == "" and result["results"][0]["target_city"] == "Lyon"
        assert "Lyon" in call.call_args.kwargs["params"]["q"]


@pytest.mark.parametrize("status", [401,403,429,500])
def test_provider_errors_do_not_leak_keys(tmp_path,status):
    response = httpx.Response(status,json={},request=httpx.Request("GET","https://service.test?api_key=SECRET"))
    with patch("httpx.Client.get", return_value=response), pytest.raises(ServiceError) as e:
        search(SearchRequest(product="cotton"), Settings(tmp_path,api_key="SECRET"))
    assert "SECRET" not in str(e.value)


@pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI")
def test_windows_encrypted_settings(client, tmp_path):
    r = client.put("/api/settings",json={"provider":"brave","key":"private-test-key"})
    assert r.status_code == 200
    assert "private-test-key" not in r.text
    content = (tmp_path / "search-settings.json").read_text()
    assert "private-test-key" not in content
    restarted = create_app(Settings(tmp_path))
    assert restarted.state.settings.api_key == "private-test-key"


def test_social_domain_dedupe():
    assert domain_key("https://www.instagram.com/shop_one/") != domain_key("https://instagram.com/shop_two/")


def test_enrich_two_pages_and_partial_failure(client):
    home = '<h1>Linge de lit mousseline</h1><a href="mailto:hello@shop.test">Email</a><a href="/contact">Contact</a>'
    contact = '<a href="tel:+33123456789">Call</a>'
    pages = [(404,"","https://shop.test/robots.txt","text/plain"),(200,home,"https://shop.test/","text/html"),(200,contact,"https://shop.test/contact","text/html")]
    with patch("firma.enrich.fetch", side_effect=pages):
        result = client.post("/api/enrich",json={"url":"https://shop.test/","product":"müslin nevresim"}).json()
        assert result["data"]["email"] == "hello@shop.test"
        assert result["data"]["phone"] == "+33123456789"
        assert result["data"]["fit"] == "possible"
        assert len(result["checked"]) == 2
    with patch("firma.enrich.fetch", side_effect=pages[:2] + [ServiceError("Offline")]):
        result = client.post("/api/enrich",json={"url":"https://shop.test/"}).json()
        assert result["data"]["email"] == "hello@shop.test"
        assert result["warnings"]


def test_whitespace_api_key_rejected(client):
    assert client.put("/api/settings",json={"provider":"brave","key":"         "}).status_code == 422


def test_robots_checked_before_request():
    from urllib.robotparser import RobotFileParser
    robot = RobotFileParser()
    robot.parse(["User-agent: *", "Disallow: /private"])
    with patch("firma.enrich.resolve_public") as resolver, pytest.raises(ServiceError):
        fetch("https://shop.test/private",time.monotonic()+2,"shop.test",robot)
    resolver.assert_not_called()
