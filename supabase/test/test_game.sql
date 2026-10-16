-- Önerilen oyun şemasının uçtan uca testi (yerel PostgreSQL, supabase_stub.sql ile).
-- Her adım beklenen sonucu kontrol eder; hata varsa exception ile durur.
\set ON_ERROR_STOP on

create schema if not exists tst;
create or replace function tst.as_user(u uuid) returns void language plpgsql as $$
begin
  perform set_config('request.jwt.claim.sub', coalesce(u::text, ''), false);
end $$;

create or replace function tst.check(cond boolean, msg text) returns void language plpgsql as $$
begin
  if not coalesce(cond, false) then raise exception 'TEST BAŞARISIZ: %', msg; end if;
  raise notice 'ok: %', msg;
end $$;

create or replace function tst.fails(sql text, msg text) returns void language plpgsql as $$
begin
  begin
    execute sql;
  exception when others then
    raise notice 'ok (beklenen hata): % → %', msg, sqlerrm;
    return;
  end;
  raise exception 'TEST BAŞARISIZ (hata bekleniyordu): %', msg;
end $$;

-- Sabit kimlikler
-- ebeveyn  a1, çocuk cihazı c1, yabancı ebeveyn e1, çocuk kaydı c0de, görevler 7a51 (günlük, inceleme) 7a52 (tek, incelemesiz)

insert into auth.users (id, is_anonymous, raw_user_meta_data) values
  ('00000000-0000-0000-0000-0000000000a1', false, '{"nickname":"Anne"}'),
  ('00000000-0000-0000-0000-0000000000c1', true, '{}'),
  ('00000000-0000-0000-0000-0000000000e1', false, '{"nickname":"Yabancı"}');

grant usage on schema tst to authenticated;
grant execute on all functions in schema tst to authenticated;
set role authenticated;

-- ---------------------------------------------------------------- ebeveyn kurulumu
select tst.as_user('00000000-0000-0000-0000-0000000000a1');
insert into public.children (id, family_id, name, avatar, birthday)
  values ('00000000-0000-0000-0000-00000000c0de', public.my_family_id(), 'Nazlı', 'flamingo', current_date - interval '11 years');
insert into public.tasks (id, family_id, title, start_date, recurring, repeat_kind, requires_review)
  values ('00000000-0000-0000-0000-000000007a51', public.my_family_id(), 'Odanı topla', current_date - 3, true, 'daily', true),
         ('00000000-0000-0000-0000-000000007a52', public.my_family_id(), 'Dişlerini fırçala', current_date, false, 'daily', false),
         ('00000000-0000-0000-0000-000000007a53', public.my_family_id(), 'Pazartesi kitap', current_date - 14, true, 'weekly', true);
update public.tasks set repeat_days = '{1}' where id = '00000000-0000-0000-0000-000000007a53';
insert into public.task_assignments (task_id, child_id, family_id, difficulty, coins) values
  ('00000000-0000-0000-0000-000000007a51', '00000000-0000-0000-0000-00000000c0de', public.my_family_id(), 'medium', 10),
  ('00000000-0000-0000-0000-000000007a52', '00000000-0000-0000-0000-00000000c0de', public.my_family_id(), 'easy', 5),
  ('00000000-0000-0000-0000-000000007a53', '00000000-0000-0000-0000-00000000c0de', public.my_family_id(), 'easy', 5);

-- yaş bandı doğrudan yazılabilir (ParentApp: çocuk eklerken / düzenlerken)
insert into public.children (id, family_id, name, avatar, age_band)
  values ('00000000-0000-0000-0000-00000000c0d2', public.my_family_id(), 'Efe', 'kedi', 'A');
update public.children set age_band = 'B' where id = '00000000-0000-0000-0000-00000000c0d2';
select tst.check((select age_band from public.children where id = '00000000-0000-0000-0000-00000000c0d2') = 'B', 'ebeveyn yaş bandını doğrudan yazar');
select tst.fails($$update public.children set age_band = 'Z' where id = '00000000-0000-0000-0000-00000000c0d2'$$, 'geçersiz bant reddedilir');

create temp table codes as select * from public.create_invite_code('child', '00000000-0000-0000-0000-00000000c0de');
grant select on codes to authenticated;

