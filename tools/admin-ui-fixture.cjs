// Isolated UI test fixture. Binds localhost only. Never included in Vercel deployment.
// This mock has no production authentication, credentials, database or mail access.
const http=require('node:http'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..');let payload=structuredClone(require('../data/cms-seed.json')),version=0;
http.createServer(async(req,res)=>{
 const url=new URL(req.url,'http://localhost');
 if(url.pathname==='/api/admin'){let raw='';for await(const c of req)raw+=c;const body=raw?JSON.parse(raw):{};const action=url.searchParams.get('action');res.setHeader('Content-Type','application/json');let result;
 if(action==='status')result={configured:true,authenticated:true,csrf:'local-ui-test-fixture'};
 else if(action==='content')result={payload,version,published_at:null};
 else if(action==='save'){if(body.version!==version){res.statusCode=409;result={error:'Yerel test: sürüm çakışması.'};}else{require('../lib/admin-security.cjs').validateDocument(body.payload);payload=body.payload;result={version:++version};}}
 else if(action==='enquiries')result=[];
 else if(action==='publish'){require('../lib/admin-security.cjs').validateDocument(body.payload,true);payload=body.payload;res.statusCode=502;result={error:'Yerel test: yayın bağlantısı geçici olarak başarısız.',version:++version,saved:true,retryPublish:true};}
 else if(action==='retry-publish')result={ok:true};
 else{res.statusCode=503;result={error:'Bu yalnızca yerel arayüz testidir. Gerçek giriş/yayın/mail bağlı değil.'};}
 return res.end(JSON.stringify(result));}
 const name=url.pathname.endsWith('/')?url.pathname+'index.html':url.pathname;const file=path.resolve(root,'.'+decodeURIComponent(name));if(!file.startsWith(root+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile()){res.writeHead(404);return res.end();}
 const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.webp':'image/webp'};res.setHeader('Content-Type',mime[path.extname(file)]||'application/octet-stream');
 if(name==='/admin/index.html')return res.end(fs.readFileSync(file,'utf8').replace('YÖNETİM STÜDYOSU','YEREL ARAYÜZ TESTİ • HESAP BAĞLI DEĞİL'));
 fs.createReadStream(file).pipe(res);
}).listen(8788,'127.0.0.1',()=>console.log('UI fixture (no real backend): http://127.0.0.1:8788/admin/'));
