"""Bounded public-page extraction with DNS pinning and robots.txt checks."""
import http.client
import ipaddress
import re
import socket
import ssl
import time
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup
import certifi

from .models import public_url
from .search import ServiceError, normalized
from .store import now

AGENT = "FirmaAtlasBot"
MAX_BYTES = 1_000_000


def resolve_public(host, port):
    if host.lower() == "localhost" or host.endswith((".local", ".internal", ".example")):
        raise ServiceError("Yalnızca herkese açık gerçek web siteleri incelenebilir.")
    addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    if not addresses:
        raise ServiceError("Site adresi çözümlenemedi.")
    for entry in addresses:
        ip = ipaddress.ip_address(entry[4][0])
        if not ip.is_global or (getattr(ip, "ipv4_mapped", None) and not ip.ipv4_mapped.is_global):
            raise ServiceError("Yerel ve özel ağ adreslerine erişim engellendi.")
    return addresses[0][4][0]


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, address, port, timeout):
        context = ssl.create_default_context()
        context.load_verify_locations(cafile=certifi.where())
        super().__init__(host, port, timeout=timeout, context=context)
        self.address = address

    def connect(self):
        sock = socket.create_connection((self.address, self.port), self.timeout)
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except Exception:
            sock.close()
            raise


def fetch(url, deadline, allowed_host=None, robot=None):
    for _ in range(3):
        url = public_url(url)
        p = urlsplit(url)
        if allowed_host and p.hostname.lower().removeprefix("www.") != allowed_host:
            raise ServiceError("Başka bir alan adına yönlendirme atlandı.")
        if robot and not robot.can_fetch(AGENT, url):
            raise ServiceError("Site bu sayfanın otomatik okunmasına izin vermiyor.")
        if time.monotonic() >= deadline:
            raise ServiceError("Site incelemesi zaman aşımına uğradı.")
        port = p.port or (443 if p.scheme == "https" else 80)
        address = resolve_public(p.hostname, port)
        timeout = max(0.2, min(5, deadline - time.monotonic()))
        conn = PinnedHTTPS(p.hostname, address, port, timeout) if p.scheme == "https" else http.client.HTTPConnection(address, port, timeout=timeout)
        try:
            conn.request("GET", (p.path or "/") + ("?" + p.query if p.query else ""), headers={"Host": p.netloc, "User-Agent": AGENT + "/1.0", "Accept": "text/html,text/plain", "Accept-Encoding": "identity"})
            resp = conn.getresponse()
            if resp.status in (301, 302, 303, 307, 308):
                url = urljoin(url, resp.getheader("Location", ""))
                continue
            body = bytearray()
            while len(body) <= MAX_BYTES:
                if time.monotonic() >= deadline:
                    raise ServiceError("Site incelemesi zaman aşımına uğradı.")
                chunk = resp.read1(min(65536, MAX_BYTES + 1 - len(body)))
                if not chunk:
                    break
                body.extend(chunk)
            if len(body) > MAX_BYTES:
                raise ServiceError("Sayfa güvenli inceleme boyutunu aşıyor.")
            content_type = resp.getheader("Content-Type", "")
            charset = re.search(r"charset=([\w-]+)", content_type)
            encoding = charset.group(1) if charset else "utf-8"
            try:
                text = body.decode(encoding, errors="replace")
            except LookupError:
                text = body.decode("utf-8", errors="replace")
            return resp.status, text, url, content_type
        finally:
            conn.close()
    raise ServiceError("Site çok fazla yönlendirme yapıyor.")


