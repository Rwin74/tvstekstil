'use strict';
const fs=require('node:fs');
const path=require('node:path');
const {spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..');
const output=path.join(root,'_site');
const publicKey=process.env.SUPABASE_PUBLISHABLE_KEY||process.env.SUPABASE_ANON_KEY;
const buildEnv={...process.env,CMS_SUPABASE_URL:process.env.SUPABASE_URL||'',CMS_SUPABASE_ANON_KEY:publicKey||''};
function python(script){const r=spawnSync(process.platform==='win32'?'python':'python3',['tools/'+script],{cwd:root,env:buildEnv,stdio:'inherit'});if(r.error)throw r.error;if(r.status!==0)throw new Error('Build validation failed: '+script);}
if(process.env.VERCEL_ENV==='production'||(buildEnv.CMS_SUPABASE_URL&&publicKey))python('fetch_cms.py');
python('build_corporate.py');
for(const script of ['check_corporate.py','check_multilingual_seo.py'])python(script);
if(fs.existsSync(path.join(root,'data/cms-published.json')))python('check_cms_output.py');
if(output!==path.resolve(root,'_site')||!output.startsWith(root+path.sep))throw new Error('Invalid build output path');
fs.rmSync(output,{recursive:true,force:true});
fs.mkdirSync(output,{recursive:true});
for(const file of fs.readdirSync(root)){if(file.endsWith('.html')||['robots.txt','sitemap.xml','site.webmanifest'].includes(file))fs.copyFileSync(path.join(root,file),path.join(output,file));}
for(const folder of ['admin','collections','css','de','es','fr','img','js','kategori','lang'])fs.cpSync(path.join(root,folder),path.join(output,folder),{recursive:true});
console.log('Validated multilingual CMS site packaged; server source and private records excluded.');
