import re
from html import escape

def refine_hero(lang,body,base,local,items,label_index):
 labels={'en':('THE MATERIAL EDIT','Three worlds. One textile story.','Explore a collection'),'fr':('L’ÉDITION MATIÈRES','Trois univers. Une histoire textile.','Découvrir une collection'),'de':('DIE MATERIALAUSWAHL','Drei Welten. Eine textile Geschichte.','Kollektion entdecken'),'es':('LA EDICIÓN DE TEXTURAS','Tres mundos. Una historia textil.','Explorar una colección')}[lang]
 featured=['muslin-duvet-covers','towels','baby-ponchos']
 panel=f'<div class="hero-material-edit"><div class="material-edit-head"><span class="eyebrow">{labels[0]}</span><span aria-hidden="true">01 — 03</span></div><p>{labels[1]}</p><div class="hero-samples">'
 for i,slug in enumerate(featured):
  name=next(it[label_index[lang]] for it in items if it[0]==slug)
  panel+=f'<a class="hero-sample" href="{base}{local(lang,"collections/"+slug)}" aria-label="{escape(labels[2]+": "+name,quote=True)}"><div><img src="{base}img/products/{slug}-768.webp" alt="" width="768" height="512" loading="lazy"><span aria-hidden="true">0{i+1}</span></div><span>{escape(name)}</span><b aria-hidden="true">↗</b></a>'
 panel+='</div></div>'
 body=re.sub(r'<div class="photo-caption">.*?</div>',panel,body,count=1,flags=re.S)
 body=body.replace('<div class="hero-copy">','<div class="hero-copy"><span class="hero-edition" aria-hidden="true">TVS / 2021 — 2026</span>',1)
 return body
