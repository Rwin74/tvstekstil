"""Explainable retail-buyer screening; scores are priorities, not probabilities."""
import re
import unicodedata
from urllib.parse import urlsplit, unquote


def normalized(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text.lower().replace("ı", "i")) if not unicodedata.combining(c))


LANGS = ["tr", "fr", "en", "de", "it", "es", "nl"]
VOCAB = [
    ("müslin nevresim", "linge de lit mousseline", "muslin bedding", "Musselin Bettwäsche", "biancheria letto mussola", "ropa de cama muselina", "mousseline beddengoed"),
    ("kadın giyim", "vêtements femme", "women clothing", "Damenmode", "abbigliamento donna", "ropa mujer", "dameskleding"),
    ("erkek giyim", "vêtements homme", "men clothing", "Herrenmode", "abbigliamento uomo", "ropa hombre", "herenkleding"),
    ("bebek giyim", "vêtements bébé", "baby clothing", "Babykleidung", "abbigliamento neonato", "ropa bebé", "babykleding"),
    ("çocuk giyim", "vêtements enfant", "children clothing", "Kinderkleidung", "abbigliamento bambini", "ropa niños", "kinderkleding"),
    ("ev tekstili", "linge de maison", "home textiles", "Heimtextilien", "tessili casa", "textiles hogar", "woontextiel"),
    ("nevresim", "linge de lit", "bedding", "Bettwäsche", "biancheria letto", "ropa de cama", "beddengoed"),
    ("elbise", "robe", "dress", "Kleid", "abito", "vestido", "jurk"),
    ("gömlek", "chemise", "shirt", "Hemd", "camicia", "camisa", "overhemd"),
    ("pantolon", "pantalon", "trousers", "Hose", "pantaloni", "pantalones", "broek"),
    ("tişört", "t-shirt", "t-shirt", "T-Shirt", "t-shirt", "camiseta", "t-shirt"),
    ("havlu", "serviette", "towel", "Handtuch", "asciugamano", "toalla", "handdoek"),
    ("bornoz", "peignoir", "bathrobe", "Bademantel", "accappatoio", "albornoz", "badjas"),
    ("pijama", "pyjama", "pyjamas", "Schlafanzug", "pigiama", "pijama", "pyjama"),
    ("çorap", "chaussettes", "socks", "Socken", "calze", "calcetines", "sokken"),
    ("iç giyim", "lingerie", "underwear", "Unterwäsche", "intimo", "ropa interior", "ondergoed"),
    ("şal", "écharpe", "scarf", "Schal", "sciarpa", "bufanda", "sjaal"),
    ("eşarp", "foulard", "headscarf", "Kopftuch", "foulard", "pañuelo", "hoofddoek"),
    ("battaniye", "couverture", "blanket", "Decke", "coperta", "manta", "deken"),
    ("perde", "rideau", "curtain", "Vorhang", "tenda", "cortina", "gordijn"),
    ("çanta", "sac", "bag", "Tasche", "borsa", "bolso", "tas"),
    ("ayakkabı", "chaussures", "shoes", "Schuhe", "scarpe", "zapatos", "schoenen"),
    ("keten", "lin", "linen", "Leinen", "lino", "lino", "linnen"),
    ("pamuk", "coton", "cotton", "Baumwolle", "cotone", "algodón", "katoen"),
    ("müslin", "mousseline", "muslin", "Musselin", "mussola", "muselina", "mousseline"),
]


def product_terms(product, language):
    result = normalized(product)
    replacements = {}
    for i, row in enumerate(VOCAB):
        term = normalized(row[0])
        if re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", result):
            marker = f"ZZ{i}ZZ"
            result = re.sub(r"(?<!\w)" + re.escape(term) + r"(?!\w)", marker, result)
            replacements[marker] = row[LANGS.index(language)]
    if not replacements:
        return product
    for marker, value in replacements.items():
        result = result.replace(marker, value)
    return result


