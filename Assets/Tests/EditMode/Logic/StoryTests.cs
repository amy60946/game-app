using System;
using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using Pofi.Logic.Island;
using Pofi.Logic.Meta;
using Pofi.Logic.Profile;
using Pofi.Logic.State;
using Pofi.Logic.Story;

namespace Pofi.Tests.Logic
{
    public class StoryTests
    {
        private static readonly DateTime Local = new DateTime(2026, 10, 23, 10, 0, 0);
        private static StoryBook Book => TestData.Load().Story;
        private static readonly HashSet<string> None = new HashSet<string>();
        private static bool NoEvent(string e) => false;

        [Test]
        public void Hikaye_verisi_tutarli()
        {
            var spots = new HashSet<string>(TestData.Load().SunBook.Spots.Select(s => s.Id));
            var errors = Book.Validate(spots);
            Assert.IsEmpty(errors, string.Join("\n", errors));
            Assert.AreEqual(9, Book.Chapters.Count);
            Assert.AreEqual(9, Book.Pages.Count);
            Assert.IsTrue(Book.Scenes.Any(s => s.Trigger == StoryDirector.Intro), "giriş filmi var");
            // dört taşlı kapanış: her onarım noktasının bir sahnesi
            foreach (var id in spots) Assert.IsTrue(Book.Scenes.Any(s => s.Trigger == StoryDirector.Spot && s.Arg == id), id);
            Assert.IsTrue(Book.Requests.All(r => string.IsNullOrEmpty(r.RewardItem) || TestData.Load().Item(r.RewardItem) != null), "ödül eşyası var");
        }

        [Test]
        public void Yeni_oyuncu_filmden_baslar_sonra_seviye_sahneleri()
        {
            var st = new StoryState();
            StoryDirector.Init(st, Book, existingPlayer: false, level: 1, None, NoEvent);
            var first = StoryDirector.Next(Book, st, 1, None, NoEvent);
            Assert.AreEqual("intro", first.Id);
            StoryDirector.MarkSeen(st, first);
            Assert.IsTrue(st.IntroSeen);
            Assert.AreEqual("ch1_open", StoryDirector.Next(Book, st, 1, None, NoEvent).Id);
            StoryDirector.MarkSeen(st, Book.Scene("ch1_open"));
            Assert.IsNull(StoryDirector.Next(Book, st, 1, None, NoEvent), "pano açılmadan sıradaki yok");
            Assert.AreEqual("ch1_board", StoryDirector.Next(Book, st, 1, None, e => e == "board_opened").Id);
        }

        [Test]
        public void Tas_yerlestirince_onarim_sahnesi_gelir()
        {
            var st = new StoryState { Initialized = true, IntroSeen = true };
            foreach (var s in Book.Scenes.Where(x => x.Chapter <= 1 && x.Trigger != StoryDirector.Spot)) st.Seen.Add(s.Id);
            Assert.IsNull(StoryDirector.Next(Book, st, 1, None, e => e == "board_opened"));
            var spots = new HashSet<string> { "spot_fog_cove" };
            Assert.AreEqual("ch1_close", StoryDirector.Next(Book, st, 1, spots, NoEvent).Id);
        }

        [Test]
        public void Eski_oyuncuya_gecmis_sahneler_yigilmaz()
        {
            var st = new StoryState();
            StoryDirector.Init(st, Book, existingPlayer: true, level: 7, new HashSet<string> { "spot_fog_cove" }, e => e == "hut_built");
            Assert.IsTrue(st.IntroSeen, "eski oyuncu filmi görmez");
            var next = StoryDirector.Next(Book, st, 7, new HashSet<string> { "spot_fog_cove" }, e => e == "hut_built");
            Assert.IsNotNull(next, "en son olan bir sahne oynar");
            StoryDirector.MarkSeen(st, next);
            Assert.IsNull(StoryDirector.Next(Book, st, 7, new HashSet<string> { "spot_fog_cove" }, e => e == "hut_built"), "geri kalanı izlenmiş sayılır");
            Assert.IsTrue(StoryDirector.Replayable(Book, st).Count >= 5, "Defter'de durur");
            StoryDirector.Init(st, Book, true, 15, None, NoEvent);
            Assert.IsNull(StoryDirector.Next(Book, st, 7, new HashSet<string> { "spot_fog_cove" }, e => e == "hut_built"), "Init bir kez");
        }

