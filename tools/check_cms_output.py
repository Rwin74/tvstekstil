"""Check publication creates active products in each language."""
from pathlib import Path
from html.parser import HTMLParser
import json
import os,re,urllib.request
ROOT=Path(__file__).resolve().parents[1]
snapshot=ROOT/'data/cms-published.json'
if not snapshot.exists():raise SystemExit('No CMS snapshot to check.')
doc=json.loads(snapshot.read_text(encoding='utf-8'))
class Page(HTMLParser):
 def __init__(self):super().__init__();self.titles=0;self.h1=0;self.descriptions=0;self.title_active=False;self.title=''
 def handle_starttag(self,tag,attrs):
  if tag=='title':self.titles+=1;self.title_active=True
  if tag=='h1':self.h1+=1
  if tag=='meta' and dict(attrs).get('name')=='description':self.descriptions+=1
 def handle_data(self,data):
  if self.title_active:self.title+=data
 def handle_endtag(self,tag):
  if tag=='title':self.title_active=False
for p in doc['products']:
 for lang in ['en','fr','de','es']:
  path=ROOT/('' if lang=='en' else lang)/'collections'/(p['slug']+'.html')
  if not p['active']:
   assert not path.exists(),f'Inactive product still published: {path}'
   continue
  page=Page();page.feed(path.read_text(encoding='utf-8'))
  assert (page.titles,page.h1,page.descriptions)==(1,1,1),path
  assert page.title==p['locales'][lang]['metaTitle'],path
 if p['active'] and p['image'].startswith('/cms-media/') and os.environ.get('CMS_SUPABASE_URL'):
  url=os.environ['CMS_SUPABASE_URL']
  assert re.fullmatch(r'https://[a-z0-9]+\.supabase\.co',url)
  request=urllib.request.Request(url+'/storage/v1/object/public/product-media/'+p['image'].split('/')[-1],method='HEAD')
  with urllib.request.urlopen(request,timeout=15) as response:assert response.headers.get('Content-Type','').startswith('image/webp')
print('CMS product publication and metadata passed in 4 languages.')