def extract(html, url, product=""):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer"]):
        # Footer contains business contacts; retain it.
        if tag.name != "footer":
            tag.decompose()
    text = soup.get_text(" ", strip=True)
    data = {"email": "", "phone": "", "whatsapp": "", "instagram": "", "fit": "unknown", "evidence": "", "sources": []}
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.lower().startswith("mailto:") and not data["email"]:
            email = href[7:].split("?")[0].strip()
            if re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", email):
                data["email"] = email
        if href.lower().startswith("tel:") and not data["phone"]:
            data["phone"] = re.sub(r"[^\d+ ()-]", "", href[4:])[:80]
        absolute = urljoin(url, href)
        parsed = urlsplit(absolute)
        host = (parsed.hostname or "").lower().removeprefix("www.")
        if host == "instagram.com" and parsed.path.strip("/") and not parsed.path.startswith(("/p/", "/reel/", "/explore/")):
            data["instagram"] = absolute
        if host == "wa.me":
            number = parsed.path.strip("/")
            if re.fullmatch(r"\d{7,15}", number):
                data["whatsapp"] = "+" + number
        if host == "api.whatsapp.com":
            from urllib.parse import parse_qs
            number = parse_qs(parsed.query).get("phone", [""])[0]
            if re.fullmatch(r"\+?\d{7,15}", number):
                data["whatsapp"] = "+" + number.lstrip("+")
        if any(t in normalized(a.get_text(" ") + " " + parsed.path) for t in ("contact", "iletisim", "kontakt", "contatti", "about")):
            if parsed.scheme in ("http", "https"):
                links.append(absolute)
    if not data["email"]:
        emails = re.findall(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
        data["email"] = next((x for x in emails if not x.endswith((".png", ".jpg", ".webp"))), "")
    if not data["phone"]:
        numbers = re.findall(r"\+\d[\d\s().-]{7,22}\d", text)
        data["phone"] = next((n.strip() for n in numbers if 8 <= len(re.sub(r"\D", "", n)) <= 15), "")
    terms = [t for t in normalized(product).split() if len(t) > 2]
    ntext = normalized(text)
    localized = []
    if "muslin" in normalized(product) and "nevresim" in normalized(product):
        localized = [("mousseline", "lit"), ("gaze de coton", "housse"), ("muslin", "bedding"), ("musselin", "bett")]
    matched = terms if terms and all(t in ntext for t in terms) else next((list(group) for group in localized if all(t in ntext for t in group)), [])
    if matched:
        data["fit"] = "possible"
        pos = ntext.find(matched[0])
        data["evidence"] = text[max(0, pos - 100):pos + 350]
    for field in ("email", "phone", "whatsapp", "instagram", "evidence"):
        if data[field]:
            data["sources"].append({"field": field, "value": data[field], "url": url, "checked_at": now()})
    return data, links


def enrich(url, product, budget=22, include_pages=False):
    deadline = time.monotonic() + budget
    host = urlsplit(url).hostname.lower().removeprefix("www.")
    base = f"{urlsplit(url).scheme}://{urlsplit(url).netloc}"
    try:
        status, body, _, _ = fetch(base + "/robots.txt", deadline, host)
        if status not in (200, 404, 410):
            raise ServiceError("Sitenin tarama izni doğrulanamadı. Bilgileri elle ekleyebilirsiniz.")
        robot = RobotFileParser()
        robot.parse(body.splitlines() if status == 200 else [])
        warnings, data = [], {"email": "", "phone": "", "whatsapp": "", "instagram": "", "fit": "unknown", "evidence": "", "sources": []}
        pending, checked, pages = [url], [], []
        while pending and len(checked) < 2:
            current = pending.pop(0)
            if not robot.can_fetch(AGENT, current):
                warnings.append("Site bu sayfanın otomatik okunmasına izin vermiyor.")
                continue
            try:
                status, body, final, mime = fetch(current, deadline, host, robot)
            except (ServiceError, OSError, ValueError, http.client.HTTPException):
                if not checked:
                    raise
                warnings.append("İletişim sayfası okunamadı; ilk sayfada bulunan bilgiler korundu.")
                break
            checked.append(final)
            if status != 200 or "text/html" not in mime.lower():
                warnings.append("Bir sayfa okunamadı; korumalı veya HTML biçiminde değil.")
                continue
            if not robot.can_fetch(AGENT, final):
                warnings.append("Yönlendirilen sayfa taramaya kapalı.")
                continue
            page = BeautifulSoup(body, "html.parser")
            for tag in page(["script","style","noscript"]):
                tag.decompose()
            pages.append({"url":final,"title":page.title.get_text(" ",strip=True) if page.title else "","heading":" ".join(h.get_text(" ",strip=True) for h in page.find_all("h1")[:3]),"text":page.get_text("\n",strip=True)[:45000]})
            extracted, links = extract(body, final, product)
            for field in ("email", "phone", "whatsapp", "instagram", "evidence"):
                if extracted[field] and not data[field]:
                    data[field] = extracted[field]
            if extracted["fit"] == "possible":
                data["fit"] = "possible"
            data["sources"].extend(extracted["sources"])
            for link in links:
                if urlsplit(link).hostname and urlsplit(link).hostname.lower().removeprefix("www.") == host and link not in checked and link not in pending:
                    pending.append(link)
        result = {"data": data, "warnings": warnings, "checked": checked}
        if include_pages:
            result["pages"] = pages
        return result
    except ServiceError:
        raise
    except (OSError, ValueError, http.client.HTTPException) as exc:
        raise ServiceError("Siteye ulaşılamadı veya site otomatik incelemeyi engelliyor. Bilgileri elle ekleyebilirsiniz.") from exc
