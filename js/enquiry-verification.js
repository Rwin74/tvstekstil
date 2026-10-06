// Add verification only after the dual-delivery service has been configured.
(async()=>{const form=document.querySelector('#enquiry-form');if(!form)return;
 try{const r=await fetch('/api/enquiry-config');if(!r.ok)return;const config=await r.json();if(!config.enabled||!config.siteKey)return;
 const container=document.createElement('div');container.id='enquiry-verification';const input=document.createElement('input');input.type='hidden';input.name='turnstileToken';form.append(container,input);
 const submit=form.querySelector('button[type="submit"]');submit.disabled=true;
 const script=document.createElement('script');script.src='https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';script.onload=()=>{const widget=window.turnstile.render(container,{sitekey:config.siteKey,callback:token=>{input.value=token;submit.disabled=false;},'expired-callback':()=>{input.value='';submit.disabled=true;},'error-callback':()=>{input.value='';submit.disabled=true;}});form.addEventListener('reset',()=>{window.turnstile.reset(widget);input.value='';submit.disabled=true;});};document.head.append(script);
 }catch{}
})();
