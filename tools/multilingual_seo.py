"""Localized metadata, contextual links and multilingual sitemaps."""
from html import escape
from html.parser import HTMLParser
from xml.etree import ElementTree as ET
from editorial_content import PRODUCTS, CORE, FACTS, GROUPS, META, UPDATED

COPY={
 'en':dict(products='Home, Hotel & Baby Textile Collections',contact='Textile Enquiries & Export Projects',guide='Textile Sourcing Guide for International Buyers',origin='Turkish Textile Supplier',hub='Explore textiles for your project',read='Read the textile sourcing guide',parent='Browse the full collection',request='Discuss specifications and request a quote',crumb='Breadcrumb',related='Related products',group_intro=[
  'Build a coordinated bedding range with muslin duvet covers, fitted sheets and duvet covers. Compare the intended feel, mattress fit and closure details, then discuss sizes, materials and quantities for your market.',
  'Plan hotel and spa textile enquiries around laundering conditions and guest use. Explore bathrobes, towels, sauna wraps, spa headbands and makeup remover cloths; specify dimensions, fabric weight and finishing for each product.',
  'Explore baby ponchos, swaddles, sleeping bags and comforters for your collection. Define the intended age and use, then confirm materials, labelling and any safety or testing requirements for the final product and destination.'
 ],group_desc=['Bedding textiles from Türkiye: muslin duvet covers, fitted sheets and duvet covers. Discuss materials, sizes and quantities with TVS Textile.','Hotel and spa textiles from Türkiye: bathrobes, towels, sauna wraps and spa accessories. Discuss your project with TVS Textile.','Baby textiles from Türkiye: ponchos, swaddles, sleeping bags and comforters. Discuss product specifications and quantities with TVS Textile.'],guide_desc='Plan your textile sourcing enquiry: materials, dimensions, samples, quantities and delivery terms. A practical guide for international buyers.',contact_desc='Contact TVS Textile in Denizli, Türkiye for bedding, hotel, spa and baby textile enquiries. Share your product brief, quantities and destination.',products_desc='Explore bedding, hotel, spa and baby textile collections from Türkiye. Find product specifications to discuss with TVS Textile.',home_desc='Source home, hotel, spa and baby textiles from Denizli, Türkiye. Explore bedding, towels, bathrobes and baby collections with TVS Textile.',alt=['Bedroom with bed linen','Textiles for beach and spa settings','Baby collection lifestyle photograph'],locale='en_US'),
 'fr':dict(products='Collections de linge de maison, hôtel et bébé',contact='Contact et projets textiles internationaux',guide='Guide d’achat de textiles en Turquie',origin='Textiles de Turquie',hub='Choisir les textiles pour votre projet',read='Lire le guide d’achat de textiles en Turquie',parent='Découvrir toute la collection',request='Discuter des spécifications et demander un devis',crumb='Fil d’Ariane',related='Produits associés',group_intro=[
  'Composez une gamme de linge de lit avec des housses de couette en gaze de coton, des draps-housses et des housses de couette. Comparez la texture, les dimensions du matelas et les fermetures, puis précisez matières et quantités pour votre marché.',
  'Préparez vos achats de textiles pour hôtel et spa selon l’usage et les conditions de lavage. Découvrez peignoirs, serviettes, kilts de sauna, bandeaux et lingettes démaquillantes. Précisez dimensions, grammage et finitions pour chaque produit.',
  'Découvrez ponchos, langes, gigoteuses et doudous pour votre collection bébé. Définissez l’âge et l’usage prévus, puis confirmez matières, étiquetage et exigences de sécurité ou d’essais applicables au produit final et au marché visé.'
 ],group_desc=['Linge de lit de Turquie : housses de couette en gaze de coton, draps-housses et housses de couette. Discutez de votre collection avec TVS Textile.','Textiles hôtel et spa de Turquie : peignoirs, serviettes, kilts de sauna et accessoires. Préparez votre projet avec TVS Textile.','Textiles bébé de Turquie : ponchos, langes, gigoteuses et doudous. Discutez des spécifications et quantités avec TVS Textile.'],guide_desc='Préparez vos achats textiles en Turquie : matières, dimensions, échantillons, quantités et livraison. Guide pratique pour acheteurs internationaux.',contact_desc='Contactez TVS Textile à Denizli pour vos projets de linge de lit, hôtel, spa et bébé. Précisez produits, quantités et destination.',products_desc='Découvrez les collections de linge de maison, hôtel, spa et bébé de Turquie. Préparez votre demande auprès de TVS Textile.',home_desc='Linge de maison, textiles hôtel, spa et bébé de Denizli, Turquie. Découvrez les collections de literie, serviettes et peignoirs de TVS Textile.',alt=['Chambre avec linge de lit','Textiles dans un cadre de plage et de spa','Photographie d’ambiance de la collection bébé'],locale='fr_FR'),
 'de':dict(products='Heimtextilien, Hoteltextilien und Babytextilien',contact='Kontakt und internationale Textilprojekte',guide='Textileinkauf in der Türkei: Einkaufsleitfaden',origin='Textilien aus der Türkei',hub='Textilien für Ihr Projekt auswählen',read='Einkaufsleitfaden für Textilien aus der Türkei lesen',parent='Die gesamte Kollektion entdecken',request='Spezifikationen besprechen und Angebot anfragen',crumb='Brotkrümelnavigation',related='Passende Produkte',group_intro=[
  'Stellen Sie ein abgestimmtes Bettwäschesortiment mit Musselin-Bettwäsche, Spannbettlaken und Bettbezügen zusammen. Vergleichen Sie Haptik, Matratzenmaße und Verschlüsse und besprechen Sie Materialien und Mengen für Ihren Markt.',
  'Planen Sie Hotel- und Spa-Textilien nach Nutzung und Waschbedingungen. Entdecken Sie Bademäntel, Handtücher, Saunakilts, Spa-Stirnbänder und Abschminktücher. Geben Sie für jedes Produkt Maße, Stoffgewicht und Verarbeitung an.',
  'Entdecken Sie Baby-Ponchos, Pucktücher, Schlafsäcke und Schmusetücher für Ihre Kollektion. Definieren Sie Alter und Verwendung und klären Sie Material, Kennzeichnung sowie Sicherheits- und Prüfanforderungen für Endprodukt und Zielmarkt.'
 ],group_desc=['Bettwäsche aus der Türkei: Musselin-Bettwäsche, Spannbettlaken und Bettbezüge. Besprechen Sie Material, Maße und Mengen mit TVS Textile.','Hotel- und Spa-Textilien aus der Türkei: Bademäntel, Handtücher, Saunakilts und Zubehör. Besprechen Sie Ihr Projekt mit TVS Textile.','Babytextilien aus der Türkei: Ponchos, Pucktücher, Schlafsäcke und Schmusetücher. Besprechen Sie Spezifikationen und Mengen mit TVS Textile.'],guide_desc='Planen Sie Ihren Textileinkauf: Material, Maße, Muster, Mengen und Lieferbedingungen. Ein Einkaufsleitfaden für internationale Käufer.',contact_desc='Kontaktieren Sie TVS Textile in Denizli für Bettwäsche, Hotel-, Spa- und Babytextilien. Teilen Sie Produktwünsche, Mengen und Zielland mit.',products_desc='Entdecken Sie Heim-, Hotel-, Spa- und Babytextilien aus der Türkei. Besprechen Sie die Anforderungen Ihrer Kollektion mit TVS Textile.',home_desc='Heim-, Hotel-, Spa- und Babytextilien aus Denizli, Türkei. Entdecken Sie Bettwäsche, Handtücher und Bademäntel für Ihr Projekt mit TVS Textile.',alt=['Schlafzimmer mit Bettwäsche','Textilien in einer Strand- und Spa-Umgebung','Atmosphärisches Foto der Babykollektion'],locale='de_DE'),
 'es':dict(products='Colecciones textiles de hogar, hotel y bebé',contact='Contacto y proyectos textiles internacionales',guide='Guía de compra de textiles en Turquía',origin='Textiles de Turquía',hub='Elegir textiles para su proyecto',read='Leer la guía de compra de textiles en Turquía',parent='Descubrir toda la colección',request='Consultar especificaciones y solicitar presupuesto',crumb='Ruta de navegación',related='Productos relacionados',group_intro=[
  'Prepare una colección de ropa de cama con fundas nórdicas de muselina, sábanas bajeras y fundas nórdicas. Compare textura, ajuste al colchón y cierres; después indique materiales, medidas y cantidades para su mercado.',
  'Planifique textiles de hotel y spa según el uso y las condiciones de lavado. Descubra albornoces, toallas, pareos de sauna, diademas y toallitas desmaquillantes. Especifique medidas, gramaje y acabados de cada producto.',
  'Descubra ponchos, muselinas, sacos de dormir y dou dou para su colección de bebé. Defina edad y uso previstos y confirme materiales, etiquetado y requisitos de seguridad o ensayos para el producto final y el mercado de destino.'
 ],group_desc=['Ropa de cama de Turquía: fundas nórdicas de muselina, sábanas bajeras y fundas nórdicas. Consulte materiales y cantidades con TVS Textile.','Textiles de hotel y spa de Turquía: albornoces, toallas, pareos de sauna y accesorios. Comente su proyecto con TVS Textile.','Textiles para bebé de Turquía: ponchos, muselinas, sacos de dormir y dou dou. Consulte especificaciones y cantidades con TVS Textile.'],guide_desc='Prepare su compra de textiles: materiales, medidas, muestras, cantidades y condiciones de entrega. Guía para compradores internacionales.',contact_desc='Contacte con TVS Textile en Denizli para ropa de cama y textiles de hotel, spa y bebé. Indique productos, cantidades y destino.',products_desc='Explore textiles para hogar, hotel, spa y bebé de Turquía. Comente las especificaciones de su colección con TVS Textile.',home_desc='Textiles de hogar, hotel, spa y bebé de Denizli, Turquía. Descubra ropa de cama, toallas y albornoces para su proyecto con TVS Textile.',alt=['Dormitorio con ropa de cama','Textiles en un entorno de playa y spa','Fotografía de ambiente de la colección de bebé'],locale='es_ES')
}

