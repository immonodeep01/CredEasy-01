-- Safe, non-destructive setup for live ledger and inventory sync.
-- Run this in the Supabase SQL Editor for the app's existing project before
-- expecting cross-device party, transaction, bill, recurring, profile or inventory
-- changes, multiple business profiles per account, or private cloud image syncing;
-- rerunning is safe. Existing rows are assigned to the `default` business.
-- Do NOT rerun docs/supabase-migration.sql on a populated project; it drops tables.
-- Android offline data recovery after reinstall also requires the device's
-- system backup/transfer service; this script does not back up offline data.

do $$
declare
    publication_operations text;
begin
    if to_regclass('public.parties') is null
       or to_regclass('public.transactions') is null
       or to_regclass('public.bills') is null
       or to_regclass('public.business_profiles') is null then
        raise exception 'public.parties, public.transactions, public.bills, and public.business_profiles must exist; apply the existing CredEasy schema first';
    end if;

    alter table public.transactions
        add column if not exists category text;

    alter table public.business_profiles
        add column if not exists profile_data jsonb not null default '{}'::jsonb;

    create table if not exists public.transaction_deletions (
        user_id uuid not null references auth.users(id) on delete cascade,
        transaction_id text not null,
        deleted_at timestamptz not null default now(),
        primary key (user_id, transaction_id)
    );

    create table if not exists public.party_deletions (
        user_id uuid not null references auth.users(id) on delete cascade,
        party_id text not null,
        deleted_at timestamptz not null default now(),
        primary key (user_id, party_id)
    );

    create table if not exists public.bill_deletions (
        user_id uuid not null references auth.users(id) on delete cascade,
        bill_id text not null,
        deleted_at timestamptz not null default now(),
        primary key (user_id, bill_id)
    );

    create table if not exists public.recurring_transactions (
        user_id uuid not null references auth.users(id) on delete cascade,
        id text not null,
        payload jsonb not null,
        updated_at timestamptz not null default now(),
        primary key (user_id, id)
    );

    create table if not exists public.recurring_transaction_deletions (
        user_id uuid not null references auth.users(id) on delete cascade,
        recurring_id text not null,
        deleted_at timestamptz not null default now(),
        primary key (user_id, recurring_id)
    );

    alter table public.transaction_deletions enable row level security;
    alter table public.party_deletions enable row level security;
    alter table public.bill_deletions enable row level security;
    alter table public.recurring_transactions enable row level security;
    alter table public.recurring_transaction_deletions enable row level security;

    if not exists (
        select 1
        from pg_policies
        where schemaname = 'public'
          and tablename = 'transaction_deletions'
          and policyname = 'transaction_deletions_select'
    ) then
        create policy transaction_deletions_select on public.transaction_deletions
            for select using (auth.uid() = user_id);
    end if;

    if not exists (
        select 1
        from pg_policies
        where schemaname = 'public'
          and tablename = 'party_deletions'
          and policyname = 'party_deletions_select'
    ) then
        create policy party_deletions_select on public.party_deletions
            for select using (auth.uid() = user_id);
    end if;

    if not exists (
        select 1
        from pg_policies
        where schemaname = 'public'
          and tablename = 'party_deletions'
          and policyname = 'party_deletions_insert'
    ) then
        create policy party_deletions_insert on public.party_deletions
            for insert with check (auth.uid() = user_id);
    end if;

    if not exists (
        select 1
        from pg_policies
        where schemaname = 'public'
          and tablename = 'transaction_deletions'
          and policyname = 'transaction_deletions_insert'
    ) then
        create policy transaction_deletions_insert on public.transaction_deletions
            for insert with check (auth.uid() = user_id);
    end if;

    if not exists (
        select 1
        from pg_policies
        where schemaname = 'public'
          and tablename = 'bill_deletions'
          and policyname = 'bill_deletions_select'
    ) then
        create policy bill_deletions_select on public.bill_deletions
            for select using (auth.uid() = user_id);
    end if;

    if not exists (
        select 1
        from pg_policies
        where schemaname = 'public'
          and tablename = 'bill_deletions'
          and policyname = 'bill_deletions_insert'
    ) then
        create policy bill_deletions_insert on public.bill_deletions
            for insert with check (auth.uid() = user_id);
    end if;

    if not exists (
        select 1 from pg_policies
        where schemaname = 'public'
          and tablename = 'recurring_transactions'
          and policyname = 'recurring_transactions_select'
    ) then
        create policy recurring_transactions_select on public.recurring_transactions
            for select using (auth.uid() = user_id);
    end if;

    if not exists (
        select 1 from pg_policies
        where schemaname = 'public'
          and tablename = 'recurring_transactions'
          and policyname = 'recurring_transactions_insert'
    ) then
        create policy recurring_transactions_insert on public.recurring_transactions
            for insert with check (auth.uid() = user_id);
    end if;

    if not exists (
        select 1 from pg_policies
        where schemaname = 'public'
          and tablename = 'recurring_transactions'
          and policyname = 'recurring_transactions_update'
    ) then
        create policy recurring_transactions_update on public.recurring_transactions
            for update using (auth.uid() = user_id)
            with check (auth.uid() = user_id);
    end if;

    if not exists (
        select 1 from pg_policies
        where schemaname = 'public'
          and tablename = 'recurring_transactions'
          and policyname = 'recurring_transactions_delete'
    ) then
        create policy recurring_transactions_delete on public.recurring_transactions
            for delete using (auth.uid() = user_id);
    end if;

    if not exists (
        select 1 from pg_policies
        where schemaname = 'public'
          and tablename = 'recurring_transaction_deletions'
          and policyname = 'recurring_transaction_deletions_select'
    ) then
        create policy recurring_transaction_deletions_select
            on public.recurring_transaction_deletions
            for select using (auth.uid() = user_id);
    end if;

    if not exists (
        select 1 from pg_policies
        where schemaname = 'public'
          and tablename = 'recurring_transaction_deletions'
          and policyname = 'recurring_transaction_deletions_insert'
    ) then
        create policy recurring_transaction_deletions_insert
            on public.recurring_transaction_deletions
            for insert with check (auth.uid() = user_id);
    end if;

    if not exists (
        select 1
        from pg_publication_tables
        where pubname = 'supabase_realtime'
          and schemaname = 'public'
          and tablename = 'parties'
    ) then
        alter publication supabase_realtime add table public.parties;
    end if;

    if not exists (
        select 1
        from pg_publication_tables
        where pubname = 'supabase_realtime'
          and schemaname = 'public'
          and tablename = 'transactions'
    ) then
        alter publication supabase_realtime add table public.transactions;
    end if;

    if not exists (
        select 1
        from pg_publication_tables
        where pubname = 'supabase_realtime'
          and schemaname = 'public'
          and tablename = 'transaction_deletions'
    ) then
        alter publication supabase_realtime add table public.transaction_deletions;
    end if;

    if not exists (
        select 1
        from pg_publication_tables
        where pubname = 'supabase_realtime'
          and schemaname = 'public'
          and tablename = 'party_deletions'
    ) then
        alter publication supabase_realtime add table public.party_deletions;
    end if;

    if not exists (
        select 1
        from pg_publication_tables
        where pubname = 'supabase_realtime'
          and schemaname = 'public'
          and tablename = 'bills'
    ) then
        alter publication supabase_realtime add table public.bills;
    end if;

    if not exists (
        select 1
        from pg_publication_tables
        where pubname = 'supabase_realtime'
          and schemaname = 'public'
          and tablename = 'business_profiles'
    ) then
        alter publication supabase_realtime add table public.business_profiles;
    end if;

    if not exists (
        select 1
        from pg_publication_tables
        where pubname = 'supabase_realtime'
          and schemaname = 'public'
          and tablename = 'bill_deletions'
    ) then
        alter publication supabase_realtime add table public.bill_deletions;
    end if;

    if not exists (
        select 1 from pg_publication_tables
        where pubname = 'supabase_realtime'
          and schemaname = 'public'
          and tablename = 'recurring_transactions'
    ) then
        alter publication supabase_realtime add table public.recurring_transactions;
    end if;

    if not exists (
        select 1 from pg_publication_tables
        where pubname = 'supabase_realtime'
          and schemaname = 'public'
          and tablename = 'recurring_transaction_deletions'
    ) then
        alter publication supabase_realtime add table public.recurring_transaction_deletions;
    end if;

    -- Keep the publication's existing operations and ensure DELETE events flow.
    select concat_ws(
        ', ',
        case when pubinsert then 'insert' end,
        case when pubupdate then 'update' end,
        case when pubdelete then 'delete' end,
        case when pubtruncate then 'truncate' end
    )
    into publication_operations
    from pg_publication
    where pubname = 'supabase_realtime';

    if publication_operations is null then
        raise exception 'supabase_realtime publication does not exist';
    end if;

    if position('delete' in publication_operations) = 0 then
        execute format(
            'alter publication supabase_realtime set (publish = %L)',
            concat_ws(', ', publication_operations, 'delete')
        );
    end if;
