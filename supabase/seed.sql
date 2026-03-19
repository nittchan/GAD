-- GAD dev seed — example triggers (optional; run after 001_initial_schema.sql)
-- These are for local/dev only. Production uses schema/examples/ YAMLs.

-- No seed data required for v0.1. Trigger definitions are created via the app
-- or loaded from schema/examples/. Uncomment below to insert a sample profile
-- and trigger if you have already run the migration and have a test user.

-- insert into public.profiles (id, display_name, role)
-- values (
--     '00000000-0000-0000-0000-000000000001'::uuid,
--     'Dev User',
--     'actuary'
-- ) on conflict (id) do nothing;