def enrich(lang,slug,title,description,body,base,t,items,group_slugs,label_index,local,domain,route,schema,noindex,details):
 c=COPY[lang]; idx=label_index[lang]; tail=slug.split('/')[-1]
 item=next((it for it in items if it[0]==tail),None) if slug.startswith('collections/') else None
 group=group_slugs.index(tail) if slug.startswith('collections/') and tail in group_slugs else None
 if slug in ['products','contact','sourcing-guide']:
  title=c[{'sourcing-guide':'guide'}.get(slug,slug)]+' | TVS Textile'
  description=c[{'sourcing-guide':'guide_desc'}.get(slug,slug+'_desc')]
 if slug=='index':description={'en':'We manufacture home, hotel, spa and baby textiles in our own Denizli factory. Founded in 2021, TVS Textile welcomes international buyer enquiries.','fr':'Nous fabriquons du linge de maison et des textiles hôtel, spa et bébé dans notre usine à Denizli. TVS Textile a été créée en 2021.','de':'Wir fertigen Heim-, Hotel-, Spa- und Babytextilien in unserer eigenen Fabrik in Denizli. TVS Textile wurde 2021 gegründet.','es':'Fabricamos textiles de hogar, hotel, spa y bebé en nuestra propia fábrica de Denizli. Fundamos TVS Textile en 2021.'}[lang]
 if slug in ['about','products','contact','sourcing-guide']:description=META[lang][{'sourcing-guide':'guide'}.get(slug,slug)]
 if group is not None:description=t['groups'][group]+': '+GROUPS[lang][group].split('. ')[0]+'.'
 if item:
  description=item[idx]+': '+PRODUCTS[lang][items.index(item)][0]
 def link(s,label):return f'<a href="{base}{local(lang,s)}">{escape(label)}</a>'
 chain=[('index',t['home'])]
 if slug.startswith('collections/'):
  chain.append(('products',t['nav'][0]))
  if item:chain.append(('collections/'+group_slugs[item[1]],t['groups'][item[1]]))
 if slug!='index':chain.append((slug,item[idx] if item else t['groups'][group] if group is not None else title.split(' | ')[0]))
 if slug not in ['index','404']:
  breadcrumbs=f'<nav class="breadcrumbs" aria-label="{c["crumb"]}"><ol>'+''.join('<li>'+ (f'<span aria-current="page">{escape(label)}</span>' if i==len(chain)-1 else link(s,label))+'</li>' for i,(s,label) in enumerate(chain))+'</ol></nav>'
  body=breadcrumbs+body
 for node in schema['@graph']:
  if node['@type'] in ['WebPage','CollectionPage']:node.update(name=title,description=description)
  if node['@type']=='BreadcrumbList':node['itemListElement']=[{'@type':'ListItem','position':i+1,'name':label,'item':domain+'/'+route(lang,s)} for i,(s,label) in enumerate(chain)]
 visual_alts={'en':['Muslin bedding concept in a warm bedroom','Folded hotel and spa towel concept','Hooded baby poncho concept'],'fr':['Concept de linge de lit en gaze de coton','Concept de serviettes pliées pour hôtel et spa','Concept de poncho bébé à capuche'],'de':['Konzeptbild von Musselin-Bettwäsche','Konzeptbild gefalteter Hotel- und Spa-Handtücher','Konzeptbild eines Baby-Ponchos mit Kapuze'],'es':['Concepto de ropa de cama de muselina','Concepto de toallas dobladas para hotel y spa','Concepto de poncho para bebé con capucha']}[lang]
 body=body.replace('alt="Bedroom textile collection"','alt="'+visual_alts[0]+'"').replace('alt="Hospitality and spa collection"','alt="'+visual_alts[1]+'"').replace('alt="Baby textile collection"','alt="'+visual_alts[2]+'"')
 section=''
 if group is not None or item:
  g=group if group is not None else item[1]
  anchors=[link('collections/'+it[0],it[idx]) for it in items if it[1]==g and (not item or it[0]!=item[0])]
  section=f'<section class="section seo-context"><span class="eyebrow">{t["buyer"]}</span><h2>{t["groups"][g]}</h2><div class="seo-links">'+''.join(anchors)+'</div><p class="sourcing-path">'+link('sourcing-guide',c['read'])+' · '+link('contact',c['request'])+'</p></section>'
 elif slug in ['index','sourcing-guide','about']:
  section=f'<section class="section seo-hub"><h2>{c["hub"]}</h2><div class="seo-hub-grid">'
  for g,group_slug in enumerate(group_slugs):
   section+='<article><h3>'+link('collections/'+group_slug,t['groups'][g])+'</h3><ul>'+''.join('<li>'+link('collections/'+it[0],it[idx])+'</li>' for it in items if it[1]==g)+'</ul></article>'
  section+='</div>'
  if slug!='sourcing-guide':section+='<p class="sourcing-path">'+link('sourcing-guide',c['read'])+'</p>'
  section+='</section>'
 if section:
  marker='<section class="project-section">'
  body=body.replace(marker,section+marker,1) if marker in body else body+section
 return title,description,body

