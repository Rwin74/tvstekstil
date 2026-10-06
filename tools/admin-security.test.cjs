'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const S=require('../lib/admin-security.cjs'),seed=require('../data/cms-seed.json');
const env={ADMIN_SESSION_KEY:crypto.randomBytes(32).toString('base64')};
const copy=()=>JSON.parse(JSON.stringify(seed));
test('missing multilingual pages and multibyte CSRF fail with controlled errors',()=>{for(const edit of [d=>delete d.pages.fr,d=>delete d.pages.en.home,d=>delete d.pages.es.contact.intro]){const d=copy();edit(d);assert.throws(()=>S.validateDocument(d,true),e=>e.status===400);}assert.throws(()=>S.csrf({headers:{origin:S.ORIGIN,'x-csrf-token':'éééé'}},{csrf:'abcd'}),e=>e.status===403);});
test('modern keys stay out of the JWT Authorization header',()=>{const DB=require('../lib/supabase.cjs');assert.deepEqual(DB.headers('sb_publishable_test'),{apikey:'sb_publishable_test'});assert.deepEqual(DB.headers('sb_secret_test'),{apikey:'sb_secret_test'});assert.equal(DB.headers('sb_publishable_test','user-jwt').Authorization,'Bearer user-jwt');assert.equal(DB.headers('legacy-jwt').Authorization,'Bearer legacy-jwt');});
test('valid four-language document and new products are accepted',()=>{S.validateDocument(copy(),true);const d=copy(),p=structuredClone(d.products[0]);p.slug='new-linen-product';d.products.push(p);S.validateDocument(d,true);});
test('arbitrary paths, remote images, prototype keys and markup cannot publish',()=>{for(const edit of [d=>d.products[0].slug='../api/admin',d=>d.products[0].slug='home-textiles',d=>d.products[0].image='https://evil.test/a.svg',d=>d.products[0].locales.en.name='<script>alert(1)</script>',d=>d.products.push(structuredClone(d.products[0])),d=>d.products[0].locales.en.specs='Bad|value;injected',d=>d.extra='unknown',d=>d.products[0].locales.en.paragraph1='x'.repeat(4001)]){const d=copy();edit(d);assert.throws(()=>S.validateDocument(d,true));}const d=copy();d.products[0].locales.en=JSON.parse('{"__proto__":{}}');assert.throws(()=>S.validateDocument(d,true));});
test('unfinished drafts can save but active products require every language to publish',()=>{const d=copy();d.products[0].locales.fr.name='';S.validateDocument(d,false);assert.throws(()=>S.validateDocument(d,true));});
test('encrypted cookies reject alteration, wrong keys and expiry',()=>{const value={token:'secret-provider-token',csrf:'testnonce',exp:Date.now()+10000},cookie=S.seal(value,env);assert(!cookie.includes(value.token));assert.deepEqual(S.unseal(cookie,env),value);assert.equal(S.unseal(cookie.slice(0,-5)+'AAAAA',env),null);assert.equal(S.unseal(cookie,{ADMIN_SESSION_KEY:crypto.randomBytes(32).toString('base64')}),null);assert.equal(S.unseal(S.seal({...value,exp:Date.now()-1},env),env),null);assert.throws(()=>S.seal(value,{}));});
test('duplicate session cookies and CSRF requests fail closed',()=>{const session={token:'x',csrf:'abcd',exp:Date.now()+10000};const value=S.seal(session,env);assert.equal(S.cookie({headers:{cookie:S.COOKIE+'='+value+'; '+S.COOKIE+'='+value}},env),null);const good={headers:{origin:S.ORIGIN,'x-csrf-token':'abcd','sec-fetch-site':'same-origin'}};S.csrf(good,session);assert.throws(()=>S.csrf({...good,headers:{...good.headers,origin:'https://evil.test'}},session));assert.throws(()=>S.csrf({...good,headers:{...good.headers,'x-csrf-token':'wrong'}},session));});
test('JSON bodies enforce type and size before processing',()=>{assert.throws(()=>S.jsonBody({headers:{'content-type':'text/plain'},body:{}}));assert.throws(()=>S.jsonBody({headers:{'content-type':'application/json'},body:{data:'x'.repeat(500)}},100));});
function response(){return{headers:{},setHeader(k,v){this.headers[k]=v;},status(n){this.code=n;return this;},json(v){this.value=v;return this;},end(){return this;}};}
test('authenticated content, saves, image upload, inbox, failed publication and retry work together',async()=>{
 const names=['SUPABASE_URL','SUPABASE_ANON_KEY','SUPABASE_SERVICE_ROLE_KEY','ADMIN_SESSION_KEY','ADMIN_GITHUB_PUBLISH_TOKEN'];const backup=Object.fromEntries(names.map(n=>[n,process.env[n]])),originalFetch=global.fetch;
 Object.assign(process.env,{SUPABASE_URL:'https://testproject.supabase.co',SUPABASE_ANON_KEY:'test-anon',SUPABASE_SERVICE_ROLE_KEY:'test-service',ADMIN_SESSION_KEY:env.ADMIN_SESSION_KEY,ADMIN_GITHUB_PUBLISH_TOKEN:'test-publisher'});
 let content=copy(),version=1,githubFails=true,uploaded=false,read=false;
 global.fetch=async(url,o={})=>{let value=null,status=200;
 if(url.endsWith('/auth/v1/user'))value={id:'test-owner',email:'owner@example.com'};
 else if(url.endsWith('/rpc/cms_is_admin')||url.endsWith('/rpc/cms_rate_limit'))value=true;
 else if(url.includes('/cms_documents?'))value=[{payload:content,version}];
 else if(url.endsWith('/rpc/cms_save')){const body=JSON.parse(o.body);assert.equal(body.expected_version,version);assert.equal(o.headers.Authorization,'Bearer owner-token');content=body.content;value=++version;}
 else if(url.includes('/storage/v1/object/product-media/')){assert.equal(o.headers['Content-Type'],'image/webp');assert.equal((await require('sharp')(o.body).metadata()).format,'webp');uploaded=true;}
 else if(url.includes('/cms_enquiries?'))value=[{id:'00000000-0000-4000-8000-000000000001',payload:{notes:'test'}}];
 else if(url.endsWith('/rpc/cms_read_enquiry'))read=true;
 else if(url.includes('api.github.com/')){if(githubFails)status=401;else if(o.method==='PUT')value={commit:{sha:'test'}};else status=404;}
 else if(url.endsWith('/auth/v1/logout'))value={};
 else throw Error('Unexpected URL '+url);
 return{ok:status>=200&&status<300,status,json:async()=>value};};
 const headers={origin:S.ORIGIN,'content-type':'application/json','x-csrf-token':'abcd',cookie:S.COOKIE+'='+S.seal({token:'owner-token',csrf:'abcd',exp:Date.now()+60000},env)};
 const call=async(action,body)=>{const res=response();await require('../api/admin.js')({query:{action},method:body===undefined?'GET':'POST',headers,body},res);return res;};
 try{
  assert.equal((await call('content')).value.payload.products.length,12);
  const draft=copy();draft.products.push({...structuredClone(draft.products[0]),slug:'integration-product',active:false});draft.settings.phone='+905324770375';
  assert.equal((await call('save',{payload:draft,version})).value.version,2);
  const png=await require('sharp')({create:{width:8,height:8,channels:3,background:'white'}}).png().toBuffer();assert.match((await call('image',{base64:png.toString('base64')})).value.path,/^\/cms-media\/[a-f0-9-]+\.webp$/);assert(uploaded);
  assert.equal((await call('image',{base64:Buffer.from('<svg xmlns="http://www.w3.org/2000/svg" width="2" height="2"></svg>').toString('base64')})).code,400);
  assert.equal((await call('enquiries')).value.length,1);assert.equal((await call('read-enquiry',{id:'00000000-0000-4000-8000-000000000001'})).code,200);assert(read);
  const failure=await call('publish',{payload:draft,version});assert.equal(failure.code,502);assert.equal(failure.value.saved,true);assert.equal(failure.value.version,3);assert.equal(failure.value.retryPublish,true);
  githubFails=false;assert.equal((await call('retry-publish',{})).code,200);assert.equal(version,3);
  const logout=await call('logout',{});assert.match(logout.headers['Set-Cookie'],/Max-Age=0/);
 }finally{global.fetch=originalFetch;for(const n of names)if(backup[n]===undefined)delete process.env[n];else process.env[n]=backup[n];}
});
test('missing configuration never grants access or accepts publication',async()=>{const handler=require('../api/admin.js');const res=response();await handler({method:'GET',url:'/api/admin?action=status',query:{action:'status'},headers:{}},res);assert.equal(res.code,200);assert.equal(res.value.authenticated,false);if(!process.env.SUPABASE_URL){const locked=response();await handler({method:'POST',url:'/api/admin?action=publish',query:{action:'publish'},headers:{origin:S.ORIGIN,'content-type':'application/json'},body:{payload:seed,version:0}},locked);assert.equal(locked.code,503);assert(!JSON.stringify(locked.value).includes('SUPABASE_SERVICE_ROLE_KEY'));}});
test('mail is never reported sent while dual delivery is unconfigured',async()=>{if(process.env.ENQUIRY_MAIL_WEBHOOK_URL)return;const res=response();await require('../api/enquiries.js')({method:'POST',headers:{origin:S.ORIGIN,'content-type':'application/json'},body:{}},res);assert.equal(res.code,503);assert.equal(res.value.ok,undefined);});
test('raster decoder normalizes pictures and excludes SVG',async()=>{const sharp=require('sharp');const png=await sharp({create:{width:4,height:4,channels:3,background:'white'}}).png().toBuffer();assert.equal((await sharp(await sharp(png).webp().toBuffer()).metadata()).format,'webp');assert.equal((await sharp(Buffer.from('<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"></svg>')).metadata()).format,'svg');});
test('publication writes only a fixed deployment marker with an optimistic Git SHA',async()=>{
 const names=['SUPABASE_URL','SUPABASE_ANON_KEY','SUPABASE_SERVICE_ROLE_KEY','ADMIN_SESSION_KEY','ADMIN_GITHUB_PUBLISH_TOKEN'];const backup=Object.fromEntries(names.map(n=>[n,process.env[n]])),previousFetch=global.fetch;
 Object.assign(process.env,{SUPABASE_URL:'https://testproject.supabase.co',SUPABASE_ANON_KEY:'test-anon',SUPABASE_SERVICE_ROLE_KEY:'test-service',ADMIN_SESSION_KEY:env.ADMIN_SESSION_KEY,ADMIN_GITHUB_PUBLISH_TOKEN:'test-publisher'});let commit=null;
 global.fetch=async(url,options)=>{let value;if(url.endsWith('/auth/v1/user'))value={id:'test-owner'};else if(url.endsWith('/rpc/cms_is_admin'))value=true;else if(url.endsWith('/rpc/cms_save'))value=2;else if(url==='https://api.github.com/repos/Rwin74/tvstekstil/contents/data/cms-revision.json?ref=main')value={sha:'previous-sha'};else if(url==='https://api.github.com/repos/Rwin74/tvstekstil/contents/data/cms-revision.json'){assert.equal(options.method,'PUT');commit=JSON.parse(options.body);value={commit:{sha:'new-sha'}};}else throw new Error('Unexpected publication URL');return{ok:true,status:200,json:async()=>value};};
 try{const session={token:'owner-token',csrf:'abcd',exp:Date.now()+10000},res=response();await require('../api/admin.js')({method:'POST',query:{action:'publish'},headers:{origin:S.ORIGIN,'content-type':'application/json','x-csrf-token':'abcd',cookie:S.COOKIE+'='+S.seal(session,env)},body:{payload:seed,version:1}},res);assert.equal(res.code,200);assert.equal(commit.branch,'main');assert.equal(commit.sha,'previous-sha');const marker=JSON.parse(Buffer.from(commit.content,'base64').toString());assert.deepEqual(Object.keys(marker).sort(),['requestId','requestedAt']);assert(!JSON.stringify(commit).includes('owner-token'));}finally{global.fetch=previousFetch;for(const n of names)if(backup[n]===undefined)delete process.env[n];else process.env[n]=backup[n];}
});
test('API denies anonymous users, revoked administrators, foreign origins and stale writes',async()=>{
 const names=['SUPABASE_URL','SUPABASE_ANON_KEY','SUPABASE_SERVICE_ROLE_KEY','ADMIN_SESSION_KEY'];const backup=Object.fromEntries(names.map(n=>[n,process.env[n]])),originalFetch=global.fetch;
 Object.assign(process.env,{SUPABASE_URL:'https://testproject.supabase.co',SUPABASE_ANON_KEY:'test-anon',SUPABASE_SERVICE_ROLE_KEY:'test-private-service',ADMIN_SESSION_KEY:env.ADMIN_SESSION_KEY});let allowed=true,writes=0;
 global.fetch=async(url,options)=>{let value,status=200;if(url.endsWith('/auth/v1/user'))value={id:'test-admin',email:'owner@example.com'};else if(url.includes('/auth/v1/token?'))value={access_token:'test-access',expires_in:3600};else if(url.endsWith('/rpc/cms_rate_limit'))value=true;else if(url.endsWith('/rpc/cms_is_admin'))value=allowed;else if(url.endsWith('/rpc/cms_save')){writes++;value={message:'CMS_CONFLICT'};status=400;}else throw new Error('Unexpected outgoing request '+url);return{ok:status===200,status,json:async()=>value};};
 const session={token:'test-access',csrf:'abcd',exp:Date.now()+10000};const headers={origin:S.ORIGIN,'content-type':'application/json',cookie:S.COOKIE+'='+S.seal(session,env),'x-csrf-token':session.csrf};const handler=require('../api/admin.js');
 async function call(action,method,custom= headers,body={payload:seed,version:0}){const res=response();await handler({url:'/api/admin',query:{action},method,headers:custom,body},res);return res;}
 try{
  assert.equal((await call('enquiries','GET',{})).code,401);
  const login=await call('login','POST',headers,{email:'owner@example.com',password:'<long-test-password>'});assert.equal(login.code,200);assert.match(login.headers['Set-Cookie'],/Secure; HttpOnly; SameSite=Strict; Max-Age=2400/);assert(!JSON.stringify(login.value).includes('test-access'));
  assert.equal((await call('save','POST',{...headers,origin:'https://evil.test'})).code,403);assert.equal(writes,0);
  assert.equal((await call('save','POST',{...headers,'x-csrf-token':'wrong'})).code,403);assert.equal(writes,0);
  assert.equal((await call('save','POST')).code,409);assert.equal(writes,1);
  allowed=false;assert.equal((await call('save','POST')).code,403);assert.equal(writes,1);
  const errors=JSON.stringify((await call('content','GET')).value);assert(!errors.includes('test-private-service')&&!errors.includes('test-access'));
 }finally{global.fetch=originalFetch;for(const n of names)if(backup[n]===undefined)delete process.env[n];else process.env[n]=backup[n];}
});