end;
$$;


create or replace function public.guard_transaction_deletion_tombstones()
returns trigger
language plpgsql
as $$
begin
    if tg_op = 'DELETE' then
        insert into public.transaction_deletions (user_id, transaction_id)
        values (old.user_id, old.id::text)
        on conflict (user_id, transaction_id) do nothing;
        return old;
    end if;

    if exists (
        select 1
        from public.transaction_deletions
        where user_id = new.user_id
          and transaction_id = new.id::text
    ) then
        raise exception using
            errcode = '23514',
            message = 'Transaction has already been deleted and cannot be restored';
    end if;

    return new;
end;
$$;

drop trigger if exists transactions_deletion_tombstone_guard on public.transactions;
create trigger transactions_deletion_tombstone_guard
    before insert or update or delete on public.transactions
    for each row execute function public.guard_transaction_deletion_tombstones();

create or replace function public.guard_party_deletion_tombstones()
returns trigger
language plpgsql
as $$
begin
    if tg_op = 'DELETE' then
        insert into public.party_deletions (user_id, party_id)
        values (old.user_id, old.id::text)
        on conflict (user_id, party_id) do nothing;
        return old;
    end if;

    if exists (
        select 1
        from public.party_deletions
        where user_id = new.user_id
          and party_id = new.id::text
    ) then
        raise exception using
            errcode = '23514',
            message = 'Party has already been deleted and cannot be restored';
    end if;

    return new;
