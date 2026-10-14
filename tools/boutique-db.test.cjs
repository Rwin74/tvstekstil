'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {PGlite}=require('@electric-sql/pglite');

test('boutique migration, permissions and transactional workspace in PostgreSQL',async t=>{
 const db=new PGlite();
 try {
  await db.exec(`create role anon; create role authenticated;
    create function public.cms_is_admin() returns boolean language sql stable as $$
      select coalesce(current_setting('request.jwt.claim.sub', true),'') = 'test-admin' $$;`);
  const migration=fs.readFileSync(path.join(__dirname,'../supabase/boutiques.sql'),'utf8');
  await db.exec(migration);await db.exec(migration);
  const rpc=async(operation,args={})=>(await db.query('select public.boutique_workspace($1,$2::jsonb) as value',[operation,JSON.stringify(args)])).rows[0].value;
  await t.test('anonymous and non-admin roles cannot read or write',async()=>{
   await db.exec('set role anon');
   await assert.rejects(rpc('list'),/permission denied/);
   await assert.rejects(db.query('select * from public.boutique_leads'),/permission denied/);
   await db.exec('set role authenticated');
   await assert.rejects(rpc('list'),/Administrator required/);
   await assert.rejects(rpc('save',{dedupe:'real:test',payload:{name:'Butik'}}),/Administrator required/);
   await db.exec("set request.jwt.claim.sub = 'test-admin'");
   assert.deepEqual(await rpc('list'),[]);
   await assert.rejects(db.query('select * from public.boutique_leads'),/permission denied/);
  });
  let saved;
  await t.test('save, duplicate protection, stale updates and Unicode preservation',async()=>{
   const input={dedupe:'real:butik.example',payload:{name:'Çığ Şişli Butik',product:'Linge de lit',product_tr:'Müslin nevresim',notes_tr:'ı İ ş Ş ğ Ğ ü Ü ö Ö ç Ç'}};
   saved=await rpc('save',input);assert.equal(saved.version,1);assert.equal(saved.product_tr,input.payload.product_tr);
   await assert.rejects(rpc('save',input),e=>e.code==='PT409');
   const updated=await rpc('save',{...input,id:saved.id,version:1});assert.equal(updated.version,2);
   await assert.rejects(rpc('save',{...input,id:saved.id,version:1}),e=>e.code==='PT409');
   await assert.rejects(rpc('delete',{id:saved.id,version:1}),e=>e.code==='PT409');
  });
  await t.test('backup restore is atomic and deduplicated',async()=>{
   const items=[{dedupe:'real:new.example',payload:{name:'New Boutique'}},{dedupe:'real:butik.example',payload:{name:'Existing Boutique'}}];
   assert.equal(await rpc('restore',{items}),1);assert.equal(await rpc('restore',{items}),0);
   const before=await rpc('list');
   await assert.rejects(rpc('restore',{items:[{dedupe:'real:rollback.example',payload:{name:'Rollback Boutique'}},{dedupe:'',payload:{name:'Invalid'}}]}),/Invalid backup lead/);
   assert.deepEqual(await rpc('list'),before);
   await rpc('delete',{id:saved.id,version:2});assert.equal((await rpc('list')).length,1);
  });
  await t.test('rate limits, cache expiry and bounded history',async()=>{
   assert.equal(await rpc('rate_limit',{bucket:'test:search',cost:3,maximum:4}),true);
   assert.equal(await rpc('rate_limit',{bucket:'test:search',cost:3,maximum:4}),false);
   const key='a'.repeat(64),payload={results:[{name:'Çığ Butik'}]};
   assert.equal(await rpc('cached',{key}),null);await rpc('cache',{key,payload});assert.deepEqual(await rpc('cached',{key}),payload);
   await db.exec("reset role;update public.boutique_cache set expires=now()-interval '1 second';set role authenticated");
   assert.equal(await rpc('cached',{key}),null);
   for(let i=0;i<103;i++)await rpc('add_history',{payload:{query:'müslin '+i,provider:'serpapi'}});
   const history=await rpc('history');assert.equal(history.length,100);assert.equal(history[0].query,'müslin 102');
   await assert.rejects(rpc('unknown'),/Unknown operation/);
  });
  await t.test('revocation immediately denies existing authenticated role',async()=>{
   await db.exec("set request.jwt.claim.sub = 'revoked'");
   await assert.rejects(rpc('list'),/Administrator required/);
  });
 } finally {await db.close();}
});
