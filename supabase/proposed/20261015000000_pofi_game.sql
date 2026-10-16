-- =====================================================================
-- Pofi Adası – oyun için sunucu eklemeleri (M4)
--
-- DURUM: ONAYLANDI (15 Ekim 2026). Uygulama: docs/M4_UYGULAMA.md. Ebeveyn uygulamasıyla
-- (ParentApp) aynı veritabanını kullanır.
-- Yerelde denendi: supabase/test/run.sh (ebeveyn şeması + bu dosya + testler).
--
-- Uygulama: Supabase panelinde SQL Editor > New query > bu dosyanın tamamını
-- yapıştır > Run. Birden fazla çalıştırılırsa zarar vermez.
--
-- İçerik:
--   1. children.age_band (A: 6–9, B: 10–12, C: 13–15) + doğum gününden öneri
--   2. completions: yeni durumlar ('declined' çocuk "yapamam", 'rejected' ebeveyn reddi) + parent_note
--   3. coin_ledger: coin defteri. Coin YALNIZCA ebeveyn onayıyla (tetikleyici) artar, harcama sunucuda düşer
--   4. game_items: dükkan fiyatları (sunucu esas; istemci fiyat belirleyemez)
--   5. game_saves: oyun kaydı yedeği
--   6. Çocuk oturumu fonksiyonları: child_me, child_tasks, child_set_status, spend_coins, game_save_get/put
--   7. Ebeveyn fonksiyonları: set_child_age_band, review_completion (onay/ret + not), child_balance, unlink_child_device
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. Yaş bandı
-- ---------------------------------------------------------------------
alter table public.children add column if not exists age_band text;
do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'children_age_band_check') then
    alter table public.children add constraint children_age_band_check check (age_band in ('A', 'B', 'C'));
  end if;
end $$;

-- Ebeveyn bandı çocuk eklerken/düzenlerken doğrudan yazabilir ("çocuk: ebeveyn" politikası korur;
-- çocuk kendi kaydını yalnız okur). set_child_age_band fonksiyonu da aynı işi yapar.
grant insert (age_band), update (age_band) on public.children to authenticated;

-- Doğum gününden önerilen bant: <10 → A, 10–12 → B, 13+ → C. Doğum günü yoksa en güvenli bant A.
create or replace function public.suggest_age_band(p_birthday date)
returns text language sql stable set search_path = '' as $$
  select case
    when p_birthday is null then 'A'
    when extract(year from age(current_date, p_birthday)) < 10 then 'A'
    when extract(year from age(current_date, p_birthday)) < 13 then 'B'
    else 'C'
  end
$$;

create or replace function public.child_age_band(p_child_id uuid)
returns text language sql stable security definer set search_path = '' as $$
  select coalesce(c.age_band, public.suggest_age_band(c.birthday)) from public.children c where c.id = p_child_id
$$;

-- Giriş kodu yanıtına age_band eklenir (gövde öncekiyle aynı).
create or replace function public.redeem_child_code(p_code text)
returns json language plpgsql security definer set search_path = '' as $$
declare
  uid uuid := auth.uid();
  inv public.invite_codes%rowtype;
  c public.children%rowtype;
begin
  if uid is null then
    raise exception 'Oturum gerekli' using errcode = '42501';
  end if;
  if exists (select 1 from public.profiles where id = uid) then
    raise exception 'Ebeveyn hesabıyla çocuk girişi yapılamaz';
  end if;

  select * into inv from public.invite_codes
    where code = upper(trim(p_code)) and kind = 'child'
    for update;

  if not found or inv.used_at is not null or inv.expires_at < now() then
    raise exception 'Kod geçersiz ya da süresi dolmuş';
  end if;

  update public.children set user_id = null where user_id = uid;
  update public.children set user_id = uid where id = inv.child_id returning * into c;
  update public.invite_codes set used_at = now(), used_by = uid where code = inv.code;

  return json_build_object('child_id', c.id, 'family_id', c.family_id, 'name', c.name, 'avatar', c.avatar,
                           'age_band', coalesce(c.age_band, public.suggest_age_band(c.birthday)));
