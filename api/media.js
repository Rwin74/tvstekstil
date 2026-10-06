'use strict';
module.exports=async(req,res)=>{
 res.setHeader('X-Content-Type-Options','nosniff');
 if(req.method!=='GET'&&req.method!=='HEAD')return res.status(405).end();
 const name=req.query?.name;
 if(!/^[a-f0-9-]{36}\.webp$/.test(name||'')||!/^https:\/\/[a-z0-9]+\.supabase\.co$/.test(process.env.SUPABASE_URL||''))return res.status(404).end();
 try{const r=await fetch(process.env.SUPABASE_URL+'/storage/v1/object/public/product-media/'+name,{signal:AbortSignal.timeout(10000),redirect:'error'});if(!r.ok||!r.headers.get('content-type')?.startsWith('image/webp'))return res.status(404).end();const data=Buffer.from(await r.arrayBuffer());if(data.length>2100000)return res.status(404).end();res.setHeader('Content-Type','image/webp');res.setHeader('Cache-Control','public,max-age=31536000,immutable');return req.method==='HEAD'?res.status(200).end():res.status(200).send(data);}catch{return res.status(502).end();}
};
