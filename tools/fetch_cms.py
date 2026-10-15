"""Fetch only the public CMS projection. No private records enter Git."""
import os,json,re,urllib.request,urllib.error,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
url=os.environ.get('CMS_SUPABASE_URL','');key=os.environ.get('CMS_SUPABASE_ANON_KEY','')
if not re.fullmatch(r'https://[a-z0-9]+\.supabase\.co',url) or not key:raise SystemExit('CMS build connection is missing.')
headers={'apikey':key,'Content-Type':'application/json'}
if not key.startswith('sb_'):headers['Authorization']='Bearer '+key
request=urllib.request.Request(url+'/rest/v1/rpc/cms_published',data=b'{}',method='POST',headers=headers)
for attempt in range(4):
 try:
  with urllib.request.urlopen(request,timeout=20) as response:raw=response.read(1100001)
  break
 except urllib.error.URLError as error:
  if isinstance(error,urllib.error.HTTPError) and error.code not in [429,500,502,503,504]:raise
  if attempt==3:raise
  print('CMS temporarily unavailable; retrying public snapshot download.',flush=True)
  time.sleep(5*(attempt+1))
if len(raw)>1100000:raise SystemExit('CMS snapshot too large.')
data=json.loads(raw)
if not isinstance(data,dict):raise SystemExit('No published snapshot exists.')
(ROOT/'data/cms-published.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
subprocess.run(['node','-e',"require('./lib/admin-security.cjs').validateDocument(require('./data/cms-published.json'),true)"],cwd=ROOT,check=True)
active={p['slug'] for p in data['products'] if p['active']};groups={'home-textiles','hotel-spa-textiles','baby-textiles'}
for lang in ['', 'fr','de','es']:
 directory=(ROOT/lang/'collections').resolve()
 for page in directory.glob('*.html'):
  if page.stem not in active|groups and page.resolve().parent==directory:page.unlink()
print('Validated public CMS snapshot downloaded; no private records exported.')
