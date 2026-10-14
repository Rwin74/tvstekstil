import json
import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from firma.app import create_app
from firma.buyers import evaluate, prefilter, product_terms
from firma.config import Settings
from firma.models import Lead, SearchRequest
from firma.search import search, build_queries, ServiceError
from firma.store import Store
from retail_fixtures import fetch_results, probe_site

HEADERS={"X-App-Request":"FirmaAtlas"}


@pytest.mark.parametrize("url",["https://fr.mappy.com/x","https://pagesjaunes.fr/x","https://amazon.fr/x","https://instagram.com/boutique","https://boutiques.carreblanc.com/lyon","https://shop.test/blog/boutique","https://kompass.com/x"])
def test_non_buyer_sources_rejected(url):
    assert prefilter(url,"Boutique textile","Müslin nevresim boutique")


def test_domain_boundaries():
    assert not prefilter("https://my-amazon.fr/","Boutique","Mode femme")
    assert prefilter("https://sub.amazon.fr/")


@pytest.mark.parametrize("url,title,snippet",[
    ("https://cars.test/", "France Automobile Multimarque", "Store accessoires robe de protection"),
    ("https://editor.test/post/shops", "Les meilleures boutiques créateurs pour bébés", "Boutique textile"),
    ("https://editor.test/2015/02/list", "1 bébé, 6 boutiques coup de cœur à Lyon", "Boutique textile"),
    ("https://club.test/", "Vêtements bébé - Olympique Lyonnais", "Boutique textile"),
    ("https://other.test/", "Shop", "Roberts online newsletter")
    ,("https://www.justacote.com/lyon/page-3.htm", "Boutiques vêtements femme", "Boutique textile")
    ,("https://blancdesvosges.fr/", "Linge de maison", "Boutique textile nos marques")
])
def test_live_false_positives_rejected(url,title,snippet):
    assert not evaluate(url,title,snippet)["accepted"]


@pytest.mark.parametrize("title",["Grossiste mode","Textile manufacturer","Toptan satış mağazası","Fabricant de linge de lit"])
def test_suppliers_not_buyers(title):
    assert not evaluate("https://seller.test/",title,"Boutique textile clothing")["accepted"]


def test_product_cross_language_and_arbitrary_keyword():
    row=evaluate("https://shop.test/","Boutique","Linge de lit en gaze de coton", "müslin nevresim")
    assert row["accepted"] and row["fit"]=="possible"
    assert evaluate("https://shop.test/","Boutique","Organic waffle towels", "waffle towels")["accepted"]
    assert not evaluate("https://shop.test/","Boutique lingerie","Underwear lingerie", "keten")["accepted"]
    assert "robe" in product_terms("keten elbise","fr")
    assert product_terms("custom product 123","fr")=="custom product 123"


def test_product_must_match_all_material_and_type_terms():
    assert not evaluate("https://shop.test/","Boutique","Linge de lit coton", "müslin nevresim")["accepted"]
    assert not evaluate("https://shop.test/","Boutique","Muslin scarf", "müslin nevresim")["accepted"]


def test_prospect_no_keyword_and_three_segments():
    req=SearchRequest(mode="prospects",city="Lyon")
    queries=build_queries(req)
    assert len(queries)==3 and all("Lyon" in q for q in queries)
    assert len(build_queries(SearchRequest(mode="prospects",sector="home")))==1
    with pytest.raises(ValueError): SearchRequest(mode="prospects",product="dress")
    with pytest.raises(ValueError): SearchRequest(mode="prospects",country="ALL")


def test_multibrand_is_not_active_demand():
    row=evaluate("https://shop.test/","Boutique indépendante","Nos marques, vêtements femme")
    assert row["opportunity"]=="multibrand"
    assert row["supplier_evidence"]=="" and row["assessment"]=="search"
    assert row["priority"]<100


def test_supplier_signal_requires_site_and_direction():
    url="https://shop.test/"
    row=evaluate(url,"Boutique textile","Become our supplier")
    assert row["opportunity"]=="potential"
    row=evaluate(url,"Boutique textile","",pages=[{"url":url,"text":"Boutique textile. Devenez notre fournisseur : proposez votre marque."}])
    assert row["opportunity"]=="supplier_invitation" and row["supplier_source"]==url
    for text in ["Boutique textile. Devenez revendeur de notre marque.","Boutique textile. Supplier applications are closed.","Boutique textile. We do not accept supplier applications."]:
        assert evaluate(url,"Boutique textile","",pages=[{"url":url,"text":text}])["opportunity"]!="supplier_invitation"


