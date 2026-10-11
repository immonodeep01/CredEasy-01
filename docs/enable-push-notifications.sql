-- Android device registry and admin push-delivery history.
-- Apply after enable-admin-panel.sql. Only the backend service role may read
-- or write device tokens and delivery records.

begin;

create table if not exists public.push_devices (
    expo_push_token text primary key check (char_length(expo_push_token) between 20 and 255),
    user_id uuid not null references auth.users(id) on delete cascade,
    platform text not null check (platform = 'android'),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists push_devices_user_updated_idx
    on public.push_devices (user_id, updated_at desc);

alter table public.push_devices enable row level security;
revoke all on public.push_devices from anon, authenticated;
grant all on public.push_devices to service_role;

alter table public.admin_announcements
    add column if not exists target_user_id uuid,
    add column if not exists sent_at timestamptz,
    add column if not exists sent_count integer not null default 0,
    add column if not exists failed_count integer not null default 0,
    add column if not exists delivery_error text;

alter table public.admin_announcements
    drop constraint if exists admin_announcements_audience_check,
    drop constraint if exists admin_announcements_status_check,
    drop constraint if exists admin_announcements_check,
    drop constraint if exists admin_announcements_schedule_state_check,
    drop constraint if exists admin_announcements_target_state_check,
    drop constraint if exists admin_announcements_delivery_counts_check,
    drop constraint if exists admin_announcements_delivery_error_check;

alter table public.admin_announcements
    add constraint admin_announcements_audience_check
        check (audience in ('all', 'active_30d', 'unverified', 'account')),
    add constraint admin_announcements_status_check
        check (status in ('draft', 'scheduled', 'sending', 'sent', 'delivery_failed')),
    add constraint admin_announcements_schedule_state_check
        check ((status = 'scheduled' and scheduled_at is not null)
            or (status <> 'scheduled' and scheduled_at is null)),
    add constraint admin_announcements_target_state_check
        check ((audience = 'account' and target_user_id is not null)
            or (audience <> 'account' and target_user_id is null)),
    add constraint admin_announcements_delivery_counts_check
        check (sent_count >= 0 and failed_count >= 0),
    add constraint admin_announcements_delivery_error_check
        check (delivery_error is null or char_length(delivery_error) <= 500);

create index if not exists admin_announcements_target_created_idx
    on public.admin_announcements (target_user_id, created_at desc)
    where target_user_id is not null;

commit;
