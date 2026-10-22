using System;
using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using Pofi.Logic.App;
using Pofi.Logic.Economy;
using Pofi.Logic.Island;
using Pofi.Logic.Progression;
using Pofi.Logic.Services.Mock;
using Pofi.Logic.State;
using Pofi.Logic.Tasks;

namespace Pofi.Tests.Logic
{
    /// <summary>Omurga Ö1 (Güneş Taşı), Ö2 (gerçek görev XP'si + beceri yıldızı), Ö5 (ilk gün).</summary>
    public class SunStoneTests
    {
        private static readonly DateTime Utc = new DateTime(2026, 10, 19, 9, 0, 0, DateTimeKind.Utc);
        private static readonly DateTime Local = new DateTime(2026, 10, 19, 12, 0, 0);
        private const string Day = "2026-10-19";

        private static SunStoneBook Book => TestData.Load().SunBook;
        private static LevelTable Levels => new LevelTable(TestData.Load().Levels);

        [Test]
        public void Veri_gecerli_ve_ilk_nokta_tek_tasla_acilir()
        {
            Assert.IsEmpty(TestData.Load().Validate());
            Assert.GreaterOrEqual(Book.Spots.Count, 3);
            Assert.AreEqual(1, Book.Spots[0].Cost, "ilk onaylı görev ilk sisi kaldırır (Ö5)");
            var map = new IslandMap(TestData.ReadText("regions.json"), Levels);
            foreach (var s in Book.Spots) Assert.IsNotNull(map.Find(s.Region), s.Id);
        }

        [Test]
        public void Tas_sirayla_yerlestirilir_ve_harcanmaz()
        {
            var st = new SunStoneState();
            var first = Book.Spots[0];
            var second = Book.Spots[1];
            Assert.AreEqual(PlaceResult.NoStones, Book.PlaceOne(st, first.Id));
            SunStoneBook.ApplyServerTotal(st, 3);
            Assert.AreEqual(PlaceResult.NotNext, Book.PlaceOne(st, second.Id), "sıradaki nokta önce");
            Assert.AreEqual(PlaceResult.Repaired, Book.PlaceOne(st, first.Id));
            Assert.AreEqual(PlaceResult.AlreadyRepaired, Book.PlaceOne(st, first.Id));
            Assert.AreEqual(second, Book.Next(st));
            Assert.AreEqual(PlaceResult.Ok, Book.PlaceOne(st, second.Id));
            Assert.AreEqual(1, SunStoneBook.Available(st));
            Assert.AreEqual(3, st.Earned, "yerleştirme toplamı düşürmez");
        }

        [Test]
        public void Onay_geri_alininca_yerlestirilen_tas_geri_alinmaz()
        {
            var st = new SunStoneState();
            Assert.AreEqual(2, SunStoneBook.ApplyServerTotal(st, 2));
            Book.PlaceOne(st, Book.Spots[0].Id);
            Book.PlaceOne(st, Book.Spots[1].Id);
            Assert.AreEqual(0, SunStoneBook.ApplyServerTotal(st, 1));
            Assert.AreEqual(0, SunStoneBook.Available(st));
            Assert.IsTrue(Book.IsRepaired(st, Book.Spots[0].Id), "ceza yok");
            Assert.AreEqual(0, SunStoneBook.ApplyServerTotal(st, 2), "aradaki fark kapanır, yeni taş sayılmaz");
            Assert.AreEqual(1, SunStoneBook.ApplyServerTotal(st, 3));
            Assert.AreEqual(0, SunStoneBook.ApplyServerTotal(st, null), "sunucu taş bilmiyorsa yerel değer kalır");
            Assert.AreEqual(3, st.Earned);
        }