end;
$$;

drop trigger if exists parties_deletion_tombstone_guard on public.parties;
create trigger parties_deletion_tombstone_guard
    before insert or update or delete on public.parties
    for each row execute function public.guard_party_deletion_tombstones();

create or replace function public.guard_bill_deletion_tombstones()
returns trigger
language plpgsql
as $$
begin
    if tg_op = 'DELETE' then
        insert into public.bill_deletions (user_id, bill_id)
        values (old.user_id, old.id::text)
        on conflict (user_id, bill_id) do nothing;
        return old;
    end if;

    if exists (
        select 1
        from public.bill_deletions
        where user_id = new.user_id
          and bill_id = new.id::text
    ) then
        raise exception using
            errcode = '23514',
            message = 'Bill has already been deleted and cannot be restored';
    end if;

    return new;
end;
$$;

drop trigger if exists bills_deletion_tombstone_guard on public.bills;
create trigger bills_deletion_tombstone_guard
    before insert or update or delete on public.bills
    for each row execute function public.guard_bill_deletion_tombstones();

create or replace function public.guard_recurring_transaction_deletion_tombstones()
returns trigger
language plpgsql
as $$
begin
    if tg_op = 'DELETE' then
        insert into public.recurring_transaction_deletions (user_id, recurring_id)
        values (old.user_id, old.id::text)
        on conflict (user_id, recurring_id) do nothing;
        return old;
    end if;

    if exists (
        select 1
        from public.recurring_transaction_deletions
        where user_id = new.user_id
          and recurring_id = new.id::text
    ) then
        raise exception using
            errcode = '23514',
            message = 'Recurring transaction has already been deleted and cannot be restored';
    end if;

    return new;
end;
$$;

drop trigger if exists recurring_transactions_deletion_tombstone_guard
    on public.recurring_transactions;
create trigger recurring_transactions_deletion_tombstone_guard
    before insert or update or delete on public.recurring_transactions
    for each row execute function public.guard_recurring_transaction_deletion_tombstones();

grant select on public.transactions to authenticated;
grant select on public.parties to authenticated;
grant select, insert, update, delete on public.bills to authenticated;
grant select, insert, update, delete on public.business_profiles to authenticated;
grant select, insert, update, delete on public.recurring_transactions to authenticated;
grant select, insert on public.transaction_deletions to authenticated;
grant select, insert on public.party_deletions to authenticated;
grant select, insert on public.bill_deletions to authenticated;
grant select, insert on public.recurring_transaction_deletions to authenticated;

-- Inventory rows use text IDs because existing local item IDs are not UUIDs.
create table if not exists public.inventory_items (
    user_id uuid not null references auth.users(id) on delete cascade,
    id text not null,
    item jsonb not null,
    current_stock numeric not null default 0,
    updated_at timestamptz not null default now(),
    primary key (user_id, id)
);

create table if not exists public.inventory_movements (
    user_id uuid not null references auth.users(id) on delete cascade,
    id text not null,
    item_id text not null,
    payload jsonb not null,
    created_at timestamptz not null default now(),
    primary key (user_id, id)
);

create table if not exists public.inventory_item_deletions (
    user_id uuid not null references auth.users(id) on delete cascade,
    item_id text not null,
    deleted_at timestamptz not null default now(),
    primary key (user_id, item_id)
);

alter table public.inventory_items enable row level security;
alter table public.inventory_movements enable row level security;
alter table public.inventory_item_deletions enable row level security;

