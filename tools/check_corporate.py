"""Check the generated export site without modifying the Turkish site."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
from xml.etree import ElementTree as ET
import json

ROOT=Path(__file__).resolve().parents[1]
class Doc(HTMLParser):
 def __init__(self):
  super().__init__(); self.links=[];self.h1=0;self.canonical=[];self.alternates=[];self.description=[];self.ld=[];self.active=False;self.buffer=''
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='h1':self.h1+=1
  if tag in ['a','link','img','script']:
   ref=a.get('href') or a.get('src')
   if ref:self.links.append(ref)
  if tag=='link' and a.get('rel')=='canonical':self.canonical.append(a['href'])
  if tag=='link' and a.get('rel')=='alternate':self.alternates.append(a['href'])
  if tag=='meta' and a.get('name')=='description':self.description.append(a.get('content'))
  if tag=='script' and a.get('type')=='application/ld+json':self.active=True;self.buffer=''
 def handle_data(self,data):
  if self.active:self.buffer+=data
 def handle_endtag(self,tag):
  if tag=='script' and self.active:self.ld.append(json.loads(self.buffer));self.active=False

def target(path):
 p=ROOT/path.lstrip('/')
 return p/'index.html' if p.is_dir() else p

errors=[];count=0
pages=list(ROOT.glob('*.html'))+list((ROOT/'collections').glob('*.html'))
for lang in ['fr','de','es']:pages+=list((ROOT/lang).rglob('*.html'))
for p in pages:
 count+=1;doc=Doc();doc.feed(p.read_text(encoding='utf-8'));label=p.relative_to(ROOT).as_posix()
 if doc.h1!=1:errors.append(f'{label}: H1 count {doc.h1}')
 if len(doc.canonical)!=1:errors.append(f'{label}: canonical missing/duplicate')
 if not doc.description:errors.append(f'{label}: description missing')
 for ref in doc.links:
  u=urlsplit(ref)
  if u.scheme or u.netloc:continue
  path=unquote(u.path)
  if not path:continue
  if path.startswith('/cms-media/'):
   import re
   if not re.fullmatch(r'/cms-media/[a-f0-9-]{36}\.webp',path):errors.append(f'{label}: invalid CMS image {ref}')
   continue # Runtime proxy; storage availability is checked by check_cms_output.py.
  dest=target(path) if path.startswith('/') else p.parent/path
  if dest.is_dir():dest=dest/'index.html'
  if not dest.exists():errors.append(f'{label}: broken link {ref}')
 for ref in doc.alternates:
  if not target(urlsplit(ref).path).exists():errors.append(f'{label}: missing alternate {ref}')
for loc in ET.parse(ROOT/'sitemap.xml').findall('.//{*}loc'):
 if not target(urlsplit(loc.text).path).exists():errors.append('Broken sitemap URL '+loc.text)
print(f'Checked {count} pages: links, H1, descriptions, canonical, language alternates, JSON-LD and sitemap.')
if errors:print('\n'.join(errors));raise SystemExit(1)
print('PASS')