        [Test]
        public void Yas_grubuna_gore_metin()
        {
            var l = new StoryLine { Text = "Uzun cümle", Short = "Kısa", Teen = "Esprili" };
            Assert.AreEqual("Kısa", StoryDirector.Text(l, AgeBand.A));
            Assert.AreEqual("Kısa", StoryDirector.Text(l, AgeBand.K));
            Assert.AreEqual("Uzun cümle", StoryDirector.Text(l, AgeBand.B));
            Assert.AreEqual("Esprili", StoryDirector.Text(l, AgeBand.C));
            Assert.AreEqual("Uzun cümle", StoryDirector.Text(new StoryLine { Text = "Uzun cümle" }, AgeBand.C));
            Assert.Greater(StoryDirector.AutoAdvance(AgeBand.K), 0f);
            Assert.AreEqual(0f, StoryDirector.AutoAdvance(AgeBand.B));
            Assert.AreEqual(4, Book.ChapterFor(6));
            Assert.AreEqual(9, Book.ChapterFor(15));
        }

        [Test]
        public void Mevsimler_gercek_takvimden()
        {
            Assert.AreEqual(Season.Autumn, Seasons.For(Local));
            Assert.AreEqual(Season.Winter, Seasons.For(new DateTime(2027, 1, 10)));
            Assert.AreEqual(Season.Spring, Seasons.For(new DateTime(2027, 4, 1)));
            Assert.AreEqual(Season.Summer, Seasons.For(new DateTime(2027, 7, 1)));
            Assert.IsTrue(Seasons.HolidayLights(new DateTime(2026, 12, 25)));
            Assert.IsTrue(Seasons.HolidayLights(new DateTime(2027, 1, 5)));
            Assert.IsFalse(Seasons.HolidayLights(new DateTime(2027, 1, 6)));
            Assert.IsFalse(Seasons.HolidayLights(new DateTime(2026, 12, 19)));
        }

        [Test]
        public void Gunluk_gunun_anilarini_yazar_puan_yok()
        {
            var st = new StoryState(); var c = new Counters();
            Assert.IsNull(Diary.Record(st, c, Local), "boş günde sayfa yok");
            c.Add("pet_fed", 2, Local); c.Add("gathered", 4, Local); c.Add("tasks_approved", 1, Local); c.Add("item_bought", 1, Local);
            var e = Diary.Record(st, c, Local);
            Assert.AreEqual(Diary.MaxLines, e.Lines.Count);
            Assert.AreEqual("diary.task", e.Lines[0].Key, "gerçek görev en üstte");
            Assert.AreEqual("4", e.Lines[1].Args[0]);
            Diary.Record(st, c, Local);
            Assert.AreEqual(1, st.Diary.Count, "aynı gün güncellenir");
            for (var d = 1; d <= 70; d++) { c.Add("pet_fed", 1, Local.AddDays(d)); Diary.Record(st, c, Local.AddDays(d)); }
            Assert.AreEqual(Diary.Keep, st.Diary.Count);
        }

