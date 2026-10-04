"""Validate reciprocal language links, contextual paths and metadata uniqueness."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
DOMAIN='https://www.tvstextile.com'
class Document(HTMLParser):
 def __init__(self):super().__init__();self.canonical='';self.alts={};self.links=[];self.title='';self.description='';self.in_title=False;self.noindex=False
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='title':self.in_title=True
  if tag=='a' and a.get('href'):self.links.append(a['href'])
  if tag=='link' and a.get('rel')=='canonical':self.canonical=a['href']
  if tag=='link' and a.get('rel')=='alternate':self.alts[a['hreflang']]=a['href']
  if tag=='meta' and a.get('name')=='description':self.description=a['content']
  if tag=='meta' and a.get('name')=='robots':self.noindex='noindex' in a['content']
 def handle_endtag(self,tag):
  if tag=='title':self.in_title=False
 def handle_data(self,text):
  if self.in_title:self.title+=text

docs={};errors=[];stats={}
for lang in ['en','fr','de','es']:
 folder=ROOT if lang=='en' else ROOT/lang
 pages=list(folder.glob('*.html'))+list((folder/'collections').glob('*.html'))
 stats[lang]=0;titles=set();descriptions=set()
 for path in pages:
  d=Document();d.feed(path.read_text(encoding='utf8'));docs[d.canonical]=(path,d)
  if d.noindex:continue
  stats[lang]+=1
  if d.title in titles:errors.append(f'Duplicate title: {path}')
  if d.description in descriptions:errors.append(f'Duplicate description: {path}')
  titles.add(d.title);descriptions.add(d.description)
  if '/collections/' in path.as_posix() or path.stem=='sourcing-guide':
   guide= ('../' if lang=='en' else '../../')+('' if lang=='en' else lang+'/')+'sourcing-guide.html'
   if path.parent.name=='collections' and guide not in d.links:errors.append(f'Missing contextual guide link: {path}')
   if not any('/collections/' in h or h.startswith('collections/') for h in d.links):errors.append(f'Missing collection link: {path}')

for url,(path,d) in docs.items():
 if not d.alts:continue
 if set(d.alts)!=set(['en','fr','de','es','x-default']):errors.append('Incomplete alternates: '+url)
 for language,target in d.alts.items():
  if target not in docs:errors.append('Missing language page: '+target);continue
  other=docs[target][1]
  if other.alts!=d.alts:errors.append('Nonreciprocal alternates: '+url+' -> '+target)
  if other.noindex:errors.append('Alternate is noindex: '+target)

entries=ET.parse(ROOT/'sitemap.xml').getroot();seen=set()
for entry in entries:
 url=entry.find('{*}loc').text;seen.add(url)
 alts={child.get('hreflang'):child.get('href') for child in entry if child.tag.endswith('link')}
 if url not in docs:errors.append('Unknown sitemap URL: '+url);continue
 if alts!=docs[url][1].alts:errors.append('Sitemap/HTML language mismatch: '+url)
 if docs[url][1].noindex:errors.append('Noindex page in sitemap: '+url)
for url,(path,d) in docs.items():
 if not d.noindex and url not in seen:errors.append('Missing sitemap entry: '+url)

# Crawl the multilingual pages from the English homepage using actual local links.
from urllib.parse import urljoin
file_index={path.resolve():url for url,(path,d) in docs.items()}
reached=set();pending=[DOMAIN+'/']
while pending:
 url=pending.pop()
 if url in reached or url not in docs:continue
 reached.add(url);path,d=docs[url]
 for href in d.links:
  u=urlsplit(href)
  if u.scheme or u.netloc or not u.path:continue
  dest=(ROOT/u.path.lstrip('/')) if u.path.startswith('/') else path.parent/u.path
  if dest.is_dir():dest=dest/'index.html'
  canonical=file_index.get(dest.resolve())
  if canonical:pending.append(canonical)
for url,(path,d) in docs.items():
 if d.alts and url not in reached:errors.append('Orphan multilingual page: '+url)
print('Indexable pages by language:',stats)
print('Sitemap URLs:',len(seen),'Pages reachable from homepage:',len(reached))
if errors:print('\n'.join(errors));raise SystemExit(1)
print('PASS: unique titles/descriptions, reciprocal hreflang, sitemap parity, contextual links and no orphan multilingual pages.')
