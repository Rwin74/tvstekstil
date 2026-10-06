"""Bridge validated CMS snapshots to the existing static multilingual site builder."""
import json, re, os, subprocess
from pathlib import Path
from html import escape
ROOT=Path(__file__).resolve().parents[1]
SEED=json.loads((ROOT/'data/cms-seed.json').read_text(encoding='utf-8'))
FILE=ROOT/'data/cms-published.json'
DOC=None
if FILE.exists():
 # Share the exact server validator with the build. Invalid snapshots stop publication.
 checked=subprocess.run(['node','-e',"const s=require('./lib/admin-security.cjs');s.validateDocument(JSON.parse(require('fs').readFileSync('data/cms-published.json','utf8')),true)"],cwd=ROOT,capture_output=True,text=True)
 if checked.returncode:raise ValueError('CMS snapshot validation failed; publication stopped.')
 DOC=json.loads(FILE.read_text(encoding='utf-8'))

def configure(namespace):
 if DOC is None:return
 import editorial_content,product_seo
 products=[p for p in DOC['products'] if p['active']]
 if not products:raise ValueError('At least one active product is required for the site.')
 namespace['ITEMS'][:]=[(p['slug'],p['group'],*(p['locales'][l]['name'] for l in ['en','fr','de','es']),p['locales']['en']['lead'],p['locales']['en']['paragraph1']) for p in products]
 for lang in ['en','fr','de','es']:
  editorial_content.PRODUCTS[lang][:]=[(p['locales'][lang]['lead'],p['locales'][lang]['heading'],p['locales'][lang]['paragraph1'],p['locales'][lang]['paragraph2']) for p in products]
  product_seo.DETAILS[lang][:]=[(p['locales'][lang]['specs'].replace('\n',';'),p['locales'][lang]['question'],p['locales'][lang]['answer']) for p in products]
  if lang!='en':namespace['DETAILS'][lang][:]=[p['locales'][lang]['paragraph1'] for p in products]

def product(slug):
 return next((p for p in DOC['products'] if p['slug']==slug),None) if DOC else None

def apply_page(lang,slug,title,description,body,note=''):
 if DOC is None:return title,description,body
 p=product(slug.split('/')[-1]) if slug.startswith('collections/') else None
 if p:
  row=p['locales'][lang];title=row['metaTitle'];description=row['metaDescription']
  if p['realPhoto']:
   notes={'en':'Product photograph. Ask us to confirm current availability and specifications.','fr':'Photographie du produit. Contactez-nous pour confirmer disponibilité et caractéristiques.','de':'Produktfoto. Fragen Sie nach aktueller Verfügbarkeit und Spezifikation.','es':'Fotografía del producto. Consulte disponibilidad y especificaciones actuales.'}
   if note:body=body.replace(note,notes[lang])
 key='home' if slug=='index' else slug
 row=DOC['pages'][lang].get(key)
 original=SEED['pages'][lang].get(key,{})
 if row:
  if row['title'] and row['title']!=original.get('title'):title=row['title']
  if row['description'] and row['description']!=original.get('description'):description=row['description']
  if row['heading'] and row['heading']!=original.get('heading'):body=re.sub(r'<h1>.*?</h1>',lambda _: '<h1>'+escape(row['heading']).replace('\n','<br>')+'</h1>',body,count=1,flags=re.S)
  if row['intro'] and row['intro']!=original.get('intro'):body=re.sub(r'(</h1>)\s*<p>.*?</p>',lambda m:m[1]+'<p>'+escape(row['intro']).replace('\n','<br>')+'</p>',body,count=1,flags=re.S)
 return title,description,body

def image_markup(slug,lang,base,eager):
 p=product(slug)
 if not p:return None
 path=p['image'];src=path if path.startswith('/cms-media/') else base+path.lstrip('/')
 alt=p['locales'][lang]['imageAlt']
 qualifier={'en':'illustrative product visual','fr':'visuel illustratif du produit','de':'illustrative Produktdarstellung','es':'imagen ilustrativa del producto'}[lang]
 if not p['realPhoto']:alt+=' — '+qualifier
 attr='fetchpriority="high"' if eager else 'loading="lazy"'
 return f'<img src="{escape(src,quote=True)}" alt="{escape(alt,quote=True)}" width="1536" height="1024" {attr} decoding="async">'

def apply_html(html,lang,slug):
 if DOC is None:return html
 old=SEED['settings'];new=DOC['settings']
 # JSON-LD must stay JSON even if text contains quote or ampersand characters.
 def structured(match):
  value=json.loads(match[1])
  def visit(item):
   if isinstance(item,dict):
    for key,val in item.items():
     if key=='foundingDate':item[key]=new['founded']
     elif key=='email' and val==old['email']:item[key]=new['email']
     elif key=='telephone':item[key]=re.sub(r'[^+0-9]','',new['phone'])
     elif key=='streetAddress':item[key]=new['address']
     else:item[key]=visit(val)
   elif isinstance(item,list):item=[visit(v) for v in item]
   elif isinstance(item,str):item=item.replace(old['address'],new['address']).replace(old['email'],new['email'])
   return item
  return '<script type="application/ld+json">'+json.dumps(visit(value),ensure_ascii=False).replace('<','\\u003c')+'</script>'
 html=re.sub(r'<script type="application/ld\+json">(.*?)</script>',structured,html,flags=re.S)
 html=html.replace(old['address'],escape(new['address'])).replace(old['phone'],escape(new['phone'])).replace('+905324770375',re.sub(r'[^+0-9]','',new['phone'])).replace(old['email'],escape(new['email'],quote=True))
 if old['address']!=new['address']:
  from urllib.parse import quote_plus
  html=html.replace('Ak%C3%A7e%C5%9Fme+2605+Sk+40+Merkezefendi+Denizli',quote_plus(new['address']))
 p=product(slug.split('/')[-1]) if slug.startswith('collections/') else None
 if p:
  html=re.sub(r'<meta property="og:image" content="[^"]*">',lambda _: '<meta property="og:image" content="https://www.tvstextile.com'+escape(p['image'],quote=True)+'">',html,count=1)
 if slug=='product-detail' and not any(p['active'] and p['slug']=='duvet-covers' for p in DOC['products']):
  target=next(p['slug'] for p in DOC['products'] if p['active'])
  html=html.replace('collections/duvet-covers.html','collections/'+target+'.html').replace('product=duvet-covers','product='+target)
 if new['founded']!=old['founded']:html=html.replace(old['founded'],new['founded'])
 # Keep downloaded briefs and texture inspection pointed at the selected CMS images.
 def catalog(match):
  data=json.loads(match[1])
  for row in data['products']:
   p=product(row['slug'])
   if p:row['image']=p['image'];row['realPhoto']=p['realPhoto']
  data['company']=DOC['settings']
  for name in ['en','fr','de','es']:
   if len([p for p in DOC['products'] if p['active']])!=12:
    data['copy']['leads'][0]={'en':'Explore our products and build your own shortlist.','fr':'Découvrez nos produits et composez votre sélection.','de':'Entdecken Sie unsere Produkte und stellen Sie Ihre Auswahl zusammen.','es':'Explore nuestros productos y prepare su selección.'}[lang]
  return '<script type="application/json" id="buyer-data">'+json.dumps(data,ensure_ascii=False).replace('<','\\u003c')+'</script>'
 return re.sub(r'<script type="application/json" id="buyer-data">(.*?)</script>',catalog,html,flags=re.S)