        [Test]
        public void Tasla_acilan_bolge_seviyeyle_acilmaz()
        {
            var levels = Levels;
            var map = new IslandMap(TestData.ReadText("regions.json"), levels);
            var st = new SunStoneState();
            var cove = Book.Spots[0];
            Assert.AreEqual("region_swim_cove", cove.Region);
            var v = map.View(15, new HashSet<string>(), Book, st).First(x => x.Region.Id == cove.Region);
            Assert.IsFalse(v.Unlocked, "Sv 15 de açmaz");
            Assert.AreEqual(1, v.StonesLeft);
            Assert.IsFalse(Book.IsOpen("minigame_swim", 15, levels, st));
            Assert.IsTrue(Book.IsOpen("region_surf_beach", 3, levels, st), "taşsız içerik seviyeyle");
            Assert.AreNotEqual(cove.Region, map.NextToUnlock(1, new HashSet<string>(), Book, st).Region.Id, "seviye havucu taşlı bölgeyi göstermez");

            SunStoneBook.ApplyServerTotal(st, 1);
            Book.PlaceOne(st, cove.Id);
            v = map.View(1, new HashSet<string>(), Book, st).First(x => x.Region.Id == cove.Region);
            Assert.IsTrue(v.Unlocked, "Sv 1'de de açılır");
            Assert.IsTrue(v.IsNew);
            Assert.IsTrue(Book.IsOpen("minigame_swim", 1, levels, st));
        }

        [Test]
        public void Seviye_kutlamasindan_tasli_icerik_cikar()
        {
            var up = Levels.Check(0, Levels.TotalXpFor(2));
            CollectionAssert.Contains(up.Unlocked, "region_swim_cove");
            Book.FilterLevelUp(up);
            CollectionAssert.DoesNotContain(up.Unlocked, "region_swim_cove");
            CollectionAssert.DoesNotContain(up.Unlocked, "minigame_swim");
            CollectionAssert.Contains(up.Unlocked, "shop_clothes");
        }

        [Test]
        public void Gunluk_gorev_tasli_oyunu_onarimdan_once_istemez()
        {
            var data = TestData.Load();
            var s = GameState.NewFor("c", Utc);
            s.Xp.TotalXp = Levels.TotalXpFor(15);
            for (var d = 0; d < 20; d++)
            {
                s.DailyQuests = new Pofi.Logic.Meta.DailyQuestState();
                Activity.EnsureQuests(s, data, Levels, Local.AddDays(d));
                Assert.IsFalse(s.DailyQuests.Ids.Any(q => q == "dq_swim_1" || q == "dq_fish_2"), "gün " + d);
            }
        }

        // ------------------------------------------------------------------ Ö2

        [Test]
        public void Beceri_etiketleri_alti_beceriye_eslenir()
        {
            // kategori = beceri (23 Ekim 2026): her kategorinin tek becerisi
            Assert.AreEqual(SkillCatalog.Teamwork, SkillCatalog.Map("home"));
            Assert.AreEqual(SkillCatalog.Stamina, SkillCatalog.Map("mind"));
            Assert.AreEqual(SkillCatalog.Knowledge, SkillCatalog.Map("learn"));
            Assert.AreEqual(SkillCatalog.Strength, SkillCatalog.Map("health"));
            Assert.AreEqual(SkillCatalog.Focus, SkillCatalog.Map("focus"));
            Assert.AreEqual(SkillCatalog.Kindness, SkillCatalog.Map("relation"));
            // eski ParentApp etiketleri ve İngilizce adlar
            Assert.AreEqual(SkillCatalog.Focus, SkillCatalog.Map("Odaklanma"));
            Assert.AreEqual(SkillCatalog.Teamwork, SkillCatalog.Map("Takım Çalışması"));
            Assert.AreEqual(SkillCatalog.Teamwork, SkillCatalog.Map("Sorumluluk"));
            Assert.AreEqual(SkillCatalog.Kindness, SkillCatalog.Map("Empati"));
            Assert.AreEqual(SkillCatalog.Kindness, SkillCatalog.Map("MİNNETTARLIK"));
            Assert.AreEqual(SkillCatalog.Stamina, SkillCatalog.Map(" Sakinleşme "));
            Assert.AreEqual(SkillCatalog.Strength, SkillCatalog.Map("Öz Bakım"));
            Assert.AreEqual(SkillCatalog.Teamwork, SkillCatalog.Map("independence"));
            Assert.AreEqual(SkillCatalog.Knowledge, SkillCatalog.Map("Okuma"));
            Assert.AreEqual(SkillCatalog.Strength, SkillCatalog.Map("Strength"));
            Assert.AreEqual(SkillCatalog.Teamwork, SkillCatalog.Map("Teamwork"));
            Assert.AreEqual(SkillCatalog.Kindness, SkillCatalog.Map("kindness"));
            Assert.IsNull(SkillCatalog.Map("Özel"));
            Assert.IsNull(SkillCatalog.Map(""));
            Assert.AreEqual("Takım Çalışması", SkillCatalog.Label(SkillCatalog.Teamwork));
            Assert.AreEqual("Dayanıklılık", SkillCatalog.Label(SkillCatalog.Stamina));
        }

