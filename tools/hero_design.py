"""Crawlable collection entrance, shared by all four languages."""
import re
from html import escape
COPY={
'en':('THREE COLLECTIONS · ONE MANUFACTURER','Choose the world you are creating.','Home textiles','Hotel & spa textiles','Baby textiles','Bedding, muslin duvet covers & fitted sheets','Towels, bathrobes & spa accessories','Ponchos, swaddles, sleeping bags & comforters','Explore collection','Our own factory in Denizli · Established 2021'),
'fr':('TROIS COLLECTIONS · UN FABRICANT','À chaque projet, son univers textile.','Linge de maison','Textiles hôtel & spa','Textiles bébé','Housses de couette, gaze de coton et draps-housses','Serviettes, peignoirs et accessoires de spa','Ponchos, langes, gigoteuses et doudous','Découvrir la collection','Notre usine à Denizli · Depuis 2021'),
'de':('DREI KOLLEKTIONEN · EIN HERSTELLER','Ihr Vorhaben. Ihre textile Welt.','Heimtextilien','Hotel- & Spa-Textilien','Babytextilien','Bettbezüge, Musselin-Bettwäsche und Spannbettlaken','Handtücher, Bademäntel und Spa-Zubehör','Ponchos, Pucktücher, Schlafsäcke und Schmusetücher','Kollektion entdecken','Eigene Fabrik in Denizli · Seit 2021'),
'es':('TRES COLECCIONES · UN FABRICANTE','Un universo textil para cada proyecto.','Textiles para el hogar','Textiles de hotel & spa','Textiles para bebé','Fundas nórdicas, muselina y sábanas bajeras','Toallas, albornoces y accesorios de spa','Ponchos, muselinas, sacos de dormir y doudous','Explorar colección','Nuestra fábrica en Denizli · Desde 2021')}
def refine_hero(lang,body,base,local,items,label_index):
 import cms_content
 c=COPY[lang]
 match=re.search(r'<section class="hero">(.*?)</section>',body,re.S)
 if not match:return body
 old=match[1]
 h1=re.search(r'<h1>.*?</h1>',old,re.S).group()
 intro=re.search(r'</h1>\s*(<p>.*?</p>)',old,re.S).group(1)
 cards=[]
 for g,slug in enumerate(['home-textiles','hotel-spa-textiles','baby-textiles']):
  available=[it for it in items if it[1]==g]
  if not available:continue
  target=['muslin-duvet-covers','towels','baby-ponchos'][g]
  featured=next((it[0] for it in available if it[0]==target),available[0][0])
  picture=cms_content.image_markup(featured,lang,base,g==0) or f'<img src="{base}img/products/{featured}-768.webp" alt="" width="768" height="512" loading="lazy">'
  cards.append(f'<a class="portal-card portal-{g}" href="{base}{local(lang,"collections/"+slug)}"><div class="portal-picture">{picture}<span class="portal-number" aria-hidden="true">0{g+1}</span><span class="portal-arrow" aria-hidden="true">↗</span></div><div class="portal-caption"><h2>{escape(c[g+2])}</h2><p>{escape(c[g+5])}</p><span class="portal-link">{escape(c[8])} <span aria-hidden="true">↗</span></span></div></a>')
 hero=f'<section class="collection-hero"><div class="portal-heading"><div><span class="eyebrow">{escape(c[0])}</span>{h1}</div><div class="portal-intro">{intro}<span class="portal-factory">{escape(c[9])}</span></div></div><div class="portal-divider"><span>{escape(c[1])}</span><span aria-hidden="true">01 — 03</span></div><div class="portal-grid">'+''.join(cards)+'</div></section>'
 return body[:match.start()]+hero+body[match.end():]
