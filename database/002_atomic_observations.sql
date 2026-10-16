-- Run in Supabase SQL editor as database owner. No destructive deduplication.
-- Serialize collector writes and recheck identity inside the same transaction.
create or replace function public.save_verified_observation(rec jsonb)
returns bigint language plpgsql security definer set search_path = '' as $$
declare pid bigint; oid bigint; observation_id bigint;
begin
  if (rec->>'platform_id')::bigint <> 1
     or rec->>'url' !~ '^https://item[.]gmarket[.]co[.]kr/Item[?]goodscode=[0-9]+$'
     or length(trim(rec->>'name')) = 0
     or (rec->>'price')::numeric <= 0
     or (rec->>'shipping')::numeric < 0
     or (rec->>'observed_at')::timestamptz > now() + interval '5 minutes'
  then raise exception 'Invalid verified observation'; end if;
  if not (rec ?& array['platform_id','url','name','price','shipping','observed_at','source_url']) then
    raise exception 'Missing fields';
  end if;
  perform pg_catalog.pg_advisory_xact_lock(1420776196);
  select id into oid from public.offers where platform_id = 1 and url = rec->>'url' order by id limit 1;
  if oid is null then
    insert into public.products(name) values(rec->>'name') returning id into pid;
    insert into public.offers(platform_id,product_id,listing_title,url,is_deal)
      values(1,pid,rec->>'name',rec->>'url',true) returning id into oid;
  end if;
  select id into observation_id from public.observations
    where offer_id=oid and observed_at=(rec->>'observed_at')::timestamptz order by id limit 1;
  if observation_id is null then
    insert into public.observations(offer_id,seller_price,shipping_fee,source_url,observed_at)
    values(oid,(rec->>'price')::numeric,(rec->>'shipping')::numeric,rec->>'source_url',(rec->>'observed_at')::timestamptz)
    returning id into observation_id;
  end if;
  return observation_id;
end $$;
revoke all on function public.save_verified_observation(jsonb) from public, anon, authenticated;
grant execute on function public.save_verified_observation(jsonb) to service_role;