        [Test]
        public void Adali_istekleri_gunde_bir_en_cok_iki_coin_yok()
        {
            var defs = Book.Requests; var st = new StoryState();
            ResidentRequests.Refresh(st, defs, 100, 3, "c1");
            ResidentRequests.Refresh(st, defs, 100, 3, "c1");
            Assert.AreEqual(1, st.Requests.Count, "günde bir");
            ResidentRequests.Refresh(st, defs, 101, 3, "c1");
            ResidentRequests.Refresh(st, defs, 102, 3, "c1");
            Assert.AreEqual(ResidentRequests.MaxOpen, st.Requests.Count, "en çok iki, süre dolmaz");
            Assert.IsTrue(st.Requests.All(o => defs.First(d => d.Id == o.Id).MinLevel <= 3));
            var have = new Dictionary<string, int> { ["stone"] = 9, ["branch"] = 9, ["wood"] = 9, ["food_coconut"] = 9 };
            var id = st.Requests[0].Id;
            var done = ResidentRequests.Fulfill(st, defs, id, k => have.TryGetValue(k, out var n) ? n : 0, (k, n) => have[k] -= n);
            Assert.IsNotNull(done);
            Assert.AreEqual(9 - done.Count, have[done.Need]);
            Assert.AreEqual(1, st.Friendship[done.Who]);
            Assert.AreEqual(1, st.Requests.Count);
            Assert.IsNull(ResidentRequests.Fulfill(st, defs, "yok", _ => 99, (k, n) => { }));
            Assert.IsTrue(defs.All(d => d.Need != "coin" && d.RewardItem != "coin"), "coin yalnız gerçek görevden");
        }

        [Test]
        public void Adali_istegi_malzemeyle_karsilanir_odul_esya()
        {
            var data = TestData.Load();
            var s = new GameState { ChildId = "c1" };
            s.Story.Requests.Add(new OpenRequest { Id = "req_kiskac_stone", Day = 1 });
            Assert.IsNull(Residents.Fulfill(s, data, "req_kiskac_stone"), "taş yokken olmaz");
            s.Gather.Materials[Gathering.Stone] = 5;
            var d = Residents.Fulfill(s, data, "req_kiskac_stone");
            Assert.IsNotNull(d);
            Assert.AreEqual(2, Gathering.Count(s.Gather, Gathering.Stone), "3 taş verildi");
            Assert.IsTrue(s.Inventory.Owns("decor_sandcastle"), "ödül eşyası");
            Assert.AreEqual(1, s.Story.Friendship["kiskac"]);
            Assert.IsTrue(Residents.Home.ContainsKey(d.Who));
            foreach (var r in Book.Requests) Assert.IsTrue(Residents.Home.ContainsKey(r.Who), r.Id + " adalının yeri var");
        }

        [Test]
        public void Gunun_surprizleri_belirlenimci_ve_bir_kez()
        {
            var defs = Book.Surprises;
            var a = DailySurprises.ForDay(defs, 200, "c1", 5).Select(s => s.Id).ToList();
            var b = DailySurprises.ForDay(defs, 200, "c1", 5).Select(s => s.Id).ToList();
            CollectionAssert.AreEqual(a, b);
            Assert.AreEqual(3, a.Count);
            Assert.IsTrue(DailySurprises.ForDay(defs, 200, "c1", 1).All(s => s.MinLevel <= 1));
            var st = new StoryState();
            Assert.IsTrue(DailySurprises.Take(st, 200, a[0]));
            Assert.IsFalse(DailySurprises.Take(st, 200, a[0]), "aynı gün ikinci kez ödül yok");
            Assert.IsTrue(DailySurprises.Take(st, 201, a[0]), "ertesi gün yeniden");
        }

        [Test]
        public void Surprizler_kiyida_ya_da_iceride_belirlenimci_yerde()
        {
            var terrain = TestData.Terrain();
            var defs = Book.Surprises;
            var a = SurprisePlaces.Place(defs, 300, "c1", terrain);
            var b = SurprisePlaces.Place(defs, 300, "c1", terrain);
            Assert.GreaterOrEqual(a.Count, defs.Count - 1, "neredeyse hepsine yer bulunur");
            CollectionAssert.AreEqual(a.Select(s => s.X), b.Select(s => s.X));
            foreach (var s in a)
            {
                Assert.IsTrue(terrain.Walkable(s.X, s.Z), s.Def.Id);
                var h = terrain.Height(s.X, s.Z);
                if (SurprisePlaces.Shore(s.Def.Kind)) Assert.LessOrEqual(h, SurprisePlaces.ShoreTop, s.Def.Id + " kıyıda");
                else Assert.Greater(h, SurprisePlaces.ShoreTop, s.Def.Id + " içeride");
            }
        }

