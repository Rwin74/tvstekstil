'use strict';
const seed=require('../data/cms-seed.json'),defaults=require('../data/seo-defaults.json');
module.exports=function upgrade(source){
 const doc=structuredClone(source);
 for(const p of doc.products){const old=seed.products.find(row=>row.slug===p.slug);if(!old)continue;let changed=false;
  for(const [lang,fields]of Object.entries(defaults.products[p.slug]||{}))for(const [field,value]of Object.entries(fields))if(p.locales[lang][field]===old.locales[lang][field]&&p.locales[lang][field]!==value){p.locales[lang][field]=value;changed=true;}
  if(changed)p.updated='2026-10-11';
 }
 for(const [lang,pages]of Object.entries(defaults.pages))for(const [slug,fields]of Object.entries(pages))for(const [field,value]of Object.entries(fields))if(doc.pages[lang][slug][field]===seed.pages[lang][slug][field])doc.pages[lang][slug][field]=value;
 return doc;
};
