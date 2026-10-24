-- ============================================================
-- IMMOBILE : schema Supabase
-- ============================================================

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
  photos text[],
  status text default 'EN_ATTENTE',
  is_active boolean default false,
  created_at timestamp default now()
);

create table if not exists favoris (
  user_id uuid references users(id) on delete cascade,
  bien_id uuid references biens(id) on delete cascade,
  primary key (user_id, bien_id)
);

create table if not exists notifications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  bien_id uuid references biens(id) on delete cascade,
  message text,
  is_read boolean default false,
  created_at timestamp default now()
);

-- Alertes par zone (point G du cahier des charges)
create table if not exists user_alerts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  country text not null,
  city text not null,
  zone text not null,
  created_at timestamp default now()
);

create index if not exists idx_biens_active on biens (is_active, created_at desc);
create index if not exists idx_biens_status on biens (status);
create index if not exists idx_biens_geo on biens (country_code, city, locality);
create index if not exists idx_notif_user on notifications (user_id, is_read);
create index if not exists idx_alerts_user on user_alerts (user_id);

-- Realtime
alter publication supabase_realtime add table biens;
alter publication supabase_realtime add table notifications;

-- Storage : creer un bucket public nomme "biens" depuis le dashboard Supabase
-- (Storage > New bucket > name: biens > Public bucket)

-- ============================================================
-- MIGRATION (si les tables users/biens existent deja sans les
-- nouvelles colonnes de la version internationale) :
-- ============================================================
-- alter table users add column if not exists email text;
-- alter table users add column if not exists country_code text default 'CM';
-- alter table biens add column if not exists country_code text default 'CM';
