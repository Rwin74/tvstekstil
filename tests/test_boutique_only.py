import pytest
from fastapi.testclient import TestClient
from firma.buyers import prefilter, boutique_site_reason
from firma.app import create_app
from firma.config import Settings
from firma.store import Store
from firma.models import Lead


@pytest.mark.parametrize('url,title',[
    ('https://www.enuygun.com/bilgi/outletler/', "Türkiye'nin En İyi Outletleri | Gidilmesi Gereken"),
    ('https://unknown.test/x', "İstanbul'un en iyi 20 butiği"),
    ('https://unknown.test/x', 'Best clothing boutiques in London'),
    ('https://unknown.test/x', 'Les meilleures boutiques de Lyon'),
    ('https://unknown.test/x', 'Ankara butik mağazalar rehberi'),
    ('https://unknown.test/rehber/alisveris', 'Kadın Giyim'),
])
def test_listing_titles_and_paths(url,title):
    assert prefilter(url,title)


def page(text,title='Mylove Butik',url='https://mylovebutik.test/'):
    return {'url':url,'title':title,'heading':'','text':text}


def test_boutique_requires_own_identity_and_sales():
    url='https://mylovebutik.test/'
    assert not boutique_site_reason(url,[page('Kadın giyim elbise. Sepete ekle. Kargo ve iade.')])
    assert boutique_site_reason(url,[])
    assert boutique_site_reason(url,[page('Verify you are human')])
    assert boutique_site_reason(url,[page('Butikleri sizin için listeliyoruz. Kadın giyim.')])
    assert boutique_site_reason(url,[page('Kadın giyim sepete ekle',url='https://other.test/')])
    assert boutique_site_reason('https://generic.test/',[page('Giyim mağazası sepete ekle',title='Giyim Dünyası',url='https://generic.test/')])


def test_editorial_page_cannot_pass_with_shop_navigation():
    p=page('Giyim butikleri, sepete ekle kargo iade.',title="Türkiye'nin en iyi butikleri")
    assert boutique_site_reason(p['url'],[p])


def test_local_boutique_without_online_checkout():
    p=page('Kadın giyim. İletişim ve çalışma saatleri. Butiğimiz.')
    assert not boutique_site_reason(p['url'],[p])


def test_product_must_be_on_own_page():
    p=page('Kadın giyim pamuk elbise. Sepete ekle.')
    assert boutique_site_reason(p['url'],[p],'keten elbise')
    assert not boutique_site_reason(p['url'],[p],'pamuk elbise')


def test_existing_bad_records_hidden_preserved_in_backup(tmp_path):
    store=Store(Settings(tmp_path))
    store.save(Lead(name="Türkiye'nin En İyi Outletleri",website='https://enuygun.com/bilgi/outletler',notes='Keep my notes'))
    store.save(Lead(name='Giyim Dünyası',website='https://generic.test/',discovery_mode='prospects',buyer_type='retailer'))
    store.save(Lead(name='Mylove Butik',website='https://mylovebutik.test/',discovery_mode='prospects',buyer_type='retailer'))
    client=TestClient(create_app(Settings(tmp_path)),headers={'X-App-Request':'FirmaAtlas'})
    response=client.get('/api/leads').json()
    assert response['hidden_count']==2
    assert [x['name'] for x in response['leads']]==['Mylove Butik']
    backup=client.get('/api/backup').json()['leads']
    assert len(backup)==3 and any(x['notes']=='Keep my notes' for x in backup)
    assert client.post('/api/leads',json={'name':'List article','website':'https://enuygun.com/'}).status_code==422