def product_groups(product):
    remaining = normalized(product)
    groups = []
    for row in VOCAB[1:]:
        variants = sorted({normalized(x) for x in row}, key=len, reverse=True)
        found = next((v for v in variants if re.search(r"(?<!\w)" + re.escape(v) + r"(?!\w)", remaining)), None)
        if found:
            if row[0] == "müslin":
                variants.append("gaze de coton")
            if row[0] == "nevresim":
                variants.extend(["housse de couette", "duvet cover"])
            groups.append(variants)
            remaining = remaining.replace(found, " ")
    stop = {"ve", "and", "de", "la", "le", "the", "icin", "ile", "satis"}
    groups.extend([[word] for word in remaining.split() if len(word) >= 3 and word not in stop])
    return groups


DIRECTORIES = {"pagesjaunes.fr", "mappy.com", "kompass.com", "europages.com", "europages.fr", "tripadvisor.com", "tripadvisor.fr", "yelp.com", "yelp.fr", "tupalo.fr", "cylex.fr", "hoodspot.fr", "societe.com", "pappers.fr", "verif.com", "google.com", "bing.com", "annuaire.com", "118000.fr", "petitfute.com", "lyon-france.com"}
DIRECTORIES.update({"magasin.tel","toolyon.com","guideliterie.com","matelasinfo.com","acheter-ou.fr","justacote.com"})
DIRECTORIES.update({"enuygun.com", "neredekal.com", "gezimanya.com", "yandex.com", "yandex.com.tr", "foursquare.com", "yellowpages.com", "sikayetvar.com"})
PLATFORMS = {"facebook.com", "instagram.com", "pinterest.com", "youtube.com", "tiktok.com", "linkedin.com", "amazon.com", "amazon.fr", "amazon.de", "amazon.com.tr", "etsy.com", "ebay.com", "ebay.fr", "alibaba.com", "aliexpress.com", "trendyol.com", "hepsiburada.com", "temu.com", "shein.com", "cdiscount.com", "zalando.fr", "zalando.com", "wikipedia.org"}
CHAINS = {"maisondelaliterie.fr", "carreblanc.com", "ikea.com", "hm.com", "zara.com", "kiabi.com", "jysk.fr", "jysk.com", "maisonsdumonde.com", "primark.com", "lcwaikiki.com", "defacto.com", "mango.com", "boyner.com.tr", "laredoute.fr", "gifi.fr", "action.com", "but.fr", "conforama.fr", "dunelm.com"}


def host_in(host, domains):
    return any(host == x or host.endswith("." + x) for x in domains)


def editorial(text):
    text = normalized(text)
    patterns = (
        r"\b(en iyi|en populer|en guzel|gidilmesi gereken|gezilecek|alisveris rehberi|butik rehberi)\b",
        r"\b(best|top|meilleur\w*)\b.{0,70}\b(boutiques?|shops?|stores?|magasins?|outlets?)\b",
        r"\b\d+\s+(?:\w+\s+){0,3}(butik|magaza|boutique|shop|store)\w*\b",
        r"\b(butikler|magazalar|boutiques|shops|stores)\b.{0,35}\b(listesi|rehberi|directory|guide|list)\b",
    )
    return any(re.search(p, text) for p in patterns)


def prefilter(url, title="", snippet=""):
    p = urlsplit(url)
    host = (p.hostname or "").lower().removeprefix("www.")
    if p.scheme not in ("http", "https") or not host:
        return "Geçersiz web adresi"
    if host_in(host, DIRECTORIES):
        return "Firma rehberi / listeleme sitesi"
    if host_in(host, PLATFORMS):
        return "Pazar yeri / sosyal platform"
    if host_in(host, CHAINS):
        return "Büyük mağaza zinciri"
    if host_in(host, {"blancdesvosges.fr", "blancdesvosges.com"}):
        return "Üretici markanın kendi mağazası"
    text = normalized(title + " " + snippet)
    if re.search(r"/(blog|blogs|post|posts|actualites|news|article|articles|magazine|annuaire|directory|bilgi|rehber|gezi|haber|liste|guides?)(/|$)", unquote(p.path).lower()):
        return "Editoryal içerik / firma listesi"
    if editorial(title):
        return "Mağazaları listeleyen rehber / öneri yazısı"
    if re.search(r"\b(annuaire|directory|liste des|top \d+|best \d+|meilleures boutiques|\d+ boutiques|best boutiques)\b", text):
        return "Firma rehberi / listeleme içeriği"
    if re.search(r"\b(automobile|voiture|vehicule|car dealer|oto galeri|oto galeri|olympique|football club|fan shop|fanshop|taraftar)\b", normalized(title)):
        return "Tekstil butiği dışındaki işletme / kulüp mağazası"
    if re.search(r"\b(grossiste|wholesaler|wholesale supplier|toptanci|toptan satis|fabricant|manufacturer|ureticisi|imalatci|fournisseur textile|usine textile)\b", normalized(title)):
        return "Üretici / toptancı odaklı işletme"
    return ""