class SitemapDoc(HTMLParser):
 def __init__(self):super().__init__();self.canonical=None;self.alts=[];self.noindex=False
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='meta' and a.get('name')=='robots' and 'noindex' in a.get('content',''):self.noindex=True
  if tag=='link' and a.get('rel')=='canonical':self.canonical=a['href']
  if tag=='link' and a.get('rel')=='alternate':self.alts.append((a['hreflang'],a['href']))

def write_sitemap(root,paths):
 import re,json
 ns='http://www.sitemaps.org/schemas/sitemap/0.9';x='http://www.w3.org/1999/xhtml'
 ET.register_namespace('',ns);ET.register_namespace('xhtml',x)
 sitemap=ET.Element('{'+ns+'}urlset')
 for p in sorted(paths):
  doc=SitemapDoc();doc.feed(p.read_text(encoding='utf-8'))
  if doc.noindex or not doc.canonical:continue
  entry=ET.SubElement(sitemap,'{'+ns+'}url');ET.SubElement(entry,'{'+ns+'}loc').text=doc.canonical
  source=p.read_text(encoding='utf-8')
  graph=json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>',source,re.S)[1])['@graph']
  modified=next(n.get('dateModified',UPDATED) for n in graph if n['@type'] in ['WebPage','CollectionPage'])
  ET.SubElement(entry,'{'+ns+'}lastmod').text=modified
  for lang,url in doc.alts:ET.SubElement(entry,'{'+x+'}link',{'rel':'alternate','hreflang':lang,'href':url})
 ET.indent(sitemap,space='  ')
 ET.ElementTree(sitemap).write(root/'sitemap.xml',encoding='utf-8',xml_declaration=True)