do $$
begin
    if not exists (
        select 1 from pg_policies
        where schemaname = 'public' and tablename = 'inventory_items'
          and policyname = 'inventory_items_select'
    ) then
        create policy inventory_items_select on public.inventory_items
            for select using (auth.uid() = user_id);
    end if;
    if not exists (
        select 1 from pg_policies
        where schemaname = 'public' and tablename = 'inventory_items'
          and policyname = 'inventory_items_insert'
    ) then
        create policy inventory_items_insert on public.inventory_items
            for insert with check (auth.uid() = user_id);
    end if;
    if not exists (
        select 1 from pg_policies
        where schemaname = 'public' and tablename = 'inventory_items'
          and policyname = 'inventory_items_update'
    ) then
        create policy inventory_items_update on public.inventory_items
            for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
    end if;
    if not exists (
        select 1 from pg_policies
        where schemaname = 'public' and tablename = 'inventory_items'
          and policyname = 'inventory_items_delete'
    ) then
        create policy inventory_items_delete on public.inventory_items
            for delete using (auth.uid() = user_id);
    end if;
    if not exists (
        select 1 from pg_policies
        where schemaname = 'public' and tablename = 'inventory_movements'
          and policyname = 'inventory_movements_select'
    ) then
        create policy inventory_movements_select on public.inventory_movements
            for select using (auth.uid() = user_id);
    end if;
    if not exists (
        select 1 from pg_policies
        where schemaname = 'public' and tablename = 'inventory_movements'
          and policyname = 'inventory_movements_insert'
    ) then
        create policy inventory_movements_insert on public.inventory_movements
            for insert with check (auth.uid() = user_id);
    end if;
    if not exists (
        select 1 from pg_policies
        where schemaname = 'public' and tablename = 'inventory_item_deletions'
          and policyname = 'inventory_item_deletions_select'
    ) then
        create policy inventory_item_deletions_select on public.inventory_item_deletions
            for select using (auth.uid() = user_id);
    end if;
    if not exists (
        select 1 from pg_policies
        where schemaname = 'public' and tablename = 'inventory_item_deletions'
          and policyname = 'inventory_item_deletions_insert'
    ) then
        create policy inventory_item_deletions_insert on public.inventory_item_deletions
            for insert with check (auth.uid() = user_id);
    end if;

    if not exists (
        select 1 from pg_publication_tables
        where pubname = 'supabase_realtime' and schemaname = 'public'
          and tablename = 'inventory_items'
    ) then
        alter publication supabase_realtime add table public.inventory_items;
    end if;
    if not exists (
        select 1 from pg_publication_tables
        where pubname = 'supabase_realtime' and schemaname = 'public'
          and tablename = 'inventory_movements'
    ) then
        alter publication supabase_realtime add table public.inventory_movements;
    end if;
    if not exists (
        select 1 from pg_publication_tables
        where pubname = 'supabase_realtime' and schemaname = 'public'
          and tablename = 'inventory_item_deletions'
    ) then
        alter publication supabase_realtime add table public.inventory_item_deletions;
    end if;
end;
$$;

create or replace function public.guard_inventory_item_tombstones()
returns trigger
language plpgsql
as $$
begin
    if tg_op = 'DELETE' then
        insert into public.inventory_item_deletions (user_id, item_id)
        values (old.user_id, old.id)
        on conflict (user_id, item_id) do nothing;
        return old;
    end if;

    if exists (
        select 1 from public.inventory_item_deletions
        where user_id = new.user_id and item_id = new.id
    ) then
        raise exception using
            errcode = '23514',
            message = 'Inventory item has already been deleted and cannot be restored';
    end if;
    return new;
end;
$$;

drop trigger if exists inventory_items_tombstone_guard on public.inventory_items;
create trigger inventory_items_tombstone_guard
    before insert or update or delete on public.inventory_items
    for each row execute function public.guard_inventory_item_tombstones();

create or replace function public.apply_inventory_movement(
    p_user_id uuid,
    p_movement_id text,
    p_item_id text,
    p_quantity_change numeric,
    p_payload jsonb
)
returns jsonb
language plpgsql
as $$
declare
    v_stock numeric;
    v_quantity_after numeric;
    v_existing jsonb;
    v_payload jsonb;
    v_deleted boolean;
