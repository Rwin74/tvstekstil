'use strict';
const crypto=require('node:crypto');
const {ORIGIN,ensure,HttpError,jsonBody,str}=require('../lib/admin-security.cjs');
const DB=require('../lib/supabase.cjs');
module.exports=async(req,res)=>{
 res.setHeader('Cache-Control','no-store');res.setHeader('X-Content-Type-Options','nosniff');
 try{
 const env=process.env;
 ensure(req.method==='POST',405,'Method not allowed.');ensure(req.headers.origin===ORIGIN,403,'Invalid origin.');
 ensure(/^https:\/\/[a-z0-9]+\.supabase\.co$/.test(env.SUPABASE_URL||'')&&DB.keys(env).secretKey&&env.TURNSTILE_SECRET_KEY&&/^https:\/\//.test(env.ENQUIRY_MAIL_WEBHOOK_URL||'')&&env.ENQUIRY_MAIL_WEBHOOK_SECRET,503,'Enquiry delivery is not configured. Please contact us by email.');
 const body=jsonBody(req,30000);for(const[k,max]of Object.entries({customerName:200,companyName:300,email:254,phone:50,notes:20000,items:2000}))str(body[k]||'',max,['customerName','email','notes'].includes(k));ensure(/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(body.email),400,'Invalid email.');
 ensure(typeof body.turnstileToken==='string'&&body.turnstileToken.length<=2048,400,'Verification required.');
 const verification=await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({secret:env.TURNSTILE_SECRET_KEY,response:body.turnstileToken}),signal:AbortSignal.timeout(10000)});const verified=await verification.json();ensure(verified.success&&verified.hostname==='www.tvstextile.com',400,'Verification failed.');
 const id=crypto.randomUUID(),payload={};for(const k of ['customerName','companyName','email','phone','notes','items'])payload[k]=body[k]||'';
 const headers={...DB.headers(DB.keys(env).secretKey),'Content-Type':'application/json'};
 const save=await fetch(env.SUPABASE_URL+'/rest/v1/cms_enquiries',{method:'POST',headers,body:JSON.stringify({id,payload}),signal:AbortSignal.timeout(10000)});ensure(save.ok,502,'Enquiry could not be saved.');
 let sent=false;try{const mail=await fetch(env.ENQUIRY_MAIL_WEBHOOK_URL,{method:'POST',redirect:'error',headers:{'Content-Type':'application/json',Authorization:'Bearer '+env.ENQUIRY_MAIL_WEBHOOK_SECRET,'Idempotency-Key':id},body:JSON.stringify({...payload,enquiryId:id}),signal:AbortSignal.timeout(15000)});sent=mail.ok;}catch{}
 const recorded=await fetch(env.SUPABASE_URL+'/rest/v1/cms_enquiries?id=eq.'+id,{method:'PATCH',headers,body:JSON.stringify({mail_status:sent?'sent':'failed'}),signal:AbortSignal.timeout(10000)});
 if(!sent||!recorded.ok)throw new HttpError(502,'Enquiry saved, but email delivery could not be confirmed. Please contact us by email.');
 res.status(200).json({ok:true});
 }catch(error){res.status(error.status||500).json({error:error.status?error.message:'Enquiry could not be sent.'});}
};
