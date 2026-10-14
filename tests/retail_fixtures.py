"""Synthetic fixtures used only by tests; never imported by the application."""
RAW = [
    {"url":"https://rivage.test/","title":"Atelier Rivage · Boutique indépendante","snippet":"Boutique multimarque de vêtements femme et linge de lit en mousseline, robes en lin à Lyon."},
    {"url":"https://indigo.test/","title":"Maison Indigo · Boutique","snippet":"Concept store textile, linge de lit mousseline et vêtements femme. Nos marques, robes et accessoires à Lyon."},
    {"url":"https://www.rivage.test/contact","title":"Atelier Rivage contact","snippet":"Boutique de linge de maison"},
    {"url":"https://fr.mappy.com/shops","title":"Boutiques Lyon","snippet":"Boutique multimarque vêtements et mousseline"},
    {"url":"https://grossiste.test/","title":"Grossiste textile fabricant","snippet":"Boutique de linge de lit mousseline"},
    {"url":"https://boutiques.carreblanc.com/lyon","title":"Boutique linge de lit","snippet":"Boutique mousseline Lyon"},
    {"url":"https://etsy.com/shop/foo","title":"Boutique linge de lit","snippet":"Boutique mousseline"},
    {"url":"https://cafe.test/","title":"Petit Café","snippet":"Restaurant et café à Lyon"},
]


def fetch_results(query,req,settings,timeout=18):
    return RAW


def probe_site(url,product):
    if "rivage" in url:
        body="Boutique indépendante multimarque vêtements femme. Robes en lin. Linge de lit en mousseline. Nos marques. Devenez notre fournisseur : proposez votre marque à notre équipe."
    elif "indigo" in url:
        body="Maison Indigo. Concept store textile. Boutique vêtements femme. Linge de lit mousseline. Nos marques. Contact."
    else:
        body="Restaurant et café"
    return {"data":{"email":"bonjour@"+url.split('/')[2],"phone":"+33411111111","instagram":"","whatsapp":"","evidence":"","fit":"unknown","sources":[{"url":url,"field":"email","value":"Contact publié"}]},"pages":[{"url":url,"title":"Boutique textile","text":body+" Ajouter au panier. Livraison."}],"checked":[url],"warnings":[]}
