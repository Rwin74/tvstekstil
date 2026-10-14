from io import BytesIO
from pathlib import Path
from unittest.mock import patch
import httpx
import pytest
from pypdf import PdfReader
from fastapi.testclient import TestClient
from firma.app import create_app
from firma.config import Settings
from firma.models import Lead
from firma.pdf_export import build_pdf
from firma.translation import translate
from firma.search import ServiceError

SAMPLE={
 'name':'Örnek Boutique Élégance - Çığ Şişli', 'name_tr':'Örnek Zarafet Butiği - Çığ Şişli',
 'website':'https://boutique.example/','email':'contact@boutique.example','phone':'+33 1 23 45 67 89',
 'whatsapp':'+33 1 23 45 67 89','instagram':'https://instagram.com/example','contact_person':'Françoise Müller',
 'product':'Linge de lit en mousseline','product_tr':'Müslin nevresim', 'city':'Lyon','country':'FR',
 'status':'qualified','fit':'possible','buyer_type':'boutique','priority':75,'opportunity':'potential','assessment':'website',
 'evidence':'Notre boutique propose du linge de lit en mousseline et des vêtements en coton.',
 'evidence_tr':'Butiğimiz müslin nevresim ve pamuklu giysiler sunmaktadır.',
 'supplier_evidence':'Devenez notre fournisseur.','supplier_evidence_tr':'Tedarikçimiz olun.',
 'notes':'Échantillons demandés.','notes_tr':'Numune talep edildi. Türkçe karakterler: ı İ ş Ş ğ Ğ ü Ü ö Ö ç Ç.',
 'reasons':['Kendi sitesinde butik ve satış kanıtı bulundu.'],
 'sources':[{'url':'https://boutique.example/contact','field':'email','value':'contact@boutique.example'}]
}


def test_pdf_unicode_bilingual_and_embedded_fonts():
    data=build_pdf([SAMPLE]); reader=PdfReader(BytesIO(data))
    text='\n'.join(p.extract_text() for p in reader.pages)
    for value in ['Çığ Şişli','Françoise Müller','Müslin nevresim','ı İ ş Ş ğ Ğ ü Ü ö Ö ç Ç','Notre boutique','Butiğimiz','Tedarikçimiz olun.']:
        assert value in text
    assert len(reader.pages)>=2 and '\ufffd' not in text
    assert any('/FontFile2' in f.get_object().get('/FontDescriptor',{}) for page in reader.pages for f in page['/Resources']['/Font'].values())
    path=Path('tmp/pdfs');path.mkdir(parents=True,exist_ok=True);(path/'bilingual-preview.pdf').write_bytes(data)


def test_long_fields_escape_and_page_flow():
    row={**SAMPLE,'name':'Uzun açıklama <b>etiket</b>','notes':('Türkçe uzun görüşme notu. '*400),'notes_tr':('Kontrol edilen Türkçe çeviri. '*500)}
    data=build_pdf([row]);reader=PdfReader(BytesIO(data));text='\n'.join(p.extract_text() for p in reader.pages)
    assert '<b>etiket</b>' in text and len(reader.pages)>4
    assert text.count('Kontrol')==500 and text.count('çeviri.')==500
    Path('tmp/pdfs/long-preview.pdf').write_bytes(data)


def test_pdf_api_only_saved_visible_selected_and_persist_translations(tmp_path):
    c=TestClient(create_app(Settings(tmp_path)),headers={'X-App-Request':'FirmaAtlas'})
    assert c.post('/api/export/pdf',json={}).status_code==422
    row=c.post('/api/leads',json=SAMPLE).json()
    c.post('/api/leads',json={'name':'Other boutique'})
    response=c.post('/api/export/pdf',json={'ids':[row['id']]})
    assert response.status_code==200 and response.headers['content-type']=='application/pdf'
    text=''.join(p.extract_text() for p in PdfReader(BytesIO(response.content)).pages)
    assert 'Müslin nevresim' in text and 'Other boutique' not in text
    assert c.post('/api/export/pdf',json={'ids':['missing']}).status_code==409
    assert c.get('/api/backup').json()['leads'][-1]['evidence_tr']==SAMPLE['evidence_tr']


@pytest.mark.parametrize('provider',['azure','google'])
def test_translation_provider_batch_and_contact_privacy(provider):
    payload=[{'translations':[{'text':'Türkçe'}]}] if provider=='azure' else {'data':{'translations':[{'translatedText':'Türkçe'}]}}
    response=httpx.Response(200,json=payload,request=httpx.Request('POST','https://service.test/'))
    with patch('httpx.Client.post',return_value=response) as post:
        result=translate({'name':'Bonjour','phone':'PRIVATE','email':'PRIVATE'},{'provider':provider,'key':'SECRET','region':'westeurope'})
    assert result=={'name_tr':'Türkçe'}
    assert 'PRIVATE' not in str(post.call_args.kwargs['json'])


def test_translation_unconfigured_and_service_failure_no_key_leak():
    with pytest.raises(ServiceError):translate(SAMPLE,{'key':''})
    response=httpx.Response(403,request=httpx.Request('POST','https://service.test/?key=SECRET'))
    with patch('httpx.Client.post',return_value=response),pytest.raises(ServiceError) as exc:
        translate(SAMPLE,{'provider':'google','key':'SECRET'})
    assert 'SECRET' not in str(exc.value)


@pytest.mark.skipif(__import__('os').name != 'nt', reason='Windows DPAPI')
def test_translation_windows_settings_persist_without_key_echo(tmp_path):
    settings=Settings(tmp_path)
    c=TestClient(create_app(settings),headers={'X-App-Request':'FirmaAtlas'})
    response=c.put('/api/translation/settings',json={'provider':'azure','key':'translation-test-secret','region':'westeurope'})
    assert response.status_code==200 and response.json()['configured']
    assert 'translation-test-secret' not in response.text
    assert 'translation-test-secret' not in (tmp_path/'translation-settings.json').read_text()
    other=TestClient(create_app(Settings(tmp_path)),headers={'X-App-Request':'FirmaAtlas'})
    assert other.get('/api/translation/settings').json()['configured']