begin
    if auth.uid() is null or auth.uid() <> p_user_id then
        raise exception using errcode = '42501', message = 'Inventory account mismatch';
    end if;
    if p_quantity_change = 0 then
        raise exception using errcode = '22023', message = 'Movement quantity must not be zero';
    end if;

    select exists (
        select 1 from public.inventory_item_deletions
        where user_id = p_user_id and item_id = p_item_id
    ) into v_deleted;

    if not v_deleted then
        select current_stock into v_stock
        from public.inventory_items
        where user_id = p_user_id and id = p_item_id
        for update;
        if not found then
            select exists (
                select 1 from public.inventory_item_deletions
                where user_id = p_user_id and item_id = p_item_id
            ) into v_deleted;
            if not v_deleted then
                raise exception using errcode = 'P0002', message = 'Inventory item does not exist';
            end if;
        end if;
    end if;

    select payload into v_existing
    from public.inventory_movements
    where user_id = p_user_id and id = p_movement_id;
    if found then
        return v_existing;
    end if;

    if v_deleted then
        v_payload := p_payload;
    else
        v_quantity_after := v_stock + p_quantity_change;
        if v_quantity_after < 0 then
            raise exception using errcode = '23514', message = 'Inventory stock cannot become negative';
        end if;
        v_payload := jsonb_set(p_payload, '{quantityAfter}', to_jsonb(v_quantity_after), true);
        update public.inventory_items
        set current_stock = v_quantity_after, updated_at = now()
        where user_id = p_user_id and id = p_item_id;
    end if;

    insert into public.inventory_movements (user_id, id, item_id, payload)
    values (p_user_id, p_movement_id, p_item_id, v_payload)
    on conflict (user_id, id) do nothing
    returning payload into v_existing;
    if v_existing is null then
        select payload into v_existing
        from public.inventory_movements
        where user_id = p_user_id and id = p_movement_id;
        return v_existing;
    end if;
    return v_existing;
end;
$$;

create or replace function public.upsert_inventory_item(
    p_user_id uuid,
    p_item_id text,
    p_item jsonb
)
returns void
language plpgsql
as $$
begin
    if auth.uid() is null or auth.uid() <> p_user_id then
        raise exception using errcode = '42501', message = 'Inventory account mismatch';
    end if;

    insert into public.inventory_items (user_id, id, item, current_stock)
    values (p_user_id, p_item_id, p_item, 0)
    on conflict (user_id, id) do update
    set item = excluded.item, updated_at = now();
end;
$$;

grant execute on function public.upsert_inventory_item(uuid, text, jsonb) to authenticated;
grant select, insert, update, delete on public.inventory_items to authenticated;
grant select, insert on public.inventory_movements to authenticated;
grant select, insert on public.inventory_item_deletions to authenticated;
grant execute on function public.apply_inventory_movement(uuid, text, text, numeric, jsonb) to authenticated;

-- One stable automatic Drive-backup device per Supabase account. The first
-- device to claim it keeps ownership; other devices can still back up manually.
create table if not exists public.drive_backup_device_owners (
    user_id uuid primary key references auth.users(id) on delete cascade,
    device_id uuid not null,
    claimed_at timestamptz not null default now()
);

alter table public.drive_backup_device_owners enable row level security;
revoke all on public.drive_backup_device_owners from anon, authenticated;

create or replace function public.claim_drive_backup_device(
    p_user_id uuid,
    p_device_id uuid
)
returns uuid
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
    v_device_id uuid;
begin
    if auth.uid() is null or auth.uid() <> p_user_id then
        raise exception using errcode = '42501', message = 'Backup account mismatch';
    end if;
    if p_device_id is null then
        raise exception using errcode = '22023', message = 'Backup device ID is required';
    end if;

    insert into public.drive_backup_device_owners (user_id, device_id)
    values (p_user_id, p_device_id)
    on conflict (user_id) do nothing;

    select device_id into v_device_id
    from public.drive_backup_device_owners
    where user_id = p_user_id;
    return v_device_id;
end;
$$;

revoke all on function public.claim_drive_backup_device(uuid, uuid) from public, anon;
grant execute on function public.claim_drive_backup_device(uuid, uuid) to authenticated;

-- Every account may keep several independent business ledgers. Existing rows
-- belong to the original/default business and are preserved in that partition.
alter table public.parties add column if not exists business_id text;
alter table public.transactions add column if not exists business_id text;
alter table public.party_deletions add column if not exists business_id text;
alter table public.transaction_deletions add column if not exists business_id text;
alter table public.bills add column if not exists business_id text;
alter table public.bill_deletions add column if not exists business_id text;
alter table public.business_profiles add column if not exists business_id text;
alter table public.inventory_items add column if not exists business_id text;
alter table public.inventory_movements add column if not exists business_id text;
alter table public.inventory_item_deletions add column if not exists business_id text;
alter table public.recurring_transactions add column if not exists business_id text;
alter table public.recurring_transaction_deletions add column if not exists business_id text;

