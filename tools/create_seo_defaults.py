"""Editorial defaults for untouched CMS fields; never overwrite an editor's copy."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
seed=json.loads((root/'data/cms-seed.json').read_text(encoding='utf-8'))
home={
'en':('Textile Manufacturer in Turkey | Bedding, Towels & Baby Textiles','Textile manufacturing.\nFrom our Denizli factory.'),
'fr':('Fabricant textile en Turquie | Linge de lit, bain et bébé','Fabricant de linge de maison.\nNotre usine à Denizli.'),
'de':('Textilhersteller Türkei | Bettwäsche, Handtücher & Babytextilien','Textilhersteller in der Türkei.\nUnsere Fabrik in Denizli.'),
'es':('Fabricante textil en Turquía | Ropa de cama, baño y bebé','Fabricamos textiles en Turquía.\nDesde nuestra fábrica en Denizli.')}
names={
'muslin-duvet-covers':['Muslin duvet covers','Housses de couette en gaze de coton','Musselin-Bettwäsche','Fundas nórdicas de muselina'],
'fitted-sheets':['Fitted sheets','Draps-housses','Spannbettlaken','Sábanas bajeras'],
'duvet-covers':['Duvet covers','Housses de couette','Bettbezüge','Fundas nórdicas'],
'bathrobes':['Bathrobes','Peignoirs','Bademäntel','Albornoces'],
'towels':['Towels','Serviettes de bain','Handtücher','Toallas'],
'sauna-wraps':['Sauna wraps','Kilts de sauna','Saunakilts','Pareos de sauna'],
'spa-headbands':['Spa headbands','Bandeaux de spa','Spa-Stirnbänder','Diademas de spa'],
'makeup-remover-cloths':['Makeup remover cloths','Lingettes démaquillantes','Abschminktücher','Toallitas desmaquillantes'],
'baby-ponchos':['Baby ponchos','Ponchos bébé','Baby-Ponchos','Ponchos para bebé'],
'baby-swaddles':['Baby swaddles','Langes bébé','Baby-Pucktücher','Muselinas para bebé'],
'baby-sleeping-bags':['Baby sleeping bags','Gigoteuses bébé','Baby-Schlafsäcke','Sacos de dormir para bebé'],
'baby-comforters':['Baby comforters','Doudous bébé','Baby-Schmusetücher','Doudous para bebé']}
result={'products':{},'pages':{}}
for lang,(title,heading) in home.items():result['pages'][lang]={'home':{'title':title,'heading':heading}}
for p in seed['products']:
 result['products'][p['slug']]={}
 for i,lang in enumerate(home):
  n=names[p['slug']][i]
  title={'en':f'{n} Manufacturer in Turkey | TVS Textile','fr':f'Fabricant de {n.lower()} en Turquie | TVS Textile','de':f'{n} Hersteller Türkei | TVS Textile','es':f'Fabricante de {n.lower()} en Turquía | TVS Textile'}[lang]
  result['products'][p['slug']][lang]={'name':n,'metaTitle':title}
(root/'data/seo-defaults.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