        [Test]
        public void Eski_beceri_yildizlari_yeni_anahtarlara_tasinir()
        {
            var s = new SkillState();
            s.Stars["responsibility"] = 3; s.Stars["independence"] = 2; s.Stars["calm"] = 4; s.Stars["self_care"] = 1;
            s.Stars["focus"] = 5; s.Stars["kindness"] = 2; s.Stars["bilinmeyen"] = 9;
            s.Normalize();
            Assert.AreEqual(5, s.StarsOf(SkillCatalog.Teamwork));
            Assert.AreEqual(4, s.StarsOf(SkillCatalog.Stamina));
            Assert.AreEqual(1, s.StarsOf(SkillCatalog.Strength));
            Assert.AreEqual(5, s.StarsOf(SkillCatalog.Focus));
            Assert.AreEqual(2, s.StarsOf(SkillCatalog.Kindness));
            Assert.IsFalse(s.Stars.ContainsKey("bilinmeyen"));
            Assert.AreEqual(5, s.Stars.Count, "bilinmeyen anahtar düşer");
            var json = SaveCodec.Serialize(new GameState { ChildId = "c", Skills = new SkillState { Stars = new System.Collections.Generic.Dictionary<string, int> { ["calm"] = 2 } } }, System.DateTime.UtcNow);
            Assert.AreEqual(2, SaveCodec.Deserialize(json).Skills.StarsOf(SkillCatalog.Stamina), "kayıt yüklenince taşınır");
        }

        [Test]
        public void Onayli_gorev_bir_kez_odullendirilir_ve_kademe_yukselir()
        {
            var s = new SkillState();
            ChildTask T(int i, string diff) => new ChildTask { TaskId = "t" + i, Date = Day, Status = ChildTaskStatus.Approved, Skill = "Sorumluluk", Difficulty = diff };
            var r = RealTaskRewards.Apply(s, T(0, "hard"));
            Assert.AreEqual(14, r.Xp, "zor görev cüzî XP (M7, 22 Ekim 2026)");
            Assert.AreEqual(SkillCatalog.Teamwork, r.Skill);
            Assert.AreEqual(1, r.Stars);
            Assert.IsNull(RealTaskRewards.Apply(s, T(0, "hard")), "aynı görev örneği ikinci kez ödül vermez");
            Assert.IsNull(RealTaskRewards.Apply(s, new ChildTask { TaskId = "x", Date = Day, Status = ChildTaskStatus.ChildDone }), "onaysız ödül yok");
            for (var i = 1; i < 4; i++) Assert.AreEqual(0, RealTaskRewards.Apply(s, T(i, "easy")).NewTier);
            var fifth = RealTaskRewards.Apply(s, T(4, null));
            Assert.AreEqual(6, fifth.Xp, "zorluk yoksa kolay");
            Assert.AreEqual(1, fifth.NewTier, "5 yıldız bronz");
            Assert.AreEqual(2, RealTaskRewards.Tier(15));
            Assert.AreEqual(3, RealTaskRewards.Tier(30));
            Assert.AreEqual(SkillCatalog.Teamwork, RealTaskRewards.Ranked(s).First().Key);
        }

        [Test]
        public void Gercek_gorev_XPsi_gunluk_sinira_sayilmaz()
        {
            var xp = new XpSystem();
            xp.Add(300, XpSource.MiniGame, Local, 300);
            Assert.AreEqual(50, xp.Add(50, XpSource.RealTask, Local, 300).Granted);
        }

