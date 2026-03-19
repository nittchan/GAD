-- GAD v0.1 — nightly notification cron slot
-- Runs at 07:00 UTC. notify_trigger_subscribers() is a stub in v0.1;
-- v0.2 implements it (check new basis_risk_reports, queue email via Edge Function → Resend).
--
-- If "create extension pg_cron" fails (e.g. not allowed in project), enable pg_cron
-- in Supabase Dashboard → Database → Extensions, then run the rest of this migration.
create extension if not exists pg_cron;

-- Stub: no-op until v0.2 implements "for each trigger with active notifications,
-- check if a new basis_risk_report was computed today; if yes, queue email".
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

-- Register nightly job (07:00 UTC)
select cron.schedule(
  'notify-trigger-updates',
  '0 7 * * *',
  $$ select public.notify_trigger_subscribers(); $$
);
