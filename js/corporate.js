'use strict';
const toggle = document.querySelector('.menu-toggle');
const nav = document.querySelector('#site-nav');
function closeMenu(){nav?.classList.remove('open');toggle?.setAttribute('aria-expanded','false');}
toggle?.addEventListener('click',()=>{const open=nav.classList.toggle('open');toggle.setAttribute('aria-expanded',String(open));});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){closeMenu();toggle?.focus();}});
nav?.querySelectorAll('a').forEach(a=>a.addEventListener('click',closeMenu));
if ('IntersectionObserver' in window && !matchMedia('(prefers-reduced-motion: reduce)').matches){
 document.documentElement.classList.add('js-motion');
 const observer=new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting){entry.target.classList.add('visible');observer.unobserve(entry.target);}}),{threshold:.08});
 document.querySelectorAll('.reveal').forEach(el=>observer.observe(el));
}
const form=document.querySelector('#enquiry-form');
if(form){
 const requested=new URLSearchParams(location.search).get('product');
 if(requested && [...form.elements.product.options].some(o=>o.value===requested))form.elements.product.value=requested;
 form.addEventListener('submit',async e=>{
  e.preventDefault();if(!form.reportValidity())return;
  const data=new FormData(form);
  const selected=form.elements.product.selectedOptions[0]?.textContent || '';
  // Preserve the existing /admin/api/quotes contract and mail service.
  const payload={customerName:data.get('name'),companyName:data.get('subject'),email:data.get('email'),phone:data.get('phone'),notes:[data.get('message'),'','Destination: '+data.get('country'),'Product: '+selected,'Quantity: '+data.get('quantity')].join('\n'),items:'Iletisim Formu Mesaji'};
  const messages={en:['Sending…','Your enquiry has been sent successfully.','Your enquiry could not be sent. Please try again or email ozkan@tvstextile.com.'],fr:['Envoi…','Votre demande a été envoyée.','Votre demande n’a pas pu être envoyée. Réessayez ou écrivez à ozkan@tvstextile.com.'],de:['Wird gesendet…','Ihre Anfrage wurde gesendet.','Ihre Anfrage konnte nicht gesendet werden. Versuchen Sie es erneut oder schreiben Sie an ozkan@tvstextile.com.'],es:['Enviando…','Su consulta se ha enviado.','No se pudo enviar la consulta. Inténtelo de nuevo o escriba a ozkan@tvstextile.com.']};
  const text=messages[document.documentElement.lang]||messages.en;
  const button=form.querySelector('button[type="submit"]');const status=document.querySelector('#form-status');const original=button.textContent;
  button.disabled=true;button.textContent=text[0];status.textContent='';
  try{
   const response=await fetch('/admin/api/quotes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
   if(!response.ok)throw new Error('Enquiry failed');
   status.textContent=text[1];form.reset();
  }catch(error){status.textContent=text[2];}
  finally{button.disabled=false;button.textContent=original;}
 });
}
