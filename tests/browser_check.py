"""Isolated Edge integration checks. Fake upstream auth/search; real cookie, API, UI and PDFs. Never deploy this harness."""
import json
import os
import socket
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import uvicorn
from playwright.sync_api import sync_playwright, expect
from firma.app import create_app
from firma.config import Settings


def run():
    stamp = str(int(time.time()))
    output = Path("test-results")
    output.mkdir(exist_ok=True)
    import importlib
    from retail_fixtures import fetch_results, probe_site
    search_module=importlib.import_module("firma.search")
    search_module.fetch_results=fetch_results
    search_module.probe_site=probe_site
    from firma.store import Store
    from firma.site_auth import AdminGateway, COOKIE
    import firma.site_auth as site_auth
    from unittest.mock import AsyncMock
    from starlette.staticfiles import StaticFiles
    from starlette.responses import JSONResponse, HTMLResponse
    from test_site_integration import sealed
    import base64
    key = os.urandom(32)
    os.environ['ADMIN_SESSION_KEY'] = base64.b64encode(key).decode()
    site_auth.verify_admin = AsyncMock(return_value=True)
    app = create_app(Settings(output / ('browser-data-'+stamp),cloud=True,api_key='fixture-key'),
                     site_store=Store(Settings(output / ('browser-data-'+stamp))))
    gateway = AdminGateway(app)
    static = StaticFiles(directory='admin/butik',html=True)
    csp = next(x for x in json.loads(Path('vercel.json').read_text())['headers'] if x['source']=='/admin(.*)')['headers']
    async def harness(scope, receive, send):
        if scope['type'] != 'http': return await app(scope,receive,send)
        path = scope['path']
        if path == '/api/admin':
            value = {'authenticated':True,'csrf':'csrf-test'} if b'action=status' in scope.get('query_string',b'') else {'ok':True}
            return await JSONResponse(value)(scope,receive,send)
        if path == '/admin/': return await HTMLResponse('<h1>TVS Yönetici girişi</h1>')(scope,receive,send)
        if path.startswith('/admin/butik/'):
            async def secured(message):
                if message['type']=='http.response.start':
                    message['headers'] += [(h['key'].lower().encode(),h['value'].encode()) for h in csp]
                await send(message)
            return await static(dict(scope,path=path[len('/admin/butik'):],root_path=''),receive,secured)
        return await gateway(scope,receive,send)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    site_auth.ORIGIN = f"http://127.0.0.1:{port}"
    server = uvicorn.Server(uvicorn.Config(harness, log_level="warning"))
    thread = threading.Thread(target=server.run, kwargs={"sockets":[sock]}, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started: break
        time.sleep(.05)
    errors, results = [], []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            context = browser.new_context(viewport={"width":1440,"height":1050}, accept_downloads=True,extra_http_headers={"Cookie":COOKIE+"="+sealed(key)})
            page = context.new_page()
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"http://127.0.0.1:{port}/admin/butik/")
            expect(page.locator("#connection-pill")).to_contain_text("Canlı arama bağlı")
            page.screenshot(path=str(output / "01-home.png"),full_page=True)
            results.append("Initial page and settings load")
            page.fill("#search-query","müslin nevresim")
            page.fill("#search-city","Lyon")
            page.click("#search-button")
            expect(page.locator("#search-results tbody tr")).to_have_count(2)
            expect(page.locator("#search-summary")).to_contain_text("2 alıcı adayı")
            assert page.locator("#demo-toggle").count()==0
            expect(page.locator("#excluded-title")).to_contain_text("5 sonuç")
            page.screenshot(path=str(output / "02-search.png"),full_page=True)
            results.append("Product retail screening; directories, chains, suppliers and platforms excluded")
            page.locator('[data-action="save-result"]').first.click()
            expect(page.locator("#stat-total")).to_have_text("1")
            expect(page.locator('[data-action="save-result"]').first).to_be_disabled()
            results.append("Save result and duplicate UI prevention")
            page.check("#select-all")
            page.click("#save-selected")
            expect(page.locator("#stat-total")).to_have_text("2")
            results.append("Bulk save")
            page.locator('.nav-item[data-view="saved"]').click()
            expect(page.locator("#saved-results tbody tr")).to_have_count(2)
            page.locator('[data-action="edit"]').first.click()
            page.locator('[name="email"]').fill("hello@fixture.example")
            page.locator('[name="phone"]').fill("+33123456789")
            page.locator('[name="whatsapp"]').fill("+33123456789")
            page.locator('[name="contact_person"]').fill("Satın alma ekibi")
            page.locator('[name="status"]').select_option("contacted")
            page.locator('[name="fit"]').select_option("confirmed")
            page.locator('[name="notes"]').fill("İlk görüşme yapıldı. Örnek koleksiyon gönderilecek.")
            page.locator('[name="evidence_tr"]').fill("Türkçe açıklama: ı İ ş Ş ğ Ğ ü Ü ö Ö ç Ç.")
            page.screenshot(path=str(output / "03-firma-card.png"),full_page=True)
            page.click("#save-lead")
            expect(page.locator("#lead-dialog")).not_to_be_visible()
            expect(page.locator("#stat-contacted")).to_have_text("1")
            page.select_option("#filter-status","contacted")
            expect(page.locator("#saved-results tbody tr")).to_have_count(1)
            page.fill("#filter-query","does-not-exist")
            expect(page.locator("#saved-results")).to_contain_text("Filtrelere uygun firma yok")
            page.fill("#filter-query","")
            page.select_option("#filter-status","")
            results.append("Edit all contact fields, status, fit, notes; filtering")
            with page.expect_download() as download:
                page.click("#export-csv")
            download.value.save_as(str(output / "browser-export.csv"))
            assert "Satın alma ekibi" in (output / "browser-export.csv").read_text(encoding="utf-8-sig")
            results.append("CSV file download and content")
            page.select_option("#filter-status","contacted")
            with page.expect_download() as pdf_download:
                page.click("#export-pdf")
            pdf_download.value.save_as(str(output / "browser-export.pdf"))
            from pypdf import PdfReader
            pdf_text=''.join(p.extract_text() for p in PdfReader(output / "browser-export.pdf").pages)
            assert "Türkçe açıklama: ı İ ş Ş ğ Ğ ü Ü ö Ö ç Ç." in pdf_text
            assert "1 firma" in pdf_text
            page.select_option("#filter-status","")
            results.append("Filtered saved firms PDF download, persisted Turkish translation and characters")
            page.click("#add-saved")
            page.locator('[name="name"]').fill("Elle Eklenen Firma")
            page.locator('[name="website"]').fill("https://manual.example")
            page.locator('[name="city"]').fill("İstanbul")
            page.click("#save-lead")
            expect(page.locator("#saved-results tbody tr")).to_have_count(3)
            page.fill("#filter-query","istanbul")
            expect(page.locator("#saved-results tbody tr")).to_have_count(1)
            page.locator('[data-action="edit"]').first.click()
            page.locator('[name="notes"]').fill("Unsaved")
            page.click("#close-drawer")
            expect(page.locator("#confirm-dialog")).to_be_visible()
            page.click("#confirm-yes")
            expect(page.locator("#lead-dialog")).not_to_be_visible()
            page.locator('[data-action="edit"]').first.click()
            expect(page.locator('[name="notes"]')).to_have_value("")
            page.click("#delete-lead")
            page.click("#confirm-yes")
            expect(page.locator("#lead-dialog")).not_to_be_visible()
            page.fill("#filter-query","")
            expect(page.locator("#saved-results tbody tr")).to_have_count(2)
            results.append("Manual entry, Turkish case folding, unsaved edit guard, delete")
            page.locator('.nav-item[data-view="settings"]').click()
            with page.expect_download() as download:
                page.click("#backup-button")
            backup = output / "browser-backup.json"
            download.value.save_as(str(backup))
            page.set_input_files("#restore-file", str(backup))
            page.click("#confirm-yes")
            expect(page.locator("#toast")).to_contain_text("0 firma eklendi, 2 tekrar veya eski örnek kayıt atlandı")
            results.append("Backup download and duplicate-safe restore")
            page.screenshot(path=str(output / "04-settings.png"),full_page=True)
            page.locator('.nav-item[data-view="history"]').click()
            expect(page.locator(".history-item")).to_have_count(1)
            page.locator('[data-action="repeat"]').first.click()
            expect(page.locator("#search-results tbody tr")).to_have_count(2)
            results.append("History and repeat search")
            page.locator('[data-mode="city"]').click()
            page.fill("#search-query", "")
            page.click("#search-button")
            expect(page.locator("#search-results tbody tr")).to_have_count(2)
            page.locator('[data-mode="general"]').click()
            page.fill("#search-query","Maison")
            page.fill("#search-city","")
            page.click("#search-button")
            expect(page.locator("#search-results tbody tr")).to_have_count(1)
            results.append("City and general search flows")
            page.locator('.nav-item[data-view="prospects"]').click()
            expect(page.locator("#search-query")).not_to_be_visible()
            page.click("#search-button")
            expect(page.locator("#search-results tbody tr")).to_have_count(2)
            expect(page.locator("#search-summary")).to_contain_text("3 servis isteği")
            expect(page.locator("#search-results")).to_contain_text("Tedarikçi başvuru ifadesi")
            page.screenshot(path=str(output / "06-prospects.png"),full_page=True)
            page.click("#search-button")
            expect(page.locator("#search-summary")).to_contain_text("Önbellek")
            results.append("Keyword-free prospects, supplier evidence, ranking and cache")
            app.state.settings.api_key=""
            page.click("#search-button")
            expect(page.locator("#search-error")).to_contain_text("anahtar")
            results.append("Live search without credentials shows actionable error")
            page.reload()
            expect(page.locator("#stat-total")).to_have_text("2")
            results.append("Persisted records survive page reload")
            page.set_viewport_size({"width":390,"height":844})
            page.screenshot(path=str(output / "05-mobile.png"),full_page=True)
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
            results.append("390px mobile layout without horizontal overflow")
            assert not errors, errors
            results.append("No uncaught browser JavaScript errors")
            page.set_viewport_size({"width":1440,"height":1050})
            page.click('#logout')
            expect(page).to_have_url(f'http://127.0.0.1:{port}/admin/')
            results.append('Existing admin logout and return navigation')
            context.set_extra_http_headers({})
            page.goto(f'http://127.0.0.1:{port}/admin/butik/')
            expect(page).to_have_url(f'http://127.0.0.1:{port}/admin/')
            results.append('Unauthenticated boutique requests redirect to admin login')
            browser.close()
    finally:
        server.should_exit = True
        thread.join(5)
        sock.close()
        (output / "browser-report.json").write_text(json.dumps({"passed":results,"errors":errors},ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"passed":len(results),"checks":results,"errors":errors},ensure_ascii=True,indent=2))


if __name__ == "__main__":
    run()