        [Test]
        public void Bekcinin_sayfalari_bolum_acilinca_yerinde_bulunur()
        {
            var st = new StoryState();
            Assert.IsNull(LorePages.OnRegion(Book, st, 4, "region_pier"), "5. bölümden önce iskele sayfası yok");
            Assert.AreEqual("page_5", LorePages.OnRegion(Book, st, 5, "region_pier").Id);
            Assert.IsNull(LorePages.OnRegion(Book, st, 5, "region_pier"), "bir kez");
            Assert.AreEqual("page_2", LorePages.OnSparkle(Book, st, 5, 100).Id);
            Assert.IsNull(LorePages.OnSparkle(Book, st, 5, 100), "parıltıdan günde bir");
            Assert.AreEqual("page_4", LorePages.OnSparkle(Book, st, 5, 101).Id);
            Assert.AreEqual("page_1", LorePages.OnPlace(Book, st, 9, LorePages.Tosbi).Id);
            CollectionAssert.AreEqual(new[] { 1, 2, 4, 5 }, LorePages.Found(Book, st).Select(p => p.Number));
            Assert.AreEqual("page_9", LorePages.OnPlace(Book, st, 9, LorePages.Lighthouse).Id);
        }

        [Test]
        public void Okti_tepkisi_art_arda_ayni_olmaz()
        {
            var st = new StoryState(); string last = null;
            for (var i = 0; i < 12; i++) { var r = OktiReactions.Next(st); Assert.AreNotEqual(last, r); last = r; }
            Assert.AreEqual(OktiReactions.All.Length, OktiReactions.All.Distinct().Count());
        }

        [Test]
        public void Yukleme_gorseli_ulasilan_bolumden_ve_tekrar_etmez()
        {
            var st = new StoryState(); string last = null;
            for (var i = 0; i < 10; i++)
            {
                var a = LoadingArts.Pick(Book, st, 2, i * 7919);
                Assert.LessOrEqual(a.Chapter, 2, "sürpriz bozulmaz");
                Assert.AreNotEqual(last, a.Id);
                last = a.Id;
            }
            CollectionAssert.Contains(new[] { "load_beach", "load_okti", "load_lighthouse" }, LoadingArts.Pick(Book, new StoryState(), 0, 5).Id, "giriş bölümü: Y1–Y3");
            var ready = new System.Collections.Generic.HashSet<string> { "load_okti" };
            Assert.AreEqual("load_okti", LoadingArts.Pick(Book, new StoryState(), 9, 3, ready.Contains).Id, "görseli olmayan seçilmez");
        }

        [Test]
        public void Santiye_malzeme_geldikce_yukselir()
        {
            var g = new GatherState();
            Assert.AreEqual(0, Gathering.HutStage(g));
            g.Materials[Gathering.Wood] = 3;
            Assert.AreEqual(1, Gathering.HutStage(g));
            g.Materials[Gathering.Wood] = 6; g.Materials[Gathering.Branch] = 4;
            Assert.AreEqual(2, Gathering.HutStage(g));
            g.Materials[Gathering.Stone] = 9;
            Assert.AreEqual(3, Gathering.HutStage(g), "fazlası sayılmaz, hazır");
            Assert.AreEqual(1f, Gathering.HutProgress(g));
            Assert.IsTrue(Gathering.Build(g));
            Assert.AreEqual(4, Gathering.HutStage(g));
        }

        [Test]
        public void Hikaye_kaydi_saklanir()
        {
            var s = new GameState { ChildId = "c" };
            s.Story.Seen.Add("intro"); s.Story.IntroSeen = true; s.Story.Pages.Add("page_1");
            var back = SaveCodec.Deserialize(SaveCodec.Serialize(s, DateTime.UtcNow));
            Assert.IsTrue(back.Story.IntroSeen);
            Assert.IsTrue(back.Story.Seen.Contains("intro"));
            Assert.IsTrue(back.Story.Pages.Contains("page_1"));
            Assert.IsTrue(back.Settings.StoryOn, "hikâye varsayılan açık");
        }
    }
}
