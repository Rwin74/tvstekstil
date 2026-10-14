import base64
import json
import os
from pathlib import Path
import subprocess
import time
from io import BytesIO
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi.testclient import TestClient
from pypdf import PdfReader

from firma.app import create_app
from firma.config import Settings
from firma.models import Lead
from firma.site_auth import AdminGateway, COOKIE, ORIGIN, TOKEN, unseal, verify_admin
from firma.site_store import SupabaseStore
from firma.store import Store, Conflict

ROOT = Path(__file__).resolve().parents[1]


def sealed(key, **changes):
    data = {'token':'test-user-jwt', 'csrf':'csrf-test', 'exp':int(time.time()*1000)+60000, **changes}
    iv = os.urandom(12)
    encrypted = AESGCM(key).encrypt(iv, json.dumps(data).encode(), None)
    return base64.urlsafe_b64encode(iv+encrypted[-16:]+encrypted[:-16]).decode().rstrip('=')


@pytest.fixture
def gateway(tmp_path, monkeypatch):
    key = os.urandom(32)
    monkeypatch.setenv('ADMIN_SESSION_KEY',base64.b64encode(key).decode())
    settings=Settings(tmp_path,cloud=True)
    store=Store(Settings(tmp_path))
    app=AdminGateway(create_app(settings,site_store=store))
    with patch('firma.site_auth.verify_admin',new_callable=AsyncMock,return_value=True) as verify:
        client=TestClient(app,base_url=ORIGIN,headers={
            'Cookie':COOKIE+'='+sealed(key),'Origin':ORIGIN,
            'X-CSRF-Token':'csrf-test','X-App-Request':'FirmaAtlas'})
        yield client,store,key,verify


def test_existing_node_cookie_cross_language(monkeypatch):
    key=base64.b64encode(os.urandom(32)).decode()
    monkeypatch.setenv('ADMIN_SESSION_KEY',key)
    script="const s=require('./lib/admin-security.cjs');process.stdout.write(s.seal({token:'jwt',csrf:'çığ',exp:Date.now()+60000},process.env))"
    value=subprocess.check_output(['node','-e',script],cwd=ROOT,text=True)
    assert unseal(COOKIE+'='+value)['csrf']=='çığ'


@pytest.mark.parametrize('mode',['missing','tampered','expired','duplicate','wrong-key','oversized'])
def test_invalid_cookie_never_reaches_auth_or_data(gateway,mode,monkeypatch):
    client,store,key,verify=gateway
    value=sealed(key)
    header=COOKIE+'='+value
    if mode=='missing': header=''
    elif mode=='tampered': header=COOKIE+'='+('A' if value[0]!='A' else 'B')+value[1:]
    elif mode=='expired': header=COOKIE+'='+sealed(key,exp=0)
    elif mode=='duplicate': header+='; '+header
    elif mode=='wrong-key': monkeypatch.setenv('ADMIN_SESSION_KEY',base64.b64encode(os.urandom(32)).decode())
    elif mode=='oversized': header=COOKIE+'='+'x'*6001
    response=client.get('/api/boutiques?route=leads',headers={'Cookie':header})
    assert response.status_code==401
    assert response.headers['cache-control']=='no-store'
    verify.assert_not_called()


@pytest.mark.parametrize('headers',[
    {'Origin':'https://evil.test'}, {'Origin':''}, {'X-CSRF-Token':''},
    {'X-CSRF-Token':'ş'.encode()}, {'Sec-Fetch-Site':'cross-site'}, {'X-App-Request':''}])
def test_mutations_require_same_origin_and_both_headers(gateway,headers):
    client,*_=gateway
    assert client.post('/admin/butik-api/leads',json={'name':'Test Butik'},headers=headers).status_code==403


def test_revoked_admin_and_outage_fail_closed(gateway):
    client,store,key,verify=gateway
    verify.return_value=False
    assert client.get('/admin/butik-api/leads').status_code==401
    verify.side_effect=RuntimeError('private upstream details')
    response=client.get('/admin/butik-api/leads')
    assert response.status_code==503 and 'private' not in response.text


@pytest.mark.parametrize('path',['/api/boutiques','/api/boutiques?route=login','/api/boutiques?route=leads&route=backup',
    '/api/boutiques?route=../settings','/api/boutiques?route=assets/app.js','/api/leads','/'])
def test_function_exposes_only_allowlisted_routes(gateway,path):
    assert gateway[0].get(path).status_code==404


