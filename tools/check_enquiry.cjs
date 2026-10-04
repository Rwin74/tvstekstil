const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('js/corporate.js','utf8');
async function scenario(ok,valid=true){
 let listener,request,resets=0;
 const button={textContent:'Send enquiry',disabled:false};const status={textContent:''};
 const values={name:'Test Buyer',subject:'Test Company',email:'buyer@example.test',phone:'+000000',country:'France',quantity:'250',message:'Sample brief'};
 const form={elements:{product:{options:[{value:'towels'}],selectedOptions:[{textContent:'Towels'}]}},reportValidity:()=>valid,addEventListener:(event,fn)=>{listener=fn;},querySelector:()=>button,reset:()=>{resets++;}};
 const document={documentElement:{lang:'en'},querySelector:s=>s==='#enquiry-form'?form:s==='#form-status'?status:null,addEventListener:()=>{}};
 const sandbox={document,window:{},location:{search:'?product=towels'},URLSearchParams,FormData:class{get(k){return values[k]||'';}},fetch:async(url,init)=>{request={url,...init};return{ok};}};
 vm.runInNewContext(source,sandbox);
 assert.equal(form.elements.product.value,'towels');
 await listener({preventDefault(){}});
 assert.equal(button.disabled,false);
 if(!valid){assert.equal(request,undefined);return;}
 assert.equal(request.url,'/admin/api/quotes');assert.equal(request.method,'POST');
 assert.equal(request.headers['Content-Type'],'application/json');
 const payload=JSON.parse(request.body);
 assert.deepEqual(Object.keys(payload).sort(),['customerName','companyName','email','phone','notes','items'].sort());
 assert.equal(payload.customerName,values.name);assert.equal(payload.companyName,values.subject);assert.equal(payload.email,values.email);assert.equal(payload.phone,values.phone);assert.equal(payload.items,'Iletisim Formu Mesaji');
 assert.match(payload.notes,/Sample brief/);assert.match(payload.notes,/France/);assert.match(payload.notes,/Towels/);assert.match(payload.notes,/250/);
 assert.equal(resets,ok?1:0);assert.match(status.textContent,ok?/successfully/:/could not/);
}
(async()=>{await scenario(true);await scenario(false);await scenario(true,false);console.log('PASS: preserved enquiry endpoint and payload; success, failure, validation and product preselection. No real enquiry sent.');})().catch(e=>{console.error(e);process.exit(1);});
