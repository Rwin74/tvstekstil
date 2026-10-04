"""Check main-product repetition and visible/schema/sitemap dates."""
from pathlib import Path
from html import unescape
import re,json
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
errors=[];paragraphs={};checked=0
dates={entry.find('{*}loc').text:entry.find('{*}lastmod').text for entry in ET.parse(ROOT/'sitemap.xml').getroot()}
for lang in ['en','fr','de','es']:
 folder=ROOT if lang=='en' else ROOT/lang;texts=[]
 for p in (folder/'collections').glob('*.html'):
  s=p.read_text(encoding='utf8')
  block=re.search(r'<section class="section product-detail">\s*<div>(.*?)</div>',s,re.S)
  if not block:continue
  content=[unescape(re.sub('<[^>]*>','',t)).strip() for t in re.findall(r'<p>(.*?)</p>',block[1],re.S)]
  if len(content)!=2:errors.append(f'{p}: expected two product-specific editorial paragraphs')
  for paragraph in content:
   if paragraph in paragraphs:errors.append(f'Repeated main paragraph: {p}, {paragraphs[paragraph]}')
   paragraphs[paragraph]=p
  words=' '.join(content).lower().split();shingles=set(tuple(words[i:i+5]) for i in range(len(words)-4))
  for previous,other in texts:
   similarity=len(shingles&other)/max(1,min(len(shingles),len(other)))
   if similarity>.45:errors.append(f'Main copy overlaps excessively: {p} / {previous}: {similarity:.0%}')
  texts.append((p,shingles));checked+=1
 for p in list(folder.glob('*.html'))+list((folder/'collections').glob('*.html')):
  s=p.read_text(encoding='utf8')
  if 'noindex,follow' in s:continue
  visible=re.findall(r'<time datetime="([^"]+)">',s)
  ld=json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>',s,re.S)[1])
  webpage=next(n for n in ld['@graph'] if n['@type'] in ['WebPage','CollectionPage'])
  if visible!=[webpage['dateModified']]:errors.append(f'{p}: visible and structured dates differ')
  if dates.get(webpage['url'])!=webpage['dateModified']:errors.append(f'{p}: sitemap date differs')
  org=next(n for n in ld['@graph'] if n['@type']=='Organization')
  if org.get('foundingDate')!='2021':errors.append(f'{p}: founding year incorrect')
  if 'datePublished' in webpage:errors.append(f'{p}: draft must not invent a publication date')
print(f'Checked {checked} product articles and {len(dates)} dated indexable pages.')
if errors:print('\n'.join(errors));raise SystemExit(1)
print('PASS: no repeated main product paragraphs or excessive five-word overlap; visible, structured and sitemap dates agree; founding year 2021.')