do $$
declare
    target_table text;
    profile_constraint text;
begin
    foreach target_table in array array[
        'parties', 'transactions', 'party_deletions', 'transaction_deletions',
        'bills', 'bill_deletions', 'business_profiles', 'inventory_items',
        'inventory_movements', 'inventory_item_deletions',
        'recurring_transactions', 'recurring_transaction_deletions'
    ] loop
        execute format(
            'update public.%I set business_id = ''default'' where business_id is null',
            target_table
        );
        execute format(
            'alter table public.%I alter column business_id set default ''default''',
            target_table
        );
        execute format(
            'alter table public.%I alter column business_id set not null',
            target_table
        );
    end loop;

    for profile_constraint in
        select conname
        from pg_constraint
        where conrelid = 'public.business_profiles'::regclass
          and contype = 'u'
          and pg_get_constraintdef(oid) = 'UNIQUE (user_id)'
    loop
        execute format(
            'alter table public.business_profiles drop constraint %I',
            profile_constraint
        );
    end loop;
end;
$$;

create unique index if not exists parties_user_business_id_uq
    on public.parties (user_id, business_id, id);
create unique index if not exists transactions_user_business_id_uq
    on public.transactions (user_id, business_id, id);
create unique index if not exists party_deletions_user_business_id_uq
    on public.party_deletions (user_id, business_id, party_id);
create unique index if not exists transaction_deletions_user_business_id_uq
    on public.transaction_deletions (user_id, business_id, transaction_id);
create unique index if not exists bills_user_business_id_uq
    on public.bills (user_id, business_id, id);
create unique index if not exists bill_deletions_user_business_id_uq
    on public.bill_deletions (user_id, business_id, bill_id);
create unique index if not exists business_profiles_user_business_id_uq
    on public.business_profiles (user_id, business_id);
create unique index if not exists inventory_items_user_business_id_uq
    on public.inventory_items (user_id, business_id, id);
create unique index if not exists inventory_movements_user_business_id_uq
    on public.inventory_movements (user_id, business_id, id);
create unique index if not exists inventory_item_deletions_user_business_id_uq
    on public.inventory_item_deletions (user_id, business_id, item_id);
create unique index if not exists recurring_transactions_user_business_id_uq
    on public.recurring_transactions (user_id, business_id, id);
create unique index if not exists recurring_deletions_user_business_id_uq
    on public.recurring_transaction_deletions (user_id, business_id, recurring_id);

create or replace function public.guard_inventory_item_tombstones()
returns trigger
language plpgsql
as $$
begin
    if tg_op = 'DELETE' then
        insert into public.inventory_item_deletions (user_id, business_id, item_id)
        values (old.user_id, old.business_id, old.id)
        on conflict (user_id, item_id) do nothing;
        return old;
    end if;

    if exists (
        select 1 from public.inventory_item_deletions
        where user_id = new.user_id
          and business_id = new.business_id
          and item_id = new.id
    ) then
        raise exception using
            errcode = '23514',
            message = 'Inventory item has already been deleted and cannot be restored';
    end if;
    return new;
end;
$$;

create or replace function public.apply_inventory_movement(
    p_user_id uuid,
    p_business_id text,
    p_movement_id text,
    p_item_id text,
    p_quantity_change numeric,
    p_payload jsonb
)
returns jsonb
language plpgsql
as $$
declare
    v_stock numeric;
    v_quantity_after numeric;
    v_existing jsonb;
    v_payload jsonb;
    v_deleted boolean;
begin
    if auth.uid() is null or auth.uid() <> p_user_id then
        raise exception using errcode = '42501', message = 'Inventory account mismatch';
    end if;
    if p_business_id is null or p_business_id = '' then
        raise exception using errcode = '22023', message = 'Business ID is required';
    end if;
    if p_quantity_change = 0 then
        raise exception using errcode = '22023', message = 'Movement quantity must not be zero';
    end if;

    select exists (
        select 1 from public.inventory_item_deletions
        where user_id = p_user_id and business_id = p_business_id and item_id = p_item_id
    ) into v_deleted;

    if not v_deleted then
        select current_stock into v_stock
        from public.inventory_items
        where user_id = p_user_id and business_id = p_business_id and id = p_item_id
        for update;
        if not found then
            raise exception using errcode = 'P0002', message = 'Inventory item does not exist';
        end if;
    end if;

    select payload into v_existing
    from public.inventory_movements
    where user_id = p_user_id and business_id = p_business_id and id = p_movement_id;
    if found then
        return v_existing;
    end if;

    if v_deleted then
        v_payload := p_payload;
    else
        v_quantity_after := v_stock + p_quantity_change;
        if v_quantity_after < 0 then
            raise exception using errcode = '23514', message = 'Inventory stock cannot become negative';
        end if;
        v_payload := jsonb_set(p_payload, '{quantityAfter}', to_jsonb(v_quantity_after), true);
        update public.inventory_items
        set current_stock = v_quantity_after, updated_at = now()
        where user_id = p_user_id and business_id = p_business_id and id = p_item_id;
    end if;

    insert into public.inventory_movements (user_id, business_id, id, item_id, payload)
    values (p_user_id, p_business_id, p_movement_id, p_item_id, v_payload)
    on conflict (user_id, id) do nothing
    returning payload into v_existing;
    if v_existing is null then
        select payload into v_existing
        from public.inventory_movements
        where user_id = p_user_id and business_id = p_business_id and id = p_movement_id;
    end if;
    return v_existing;