-- ---------------------------------------------------------------- çocuk girişi
select tst.as_user('00000000-0000-0000-0000-0000000000c1');
select tst.check((public.redeem_child_code((select code from codes)) ->> 'age_band') = 'B', 'giriş yanıtında age_band');
select tst.check((public.child_me() ->> 'balance')::int = 0, 'başlangıç bakiyesi 0');

-- görev listesi: bugünden önceki 3 gün + bugün (günlük) + tek seferlik bugün + haftalık pazartesiler
select tst.check((select count(*) from public.child_tasks(current_date - 1, current_date)
                      where task_id = '00000000-0000-0000-0000-000000007a51') = 2, 'günlük görev her gün açılır');
select tst.check((select count(*) from public.child_tasks(current_date - 1, current_date + 1)
                      where task_id = '00000000-0000-0000-0000-000000007a52') = 1, 'tek seferlik görev yalnız başlangıç günü');
select tst.check((select count(*) from public.child_tasks(current_date - 13, current_date)
                      where task_id = '00000000-0000-0000-0000-000000007a53') = 2, 'haftalık görev yalnız pazartesi (14 günde 2)');
select tst.check((select bool_and(extract(isodow from date) = 1) from public.child_tasks(current_date - 13, current_date)
                      where task_id = '00000000-0000-0000-0000-000000007a53'), 'haftalık görevin günleri pazartesi');
select tst.fails($$select * from public.child_tasks(current_date - 40, current_date)$$, '31 günden uzun aralık reddedilir');

-- yaptım → bekliyor; coin yok
select tst.check(public.child_set_status('00000000-0000-0000-0000-000000007a51', current_date, 'pending') = 'pending', 'yaptım → pending');
select tst.check((public.child_me() ->> 'balance')::int = 0, 'onaysız coin yok');
-- incelemesiz görev: yaptım = onay → +5
select tst.check(public.child_set_status('00000000-0000-0000-0000-000000007a52', current_date, 'pending') = 'approved', 'incelemesiz görev doğrudan onaylanır');
select tst.check((public.child_me() ->> 'balance')::int = 5, 'incelemesiz görev coin verir');
-- geri al / yapamam
select tst.check(public.child_set_status('00000000-0000-0000-0000-000000007a51', current_date - 1, 'declined') = 'declined', 'yapamam');
select tst.check(public.child_set_status('00000000-0000-0000-0000-000000007a51', current_date - 1, 'assigned') = 'assigned', 'geri al');
select tst.fails($$select public.child_set_status('00000000-0000-0000-0000-000000007a51', current_date + 5, 'pending')$$, 'gelecek gün işaretlenemez');
select tst.fails($$select public.child_set_status('00000000-0000-0000-0000-000000007a51', current_date, 'approved')$$, 'çocuk kendini onaylayamaz');
-- çocuk defteri doğrudan yazamaz
select tst.fails($$insert into public.coin_ledger (family_id, child_id, amount, reason, ref) values (public.my_any_family_id(), public.my_child_id(), 999, 'adjust', 'hile')$$, 'çocuk coin ekleyemez');
update public.children set age_band = 'C' where user_id = auth.uid();   -- RLS: çocuk kendi kaydını güncelleyemez → 0 satır
select tst.check((select age_band from public.children where user_id = auth.uid()) is null, 'çocuk yaş bandını değiştiremez');
update public.completions set status = 'approved' where child_id = public.my_child_id();   -- RLS: güncelleme politikası yok → 0 satır
select tst.check((select count(*) from public.completions where status = 'approved' and task_id = '00000000-0000-0000-0000-000000007a51') = 0, 'RLS: güncelleme etkisiz');

-- ---------------------------------------------------------------- yabancı ebeveyn
select tst.as_user('00000000-0000-0000-0000-0000000000e1');
select tst.fails($$select public.review_completion('00000000-0000-0000-0000-000000007a51', '00000000-0000-0000-0000-00000000c0de', current_date, 'approved')$$, 'başka aile onaylayamaz');
select tst.fails($$select public.child_balance('00000000-0000-0000-0000-00000000c0de')$$, 'başka aile bakiyeyi göremez');
select tst.check((select count(*) from public.coin_ledger) = 0, 'başka aile defteri göremez');

