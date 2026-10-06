'use strict';
module.exports=(req,res)=>{res.setHeader('Cache-Control','no-store');if(req.method!=='GET')return res.status(405).end();const e=process.env;res.status(200).json({siteKey:e.TURNSTILE_SITE_KEY||'',enabled:!!(e.TURNSTILE_SITE_KEY&&e.TURNSTILE_SECRET_KEY&&e.ENQUIRY_MAIL_WEBHOOK_URL&&e.ENQUIRY_MAIL_WEBHOOK_SECRET&&(e.SUPABASE_SECRET_KEY||e.SUPABASE_SERVICE_ROLE_KEY))});};