        [Test]
        public void Gercek_gorev_XPsi_gorunmez_gunluk_payi_gecmez()
        {
            var xp = new XpSystem();
            // oyun oynamadan: pay en az 20 (2 orta görev), üçüncü görev XP vermez ama hedef mesajı tetiklenir
            Assert.AreEqual(10, xp.AddRealTask(10, Local).Granted);
            Assert.AreEqual(10, xp.AddRealTask(10, Local).Granted);
            var third = xp.AddRealTask(10, Local);
            Assert.AreEqual(0, third.Granted);
            Assert.IsTrue(third.CapReached);
            // oyun içi XP payı büyütür: bugün 45 oyun içi → toplam 45'e kadar gerçek görev XP'si
            xp.Add(45, XpSource.DailyQuest, Local, 300);
            Assert.AreEqual(14, xp.AddRealTask(14, Local).Granted);
            var cut = xp.AddRealTask(14, Local);
            Assert.AreEqual(11, cut.Granted, "kalan pay kadar (45 − 20 − 14)");
            Assert.IsTrue(cut.CapReached);
            Assert.AreEqual(45 + 45, xp.TotalXp);
            // ertesi gün sıfırlanır; seri bonusu oyun içi sayılmaz
            var next = Local.AddDays(1);
            xp.Add(40, XpSource.TaskStreak, next, int.MaxValue);
            Assert.AreEqual(0, xp.InGameToday);
            Assert.AreEqual(14, xp.AddRealTask(14, next).Granted);
        }

        [Test]
        public void Senkron_onayda_tas_XP_ve_yildiz_verir()
        {
            var data = TestData.Load();
            var server = new MockBackend(data);
            var sync = new SyncCoordinator(server, server, server, data);
            var s = GameState.NewFor("c", Utc);
            s.PetId = "pet_01"; s.PetName = "Pofi";
            server.ParentAssign("t_room", Day, "Odanı topla", 10, Recurrence.Once, "Sorumluluk", "medium");
            sync.SyncAsync(s, Local, Utc).Wait();
            s.Tasks.Mark("t_room|" + Day, ChildTaskStatus.ChildDone, Local, Utc);
            sync.SyncAsync(s, Local, Utc).Wait();
            server.ParentApprove("t_room|" + Day);

            var r = sync.SyncAsync(s, Local, Utc).Result;
            Assert.AreEqual(2, r.SunStonesEarned, "orta görev 2 taş");
            Assert.AreEqual(2, s.SunStones.Earned);
            Assert.AreEqual(10, r.RealTaskXp);
            Assert.AreEqual(10 + TaskStreak.Bonus(1), s.Xp.TotalXp, "görev XP'si + seri bonusu");
            Assert.IsFalse(r.RealTaskGoalReached, "tek görev günlük payı doldurmaz");
            Assert.AreEqual(1, s.Skills.StarsOf(SkillCatalog.Teamwork));
            Assert.AreEqual(10, s.Wallet.Available);

            var again = sync.SyncAsync(s, Local, Utc).Result;
            Assert.AreEqual(0, again.SunStonesEarned + again.RealTaskXp, "tekrar senkron ödül vermez");

            s = SaveCodec.Deserialize(SaveCodec.Serialize(s, Utc));
            Assert.AreEqual(2, s.SunStones.Earned, "kayıtta kalır");
            Assert.AreEqual(1, s.Skills.StarsOf(SkillCatalog.Teamwork));
        }

        [Test]
        public void Gorev_XPsi_seviye_atlatirsa_kutlama_bilgisi_doner()
        {
            var data = TestData.Load();
            var server = new MockBackend(data);
            var sync = new SyncCoordinator(server, server, server, data);
            var s = GameState.NewFor("c", Utc);
            s.Xp.TotalXp = Levels.TotalXpFor(2) - 1;
            server.ParentAssign("t1", Day, "Ödev", 5, Recurrence.Once, null, "hard");
            sync.SyncAsync(s, Local, Utc).Wait();
            s.Tasks.Mark("t1|" + Day, ChildTaskStatus.ChildDone, Local, Utc);
            sync.SyncAsync(s, Local, Utc).Wait();
            server.ParentApprove("t1|" + Day);
            var r = sync.SyncAsync(s, Local, Utc).Result;
            Assert.IsNotNull(r.LevelUp);
            Assert.AreEqual(2, r.LevelUp.To);
            Assert.IsNull(r.RealTaskRewards.Single().Skill, "becerisiz görev yalnız XP");
        }

