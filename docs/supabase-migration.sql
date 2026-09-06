-- Supabase schema for CredEasy — v2
-- Run this in the Supabase SQL Editor.
--
-- Changes from v1, and why:
--
--   1. Ids the app generates are TEXT, not UUID. StorageService.newId() produces
--      values like "party-1740412800000-a1b2c3d4", which Postgres rejects for a
--      UUID column with "invalid input syntax for type uuid" — so every cloud
--      upsert failed and sync never wrote a single row. `user_id` stays UUID
--      because it must reference auth.users(id).
--
--   2. Every UPDATE policy gained WITH CHECK. USING alone controls which rows
--      you may update; without WITH CHECK a signed-in user could update their
--      own row and set user_id to somebody else's, writing into another
--      person's account.
--
--   3. business_profiles gained the DELETE policy it was missing, so a user can
--      actually remove their own profile.
--
-- v3 note (2026-09-06): The mobile app now generates real UUIDs via
-- crypto.randomUUID() instead of the time-stamped strings above. The PK columns
-- remain TEXT so Postgres accepts the new format without a migration. If you
-- prefer strict UUID enforcement, change `text primary key` to
-- `uuid primary key default gen_random_uuid()` — but this requires ALTERing
-- existing rows (they contain legacy string IDs) so is not done automatically.
--
-- Safe to run on a fresh project. It DROPS the four tables first, so if you
-- already have rows in them, back them up before running:
--   select count(*) from parties;   -- etc.

begin;

drop view  if exists party_balances;
drop table if exists transactions      cascade;
drop table if exists bills             cascade;
drop table if exists parties           cascade;
drop table if exists business_profiles cascade;

-- --------------------------------------------------------------- profiles ---
create table business_profiles (
    id          text primary key,
    user_id     uuid not null references auth.users(id) on delete cascade,
    name        text not null default '',
    owner_phone text default '',
    gstin       text default '',
    upi_id      text default '',
    updated_at  timestamptz default now(),
    unique (user_id)
);

alter table business_profiles enable row level security;

create policy "profiles_select" on business_profiles for select
    using (auth.uid() = user_id);
create policy "profiles_insert" on business_profiles for insert
    with check (auth.uid() = user_id);
create policy "profiles_update" on business_profiles for update
    using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "profiles_delete" on business_profiles for delete
    using (auth.uid() = user_id);

-- ---------------------------------------------------------------- parties ---
create table parties (
    id              text primary key,
    user_id         uuid not null references auth.users(id) on delete cascade,
    name            text not null,
    phone           text default '',
    photo_uri       text,
    type            text not null check (type in ('CUSTOMER', 'SUPPLIER')),
    -- NOT NULL with a default: a NaN opening balance serialises to JSON null,
    -- and a null here would poison every total the party appears in.
    opening_balance numeric(15, 2) not null default 0,
    created_at      timestamptz not null default now()
);

create index idx_parties_user_id on parties(user_id);

alter table parties enable row level security;

create policy "parties_select" on parties for select
    using (auth.uid() = user_id);
create policy "parties_insert" on parties for insert
    with check (auth.uid() = user_id);
create policy "parties_update" on parties for update
    using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "parties_delete" on parties for delete
    using (auth.uid() = user_id);

-- ----------------------------------------------------------- transactions ---
create table transactions (
    id          text primary key,
    user_id     uuid not null references auth.users(id) on delete cascade,
    -- TEXT to match parties.id. The foreign key means parties must be pushed
    -- before transactions — CloudSync.pushToCloud already does them in order.
    party_id    text not null references parties(id) on delete cascade,
    amount      numeric(15, 2) not null,
    type        text not null check (type in ('DEBIT', 'CREDIT')),
    note        text default '',
    photo_uri   text,
    date        timestamptz not null,
    sync_status text default 'SYNCED' check (sync_status in ('SYNCED', 'PENDING')),
    created_at  timestamptz default now()
);

create index idx_transactions_user_id  on transactions(user_id);
create index idx_transactions_party_id on transactions(party_id);
create index idx_transactions_date     on transactions(date desc);

alter table transactions enable row level security;

create policy "tx_select" on transactions for select
    using (auth.uid() = user_id);
create policy "tx_insert" on transactions for insert
    with check (auth.uid() = user_id);
create policy "tx_update" on transactions for update
    using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "tx_delete" on transactions for delete
    using (auth.uid() = user_id);

-- ------------------------------------------------------------------ bills ---
create table bills (
    id             text primary key,
    user_id        uuid not null references auth.users(id) on delete cascade,
    party_id       text not null references parties(id) on delete cascade,
    items          jsonb not null default '[]',
    gst_applicable boolean not null default false,
    total          numeric(15, 2) not null,
    status         text default 'UNPAID' check (status in ('UNPAID', 'PAID')),
    created_at     timestamptz default now()
);

create index idx_bills_user_id  on bills(user_id);
create index idx_bills_party_id on bills(party_id);

alter table bills enable row level security;

create policy "bills_select" on bills for select
    using (auth.uid() = user_id);
create policy "bills_insert" on bills for insert
    with check (auth.uid() = user_id);
create policy "bills_update" on bills for update
    using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "bills_delete" on bills for delete
    using (auth.uid() = user_id);

-- ------------------------------------------------- party balances (view) ---
-- Same sign convention as frontend/src/utils/ledger.ts, and it is
-- type-agnostic — identical for CUSTOMER and SUPPLIER:
--   balance = opening_balance + Σ DEBIT − Σ CREDIT
--   > 0 → "You'll Get" (receivable)   < 0 → "You'll Give" (payable)
create or replace view party_balances as
select
    p.id      as party_id,
    p.user_id,
    p.name,
    p.phone,
    p.type,
    p.opening_balance,
    coalesce(sum(case when t.type = 'DEBIT'  then  t.amount
                      when t.type = 'CREDIT' then -t.amount
                      else 0 end), 0) as net_transactions,
    p.opening_balance
      + coalesce(sum(case when t.type = 'DEBIT'  then  t.amount
                          when t.type = 'CREDIT' then -t.amount
                          else 0 end), 0) as current_balance
from parties p
left join transactions t on t.party_id = p.id
group by p.id, p.user_id, p.name, p.phone, p.type, p.opening_balance;

-- security_invoker makes the view run under the *caller's* RLS rather than the
-- view owner's. Without it the view is a hole straight through every policy above.
alter view party_balances set (security_invoker = true);

commit;

-- --------------------------------------------------------------- verify -----
-- Run these separately afterwards. Both must come back clean.
--
--   -- every table must show rowsecurity = true
--   select tablename, rowsecurity from pg_tables where schemaname = 'public';
--
--   -- each table must have 4 policies
--   select tablename, count(*) from pg_policies
--   where schemaname = 'public' group by tablename;
