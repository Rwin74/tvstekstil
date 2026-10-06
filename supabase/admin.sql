-- Run once in a NEW Supabase project's SQL editor. Never expose the service-role key.
begin;
create table public.cms_admins (user_id uuid primary key references auth.users(id) on delete cascade);
alter table public.cms_admins enable row level security;
revoke all on public.cms_admins from anon, authenticated;
create function public.cms_is_admin() returns boolean language sql stable security definer set search_path='' as $$
 select exists(select 1 from public.cms_admins where user_id=(select auth.uid()));
$$;
revoke all on function public.cms_is_admin() from public, anon;
grant execute on function public.cms_is_admin() to authenticated;
create table public.cms_documents (
 id text primary key check(id='site'), payload jsonb not null, version integer not null default 1,
 published jsonb, published_at timestamptz, updated_at timestamptz not null default now(), updated_by uuid,
 check(jsonb_typeof(payload)='object' and octet_length(payload::text)<=1100000)
);
create table public.cms_audit (
 id bigint generated always as identity primary key, created_at timestamptz not null default now(),
 actor uuid, version integer, action text not null, snapshot jsonb
);
create table public.cms_enquiries (
 id uuid primary key default gen_random_uuid(), created_at timestamptz not null default now(),
 payload jsonb not null, mail_status text not null default 'pending' check(mail_status in ('pending','sent','failed')),
 read_at timestamptz, check(octet_length(payload::text)<=30000)
);
create table public.cms_rate_limits (key text primary key, started_at timestamptz not null, attempts integer not null);
alter table public.cms_documents enable row level security;
alter table public.cms_audit enable row level security;
alter table public.cms_enquiries enable row level security;
alter table public.cms_rate_limits enable row level security;
revoke all on public.cms_documents,public.cms_audit,public.cms_enquiries,public.cms_rate_limits from anon, authenticated;
grant select on public.cms_documents,public.cms_enquiries to authenticated;
create policy admin_document_read on public.cms_documents for select to authenticated using ((select public.cms_is_admin()));
create policy admin_enquiry_read on public.cms_enquiries for select to authenticated using ((select public.cms_is_admin()));
create function public.cms_save(content jsonb, expected_version integer, make_public boolean default false)
returns integer language plpgsql security definer set search_path='' as $$
declare current_version integer; next_version integer;
begin
 if not public.cms_is_admin() then raise exception 'ADMIN_REQUIRED' using errcode='42501'; end if;
 if jsonb_typeof(content)<>'object' or content->>'schemaVersion'<>'1' or jsonb_typeof(content->'products')<>'array' or octet_length(content::text)>1100000 then raise exception 'INVALID_CONTENT'; end if;
 -- Lock across both initial insertion and subsequent saves, including concurrent first saves.
 perform pg_advisory_xact_lock(730621);
 select version into current_version from public.cms_documents where id='site' for update;
 if coalesce(current_version,0)<>expected_version then raise exception 'CMS_CONFLICT'; end if;
 next_version:=coalesce(current_version,0)+1;
 insert into public.cms_documents(id,payload,version,published,published_at,updated_by)
 values('site',content,next_version,case when make_public then content else null end,case when make_public then now() else null end,auth.uid())
 on conflict(id) do update set payload=content,version=next_version,updated_at=now(),updated_by=auth.uid(),
 published=case when make_public then content else cms_documents.published end,
 published_at=case when make_public then now() else cms_documents.published_at end;
 insert into public.cms_audit(actor,version,action,snapshot) values(auth.uid(),next_version,case when make_public then 'publish' else 'save' end,content);
 return next_version;
end; $$;
revoke all on function public.cms_save(jsonb,integer,boolean) from public,anon;
grant execute on function public.cms_save(jsonb,integer,boolean) to authenticated;
create function public.cms_published() returns jsonb language sql stable security definer set search_path='' as $$
 select published from public.cms_documents where id='site';
$$;
revoke all on function public.cms_published() from public;
grant execute on function public.cms_published() to anon,authenticated;
create function public.cms_read_enquiry(enquiry_id uuid) returns void language plpgsql security definer set search_path='' as $$
begin
 if not public.cms_is_admin() then raise exception 'ADMIN_REQUIRED' using errcode='42501'; end if;
 update public.cms_enquiries set read_at=now() where id=enquiry_id;
end; $$;
revoke all on function public.cms_read_enquiry(uuid) from public,anon;
grant execute on function public.cms_read_enquiry(uuid) to authenticated;
create function public.cms_rate_limit(bucket text,max_attempts integer,window_seconds integer) returns boolean
language plpgsql security definer set search_path='' as $$
declare amount integer;
begin
 if length(bucket)>100 or max_attempts not between 1 and 100 or window_seconds not between 60 and 3600 then return false; end if;
 insert into public.cms_rate_limits(key,started_at,attempts) values(bucket,now(),1)
 on conflict(key) do update set
 attempts=case when cms_rate_limits.started_at<now()-make_interval(secs=>window_seconds) then 1 else cms_rate_limits.attempts+1 end,
 started_at=case when cms_rate_limits.started_at<now()-make_interval(secs=>window_seconds) then now() else cms_rate_limits.started_at end
 returning attempts into amount;
 delete from public.cms_rate_limits where started_at<now()-interval '2 days';
 return amount<=max_attempts;
end; $$;
revoke all on function public.cms_rate_limit(text,integer,integer) from public,anon,authenticated;
grant execute on function public.cms_rate_limit(text,integer,integer) to service_role;
insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
 values('product-media','product-media',true,2100000,array['image/webp']);
-- No browser write policies: only the authenticated, validating server can upload
-- normalized raster bytes using service_role. Immutable names preserve old images.
commit;
-- Then create the owner in Authentication > Users, and allow its immutable UUID:
-- insert into public.cms_admins(user_id) values ('OWNER-USER-UUID');
-- Disable public registration in Authentication settings. Set minimum password length 12.
