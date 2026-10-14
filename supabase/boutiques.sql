-- Additive migration. Run after admin.sql in the Supabase SQL editor.
-- All TVS administrators share this company workspace. No anonymous/customer access.
begin;
create table if not exists public.boutique_leads (
  id uuid primary key default gen_random_uuid(), dedupe text unique not null,
  payload jsonb not null check (jsonb_typeof(payload) = 'object' and octet_length(payload::text) <= 150000),
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  version integer not null default 1 check (version > 0)
);
create table if not exists public.boutique_history (
  id uuid primary key default gen_random_uuid(), payload jsonb not null,
  created_at timestamptz not null default now()
);
create table if not exists public.boutique_limits (
  bucket text primary key, count integer not null, created_at timestamptz not null default now()
);
create table if not exists public.boutique_cache (
  key text primary key, payload jsonb not null, expires timestamptz not null
);
alter table public.boutique_leads enable row level security;
alter table public.boutique_history enable row level security;
alter table public.boutique_limits enable row level security;
alter table public.boutique_cache enable row level security;
revoke all on public.boutique_leads, public.boutique_history, public.boutique_limits, public.boutique_cache from public, anon, authenticated;

create or replace function public.boutique_workspace(operation text, arguments jsonb default '{}'::jsonb)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  result jsonb; row_value public.boutique_leads; entry jsonb;
  affected integer; added integer := 0; counter integer;
begin
  if not coalesce(public.cms_is_admin(), false) then
    raise insufficient_privilege using message = 'Administrator required';
  end if;
  if jsonb_typeof(arguments) is distinct from 'object' or octet_length(arguments::text) > 4200000 then
    raise exception 'Invalid request' using errcode = '22023';
  end if;
  if operation = 'list' then
    select coalesce(jsonb_agg(l.payload || jsonb_build_object('id', l.id, 'created_at', l.created_at,
      'updated_at', l.updated_at, 'version', l.version) order by l.updated_at desc, l.id), '[]'::jsonb)
      into result from public.boutique_leads l;
    return result;
  elsif operation = 'save' then
    if coalesce(length(arguments->>'dedupe'), 0) not between 3 and 1000
      or jsonb_typeof(arguments->'payload') is distinct from 'object'
      or coalesce(length(arguments->'payload'->>'name'), 0) not between 2 and 200
      or coalesce((arguments->'payload'->>'is_demo')::boolean, false) then
      raise exception 'Invalid lead' using errcode = '22023';
    end if;
    if arguments->>'id' is null then
      insert into public.boutique_leads(dedupe,payload) values(arguments->>'dedupe',arguments->'payload') returning * into row_value;
    else
      update public.boutique_leads set dedupe=arguments->>'dedupe',payload=arguments->'payload',
        updated_at=clock_timestamp(),version=version+1
        where id=(arguments->>'id')::uuid and version=(arguments->>'version')::integer returning * into row_value;
      if not found then raise exception 'Record changed' using errcode = 'PT409'; end if;
    end if;
    return row_value.payload || jsonb_build_object('id',row_value.id,'created_at',row_value.created_at,
      'updated_at',row_value.updated_at,'version',row_value.version);
  elsif operation = 'delete' then
    delete from public.boutique_leads where id=(arguments->>'id')::uuid and version=(arguments->>'version')::integer;
    if not found then raise exception 'Record changed' using errcode = 'PT409'; end if;
    return 'true'::jsonb;
  elsif operation = 'restore' then
    if jsonb_typeof(arguments->'items') is distinct from 'array' or jsonb_array_length(arguments->'items') > 10000 then
      raise exception 'Invalid backup' using errcode = '22023';
    end if;
    for entry in select value from jsonb_array_elements(arguments->'items') loop
      if coalesce(length(entry->>'dedupe'),0) not between 3 and 1000
        or jsonb_typeof(entry->'payload') is distinct from 'object'
        or coalesce(length(entry->'payload'->>'name'),0) not between 2 and 200
        or coalesce((entry->'payload'->>'is_demo')::boolean,false) then
        raise exception 'Invalid backup lead' using errcode = '22023';
      end if;
      insert into public.boutique_leads(dedupe,payload) values(entry->>'dedupe',entry->'payload') on conflict(dedupe) do nothing;
      get diagnostics affected = row_count;
      added := added + affected;
    end loop;
    return to_jsonb(added);
  elsif operation = 'history' then
    select coalesce(jsonb_agg(h.payload || jsonb_build_object('id',h.id,'created_at',h.created_at)
      order by h.created_at desc,h.id), '[]'::jsonb) into result from public.boutique_history h;
    return result;
  elsif operation = 'add_history' then
    if jsonb_typeof(arguments->'payload') is distinct from 'object' or octet_length((arguments->'payload')::text) > 20000 then
      raise exception 'Invalid history' using errcode = '22023';
    end if;
    perform pg_advisory_xact_lock(741526911);
    insert into public.boutique_history(payload) values(arguments->'payload');
    delete from public.boutique_history where id not in
      (select id from public.boutique_history order by created_at desc,id limit 100);
    return 'true'::jsonb;
  elsif operation = 'rate_limit' then
    if coalesce(length(arguments->>'bucket'),0) not between 1 and 200
      or coalesce((arguments->>'cost')::integer,0) not between 1 and 120
      or coalesce((arguments->>'maximum')::integer,0) not between 1 and 120 then
      raise exception 'Invalid limit' using errcode = '22023';
    end if;
    delete from public.boutique_limits where created_at < now() - interval '48 hours';
    insert into public.boutique_limits(bucket,count) values(arguments->>'bucket',(arguments->>'cost')::integer)
      on conflict(bucket) do update set count=public.boutique_limits.count+excluded.count returning count into counter;
    return to_jsonb(counter <= (arguments->>'maximum')::integer);
  elsif operation = 'cached' then
    select payload into result from public.boutique_cache where key=arguments->>'key' and expires > now();
    return result;
  elsif operation = 'cache' then
    if coalesce(length(arguments->>'key'),0) != 64 or jsonb_typeof(arguments->'payload') is distinct from 'object'
      or octet_length((arguments->'payload')::text) > 2000000 then
      raise exception 'Invalid cache' using errcode = '22023';
    end if;
    delete from public.boutique_cache where expires <= now();
    insert into public.boutique_cache(key,payload,expires) values(arguments->>'key',arguments->'payload',now()+interval '15 minutes')
      on conflict(key) do update set payload=excluded.payload,expires=excluded.expires;
    return 'true'::jsonb;
  end if;
  raise exception 'Unknown operation' using errcode = '22023';
exception when unique_violation then
  raise exception 'Already saved' using errcode = 'PT409';
end;
$$;
revoke all on function public.boutique_workspace(text,jsonb) from public, anon;
grant execute on function public.boutique_workspace(text,jsonb) to authenticated;
commit;
