-- GAD v0.1 — initial Supabase schema
-- Run with: supabase db push (or via Supabase dashboard SQL editor)

create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------------------
-- PROFILES (thin wrapper around auth.users)
-- ---------------------------------------------------------------------------
create table public.profiles (
    id              uuid primary key references auth.users(id) on delete cascade,
    display_name    text,
    company         text,
    role            text,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

alter table public.profiles enable row level security;

create policy "profiles: owner read"
    on public.profiles for select using (auth.uid() = id);
create policy "profiles: owner insert"
    on public.profiles for insert with check (auth.uid() = id);
create policy "profiles: owner update"
    on public.profiles for update using (auth.uid() = id);

-- ---------------------------------------------------------------------------
-- TRIGGER DEFINITIONS
-- ---------------------------------------------------------------------------
create table public.trigger_defs (
    trigger_id          uuid primary key default uuid_generate_v4(),
    created_by          uuid references public.profiles(id) on delete set null,
    name                text not null,
    description         text not null default '',
    peril               text not null check (peril in (
        'flight_delay', 'drought', 'flood', 'earthquake', 'wind'
    )),
    threshold           numeric not null,
    threshold_unit      text not null,
    data_source         text not null,
    geography           jsonb not null,
    provenance          jsonb not null,
    policy_binding      jsonb,
    is_public           boolean not null default false,
    parent_trigger_id   uuid references public.trigger_defs(trigger_id),
    version             integer not null default 1,
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now()
);

create index trigger_defs_created_by_idx on public.trigger_defs(created_by);
create index trigger_defs_peril_idx on public.trigger_defs(peril);
create index trigger_defs_is_public_idx on public.trigger_defs(is_public);

alter table public.trigger_defs enable row level security;

create policy "trigger_defs: public read"
    on public.trigger_defs for select
    using (is_public = true or auth.uid() = created_by);
create policy "trigger_defs: owner insert"
    on public.trigger_defs for insert with check (auth.uid() = created_by);
create policy "trigger_defs: owner update"
    on public.trigger_defs for update using (auth.uid() = created_by);
create policy "trigger_defs: owner delete"
    on public.trigger_defs for delete using (auth.uid() = created_by);

-- ---------------------------------------------------------------------------
-- BASIS RISK REPORTS (immutable)
-- ---------------------------------------------------------------------------
create table public.basis_risk_reports (
    report_id               uuid primary key default uuid_generate_v4(),
    trigger_id              uuid not null references public.trigger_defs(trigger_id),
    computed_by             uuid references public.profiles(id) on delete set null,
    spearman_rho            numeric not null,
    spearman_ci_lower       numeric not null,
    spearman_ci_upper       numeric not null,
    p_value                 numeric not null,
    false_positive_rate     numeric not null,
    false_negative_rate     numeric not null,
    backtest_periods        integer not null,
    backtest_start          timestamptz not null,
    backtest_end_inclusive  timestamptz not null,
    lloyds_score            numeric not null,
    lloyds_detail           jsonb not null,
    independent_verifiable  boolean not null,
    gad_version             text,
    computed_at             timestamptz not null default now()
);

create index basis_risk_reports_trigger_id_idx on public.basis_risk_reports(trigger_id);
create index basis_risk_reports_computed_by_idx on public.basis_risk_reports(computed_by);

alter table public.basis_risk_reports enable row level security;

create policy "basis_risk_reports: readable if trigger readable"
    on public.basis_risk_reports for select
    using (
        exists (
            select 1 from public.trigger_defs td
            where td.trigger_id = basis_risk_reports.trigger_id
              and (td.is_public = true or td.created_by = auth.uid())
        )
    );
create policy "basis_risk_reports: owner insert"
    on public.basis_risk_reports for insert
    with check (auth.uid() = computed_by);

-- ---------------------------------------------------------------------------
-- SAVED TRIGGERS
-- ---------------------------------------------------------------------------
create table public.saved_triggers (
    id          uuid primary key default uuid_generate_v4(),
    user_id     uuid not null references public.profiles(id) on delete cascade,
    trigger_id  uuid not null references public.trigger_defs(trigger_id) on delete cascade,
    saved_at    timestamptz not null default now(),
    unique(user_id, trigger_id)
);

alter table public.saved_triggers enable row level security;
create policy "saved_triggers: owner only"
    on public.saved_triggers for all using (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- TRIGGER NOTIFICATIONS
-- ---------------------------------------------------------------------------
create table public.trigger_notifications (
    id          uuid primary key default uuid_generate_v4(),
    user_id     uuid not null references public.profiles(id) on delete cascade,
    trigger_id  uuid not null references public.trigger_defs(trigger_id) on delete cascade,
    email       text not null,
    active      boolean not null default true,
    created_at  timestamptz not null default now(),
    unique(user_id, trigger_id)
);

alter table public.trigger_notifications enable row level security;
create policy "trigger_notifications: owner only"
    on public.trigger_notifications for all using (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- ORACLE DETERMINATIONS (mirror of R2, queryable)
-- ---------------------------------------------------------------------------
create table public.oracle_determinations (
    determination_id        uuid primary key,
    policy_id               uuid not null,
    trigger_id              uuid not null references public.trigger_defs(trigger_id),
    fired                   boolean not null,
    fired_at                timestamptz,
    data_snapshot_hash      text not null,
    computation_version     text not null,
    determined_at           timestamptz not null,
    prev_hash               text not null,
    signature               text not null default '',
    created_at              timestamptz not null default now()
);

create index oracle_determinations_trigger_id_idx on public.oracle_determinations(trigger_id);
create index oracle_determinations_policy_id_idx on public.oracle_determinations(policy_id);
create index oracle_determinations_determined_at_idx on public.oracle_determinations(determined_at);

alter table public.oracle_determinations enable row level security;
create policy "oracle_determinations: public read"
    on public.oracle_determinations for select using (true);
create policy "oracle_determinations: no user insert"
    on public.oracle_determinations for insert with check (false);

-- ---------------------------------------------------------------------------
-- GAD EVENTS (activity log, append-only, service-role only read)
-- ---------------------------------------------------------------------------
create table public.gad_events (
    event_id        uuid primary key default uuid_generate_v4(),
    user_id         uuid references public.profiles(id) on delete set null,
    session_id      text not null,
    event_type      text not null,
    trigger_id      uuid references public.trigger_defs(trigger_id) on delete set null,
    report_id       uuid references public.basis_risk_reports(report_id) on delete set null,
    metadata        jsonb not null default '{}',
    created_at      timestamptz not null default now()
);

create index gad_events_user_id_idx on public.gad_events(user_id);
create index gad_events_event_type_idx on public.gad_events(event_type);
create index gad_events_trigger_id_idx on public.gad_events(trigger_id);
create index gad_events_created_at_idx on public.gad_events(created_at);

alter table public.gad_events enable row level security;
create policy "gad_events: no user select"
    on public.gad_events for select using (false);
-- Only service role can insert (bypasses RLS); anon cannot
create policy "gad_events: no anon insert"
    on public.gad_events for insert with check (false);

-- ---------------------------------------------------------------------------
-- API KEYS
-- ---------------------------------------------------------------------------
create table public.api_keys (
    key_id          uuid primary key default uuid_generate_v4(),
    user_id         uuid not null references public.profiles(id) on delete cascade,
    key_hash        text not null unique,
    label           text,
    last_used_at    timestamptz,
    created_at      timestamptz not null default now(),
    revoked_at      timestamptz
);

alter table public.api_keys enable row level security;
create policy "api_keys: owner only"
    on public.api_keys for all using (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- UPDATED_AT TRIGGERS
-- ---------------------------------------------------------------------------
create or replace function update_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create trigger profiles_updated_at
    before update on public.profiles
    for each row execute function update_updated_at();

create trigger trigger_defs_updated_at
    before update on public.trigger_defs
    for each row execute function update_updated_at();