end;
$$;

create or replace function public.upsert_inventory_item(
    p_user_id uuid,
    p_business_id text,
    p_item_id text,
    p_item jsonb
)
returns void
language plpgsql
as $$
begin
    if auth.uid() is null or auth.uid() <> p_user_id then
        raise exception using errcode = '42501', message = 'Inventory account mismatch';
    end if;
    if p_business_id is null or p_business_id = '' then
        raise exception using errcode = '22023', message = 'Business ID is required';
    end if;

    insert into public.inventory_items (user_id, business_id, id, item, current_stock)
    values (p_user_id, p_business_id, p_item_id, p_item, 0)
    on conflict (user_id, id) do update
    set item = excluded.item, updated_at = now()
    where public.inventory_items.business_id = excluded.business_id;
end;
$$;

revoke all on function public.upsert_inventory_item(uuid, text, text, jsonb) from public, anon;
revoke all on function public.apply_inventory_movement(uuid, text, text, text, numeric, jsonb) from public, anon;
grant execute on function public.upsert_inventory_item(uuid, text, text, jsonb) to authenticated;
grant execute on function public.apply_inventory_movement(uuid, text, text, text, numeric, jsonb) to authenticated;

-- Restrictive guards ensure a permissive legacy UPDATE policy cannot reassign
-- rows to another account by changing user_id.
do $$
declare
    target_table text;
    guard_policy text;
begin
    foreach target_table in array array[
        'business_profiles',
        'parties',
        'transactions',
        'bills',
        'inventory_items'
    ] loop
        guard_policy := target_table || '_account_update_guard';
        if not exists (
            select 1 from pg_policies
            where schemaname = 'public'
              and tablename = target_table
              and policyname = guard_policy
        ) then
            execute format(
                'create policy %I on public.%I as restrictive for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id)',
                guard_policy,
                target_table
            );
        end if;
    end loop;
end;
$$;

-- Private image storage for party, transaction, and business-profile media.
-- Every object path starts with the owning auth user ID.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
    'credeasy-ledger-media',
    'credeasy-ledger-media',
    false,
    5242880,
    array['image/jpeg', 'image/png', 'image/webp', 'image/gif']
)
on conflict (id) do update
set public = false,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

do $$
begin
    if not exists (
        select 1 from pg_policies
        where schemaname = 'storage' and tablename = 'objects'
          and policyname = 'credeasy_media_select_own'
    ) then
        create policy credeasy_media_select_own on storage.objects
            for select to authenticated
            using (
                bucket_id = 'credeasy-ledger-media'
                and (storage.foldername(name))[1] = (select auth.uid())::text
            );
    end if;
    if not exists (
        select 1 from pg_policies
        where schemaname = 'storage' and tablename = 'objects'
          and policyname = 'credeasy_media_insert_own'
    ) then
        create policy credeasy_media_insert_own on storage.objects
            for insert to authenticated
            with check (
                bucket_id = 'credeasy-ledger-media'
                and (storage.foldername(name))[1] = (select auth.uid())::text
            );
    end if;
    if not exists (
        select 1 from pg_policies
        where schemaname = 'storage' and tablename = 'objects'
          and policyname = 'credeasy_media_update_own'
    ) then
        create policy credeasy_media_update_own on storage.objects
            for update to authenticated
            using (
                bucket_id = 'credeasy-ledger-media'
                and (storage.foldername(name))[1] = (select auth.uid())::text
            )
            with check (
                bucket_id = 'credeasy-ledger-media'
                and (storage.foldername(name))[1] = (select auth.uid())::text
            );
    end if;
end;
$$;