RETAIL = ("boutique", "magasin", "shop", "store", "perakende", "magaza", "butik", "e-shop", "online shop", "negozio", "tienda", "winkel", "laden", "boetiek", "add to cart", "ajouter au panier", "sepete ekle")
MULTIBRAND = ("multimarque", "multi-marque", "multi marque", "multi-brand", "multibrand", "multi brand", "cok markali", "nos marques", "our brands", "marques selectionnees", "markalarimiz")
TEXTILE = ("textile", "tekstil", "linge", "vetement", "pret-a-porter", "pret a porter", "mode femme", "mode homme", "fashion", "clothing", "apparel", "giyim", "elbise", "nevresim", "bedding", "baby", "bebe", "enfant", "decoration", "homeware", "accessoir", "aksesuar", "lingerie", "robe", "chemise", "knitwear", "coton", "linen", "chaussure", "schuhe", "kleidung", "damenmode", "abbigliamento", "ropa", "kleding", "mousseline")
SUPPLIER_PATTERNS = (r"deven(?:ez|ir) (?:notre )?fournisseur", r"propos(?:ez|er) votre marque", r"soumettre votre marque", r"become (?:a|our) supplier", r"submit your brand", r"supplier applications?", r"tedarikci basvur", r"tedarikcimiz olun", r"markanizi oner", r"lieferant werden", r"diventa (?:un )?fornitore", r"conviertete en proveedor")
TEXTILE += ("accessoire", "accessories", "damenkleidung", "babywear", "kidswear")


def contains(text, term):
    return bool(re.search(r"(?<!\w)" + re.escape(normalized(term)) + r"(?:s|es|ler|lar)?(?!\w)", text))


def product_match(text, term):
    words = normalized(term).split()
    return all(re.search(r"(?<!\w)" + re.escape(word[:-1] if len(word)>4 and word.endswith('s') and not word.endswith('ss') else word) + r"(?:s|es)?(?!\w)",text) for word in words)


def boutique_site_reason(url, pages, product=""):
    """Fail closed: search snippets alone cannot establish a boutique's identity."""
    if not pages:
        return "Butiğin kendi sitesi okunamadı; butik niteliği doğrulanamadı"
    host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
    identity_terms = ("butik", "boutique", "boetiek", "concept store", "multibrand", "multimarque", "cok markali")
    commerce_terms = ("sepete ekle", "sepetim", "alisveris sepeti", "add to cart", "ajouter au panier", "panier", "checkout", "kargo", "livraison", "shipping", "iade", "returns")
    for page in pages:
        page_host = (urlsplit(page["url"]).hostname or "").lower().removeprefix("www.")
        if page_host != host:
            continue
        heading = page.get("title", "") + " " + page.get("heading", "")
        if prefilter(page["url"], heading):
            continue
        text = normalized(page["text"])
        identity = any(contains(normalized(heading), term) for term in identity_terms)
        identity = identity or any(term in normalized(host) for term in ("butik", "boutique", "boetiek"))
        identity = identity or any(contains(text, term) for term in ("butigimiz", "butigimize", "notre boutique", "our boutique", "boutique independante", "independent boutique"))
        commerce = any(contains(text, term) for term in commerce_terms)
        local_contact = bool(re.search(r"\b(iletisim|contact|adresse|address)\b", text)) and bool(re.search(r"\b(horaires|opening hours|calisma saatleri|acilis saatleri)\b", text))
        if identity and (commerce or local_contact) and any(contains(text, term) for term in TEXTILE):
            if product and not all(any(product_match(text, term) for term in group) for group in product_groups(product)):
                continue
            return ""
    return "Kendi sitesinde butik kimliği ve doğrudan satış / mağaza kanıtı birlikte bulunamadı"


