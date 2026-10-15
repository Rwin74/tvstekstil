'use strict';
// Public health probe: reads only the already-public CMS projection, never drafts.
// Vercel runs this daily even when the static website has no visitors.
const DB=require('../lib/supabase.cjs');
module.exports=async(req,res)=>{
 res.setHeader('X-Content-Type-Options','nosniff');
 res.setHeader('X-Robots-Tag','noindex, nofollow');
 res.setHeader('Cache-Control','no-store');
 if(req.method!=='GET')return res.status(405).json({ok:false});
 const url=process.env.SUPABASE_URL,key=DB.keys(process.env).publicKey;
 if(!/^https:\/\/[a-z0-9]+\.supabase\.co$/.test(url||'')||!key)return res.status(503).json({ok:false,service:'cms'});
 try{
  const response=await fetch(url+'/rest/v1/rpc/cms_published',{method:'POST',headers:{...DB.headers(key),'Content-Type':'application/json'},body:'{}',signal:AbortSignal.timeout(12000)});
  if(!response.ok)throw Error('CMS unavailable');
  const doc=await response.json();
  if(doc?.schemaVersion!==1||!Array.isArray(doc.products)||!doc.products.some(p=>p.active))throw Error('Published content missing');
  res.setHeader('Vercel-CDN-Cache-Control','public, max-age=600');
  return res.status(200).json({ok:true,service:'cms',checkedAt:new Date().toISOString()});
 }catch{return res.status(503).json({ok:false,service:'cms'});}
};
