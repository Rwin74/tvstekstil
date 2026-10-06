'use strict';
const crypto = require('node:crypto');
const ORIGIN = 'https://www.tvstextile.com';
const COOKIE = '__Host-tvs-admin';
const LANGS = ['en','fr','de','es'];
const FIELDS = {name:120,lead:700,heading:200,paragraph1:4000,paragraph2:4000,metaTitle:180,metaDescription:500,question:500,answer:2500,specs:2000,imageAlt:250};
class HttpError extends Error { constructor(status,message){super(message);this.status=status;} }
function ensure(condition,status,message){if(!condition)throw new HttpError(status,message);}
function object(value){return value && typeof value==='object' && !Array.isArray(value);}
function keys(value,allowed){ensure(object(value)&&Object.keys(value).every(k=>allowed.includes(k)),400,'Geçersiz veri alanları.');}
function str(value,max,required=false){ensure(typeof value==='string'&&value.length<=max&&(!required||value.trim().length>0)&&!/[\u0000-\u0008\u000b\u000c\u000e-\u001f<>]/.test(value),400,'Metinleri belirtilen uzunlukta, HTML kullanmadan girin.');return value;}
function imagePath(value){return /^\/img\/products\/[a-z0-9-]+(?:-768)?\.webp$/.test(value)||/^\/cms-media\/[a-f0-9-]{36}\.webp$/.test(value);}
function validateDocument(doc,publishing=false){
 keys(doc,['schemaVersion','settings','pages','products']);ensure(doc.schemaVersion===1,400,'İçerik sürümü geçersiz.');
 keys(doc.settings,['address','phone','email','founded']);str(doc.settings.address,500,true);str(doc.settings.phone,40,true);str(doc.settings.email,254,true);
 ensure(/^\+[0-9 ()-]{8,30}$/.test(doc.settings.phone)&&/^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/.test(doc.settings.email)&&/^\d{4}$/.test(doc.settings.founded),400,'İletişim bilgilerini kontrol edin.');
 keys(doc.pages,LANGS);ensure(LANGS.every(lang=>object(doc.pages[lang])),400,'Dört dilin sayfa alanları eksik.');
 for(const lang of LANGS){const slugs=['home','about','sourcing-guide','contact'];keys(doc.pages[lang],slugs);ensure(slugs.every(slug=>object(doc.pages[lang][slug])),400,'Sayfa alanları eksik.');for(const page of Object.values(doc.pages[lang])){const fields=['title','description','heading','intro'];keys(page,fields);ensure(fields.every(field=>typeof page[field]==='string'),400,'Sayfa alanları eksik.');for(const [key,value]of Object.entries(page))str(value,key==='intro'?6000:500);}}
 ensure(Array.isArray(doc.products)&&doc.products.length>0&&doc.products.length<=200,400,'Ürün sayısı 1–200 arasında olmalı.');const seen=new Set();
 for(const p of doc.products){keys(p,['slug','group','active','image','realPhoto','locales','updated']);
 ensure(/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(p.slug)&&p.slug.length<=80&&!['home-textiles','hotel-spa-textiles','baby-textiles'].includes(p.slug)&&!seen.has(p.slug),400,'Ürün adresi geçersiz veya tekrarlanmış.');seen.add(p.slug);
 ensure(Number.isInteger(p.group)&&p.group>=0&&p.group<=2&&typeof p.active==='boolean'&&typeof p.realPhoto==='boolean',400,'Ürün kategorisi geçersiz.');
 ensure(typeof p.image==='string'&&imagePath(p.image),400,'Görseli panelden yükleyin.');ensure(/^\d{4}-\d{2}-\d{2}$/.test(p.updated),400,'Güncelleme tarihi geçersiz.');keys(p.locales,LANGS);
 for(const lang of LANGS){keys(p.locales[lang],Object.keys(FIELDS));ensure(Object.keys(p.locales[lang]).length===Object.keys(FIELDS).length,400,'Ürün alanları eksik.');for(const [key,max]of Object.entries(FIELDS))str(p.locales[lang][key],max,publishing&&p.active);
 if(publishing&&p.active){const rows=p.locales[lang].specs.split('\n');ensure(rows.length>=1&&rows.length<=10&&rows.every(row=>!row.includes(';')&&row.split('|').length===2&&row.split('|').every(x=>x.trim())),400,'Özellikler: her satıra Başlık|Açıklama yazın; noktalı virgül kullanmayın.');}}
 }
 if(publishing)ensure(doc.products.some(p=>p.active),400,'Yayın için en az bir aktif ürün gerekli.');
 ensure(Buffer.byteLength(JSON.stringify(doc))<=900000,413,'İçerik dosyası çok büyük.');return doc;
}
function sessionKey(env){const value=Buffer.from(env.ADMIN_SESSION_KEY||'','base64');ensure(value.length===32,503,'Panel bağlantısı henüz tamamlanmadı.');return value;}
function seal(value,env){const iv=crypto.randomBytes(12),cipher=crypto.createCipheriv('aes-256-gcm',sessionKey(env),iv);const encrypted=Buffer.concat([cipher.update(JSON.stringify(value),'utf8'),cipher.final()]);return Buffer.concat([iv,cipher.getAuthTag(),encrypted]).toString('base64url');}
function unseal(value,env){try{if(typeof value!=='string'||value.length>6000)return null;const bytes=Buffer.from(value,'base64url');if(bytes.length<30)return null;const cipher=crypto.createDecipheriv('aes-256-gcm',sessionKey(env),bytes.subarray(0,12));cipher.setAuthTag(bytes.subarray(12,28));const data=JSON.parse(Buffer.concat([cipher.update(bytes.subarray(28)),cipher.final()]).toString());return data.exp>Date.now()&&typeof data.token==='string'&&typeof data.csrf==='string'?data:null;}catch{return null;}}
function cookie(req,env){const values=(req.headers.cookie||'').split(';').map(x=>x.trim()).filter(x=>x.startsWith(COOKIE+'='));return values.length===1?unseal(values[0].slice(COOKIE.length+1),env):null;}
function sameOrigin(req){ensure(req.headers.origin===ORIGIN,403,'İstek kaynağı reddedildi.');ensure(!req.headers['sec-fetch-site']||req.headers['sec-fetch-site']==='same-origin',403,'İstek kaynağı reddedildi.');}
function csrf(req,session){sameOrigin(req);const value=req.headers['x-csrf-token'];ensure(typeof value==='string'&&Buffer.byteLength(value)===Buffer.byteLength(session.csrf)&&crypto.timingSafeEqual(Buffer.from(value),Buffer.from(session.csrf)),403,'Oturumu yenileyin.');}
function jsonBody(req,max=1000000){ensure((req.headers['content-type']||'').split(';')[0]==='application/json',415,'JSON isteği gerekli.');ensure(Number(req.headers['content-length']||0)<=max,413,'Dosya çok büyük.');let body;try{body=typeof req.body==='string'?JSON.parse(req.body):req.body;}catch{throw new HttpError(400,'JSON isteği geçersiz.');}ensure(object(body)&&Buffer.byteLength(JSON.stringify(body))<=max,413,'Dosya çok büyük.');return body;}
module.exports={ORIGIN,COOKIE,LANGS,FIELDS,HttpError,ensure,object,str,validateDocument,imagePath,seal,unseal,cookie,csrf,sameOrigin,jsonBody};
