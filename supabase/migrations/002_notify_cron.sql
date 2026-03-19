-- GAD v0.1 — nightly notification cron slot
-- Stub function always created so migration never aborts. pg_cron is Pro-only on Supabase;
-- on free tier the extension and schedule are skipped and a notice is raised.
-- v0.2: implement notify_trigger_subscribers (check new basis_risk_reports, queue email via Edge Function → Resend).

-- Stub: no-op until v0.2. Exists regardless of pg_cron so migration is safe on free tier.
create or replace function public.notify_trigger_subscribers()
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  -- v0.2: select triggers with active trigger_notifications,
  --       join to basis_risk_reports where computed_at >= current_date,
  --       call Edge Function to send via Resend.
  null;
end;
$$;

-- pg_cron is only available on Pro and above. Fail softly so migration completes on free tier.
do $$
begin
  execute 'create extension if not exists pg_cron';
exception when others then
  raise notice 'pg_cron not available — enable in Supabase Dashboard or upgrade to Pro';
end;
$$;

do $$
begin
  perform cron.schedule(
    'notify-trigger-updates',
    '0 7 * * *',
    $inner$ select public.notify_trigger_subscribers(); $inner$
  );
exception when others then
  raise notice 'pg_cron not available — schedule manually when upgrading to Pro';
end;
$$;
