using System;
using System.Linq;
using NUnit.Framework;
using Pofi.Logic.App;
using Pofi.Logic.Island;
using Pofi.Logic.State;

namespace Pofi.Tests.Logic
{
    /// <summary>Sv1–3 rehberli görev zinciri (App/Guide).</summary>
    public class GuideTests
    {
        private static readonly DateTime Local = new DateTime(2026, 10, 19, 12, 0, 0);

        private static GameState NewPlayer() => new GameState { PetId = "pet_01", PetName = "Pofi" };

        private static System.Collections.Generic.List<GuideStep> Do(GameState s, string counter, int level = 1)
        {
            s.Counters.Add(counter, 1, Local);   // RecordActivity sırası: önce sayaç, sonra rehber
            return Guide.OnActivity(s, level, counter);
        }

        [Test]
        public void On_iki_adim_ve_sayaclar_essiz()
        {
            Assert.AreEqual(12, Guide.Steps.Count);
            Assert.AreEqual(Guide.Steps.Count, Guide.Steps.Select(x => x.Id).Distinct().Count());
            Assert.AreEqual(Guide.Steps.Count, Guide.Steps.Select(x => x.Counter).Distinct().Count());
            Assert.That(Guide.Steps.All(x => x.Xp > 0));
        }

        [Test]
        public void Ilk_adim_besle_ve_sirayla_ilerler()
        {
            var s = NewPlayer();
            Assert.AreEqual("feed", Guide.Current(s, 1).Id);
            Assert.IsEmpty(Do(s, "pet_washed"), "sırası gelmeyen adım ödül vermez");
            var r = Do(s, "pet_fed");
            Assert.AreEqual("feed", r.Single().Id, "yıkama önceden yapıldı: ödülsüz geçilir");
            Assert.AreEqual("home", Guide.Current(s, 1).Id);
            Assert.AreEqual(2, Guide.DoneCount(s));
        }

        [Test]
        public void Tas_adimi_tas_yokken_atlanir_tas_gelince_doner()
        {
            var s = NewPlayer();
            foreach (var c in new[] { "pet_fed", "pet_washed", "home_entered", "home_tidied", "item_equipped", "board_opened", "gathered", "hut_built", "coconuts_caught", "item_bought" })
                Do(s, c);
            Assert.IsNull(Guide.Current(s, 1), "taş yok, kart adımı Sv3: gösterilecek adım yok");
            Assert.AreEqual("cards", Guide.Current(s, 3).Id, "Sv3'te kart adımı taşı beklemez");
            SunStoneBook.ApplyServerTotal(s.SunStones, 1);
            Assert.AreEqual("stone", Guide.Current(s, 1).Id);
            Assert.AreEqual("stone", Do(s, "stone_placed").Single().Id);
        }

        [Test]
        public void Hepsi_bitince_ya_da_Sv3_gecilince_kapanir()
        {
            var s = NewPlayer();
            SunStoneBook.ApplyServerTotal(s.SunStones, 1);
            foreach (var st in Guide.Steps) Do(s, st.Counter, 3);
            Assert.IsFalse(Guide.Active(s, 3));
            Assert.IsNull(Guide.Current(s, 3));

            var old = NewPlayer();
            Guide.Start(old, 4);
            Assert.IsFalse(Guide.Active(old, 3), "Sv3'ü geçmiş oyuncu rehberi görmez");
        }

        [Test]
        public void Onceden_yapilmis_kulube_odulsuz_gecilir()
        {
            var s = NewPlayer();
            s.Gather.HutBuilt = true;
            foreach (var c in new[] { "pet_fed", "pet_washed", "home_entered", "home_tidied", "item_equipped", "board_opened" }) Do(s, c);
            var r = Do(s, "gathered");
            Assert.AreEqual("gather", r.Single().Id);
            Assert.AreEqual("coconut", Guide.Current(s, 1).Id, "kulübe zaten yapılmış: adım geçildi");
        }
    }
}