-- ---------------------------------------------------------------- ebeveyn onayı / reddi
select tst.as_user('00000000-0000-0000-0000-0000000000a1');
select public.review_completion('00000000-0000-0000-0000-000000007a51', '00000000-0000-0000-0000-00000000c0de', current_date, 'approved', 'Aferin!');
select tst.check(public.child_balance('00000000-0000-0000-0000-00000000c0de') = 15, 'onay +10 (toplam 15)');
select public.review_completion('00000000-0000-0000-0000-000000007a51', '00000000-0000-0000-0000-00000000c0de', current_date, 'approved', 'Aferin!');
select tst.check(public.child_balance('00000000-0000-0000-0000-00000000c0de') = 15, 'aynı onay iki kez coin vermez');
select public.review_completion('00000000-0000-0000-0000-000000007a51', '00000000-0000-0000-0000-00000000c0de', current_date - 2, 'rejected', 'Yatak dağınık kalmış');
select tst.check(public.child_balance('00000000-0000-0000-0000-00000000c0de') = 15, 'ret coin vermez');
select public.set_child_age_band('00000000-0000-0000-0000-00000000c0de', 'C');

-- ---------------------------------------------------------------- çocuk: sonuç ve harcama
select tst.as_user('00000000-0000-0000-0000-0000000000c1');
select tst.check((public.child_me() ->> 'age_band') = 'C', 'ebeveynin seçtiği bant geçerli');
select tst.check((select status from public.child_tasks(current_date - 2, current_date - 2) where task_id = '00000000-0000-0000-0000-000000007a51') = 'rejected', 'ret çocuğa görünür');
select tst.check((select parent_note from public.child_tasks(current_date - 2, current_date - 2) where task_id = '00000000-0000-0000-0000-000000007a51') = 'Yatak dağınık kalmış', 'ret notu');
select tst.fails($$select public.child_set_status('00000000-0000-0000-0000-000000007a51', current_date, 'assigned')$$, 'onaylanan görev geri alınamaz');

select tst.check((public.spend_coins('tx-0000000001', 'glasses_round', 1) ->> 'balance')::int = 0, 'gözlük 15 coin → bakiye 0');
select tst.check((public.spend_coins('tx-0000000001', 'glasses_round', 1) ->> 'ok')::boolean, 'aynı işlem tekrar: düşmez, ok');
select tst.check((public.child_me() ->> 'balance')::int = 0, 'idempotent harcama');
select tst.check((public.spend_coins('tx-0000000002', 'food_apple', 1) ->> 'error') = 'not_enough_coins', 'yetersiz coin');
select tst.check((public.spend_coins('tx-0000000003', 'yok_boyle', 1) ->> 'error') = 'unknown_item', 'bilinmeyen eşya');
select tst.check((public.spend_coins('tx-0000000004', 'food_apple', 99) ->> 'error') = 'unknown_item', 'aşırı adet reddedilir');

-- kayıt yedeği
select public.game_save_put('{"Schema":1,"PetId":"pet_03"}'::jsonb);
select tst.check((public.game_save_get() ->> 'PetId') = 'pet_03', 'kayıt yedeği okunur');

-- ---------------------------------------------------------------- onay geri alınırsa coin düşer
select tst.as_user('00000000-0000-0000-0000-0000000000a1');
select public.review_completion('00000000-0000-0000-0000-000000007a51', '00000000-0000-0000-0000-00000000c0de', current_date, 'pending');
select tst.check(public.child_balance('00000000-0000-0000-0000-00000000c0de') = -10, 'onay geri alınınca coin geri düşer (harcandıysa eksi görünür)');

-- ---------------------------------------------------------------- bağlantı kaldırma (kod iptali)
select tst.as_user('00000000-0000-0000-0000-0000000000e1');
select tst.fails($$select public.unlink_child_device('00000000-0000-0000-0000-00000000c0de')$$, 'başka aile bağlantıyı kaldıramaz');
select tst.as_user('00000000-0000-0000-0000-0000000000a1');
select public.unlink_child_device('00000000-0000-0000-0000-00000000c0de');
select tst.as_user('00000000-0000-0000-0000-0000000000c1');
select tst.fails($$select public.child_me()$$, 'bağlantı kaldırılınca child_me hata verir');
select tst.fails($$select public.spend_coins('tx-0000000009', 'food_apple', 1)$$, 'bağlantısız harcama yok');

reset role;
select 'TÜM OYUN SUNUCU TESTLERİ GEÇTİ' as sonuc;
