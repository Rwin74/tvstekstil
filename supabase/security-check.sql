-- Run after admin.sql, in SQL Editor. Rolls back; creates no users or customer data.
begin;
set local role anon;
do $$begin
 begin perform 1 from public.cms_documents;raise exception 'FAIL: anon read draft';exception when insufficient_privilege then null;end;
 begin perform 1 from public.cms_enquiries;raise exception 'FAIL: anon read enquiries';exception when insufficient_privilege then null;end;
 begin perform public.cms_save('{}'::jsonb,0,false);raise exception 'FAIL: anon save';exception when insufficient_privilege then null;end;
 -- The one intentionally public projection may be empty before first publication.
 perform public.cms_published();
end$$;
reset role;
select set_config('request.jwt.claims','{"sub":"00000000-0000-4000-8000-000000000001","role":"authenticated"}',true);
set local role authenticated;
do $$begin
 if public.cms_is_admin() then raise exception 'FAIL: unknown user is admin';end if;
 if exists(select 1 from public.cms_documents) then raise exception 'FAIL: ordinary user read draft';end if;
 if exists(select 1 from public.cms_enquiries) then raise exception 'FAIL: ordinary user read enquiries';end if;
 begin perform public.cms_save('{"schemaVersion":1,"products":[]}'::jsonb,0,false);raise exception 'FAIL: ordinary user save';exception when insufficient_privilege then null;end;
 begin perform public.cms_rate_limit('test',5,900);raise exception 'FAIL: ordinary user rate RPC';exception when insufficient_privilege then null;end;
end$$;
reset role;
rollback;
-- Successful completion verifies anonymous and non-admin denial. Also test the real owner and revocation via the panel.