def test_saved_records_pdf_backup_conflict_and_translation_fields(gateway):
    client,store,key,verify=gateway
    base='/admin/butik-api'
    payload={'name':'Çığ Butik','website':'https://cigbutik.example/','product':'Linge de lit',
             'product_tr':'Müslin nevresim','notes_tr':'ı İ ş Ş ğ Ğ ü Ü ö Ö ç Ç','country':'FR'}
    created=client.post(base+'/leads',json=payload)
    assert created.status_code==201
    row=created.json()
    assert client.post(base+'/leads',json=payload).status_code==409
    assert client.get('/api/boutiques?route=leads').json()['leads'][0]['product_tr']=='Müslin nevresim'
    pdf=client.post(base+'/export/pdf',json={'ids':[row['id']]})
    assert pdf.status_code==200 and pdf.headers['content-type']=='application/pdf'
    text=''.join(p.extract_text() for p in PdfReader(BytesIO(pdf.content)).pages)
    assert all(value in text for value in ['Çığ Butik','Linge de lit','Müslin nevresim','ı İ ş Ş ğ Ğ ü Ü ö Ö ç Ç'])
    backup=client.get(base+'/backup').json()
    assert client.post(base+'/restore',json={'format':backup['format'],'leads':backup['leads']}).json()=={'added':0,'skipped':1}
    assert client.put(base+'/leads/'+row['id'],json={'lead':{**payload,'notes':'Görüşüldü'},'version':1}).status_code==200
    assert client.delete('/api/boutiques?route=leads/'+row['id']+'&version=1').status_code==409
    assert client.delete('/api/boutiques?route=leads/'+row['id']+'&version=2').status_code==200
    assert TOKEN.get() is None
    assert verify.await_count>=9


def test_cloud_settings_readonly_and_request_size(gateway):
    client,*_=gateway
    assert client.get('/admin/butik-api/session').json()=={'authenticated':True,'cloud':True}
    assert client.put('/admin/butik-api/settings',json={'provider':'serpapi','key':'test12345678'}).status_code==403
    response=client.post('/admin/butik-api/restore',content=b'x'*4_000_001)
    assert response.status_code==413


def test_rpc_uses_request_jwt_no_service_key_and_resets(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL','https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_PUBLISHABLE_KEY','sb_publishable_test')
    monkeypatch.setenv('SUPABASE_SECRET_KEY','DO-NOT-USE')
    store=SupabaseStore()
    with pytest.raises(RuntimeError): store.list()
    token=TOKEN.set('user-jwt')
    try:
        with patch('httpx.Client.post',return_value=httpx.Response(200,json=[])) as post:
            assert store.list()==[]
            assert post.call_args.kwargs['headers']=={'apikey':'sb_publishable_test','Authorization':'Bearer user-jwt'}
            assert post.call_args.kwargs['json']=={'operation':'list','arguments':{}}
        with patch('httpx.Client.post',return_value=httpx.Response(409,json={'message':'private'})):
            with pytest.raises(Conflict):store.save(Lead(name='Test Butik'))
        with patch('httpx.Client.post',return_value=httpx.Response(500,json={'message':'private'})):
            with pytest.raises(RuntimeError,match='Kurulumu'):store.list()
    finally:TOKEN.reset(token)


def test_no_auth_bypass_by_constructing_base_app(tmp_path):
    inner=create_app(Settings(tmp_path,cloud=True),site_store=SupabaseStore())
    assert TestClient(inner).get('/api/health').status_code==401


def test_user_tokens_stay_isolated_in_concurrent_requests(tmp_path,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    key=os.urandom(32)
    monkeypatch.setenv('ADMIN_SESSION_KEY',base64.b64encode(key).decode())
    gateway=AdminGateway(create_app(Settings(tmp_path,cloud=True),site_store=SupabaseStore()))
    def rpc(self,operation,**arguments):
        captured=TOKEN.get()
        time.sleep(.03)
        assert captured==TOKEN.get()
        return [{'id':captured,'name':'Test Butik'}]
    def read(token):
        with TestClient(gateway,base_url=ORIGIN) as client:
            return client.get('/admin/butik-api/leads',headers={'Cookie':COOKIE+'='+sealed(key,token=token)}).json()['leads'][0]['id']
    with patch('firma.site_auth.verify_admin',new_callable=AsyncMock,return_value=True),patch.object(SupabaseStore,'rpc',rpc):
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert list(pool.map(read,['user-one','user-two']))==['user-one','user-two']
    assert TOKEN.get() is None


@pytest.mark.parametrize('user_status,role_status,role,expected',[(200,200,True,True),(200,200,False,False),(401,200,True,False),(200,500,True,False)])
def test_supabase_rechecks_user_and_admin(monkeypatch,user_status,role_status,role,expected):
    import asyncio
    monkeypatch.setenv('SUPABASE_URL','https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_PUBLISHABLE_KEY','sb_publishable_test')
    with patch('httpx.AsyncClient.get',new_callable=AsyncMock,return_value=httpx.Response(user_status,json={'id':'user'})) as get:
        with patch('httpx.AsyncClient.post',new_callable=AsyncMock,return_value=httpx.Response(role_status,json=role)) as post:
            assert asyncio.run(verify_admin('jwt')) is expected
            assert get.call_args.kwargs['headers']['Authorization']=='Bearer jwt'
            if user_status==200: assert post.call_args.kwargs['json']=={}