end $$;

-- ---------------------------------------------------------------------
-- 2. Tamamlama durumları
--    pending  = çocuk "yaptım" dedi (ebeveyn bakacak)
--    approved = ebeveyn onayladı (coin verilir)
--    declined = çocuk "yapamam" dedi
--    rejected = ebeveyn reddetti (parent_note ile)
-- ---------------------------------------------------------------------
alter table public.completions drop constraint if exists completions_status_check;
alter table public.completions add constraint completions_status_check
  check (status in ('pending', 'approved', 'declined', 'rejected'));
alter table public.completions add column if not exists parent_note text;
do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'completions_parent_note_check') then
    alter table public.completions add constraint completions_parent_note_check check (char_length(parent_note) <= 300);
  end if;
end $$;

-- Çocuğun doğrudan tablo yazımı (ParentApp'teki çocuk ekranı) için: "yapamam" da serbest.
create or replace function public.child_may_complete(p_task_id uuid, p_status text)
returns boolean language sql stable security definer set search_path = '' as $$
  select public.task_assigned_to_me(p_task_id)
     and (p_status in ('pending', 'declined') or (p_status = 'approved' and not (select requires_review from public.tasks where id = p_task_id)))
$$;
drop policy if exists "tamamlama: çocuk geri alır" on public.completions;
create policy "tamamlama: çocuk geri alır" on public.completions for delete to authenticated
  using (child_id = public.my_child_id() and status in ('pending', 'declined'));

-- ---------------------------------------------------------------------
-- 3. Coin defteri
-- ---------------------------------------------------------------------
create table if not exists public.coin_ledger (
  id          bigserial primary key,
  family_id   uuid not null references public.families (id) on delete cascade,
  child_id    uuid not null references public.children (id) on delete cascade,
  amount      integer not null check (amount <> 0),
  reason      text not null check (reason in ('task', 'task_undo', 'spend', 'adjust')),
  ref         text not null,              -- tamamlama kimliği / harcama işlem kimliği
  item_id     text,
  quantity    integer,
  created_at  timestamptz not null default now(),
  unique (child_id, reason, ref)
);
create index if not exists coin_ledger_child_idx on public.coin_ledger (child_id);
alter table public.coin_ledger enable row level security;
drop policy if exists "coin: ebeveyn okur" on public.coin_ledger;
create policy "coin: ebeveyn okur" on public.coin_ledger for select to authenticated
  using (family_id = public.my_family_id());
drop policy if exists "coin: çocuk okur" on public.coin_ledger;
create policy "coin: çocuk okur" on public.coin_ledger for select to authenticated
  using (child_id = public.my_child_id());
-- Yazma politikası yok: defter yalnızca aşağıdaki tetikleyici ve fonksiyonlarla yazılır.
revoke insert, update, delete on public.coin_ledger from anon, authenticated;

create or replace function public.coin_balance(p_child_id uuid)
returns integer language sql stable security definer set search_path = '' as $$
  select coalesce(sum(amount), 0)::integer from public.coin_ledger where child_id = p_child_id
$$;

-- Onay → coin; onay geri alınırsa (durum değişir ya da kayıt silinir) → geri düş.
create or replace function public.completions_coin_trigger()
returns trigger language plpgsql security definer set search_path = '' as $$
declare
  coins integer;
  was_approved boolean := tg_op in ('UPDATE', 'DELETE') and old.status = 'approved';
  is_approved boolean := tg_op in ('INSERT', 'UPDATE') and new.status = 'approved';
  row_ public.completions%rowtype;
begin
  if tg_op = 'DELETE' then row_ := old; else row_ := new; end if;
  if is_approved = was_approved then
    return null;
  end if;
  select a.coins into coins from public.task_assignments a where a.task_id = row_.task_id and a.child_id = row_.child_id;
  coins := coalesce(coins, 0);
  if coins = 0 then
    return null;
  end if;
  if is_approved then
    insert into public.coin_ledger (family_id, child_id, amount, reason, ref)
    values (row_.family_id, row_.child_id, coins, 'task', row_.id::text || ':' || extract(epoch from clock_timestamp())::text)
    on conflict do nothing;
  else
    insert into public.coin_ledger (family_id, child_id, amount, reason, ref)
    values (row_.family_id, row_.child_id, -coins, 'task_undo', row_.id::text || ':' || extract(epoch from clock_timestamp())::text)
    on conflict do nothing;
  end if;
  return null;
end $$;

drop trigger if exists completions_coin on public.completions;
create trigger completions_coin after insert or update of status or delete on public.completions
  for each row execute function public.completions_coin_trigger();

-- ---------------------------------------------------------------------
-- 4. Dükkan fiyatları (oyun verisi items.json ile aynı; sunucu esas)
-- ---------------------------------------------------------------------
create table if not exists public.game_items (
  item_id    text primary key,
  price      integer not null check (price >= 0),
  min_level  integer not null default 1
);
alter table public.game_items enable row level security;
drop policy if exists "eşya: herkes okur" on public.game_items;
create policy "eşya: herkes okur" on public.game_items for select to authenticated using (true);
revoke insert, update, delete on public.game_items from anon, authenticated;

insert into public.game_items (item_id, price, min_level) values
  ('food_apple', 3, 1), ('food_coconut', 4, 1), ('food_bread', 3, 1), ('food_watermelon', 5, 2), ('food_carrot', 3, 2),
  ('food_fish', 6, 3), ('food_icecream', 6, 4), ('food_corn', 4, 6), ('food_tomato', 3, 6),
  ('clean_soap', 3, 1), ('clean_bubble_bath', 8, 4),
  ('glasses_round', 15, 1), ('glasses_sun', 20, 2), ('glasses_star', 25, 5),
  ('shirt_stripes', 25, 2), ('shirt_hawaii', 35, 2), ('apron_sailor', 30, 2), ('hoodie_soft', 45, 4),
  ('vest_explorer', 50, 7), ('raincoat', 60, 8),
  ('hat_cap', 20, 3), ('hat_straw', 25, 3), ('hat_beanie', 22, 3), ('hat_crown', 40, 5), ('headphones', 35, 4),
  ('scarf_knit', 18, 2), ('backpack_small', 30, 3), ('cape_hero', 45, 5), ('badge_patch', 12, 2), ('sash_belt', 15, 3),
  ('glove_mitten', 15, 4), ('hand_flag', 10, 2),
  ('home_bed', 60, 4), ('home_rug', 40, 4), ('home_lamp', 45, 4), ('home_bookshelf', 80, 6), ('home_aquarium', 100, 8),
  ('seed_carrot', 2, 6), ('seed_corn', 2, 6), ('seed_tomato', 2, 6), ('seed_watermelon', 3, 7),
  ('decor_umbrella', 35, 3), ('decor_sandcastle', 25, 2), ('decor_palm', 50, 5), ('decor_lanterns', 70, 12),
  ('set_captain', 180, 9), ('set_captain_hat', 70, 9), ('set_star_cape', 150, 14)
on conflict (item_id) do update set price = excluded.price, min_level = excluded.min_level;

-- ---------------------------------------------------------------------
-- 5. Oyun kaydı yedeği
-- ---------------------------------------------------------------------
create table if not exists public.game_saves (
  child_id    uuid primary key references public.children (id) on delete cascade,
  family_id   uuid not null references public.families (id) on delete cascade,
  data        jsonb not null,
  updated_at  timestamptz not null default now()
);
alter table public.game_saves enable row level security;
drop policy if exists "kayıt: çocuk okur" on public.game_saves;
create policy "kayıt: çocuk okur" on public.game_saves for select to authenticated using (child_id = public.my_child_id());
drop policy if exists "kayıt: ebeveyn okur" on public.game_saves;
create policy "kayıt: ebeveyn okur" on public.game_saves for select to authenticated using (family_id = public.my_family_id());
revoke insert, update, delete on public.game_saves from anon, authenticated;

-- ---------------------------------------------------------------------
-- 6. Çocuk oturumu fonksiyonları
-- ---------------------------------------------------------------------

-- Oturumdaki çocuğun bilgisi; bağlantı kaldırıldıysa hata (oyun "kod iptal" ekranını gösterir).
create or replace function public.child_me()
returns json language plpgsql stable security definer set search_path = '' as $$
declare
  c public.children%rowtype;
begin
  select * into c from public.children where user_id = auth.uid();
  if not found then
    raise exception 'Bağlantı yok' using errcode = '42501';
  end if;
  return json_build_object('child_id', c.id, 'name', c.name, 'avatar', c.avatar,
                           'age_band', coalesce(c.age_band, public.suggest_age_band(c.birthday)),
                           'balance', public.coin_balance(c.id));
end $$;

-- Görev o gün var mı? (tek seferlik: başlangıç günü; tekrarlı: günlük / haftanın / ayın seçilen günleri)
create or replace function public.task_occurs_on(t public.tasks, d date)
returns boolean language sql stable set search_path = '' as $$
  select d >= t.start_date and (t.end_date is null or d <= t.end_date) and (
    (not t.recurring and d = t.start_date)
    or (t.recurring and t.repeat_kind = 'daily')
    or (t.recurring and t.repeat_kind = 'weekly' and extract(isodow from d)::smallint = any (t.repeat_days))
    or (t.recurring and t.repeat_kind = 'monthly' and (
          extract(day from d)::smallint = any (t.repeat_days)
          -- ayda o gün yoksa ayın son günü sayılır (ör. 31 → Şubat'ta 28/29)
          or (d = (date_trunc('month', d) + interval '1 month - 1 day')::date
              and exists (select 1 from unnest(t.repeat_days) x where x > extract(day from d)))
    ))
  )
$$;

-- Tarih aralığındaki görev örnekleri (en fazla 31 gün) ve durumları.
create or replace function public.child_tasks(p_from date, p_to date)
returns table (task_id uuid, date date, title text, description text, emoji text, coins integer,
               recurring boolean, repeat_kind text, requires_review boolean, status text, parent_note text)
language plpgsql stable security definer set search_path = '' as $$
declare
  me uuid := public.my_child_id();
begin
  if me is null then
    raise exception 'Bağlantı yok' using errcode = '42501';
  end if;
  if p_to < p_from or p_to - p_from > 31 then
    raise exception 'Tarih aralığı en fazla 31 gün olabilir';
  end if;
  return query
    select t.id, d::date, t.title, t.description, t.emoji, a.coins, t.recurring, t.repeat_kind, t.requires_review,
           coalesce(c.status, 'assigned'), c.parent_note
    from public.task_assignments a
    join public.tasks t on t.id = a.task_id
    cross join generate_series(p_from, p_to, interval '1 day') as d
    left join public.completions c on c.task_id = t.id and c.child_id = me and c.date = d::date
    where a.child_id = me and public.task_occurs_on(t, d::date)
    order by d, t.sort_order;
end $$;

-- Çocuğun niyeti: 'pending' (yaptım), 'declined' (yapamam), 'assigned' (geri al).
-- Ebeveyn karar verdiyse (approved/rejected) değiştirilemez. İnceleme gerektirmeyen görevde "yaptım" = onay.
create or replace function public.child_set_status(p_task_id uuid, p_date date, p_status text)
returns text language plpgsql security definer set search_path = '' as $$
declare
  me uuid := public.my_child_id();
  t public.tasks%rowtype;
  cur public.completions%rowtype;
  target text := p_status;
begin
  if me is null then
    raise exception 'Bağlantı yok' using errcode = '42501';
  end if;
  if p_status not in ('pending', 'declined', 'assigned') then
    raise exception 'Geçersiz durum';
  end if;
  select tk.* into t from public.tasks tk
    join public.task_assignments a on a.task_id = tk.id and a.child_id = me
    where tk.id = p_task_id;
  if not found or not public.task_occurs_on(t, p_date) then
    raise exception 'Görev bulunamadı';
  end if;
  if p_date > current_date + 1 then
    raise exception 'Gelecek günün görevi işaretlenemez';
  end if;

  select * into cur from public.completions where task_id = p_task_id and child_id = me and date = p_date for update;
  if found and cur.status in ('approved', 'rejected') then
    raise exception 'Ebeveyn karar verdi' using errcode = 'P0001';
  end if;

  if p_status = 'assigned' then
    delete from public.completions where task_id = p_task_id and child_id = me and date = p_date;
    return 'assigned';
  end if;
  if p_status = 'pending' and not t.requires_review then
    target := 'approved';
  end if;
  insert into public.completions (family_id, task_id, child_id, date, status)
  values (t.family_id, p_task_id, me, p_date, target)
  on conflict (task_id, child_id, date) do update set status = excluded.status, created_at = now();
  return target;
end $$;

-- Harcama: fiyat sunucudan, idempotent (aynı p_tx ikinci kez düşmez), bakiye eksiye düşmez.
create or replace function public.spend_coins(p_tx text, p_item_id text, p_quantity integer)
returns json language plpgsql security definer set search_path = '' as $$
declare
  me public.children%rowtype;
  it public.game_items%rowtype;
  total integer;
  bal integer;
begin
  select * into me from public.children where user_id = auth.uid() for update;   -- aynı çocuğun eşzamanlı harcamaları sıraya girer
  if not found then
    raise exception 'Bağlantı yok' using errcode = '42501';
  end if;
  if p_tx is null or char_length(p_tx) not between 8 and 64 then
    raise exception 'Geçersiz işlem kimliği';
  end if;
  if exists (select 1 from public.coin_ledger where child_id = me.id and reason = 'spend' and ref = p_tx) then
    return json_build_object('ok', true, 'error', null, 'balance', public.coin_balance(me.id));
  end if;
  select * into it from public.game_items where item_id = p_item_id;
  if not found or p_quantity is null or p_quantity not between 1 and 20 then
    return json_build_object('ok', false, 'error', 'unknown_item', 'balance', public.coin_balance(me.id));
  end if;
  total := it.price * p_quantity;
  bal := public.coin_balance(me.id);
  if total > bal then
    return json_build_object('ok', false, 'error', 'not_enough_coins', 'balance', bal);
  end if;
  if total > 0 then
    insert into public.coin_ledger (family_id, child_id, amount, reason, ref, item_id, quantity)
    values (me.family_id, me.id, -total, 'spend', p_tx, p_item_id, p_quantity);
  end if;
  return json_build_object('ok', true, 'error', null, 'balance', bal - total);
end $$;

create or replace function public.game_save_get()
returns jsonb language sql stable security definer set search_path = '' as $$
  select data from public.game_saves where child_id = public.my_child_id()
$$;

create or replace function public.game_save_put(p_data jsonb)
returns void language plpgsql security definer set search_path = '' as $$
declare
  me public.children%rowtype;
begin
  select * into me from public.children where user_id = auth.uid();
  if not found then
    raise exception 'Bağlantı yok' using errcode = '42501';
  end if;
  if pg_column_size(p_data) > 262144 then
    raise exception 'Kayıt çok büyük';
  end if;
  insert into public.game_saves (child_id, family_id, data) values (me.id, me.family_id, p_data)
  on conflict (child_id) do update set data = excluded.data, updated_at = now();
end $$;

-- ---------------------------------------------------------------------
-- 7. Ebeveyn fonksiyonları
-- ---------------------------------------------------------------------
create or replace function public.set_child_age_band(p_child_id uuid, p_band text)
returns void language plpgsql security definer set search_path = '' as $$
begin
  if p_band is not null and p_band not in ('A', 'B', 'C') then
    raise exception 'Geçersiz yaş bandı';
  end if;
  update public.children set age_band = p_band where id = p_child_id and family_id = public.my_family_id();
  if not found then
    raise exception 'Çocuk bulunamadı' using errcode = '42501';
  end if;
end $$;

-- İnceleme: onay ('approved') ya da ret ('rejected' + not). Tamamlama kaydı yoksa (çocuk henüz işaretlemedi) oluşturulur.
create or replace function public.review_completion(p_task_id uuid, p_child_id uuid, p_date date, p_status text, p_note text default null)
returns void language plpgsql security definer set search_path = '' as $$
declare
  fam uuid := public.my_family_id();
begin
  if fam is null or public.child_family(p_child_id) is distinct from fam or public.task_family(p_task_id) is distinct from fam then
    raise exception 'Yetki yok' using errcode = '42501';
  end if;
  if p_status not in ('approved', 'rejected', 'pending') then
    raise exception 'Geçersiz durum';
  end if;
  insert into public.completions (family_id, task_id, child_id, date, status, parent_note, reviewed_at, reviewed_by)
  values (fam, p_task_id, p_child_id, p_date, p_status, nullif(trim(p_note), ''), now(), auth.uid())
  on conflict (task_id, child_id, date) do update
    set status = excluded.status, parent_note = excluded.parent_note, reviewed_at = now(), reviewed_by = auth.uid();
end $$;

-- Cihaz bağlantısını kaldır (kod iptali, FR-AUTH-4): oyun bir sonraki kontrolde "bağlantın kapatıldı" der.
create or replace function public.unlink_child_device(p_child_id uuid)
returns void language plpgsql security definer set search_path = '' as $$
begin
  update public.children set user_id = null where id = p_child_id and family_id = public.my_family_id();
  if not found then
    raise exception 'Çocuk bulunamadı' using errcode = '42501';
  end if;
end $$;

create or replace function public.child_balance(p_child_id uuid)
returns integer language plpgsql stable security definer set search_path = '' as $$
begin
  if public.child_family(p_child_id) is distinct from public.my_any_family_id() then
    raise exception 'Yetki yok' using errcode = '42501';
  end if;
  return public.coin_balance(p_child_id);
end $$;

-- ---------------------------------------------------------------------
-- Yetkiler
-- ---------------------------------------------------------------------
revoke execute on function public.suggest_age_band(date) from public, anon;
revoke execute on function public.child_age_band(uuid) from public, anon, authenticated;
revoke execute on function public.coin_balance(uuid) from public, anon, authenticated;
revoke execute on function public.completions_coin_trigger() from public, anon, authenticated;
revoke execute on function public.task_occurs_on(public.tasks, date) from public, anon;
revoke execute on function public.child_me() from public, anon;
revoke execute on function public.child_tasks(date, date) from public, anon;
revoke execute on function public.child_set_status(uuid, date, text) from public, anon;
revoke execute on function public.spend_coins(text, text, integer) from public, anon;
revoke execute on function public.game_save_get() from public, anon;
revoke execute on function public.game_save_put(jsonb) from public, anon;
revoke execute on function public.set_child_age_band(uuid, text) from public, anon;
revoke execute on function public.review_completion(uuid, uuid, date, text, text) from public, anon;
revoke execute on function public.child_balance(uuid) from public, anon;
revoke execute on function public.unlink_child_device(uuid) from public, anon;
grant execute on function public.unlink_child_device(uuid) to authenticated;
grant execute on function public.suggest_age_band(date) to authenticated;
grant execute on function public.task_occurs_on(public.tasks, date) to authenticated;
grant execute on function public.child_me() to authenticated;
grant execute on function public.child_tasks(date, date) to authenticated;
grant execute on function public.child_set_status(uuid, date, text) to authenticated;
grant execute on function public.spend_coins(text, text, integer) to authenticated;
grant execute on function public.game_save_get() to authenticated;
grant execute on function public.game_save_put(jsonb) to authenticated;
grant execute on function public.set_child_age_band(uuid, text) to authenticated;
grant execute on function public.review_completion(uuid, uuid, date, text, text) to authenticated;
grant execute on function public.child_balance(uuid) to authenticated;
