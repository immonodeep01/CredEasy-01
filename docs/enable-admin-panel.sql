-- CredEasy internal admin console.
-- Apply in the Supabase SQL editor after the base app schema exists.
-- Admin data tables are intentionally private: no anon/authenticated RLS
-- policies are created. The backend accesses them with its service-role key
-- only after validating the caller's Supabase session and admin role.

begin;

create table if not exists public.admin_roles (
    user_id uuid primary key references auth.users(id) on delete cascade,
    email text not null unique,
    role text not null check (role in ('admin', 'support', 'analyst', 'content', 'finance')),
    active boolean not null default true,
    created_by uuid references auth.users(id) on delete set null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.admin_audit_logs (
    id bigint generated always as identity primary key,
    actor_id uuid not null,
    actor_email text not null,
    action text not null,
    resource_type text not null,
    resource_id text,
    details jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);
create index if not exists admin_audit_logs_created_at_idx
    on public.admin_audit_logs (created_at desc);
create index if not exists admin_audit_logs_actor_id_idx
    on public.admin_audit_logs (actor_id, created_at desc);

create table if not exists public.admin_content_items (
    id uuid primary key default gen_random_uuid(),
    title text not null check (char_length(title) between 1 and 160),
    content_type text not null check (content_type in ('banner', 'category', 'announcement')),
    body text not null default '' check (char_length(body) <= 4000),
    status text not null default 'draft' check (status in ('draft', 'review')),
    created_by uuid not null,
    updated_by uuid not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.admin_announcements (
    id uuid primary key default gen_random_uuid(),
    title text not null check (char_length(title) between 1 and 160),
    body text not null check (char_length(body) between 1 and 4000),
    audience text not null default 'all' check (audience in ('all', 'active_30d', 'unverified')),
    status text not null default 'draft' check (status in ('draft', 'scheduled')),
    scheduled_at timestamptz,
    created_by uuid not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    check ((status = 'draft' and scheduled_at is null)
        or (status = 'scheduled' and scheduled_at is not null))
);

create table if not exists public.admin_support_tickets (
    id uuid primary key default gen_random_uuid(),
    requester_email text not null check (char_length(requester_email) <= 320),
    subject text not null check (char_length(subject) between 1 and 200),
    description text not null default '' check (char_length(description) <= 4000),
    status text not null default 'open' check (status in ('open', 'in_progress', 'resolved')),
    priority text not null default 'normal' check (priority in ('low', 'normal', 'high', 'urgent')),
    assigned_to uuid,
    created_by uuid not null,
    updated_by uuid not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
create index if not exists admin_support_tickets_status_idx
    on public.admin_support_tickets (status, priority, updated_at desc);

create table if not exists public.admin_app_configuration (
    key text primary key check (key ~ '^[a-z][a-z0-9_.-]{1,79}$'),
    value jsonb not null,
    updated_by uuid not null,
    updated_at timestamptz not null default now()
);

create table if not exists public.admin_coupons (
    id uuid primary key default gen_random_uuid(),
    code text not null unique check (code ~ '^[A-Z0-9_-]{3,32}$'),
    description text not null default '' check (char_length(description) <= 500),
    discount_percent numeric(5,2) not null check (discount_percent > 0 and discount_percent <= 100),
    starts_at timestamptz,
    ends_at timestamptz,
    active boolean not null default false,
    created_by uuid not null,
    created_at timestamptz not null default now(),
    check (ends_at is null or starts_at is null or ends_at > starts_at)
);

-- Keep admin history if a staff member's Auth identity is removed. These
-- UUIDs are attribution data, not ownership constraints on an Auth account.
alter table public.admin_audit_logs drop constraint if exists admin_audit_logs_actor_id_fkey;
alter table public.admin_content_items drop constraint if exists admin_content_items_created_by_fkey;
alter table public.admin_content_items drop constraint if exists admin_content_items_updated_by_fkey;
alter table public.admin_announcements drop constraint if exists admin_announcements_created_by_fkey;
alter table public.admin_support_tickets drop constraint if exists admin_support_tickets_assigned_to_fkey;
alter table public.admin_support_tickets drop constraint if exists admin_support_tickets_created_by_fkey;
alter table public.admin_support_tickets drop constraint if exists admin_support_tickets_updated_by_fkey;
alter table public.admin_app_configuration drop constraint if exists admin_app_configuration_updated_by_fkey;
alter table public.admin_coupons drop constraint if exists admin_coupons_created_by_fkey;

alter table public.admin_roles enable row level security;
alter table public.admin_audit_logs enable row level security;
alter table public.admin_content_items enable row level security;
alter table public.admin_announcements enable row level security;
alter table public.admin_support_tickets enable row level security;
alter table public.admin_app_configuration enable row level security;
alter table public.admin_coupons enable row level security;

revoke all on public.admin_roles from anon, authenticated;
revoke all on public.admin_audit_logs from anon, authenticated;
revoke all on public.admin_content_items from anon, authenticated;
revoke all on public.admin_announcements from anon, authenticated;
revoke all on public.admin_support_tickets from anon, authenticated;
revoke all on public.admin_app_configuration from anon, authenticated;
revoke all on public.admin_coupons from anon, authenticated;

grant all on public.admin_roles to service_role;
grant all on public.admin_audit_logs to service_role;
grant all on public.admin_content_items to service_role;
grant all on public.admin_announcements to service_role;
grant all on public.admin_support_tickets to service_role;
grant all on public.admin_app_configuration to service_role;
grant all on public.admin_coupons to service_role;
grant usage, select on sequence public.admin_audit_logs_id_seq to service_role;

commit;
