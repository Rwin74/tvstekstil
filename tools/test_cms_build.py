"""Integration test: new product, retired product, 4 languages and company updates.
Uses reversible local generated files; restores every page even when checks fail.
"""
from pathlib import Path
import subprocess,json,re
ROOT=Path(__file__).resolve().parents[1]
snapshot=ROOT/'data/cms-published.json'
if snapshot.exists():raise SystemExit('Test requires no real CMS snapshot; refusing to overwrite it.')
def pages():
 return list(ROOT.glob('*.html'))+list((ROOT/'collections').glob('*.html'))+[p for l in ['fr','de','es','kategori'] for p in (ROOT/l).rglob('*.html')]
backups={p:p.read_bytes() for p in pages()+[ROOT/'sitemap.xml']}
try:
 doc=json.loads((ROOT/'data/cms-seed.json').read_text(encoding='utf-8'))
 doc['settings']['address']='Test address 42, Denizli'
 doc['settings']['email']='studio@example.com'
 doc['settings']['phone']='+90 555 111 2233'
 p=json.loads(json.dumps(doc['products'][0]));p['slug']='test-new-linen';p['realPhoto']=True;p['updated']='2026-10-06'
 for lang,row in p['locales'].items():
  row['name']='New collection '+lang;row['metaTitle']='New linen manufacturer '+lang+' | TVS';row['metaDescription']='A distinct new collection for buyers in '+lang+'.';row['paragraph1']='Our new collection begins with a new fabric brief in '+lang+'.';row['paragraph2']='We confirm the details for this individual textile product in '+lang+'.'
 doc['products'].append(p)
 doc['products'][0]['active']=False
 doc['pages']['en']['home']['heading']='A new textile story'
 for lang in ['', 'fr','de','es']:
  old=ROOT/lang/'collections/muslin-duvet-covers.html'
  old.unlink()
 snapshot.write_text(json.dumps(doc,ensure_ascii=False),encoding='utf-8')
 for command in [['python','tools/build_corporate.py'],['python','tools/check_corporate.py'],['python','tools/check_multilingual_seo.py'],['python','tools/check_cms_output.py']]:subprocess.run(command,cwd=ROOT,check=True)
 for lang in ['', 'fr','de','es']:
  path=ROOT/lang/'collections/test-new-linen.html';html=path.read_text(encoding='utf-8')
  assert 'studio@example.com' in html and 'Test address 42, Denizli' in html
  assert 'href="tel:+905551112233"' in html
  assert '<meta property="og:image" content="https://www.tvstextile.com/img/products/muslin-duvet-covers.webp">' in html
 assert '<h1>A new textile story</h1>' in (ROOT/'index.html').read_text(encoding='utf-8')
 print('PASS: new/retired products, four languages, SEO, contact details and page editing.')
finally:
 for path in pages():
  if path not in backups and path.resolve().is_relative_to(ROOT):path.unlink()
 for path,data in backups.items():path.write_bytes(data)
 if snapshot.exists():snapshot.unlink()
