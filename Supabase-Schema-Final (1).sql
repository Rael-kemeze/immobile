-- ============================================================
-- IMMOBILE : schema Supabase FINAL avec OTP + cuisine/salons
-- ============================================================

-- 1. USERS (code + unique phone déjà ok)
create table if not exists users (
  id uuid primary key default gen_random_uuid(),
  username text not null,
  phone text unique not null,
  email text,
  password_hash text not null,
  country_code text default 'CM',
  city text not null,
  locality text not null,
  profile_photo_url text,
  role text default 'USER',
  is_blocked boolean default false,
  created_at timestamp default now()
);

-- 2. BIENS - version complète avec tous les champs utilisés dans publish_view.py
create table if not exists biens (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  titre text not null,
  type_bien text not null,
  transaction text not null,
  categorie text not null,
  country_code text default 'CM',
  city text not null,
  locality text not null,
  prix integer,
  prix_discutable boolean default false,
  prix_sur_place boolean default false,
  whatsapp text not null,
  description text,
  superficie integer,
  chambres integer,
  salles_de_bain integer,
  salons integer default 0,
  -- Cuisine
  cuisines integer default 0,
  nb_cuisines integer default 0,
  cuisine_interne boolean default false,
  cuisine_externe boolean default false,
  cuisine_type text default '',
  photos text[],
  status text default 'EN_ATTENTE',
  is_active boolean default false,
  created_at timestamp default now()
);

-- 3. FAVORIS
create table if not exists favoris (
  user_id uuid references users(id) on delete cascade,
  bien_id uuid references biens(id) on delete cascade,
  primary key (user_id, bien_id)
);

-- 4. NOTIFICATIONS
create table if not exists notifications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  bien_id uuid references biens(id) on delete cascade,
  message text,
  is_read boolean default false,
  created_at timestamp default now()
);

-- 5. ALERTES PAR ZONE
create table if not exists user_alerts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  country text not null,
  city text not null,
  zone text not null,
  created_at timestamp default now()
);

-- 6. OTP CODES - NOUVEAU pour vérification SMS
create table if not exists otp_codes (
  id uuid primary key default gen_random_uuid(),
  phone text not null,
  phone_normalized text not null,
  code text not null,
  attempts integer default 0,
  is_used boolean default false,
  expires_at timestamp with time zone not null,
  created_at timestamp with time zone default now()
);

-- INDEX
create index if not exists idx_biens_active on biens (is_active, created_at desc);
create index if not exists idx_biens_status on biens (status);
create index if not exists idx_biens_geo on biens (country_code, city, locality);
create index if not exists idx_notif_user on notifications (user_id, is_read);
create index if not exists idx_alerts_user on user_alerts (user_id);
create index if not exists idx_otp_phone on otp_codes (phone_normalized);
create index if not exists idx_otp_expires on otp_codes (expires_at);
create index if not exists idx_users_phone on users (phone);

-- REALTIME
alter publication supabase_realtime add table biens;
alter publication supabase_realtime add table notifications;

-- STORAGE : créer bucket public "biens" depuis dashboard > Storage > New bucket

-- ============================================================
-- MIGRATIONS si tables existent déjà (à exécuter si tu as déjà des données)
-- ============================================================
alter table biens add column if not exists salons integer default 0;
alter table biens add column if not exists cuisines integer default 0;
alter table biens add column if not exists nb_cuisines integer default 0;
alter table biens add column if not exists cuisine_interne boolean default false;
alter table biens add column if not exists cuisine_externe boolean default false;
alter table biens add column if not exists cuisine_type text default '';

-- Nettoyage auto des OTP expirés (optionnel, à mettre dans un cron Supabase)
-- delete from otp_codes where expires_at < now() - interval '10 minutes';