def test_captcha_not_site_verified():
    row=evaluate("https://shop.test/","Boutique textile","Nos marques",pages=[{"url":"https://shop.test/","text":"Verify you are human. Access denied"}])
    assert row["assessment"]=="search"


def test_fixture_filter_sort_contacts_and_explanations(tmp_path):
    with patch("firma.search.fetch_results",side_effect=fetch_results),patch("firma.search.probe_site",side_effect=probe_site):
        result=search(SearchRequest(product="müslin nevresim",city="Lyon"),Settings(tmp_path,api_key="fixture"))
    assert len(result["results"])==2 and len(result["excluded"])==5
    first=result["results"][0]
    assert first["opportunity"]=="supplier_invitation"
    assert first["priority"]>=result["results"][1]["priority"]
    assert first["email"] and first["reasons"] and first["sources"]
    assert first["city"]=="" and first["target_city"]=="Lyon"


def test_site_failure_does_not_admit_unverified_boutiques(tmp_path):
    with patch("firma.search.fetch_results",side_effect=fetch_results),patch("firma.search.probe_site",side_effect=ServiceError("blocked")):
        result=search(SearchRequest(product="müslin nevresim"),Settings(tmp_path,api_key="fixture"))
    assert result["results"]==[]
    assert any("okunamadı" in r["reason"] for r in result["excluded"])


def test_partial_provider_failure_visible(tmp_path):
    with patch("firma.search.fetch_results",side_effect=[fetch_results(None,None,None),ServiceError("Kota doldu")]),patch("firma.search.probe_site",return_value=None),patch("firma.search.time.sleep"):
        result=search(SearchRequest(mode="prospects"),Settings(tmp_path,api_key="fixture"))
    assert result["warnings"]==["Kota doldu"] and result["requests_used"]==2


def test_cache_and_quota_no_second_provider_call(tmp_path):
    app=create_app(Settings(tmp_path,api_key="fixture"))
    client=TestClient(app,headers=HEADERS)
    with patch("firma.search.fetch_results",side_effect=fetch_results) as provider,patch("firma.search.probe_site",side_effect=probe_site):
        first=client.post("/api/search",json={"product":"müslin nevresim"}).json()
        second=client.post("/api/search",json={"product":"müslin nevresim"}).json()
    assert not first["cached"] and second["cached"] and second["requests_used"]==0
    assert provider.call_count==1
    assert len(client.get('/api/history').json()['history'])==1


def test_legacy_records_preserved_hidden_and_not_restored(tmp_path):
    store=Store(Settings(tmp_path))
    store.save(Lead(name="Old example",is_demo=True))
    store.save(Lead(name="Real boutique",priority=65,buyer_type="multibrand",opportunity="multibrand",reasons=["Published brands"]))
    assert len(store.list())==1 and len(store.list(include_legacy=True))==2
    app=create_app(Settings(tmp_path)); c=TestClient(app,headers=HEADERS)
    assert len(c.get('/api/leads').json()['leads'])==1
    backup=c.get('/api/backup').json()
    other=TestClient(create_app(Settings(tmp_path/'other')),headers=HEADERS)
    assert other.post('/api/restore',json=backup).json()=={"added":1,"skipped":1}
    row=other.get('/api/leads').json()['leads'][0]
    assert row['priority']==65 and row['reasons']==['Published brands']


def test_old_lead_payload_compatible(tmp_path):
    store=Store(Settings(tmp_path));store.init()
    with store.connection() as conn:
        store.sql(conn,"INSERT INTO leads VALUES (?,?,?,?,?,?)",("old","real:old",json.dumps({"name":"Existing buyer","website":"","status":"research","is_demo":False}),"now","now",1))
    row=store.list()[0]
    assert row['name']=="Existing buyer"
    assert Lead.model_validate({k:v for k,v in row.items() if k not in ('id','created_at','updated_at','version')}).priority==0


def test_serpapi_empty_result_is_not_connection_failure(tmp_path):
    import httpx
    from firma.search import fetch_results as fetch
    response=httpx.Response(200,json={"error":"Google hasn't returned any results for this query.","search_information":{"organic_results_state":"Fully empty"}},request=httpx.Request("GET","https://serpapi.com/search.json"))
    with patch("httpx.Client.get",return_value=response):
        assert fetch("query",SearchRequest(product="linen"),Settings(tmp_path,api_key="fixture"))==[]