-- Delete one business workspace atomically after its owner explicitly confirms.
create table if not exists public.business_workspace_deletions (
    user_id uuid not null references auth.users(id) on delete cascade,
    business_id text not null,
    deleted_at timestamptz not null default now(),
    primary key (user_id, business_id)
);
alter table public.business_workspace_deletions enable row level security;
grant select on public.business_workspace_deletions to authenticated;
do $$
begin
    if not exists (
        select 1 from pg_policies
        where schemaname = 'public'
          and tablename = 'business_workspace_deletions'
          and policyname = 'business_workspace_deletions_select'
    ) then
        create policy business_workspace_deletions_select on public.business_workspace_deletions
            for select to authenticated using (auth.uid() = user_id);
    end if;
end;
$$;

create or replace function public.delete_business_workspace(p_business_id text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
    current_user_id uuid := auth.uid();
    profile_count integer;
begin
    if current_user_id is null then
        raise exception using errcode = '42501', message = 'Authentication is required';
    end if;
    if p_business_id is null or p_business_id = '' then
        raise exception using errcode = '22023', message = 'Business ID is required';
    end if;

    perform 1
    from public.business_profiles
    where user_id = current_user_id
    for update;

    if not exists (
        select 1 from public.business_profiles
        where user_id = current_user_id and business_id = p_business_id
    ) then
        if exists (
            select 1 from public.business_workspace_deletions
            where user_id = current_user_id and business_id = p_business_id
        ) then
            return;
        end if;
        if p_business_id = 'default' then
            raise exception using errcode = 'P0002', message = 'Business profile was not found';
        end if;
        insert into public.business_workspace_deletions (user_id, business_id)
        values (current_user_id, p_business_id);
        delete from storage.objects
        where bucket_id = 'credeasy-ledger-media'
          and left(name, length(current_user_id::text || '/' || p_business_id || '/'))
              = current_user_id::text || '/' || p_business_id || '/';
        return;
    end if;
    select count(*) into profile_count
    from public.business_profiles
    where user_id = current_user_id;
    if profile_count <= 1 then
        raise exception using errcode = '22023', message = 'The last business profile cannot be deleted';
    end if;

    insert into public.business_workspace_deletions (user_id, business_id)
    values (current_user_id, p_business_id)
    on conflict (user_id, business_id) do update set deleted_at = now();

    delete from public.transactions
    where user_id = current_user_id and business_id = p_business_id;
    delete from public.bills
    where user_id = current_user_id and business_id = p_business_id;
    delete from public.recurring_transactions
    where user_id = current_user_id and business_id = p_business_id;
    delete from public.parties
    where user_id = current_user_id and business_id = p_business_id;
    delete from public.inventory_movements
    where user_id = current_user_id and business_id = p_business_id;
    delete from public.inventory_items
    where user_id = current_user_id and business_id = p_business_id;
    delete from public.transaction_deletions
    where user_id = current_user_id and business_id = p_business_id;
    delete from public.party_deletions
    where user_id = current_user_id and business_id = p_business_id;
    delete from public.bill_deletions
    where user_id = current_user_id and business_id = p_business_id;
    delete from public.recurring_transaction_deletions
    where user_id = current_user_id and business_id = p_business_id;
    delete from public.inventory_item_deletions
    where user_id = current_user_id and business_id = p_business_id;
    delete from public.business_profiles
    where user_id = current_user_id and business_id = p_business_id;
    delete from storage.objects
    where bucket_id = 'credeasy-ledger-media'
      and left(name, length(current_user_id::text || '/' || p_business_id || '/'))
          = current_user_id::text || '/' || p_business_id || '/';
end;
$$;

revoke all on function public.delete_business_workspace(text) from public, anon;
grant execute on function public.delete_business_workspace(text) to authenticated;

create or replace function public.guard_deleted_business_workspace()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    if auth.uid() is null or auth.uid() <> new.user_id then
        raise exception using errcode = '42501', message = 'Business account mismatch';
    end if;
    if exists (
        select 1 from public.business_workspace_deletions
        where user_id = new.user_id and business_id = new.business_id
    ) then
        raise exception using errcode = '23514', message = 'Business workspace has been deleted';
    end if;
    return new;
end;
$$;

drop trigger if exists business_profiles_deleted_workspace_guard on public.business_profiles;
create trigger business_profiles_deleted_workspace_guard
    before insert or update on public.business_profiles
    for each row execute function public.guard_deleted_business_workspace();

revoke all on function public.guard_deleted_business_workspace() from public, anon;

do $$
begin
    if not exists (
        select 1 from pg_publication_tables
        where pubname = 'supabase_realtime'
          and schemaname = 'public'
          and tablename = 'business_workspace_deletions'
    ) then
        alter publication supabase_realtime add table public.business_workspace_deletions;
    end if;
end;
$$;
