"""Explicit translation using official APIs; private contact fields are never sent."""
import os
import json
import base64
import html
import httpx
from .vault import crypt
from .search import ServiceError

FIELDS = ('name','product','evidence','supplier_evidence','notes')


def settings_for(settings):
    result={'provider':os.getenv('TRANSLATION_PROVIDER','azure'),'key':os.getenv('TRANSLATION_KEY',''),'region':os.getenv('TRANSLATION_REGION','')}
    path=settings.data_dir/'translation-settings.json'
    if not settings.cloud and not result['key'] and path.exists():
        try:
            data=json.loads(path.read_text(encoding='utf-8'))
            result={**data,'key':crypt(base64.b64decode(data['key']),decrypt=True).decode()}
        except (OSError,ValueError,KeyError,RuntimeError): pass
    return result


def save_settings(settings,provider,key,region):
    path=settings.data_dir/'translation-settings.json';path.parent.mkdir(parents=True,exist_ok=True)
    data={'provider':provider,'key':base64.b64encode(crypt(key.encode())).decode(),'region':region}
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data),encoding='utf-8');temp.replace(path)


def translate(lead, config):
    if not config['key']: raise ServiceError('Otomatik çeviri için Ayarlar bölümüne çeviri bağlantısı ekleyin. Türkçe alanları elle de doldurabilirsiniz.')
    keys=[k for k in FIELDS if lead.get(k)]
    if not keys: return {}
    texts=[lead[k] for k in keys]
    if sum(map(len,texts))>18000: raise ServiceError('Çevrilecek metin çok uzun. Notları kısaltarak tekrar deneyin.')
    try:
        with httpx.Client(timeout=25,follow_redirects=False) as client:
            if config['provider']=='google':
                r=client.post('https://translation.googleapis.com/language/translate/v2',headers={'X-goog-api-key':config['key']},json={'q':texts,'target':'tr','format':'text'})
                r.raise_for_status(); values=[html.unescape(x['translatedText']) for x in r.json()['data']['translations']]
            else:
                headers={'Ocp-Apim-Subscription-Key':config['key']}
                if config.get('region'): headers['Ocp-Apim-Subscription-Region']=config['region']
                r=client.post('https://api.cognitive.microsofttranslator.com/translate',params={'api-version':'3.0','to':'tr'},headers=headers,json=[{'Text':t} for t in texts])
                r.raise_for_status();values=[x['translations'][0]['text'] for x in r.json()]
        if len(values)!=len(keys) or any(not isinstance(v,str) or not v.strip() for v in values): raise ValueError()
        return {k+'_tr':v for k,v in zip(keys,values)}
    except (httpx.HTTPError,ValueError,KeyError,IndexError,TypeError):
        raise ServiceError('Çeviri tamamlanamadı. Çeviri anahtarını, bölgeyi, bağlantıyı ve servis kotasını kontrol edin.') from None