        // ------------------------------------------------------------------ Ö5

        [Test]
        public void Ilk_gun_akisi_adim_adim_ilerler()
        {
            var data = TestData.Load();
            var server = new MockBackend(data);
            var sync = new SyncCoordinator(server, server, server, data);
            var s = GameState.NewFor("c", Utc);
            FirstDay.Start(s, Utc);
            Assert.AreEqual(FirstDayStep.Story, FirstDay.Current(s, Local, Utc));
            Onboarding.Done(s, Onboarding.Story);
            Assert.AreEqual(FirstDayStep.Pet, FirstDay.Current(s, Local, Utc));
            s.PetId = "pet_01"; s.PetName = "Pofi";
            Assert.AreEqual(FirstDayStep.Walk, FirstDay.Current(s, Local, Utc));
            Assert.IsFalse(FirstDay.AllowsTip(FirstDayStep.Walk, Onboarding.Wardrobe), "diğer ipuçları bekler");
            Assert.IsTrue(FirstDay.AllowsTip(FirstDayStep.Walk, Onboarding.Enter));
            Onboarding.Done(s, Onboarding.Walk);
            Assert.AreEqual(FirstDayStep.Feed, FirstDay.Current(s, Local, Utc));
            Onboarding.Done(s, Onboarding.Feed);

            server.ParentAssign("t_teeth", Day, "Dişlerini fırçala", 5, Recurrence.Once, "Öz Bakım", "easy");
            sync.SyncAsync(s, Local, Utc).Wait();
            Assert.AreEqual(FirstDayStep.Board, FirstDay.Current(s, Local, Utc));
            Onboarding.Done(s, Onboarding.Board);
            Assert.AreEqual(FirstDayStep.Mark, FirstDay.Current(s, Local, Utc));
            s.Tasks.Mark("t_teeth|" + Day, ChildTaskStatus.ChildDone, Local, Utc);
            Assert.AreEqual(FirstDayStep.Wait, FirstDay.Current(s, Local, Utc));
            sync.SyncAsync(s, Local, Utc).Wait();
            server.ParentApprove("t_teeth|" + Day);
            sync.SyncAsync(s, Local, Utc).Wait();
            Assert.AreEqual(FirstDayStep.Stone, FirstDay.Current(s, Local, Utc));
            Assert.AreEqual(PlaceResult.Repaired, data.SunBook.PlaceOne(s.SunStones, data.SunBook.Next(s.SunStones).Id));
            Assert.AreEqual(FirstDayStep.Done, FirstDay.Current(s, Local, Utc), "ilk sis kalktı: akış bitti");
            Assert.IsTrue(FirstDay.AllowsTip(FirstDayStep.Done, Onboarding.Wardrobe));
        }

        [Test]
        public void Ilk_gun_cocugu_bekletmez()
        {
            var s = GameState.NewFor("c", Utc);
            FirstDay.Start(s, Utc);
            foreach (var id in new[] { Onboarding.Story, Onboarding.Walk, Onboarding.Feed, Onboarding.Board }) Onboarding.Done(s, id);
            s.PetId = "pet_01"; s.PetName = "Pofi";
            Assert.AreEqual(FirstDayStep.Done, FirstDay.Current(s, Local, Utc), "panoda görev yok: biter");

            var waiting = GameState.NewFor("c", Utc);
            FirstDay.Start(waiting, Utc);
            Assert.AreEqual(FirstDayStep.Story, FirstDay.Current(waiting, Local, Utc.AddHours(23)));
            Assert.AreEqual(FirstDayStep.Done, FirstDay.Current(waiting, Local, Utc.AddHours(25)), "24 saatten sonra biter");

            var old = GameState.NewFor("c", Utc);
            old.PetId = "pet_02"; old.PetName = "Eski";
            FirstDay.Start(old, Utc);
            Assert.AreEqual(FirstDayStep.Done, FirstDay.Current(old, Local, Utc), "eski oyuncu akışı görmez");
        }
    }
}