def saved_exclusion(row):
    reason = prefilter(row.get("website", ""), row.get("name", ""), row.get("evidence", "")) if row.get("website") else ""
    if reason:
        return reason
    if row.get("discovery_mode") and row.get("buyer_type") in ("retailer", "unknown", None):
        name = normalized(row.get("name", "") + " " + (urlsplit(row.get("website", "")).hostname or ""))
        if not any(term in name for term in ("butik", "boutique", "boetiek")):
            return "Eski genel mağaza sonucu; butik niteliği doğrulanmadı"
    return ""


def evaluate(url, title, snippet, product="", pages=None):
    pages = pages or []
    text = normalized(title + " " + snippet + " " + " ".join(p["text"] for p in pages))
    reject = prefilter(url, title, snippet)
    if reject:
        return {"accepted":False,"reason":reject}
    retail = any(contains(text, x) for x in RETAIL)
    multi = any(contains(text, x) for x in MULTIBRAND)
    textile = any(contains(text, x) for x in TEXTILE)
    if re.search(r"\b(nous sommes (?:un )?(?:fabricant|grossiste)|nous fabriquons|nous confectionnons|createur fabricant|fabrication dans notre atelier|we manufacture|we are (?:a )?(?:manufacturer|wholesaler)|wholesale only|uniquement aux professionnels|yalnizca toptan|sadece toptan|kendi uretimimiz|kendi atolye)\b", text):
        return {"accepted":False,"reason":"Üretici / yalnızca toptan satış kanıtı"}
    if not retail:
        return {"accepted":False,"reason":"Perakende mağaza kanıtı bulunamadı"}
    groups = product_groups(product)
    matched = bool(groups) and all(any(product_match(text, term) for term in group) for group in groups)
    if product and not matched:
        return {"accepted":False,"reason":"Girilen ürüne ilişkin yeterli eşleşme yok"}
    if not product and not textile:
        return {"accepted":False,"reason":"Tekstil / giyim / ev yaşam kategorisi kanıtı yok"}
    reasons, score = ["Perakende mağaza ifadesi bulundu"], 35
    if matched:
        reasons.append("Ürün anahtar kelimeleriyle eşleşiyor")
        score += 20
    elif textile:
        reasons.append("Tekstil / giyim / ev yaşam kategorisinde")
        score += 10
    opportunity = "potential"
    if multi:
        reasons.append("Çok markalı seçki: dış markalarla çalışmaya uygun aday")
        score += 20
        opportunity = "multibrand"
    if any(contains(text, x) for x in ("independant", "independent", "bagimsiz", "local boutique")):
        reasons.append("Bağımsız mağaza ifadesi bulundu")
        score += 5
    proof, proof_url = "", ""
    for page in pages:
        for sentence in re.split(r"[\n.!?]", page["text"]):
            n = normalized(sentence)
            if re.search(r"\b(ne .*pas|not accept|no longer|closed|kapali|kabul etmiyor|no new suppliers)\b", n):
                continue
            if any(re.search(pattern, n) for pattern in SUPPLIER_PATTERNS):
                proof, proof_url = sentence.strip()[:1000], page["url"]
                break
        if proof:
            break
    if proof:
        opportunity = "supplier_invitation"
        score += 20
        reasons.append("Sitede tedarikçi / marka başvurusu ifadesi bulundu; güncelliğini kontrol edin")
    site_verified = any(any(contains(normalized(page["text"]),term) for term in RETAIL) for page in pages)
    if site_verified:
        score += 10
        reasons.append("İşletmenin web sayfası okunarak incelendi")
    else:
        reasons.append("Yalnızca arama özeti incelendi; site doğrulaması gerekli")
    buyer = "multibrand" if multi else "concept" if "concept store" in text else "boutique" if any(contains(text, x) for x in ("boutique", "butik")) else "retailer"
    return {"accepted":True,"buyer_type":buyer,"priority":min(score,95),"opportunity":opportunity,"reasons":reasons,"assessment":"website" if site_verified else "search","supplier_evidence":proof,"supplier_source":proof_url,"fit":"possible" if matched else "unknown"}
