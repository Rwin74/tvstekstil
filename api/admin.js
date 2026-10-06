'use strict';
const crypto=require('node:crypto');
const sharp=require('sharp');
const S=require('../lib/admin-security.cjs');
const DB=require('../lib/supabase.cjs');
const seed=require('../data/cms-seed.json');
const env=process.env;
function config(){const keys=DB.keys(env);S.ensure(/^https:\/\/[a-z0-9]+\.supabase\.co$/.test(env.SUPABASE_URL||'')&&keys.publicKey&&keys.secretKey,503,'Panel bağlantısı henüz tamamlanmadı.');S.seal({test:true},env);}
async function remote(path,{token,method='GET',body,service=false,headers={}}={}){
 const keys=DB.keys(env),key=service?keys.secretKey:keys.publicKey;
 const response=await fetch(env.SUPABASE_URL+path,{method,headers:{...DB.headers(key,service?undefined:token),'Content-Type':'application/json',...headers},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(12000)});
 const result=await response.json().catch(()=>null);
 if(!response.ok){if(response.status===409||result?.message?.includes('CMS_CONFLICT'))throw new S.HttpError(409,'İçerik başka bir sekmede değişmiş. Yeniden yükleyin.');throw new S.HttpError(response.status===401||response.status===403?401:502,'İşlem tamamlanamadı. Bağlantıyı veya oturumu kontrol edin.');}return result;
}
async function admin(token){const user=await remote('/auth/v1/user',{token});S.ensure(user&&user.id,401,'Giriş yapın.');const allowed=await remote('/rest/v1/rpc/cms_is_admin',{token,method:'POST',body:{}});S.ensure(allowed===true,403,'Bu hesap için yönetici erişimi yok.');return user;}
async function rate(req,purpose,limit){
 // On Vercel this header is set by the edge, rather than by the caller.
 const ip=env.VERCEL==='1'?(req.headers['x-vercel-forwarded-for']||'unknown'):req.socket?.remoteAddress||'local';
 const key=crypto.createHmac('sha256',Buffer.from(env.ADMIN_SESSION_KEY,'base64')).update(String(ip)).digest('hex');
 const allowed=await remote('/rest/v1/rpc/cms_rate_limit',{service:true,method:'POST',body:{bucket:purpose+':'+key,max_attempts:limit,window_seconds:900}});S.ensure(allowed===true,429,'Çok fazla deneme. 15 dakika sonra tekrar deneyin.');
}
function setCookie(res,value,seconds){res.setHeader('Set-Cookie',`${S.COOKIE}=${value}; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age=${seconds}`);}
async function dispatch(){S.ensure(env.ADMIN_GITHUB_PUBLISH_TOKEN,503,'Yayın bağlantısı henüz kurulmadı.');const r=await fetch('https://api.github.com/repos/Rwin74/tvstekstil/dispatches',{method:'POST',headers:{Authorization:'Bearer '+env.ADMIN_GITHUB_PUBLISH_TOKEN,Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','Content-Type':'application/json'},body:JSON.stringify({event_type:'cms-publish'}),signal:AbortSignal.timeout(12000)});S.ensure(r.ok,502,'İçerik kaydedildi; yayın kuyruğu başlatılamadı. Yayını tekrar dene.');}
module.exports=async function(req,res){
 res.setHeader('Cache-Control','no-store');res.setHeader('X-Content-Type-Options','nosniff');res.setHeader('X-Robots-Tag','noindex, nofollow');res.setHeader('Referrer-Policy','no-referrer');
 try{
 const action=req.query?.action||new URL(req.url,S.ORIGIN).searchParams.get('action')||'status';const session=S.cookie(req,env);
 if(action==='status') {S.ensure(req.method==='GET',405,'İstek yöntemi geçersiz.');let configured=true;try{config();}catch{configured=false;}if(!configured||!session)return res.status(200).json({configured,authenticated:false});const user=await admin(session.token);return res.status(200).json({configured,authenticated:true,email:user.email,csrf:session.csrf,expires:session.exp});}
 config();
 if(action==='login'){
 S.ensure(req.method==='POST',405,'İstek yöntemi geçersiz.');S.sameOrigin(req);const data=S.jsonBody(req,2000);await rate(req,'login',5);S.str(data.email,254,true);S.ensure(typeof data.password==='string'&&data.password.length>=12&&data.password.length<=200,400,'Şifre en az 12 karakter olmalı.');
 const account=crypto.createHmac('sha256',Buffer.from(env.ADMIN_SESSION_KEY,'base64')).update(data.email.trim().toLowerCase()).digest('hex');
 const attempts=await remote('/rest/v1/rpc/cms_rate_limit',{service:true,method:'POST',body:{bucket:'account:'+account,max_attempts:10,window_seconds:900}});S.ensure(attempts===true,429,'Çok fazla deneme. 15 dakika sonra tekrar deneyin.');
 let result;try{result=await remote('/auth/v1/token?grant_type=password',{method:'POST',body:{email:data.email,password:data.password}});await admin(result.access_token);}catch{throw new S.HttpError(401,'E-posta, şifre veya yönetici yetkisi doğrulanamadı.');}
 const age=Math.min(2400,Number(result.expires_in)||0);S.ensure(age>0,401,'Oturum oluşturulamadı.');const value={token:result.access_token,csrf:crypto.randomBytes(24).toString('hex'),exp:Date.now()+age*1000};setCookie(res,S.seal(value,env),age);return res.status(200).json({ok:true});}
 S.ensure(session,401,'Giriş yapın.');await admin(session.token);
 if(req.method!=='GET')S.csrf(req,session);
 if(action==='logout'){S.ensure(req.method==='POST',405,'İstek yöntemi geçersiz.');setCookie(res,'',0);await remote('/auth/v1/logout',{token:session.token,method:'POST'}).catch(()=>{});return res.status(200).json({ok:true});}
 if(action==='content'){S.ensure(req.method==='GET',405,'İstek yöntemi geçersiz.');const rows=await remote('/rest/v1/cms_documents?id=eq.site&select=payload,version,published_at',{token:session.token});return res.status(200).json(rows[0]||{payload:seed,version:0,published_at:null});}
 if(action==='save'||action==='publish'){
 S.ensure(req.method==='POST',405,'İstek yöntemi geçersiz.');const data=S.jsonBody(req);S.ensure(Number.isInteger(data.version)&&data.version>=0,400,'İçerik sürümü geçersiz.');S.validateDocument(data.payload,action==='publish');if(action==='publish')S.ensure(env.ADMIN_GITHUB_PUBLISH_TOKEN,503,'Yayın bağlantısı henüz kurulmadı.');
 const result=await remote('/rest/v1/rpc/cms_save',{token:session.token,method:'POST',body:{content:data.payload,expected_version:data.version,make_public:action==='publish'}});
 if(action==='publish')await dispatch();return res.status(200).json({version:result,published:action==='publish'});}
 if(action==='retry-publish'){S.ensure(req.method==='POST',405,'İstek yöntemi geçersiz.');await dispatch();return res.status(200).json({ok:true});}
 if(action==='image'){
 S.ensure(req.method==='POST',405,'İstek yöntemi geçersiz.');await rate(req,'image',30);const data=S.jsonBody(req,3000000);S.ensure(typeof data.base64==='string'&&/^[A-Za-z0-9+/]+={0,2}$/.test(data.base64),400,'Görsel dosyası geçersiz.');const input=Buffer.from(data.base64,'base64');S.ensure(input.length<=2100000,413,'Görsel en fazla 2 MB olabilir.');
 const decoder=sharp(input,{limitInputPixels:16000000,animated:false});const meta=await decoder.metadata();S.ensure(['jpeg','png','webp'].includes(meta.format)&&(!meta.pages||meta.pages===1),400,'Tek kare JPEG, PNG veya WebP yükleyin.');
 const output=await decoder.rotate().resize({width:1536,height:1536,fit:'inside',withoutEnlargement:true}).webp({quality:88}).toBuffer();const name=crypto.randomUUID()+'.webp';
 const r=await fetch(env.SUPABASE_URL+'/storage/v1/object/product-media/'+name,{method:'POST',headers:{...DB.headers(DB.keys(env).secretKey),'Content-Type':'image/webp','x-upsert':'false'},body:output,signal:AbortSignal.timeout(15000)});S.ensure(r.ok,502,'Görsel depoya kaydedilemedi.');return res.status(200).json({path:'/cms-media/'+name});}
 if(action==='enquiries'){S.ensure(req.method==='GET',405,'İstek yöntemi geçersiz.');const rows=await remote('/rest/v1/cms_enquiries?select=id,created_at,payload,mail_status,read_at&order=created_at.desc&limit=100',{token:session.token});return res.status(200).json(rows);}
 if(action==='read-enquiry'){S.ensure(req.method==='POST',405,'İstek yöntemi geçersiz.');const data=S.jsonBody(req,1000);S.ensure(/^[a-f0-9-]{36}$/.test(data.id),400,'Mesaj kimliği geçersiz.');await remote('/rest/v1/rpc/cms_read_enquiry',{token:session.token,method:'POST',body:{enquiry_id:data.id}});return res.status(200).json({ok:true});}
 throw new S.HttpError(404,'İşlem bulunamadı.');
 }catch(error){res.status(error.status||500).json({error:error.status?error.message:'İşlem tamamlanamadı. Daha sonra tekrar deneyin.'});}
};
