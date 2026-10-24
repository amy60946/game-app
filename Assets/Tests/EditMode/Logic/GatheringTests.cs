using System;
using System.Linq;
using NUnit.Framework;
using Pofi.Logic.Island;
using Pofi.Logic.Progression;

namespace Pofi.Tests.Logic
{
    public class GatheringTests
    {
        private static IslandTerrain _t;
        private static IslandTerrain T
        {
            get
            {
                if (_t != null) return _t;
                var data = TestData.Load();
                var map = new IslandMap(TestData.ReadText("regions.json"), new LevelTable(data.Levels));
                return _t = new IslandTerrain(map.Regions, map.Terrain);
            }
        }

        private static readonly DateTime Now = new DateTime(2026, 10, 15, 12, 0, 0, DateTimeKind.Utc);

        [Test]
        public void Noktalar_belirlenimci_yurunebilir_ve_turlerine_uygun_yerde()
        {
            var a = Gathering.Place(T); var b = Gathering.Place(T);
            Assert.AreEqual(a.Count, b.Count);
            for (var i = 0; i < a.Count; i++) { Assert.AreEqual(a[i].X, b[i].X); Assert.AreEqual(a[i].Kind, b[i].Kind); }
            Assert.AreEqual(5, a.Count(n => n.Kind == GatherKind.Log));
            Assert.AreEqual(6, a.Count(n => n.Kind == GatherKind.Bush));
            Assert.GreaterOrEqual(a.Count(n => n.Kind == GatherKind.Rock), 8, "kulübeye yetecek kadar taş (kullanıcı, 24 Ekim 2026)");
            Assert.GreaterOrEqual(a.Count(n => n.Kind == GatherKind.Coconut), 3, "yerde hindistan cevizi");
            Assert.GreaterOrEqual(a.Count(n => n.Kind == GatherKind.Rock && IslandTerrain.Dist(n.X, n.Z, T.PlazaX, T.PlazaZ) < 22f), 3, "taşların bir kısmı meydana yakın");
            foreach (var n in a)
            {
                Assert.IsTrue(T.Walkable(n.X, n.Z), n.Kind + " yürünebilir yerde");
                Assert.IsNull(T.BuildingAt(n.X, n.Z));
                var s = T.SurfaceAt(n.X, n.Z);
                if (n.Kind == GatherKind.Rock) Assert.IsTrue(s == Surface.Sand || s == Surface.Rock || s == Surface.Grass);
                else if (n.Kind == GatherKind.Coconut) { Assert.AreEqual(Surface.Sand, s); Assert.Less(T.Height(n.X, n.Z), Gathering.BeachTop, "ceviz kumsalda"); }
                else Assert.AreEqual(Surface.Grass, s);
                Assert.Greater(T.FindPath(T.PlazaX, T.PlazaZ, n.X, n.Z).Count, 0, "meydandan ulaşılır");
            }
            foreach (var n in a) foreach (var m in a) if (n != m) Assert.Greater(IslandTerrain.Dist(n.X, n.Z, m.X, m.Z), 3f);
            // ilk kütükler meydana yakın (çocuk hemen bulsun)
            Assert.Less(a.Where(n => n.Kind == GatherKind.Log).Min(n => IslandTerrain.Dist(n.X, n.Z, T.PlazaX, T.PlazaZ)), 22f);
        }

        [Test]
        public void Kulube_yeri_cimende_ulasilir_ve_binalardan_uzak()
        {
            var (x, z) = Gathering.HutSite(T);
            Assert.AreEqual(Surface.Grass, T.SurfaceAt(x, z));
            Assert.IsTrue(T.Walkable(x, z));
            Assert.Greater(T.FindPath(T.PlazaX, T.PlazaZ, x, z).Count, 0);
            foreach (var r in T.Regions) Assert.Greater(IslandTerrain.Dist(x, z, r.X, r.Z), r.Size * 0.8f);
        }

        [Test]
        public void Toplama_malzeme_ekler_ve_nokta_bekler_sonra_yeniden_cikar()
        {
            var s = new GatherState();
            var log = new GatherNode { Index = 0, Kind = GatherKind.Log };
            Assert.AreEqual(2, Gathering.Harvest(s, log, Now));
            Assert.AreEqual(2, Gathering.Count(s, Gathering.Wood));
            Assert.AreEqual(0, Gathering.Harvest(s, log, Now.AddMinutes(1)), "bekleme sürüyor");
            Assert.IsFalse(Gathering.Available(s, 0, Now.AddMinutes(7)));
            Assert.IsTrue(Gathering.Available(s, 0, Now + Gathering.Respawn));
            Assert.AreEqual(2, Gathering.Harvest(s, log, Now + Gathering.Respawn));
            Assert.AreEqual(4, Gathering.Count(s, Gathering.Wood));
            Assert.AreEqual(4, s.Total);
        }

        [Test]
        public void Ceviz_malzeme_sayilmaz_cagirana_doner()
        {
            var s = new GatherState();
            var nut = new GatherNode { Index = 30, Kind = GatherKind.Coconut };
            Assert.AreEqual(1, Gathering.Harvest(s, nut, Now));
            Assert.AreEqual(0, Gathering.Count(s, Gathering.Coconut), "ceviz çantadaki malzemeye değil envantere (yiyecek) girer");
            Assert.AreEqual(0, s.Total);
            Assert.IsFalse(Gathering.Available(s, 30, Now.AddMinutes(1)));
            Assert.IsFalse(Gathering.IsMaterial(Gathering.Coconut));
        }

        [Test]
        public void Eksik_malzeme_yalniz_tarifte_eksik_olan()
        {
            var s = new GatherState();
            s.Materials[Gathering.Wood] = 6;
            Assert.IsFalse(Gathering.Lacking(s, Gathering.Wood));
            Assert.IsTrue(Gathering.Lacking(s, Gathering.Stone));
            s.HutBuilt = true;
            Assert.IsFalse(Gathering.Lacking(s, Gathering.Stone));
        }

        [Test]
        public void Kulube_tarif_tamamlaninca_insa_edilir_bir_kez()
        {
            var s = new GatherState();
            Assert.IsFalse(Gathering.CanBuild(s));
            s.Materials[Gathering.Wood] = 7; s.Materials[Gathering.Branch] = 4; s.Materials[Gathering.Stone] = 2;
            Assert.IsFalse(Gathering.Build(s), "taş eksik");
            s.Materials[Gathering.Stone] = 3;
            Assert.IsTrue(Gathering.Build(s));
            Assert.IsTrue(s.HutBuilt);
            Assert.AreEqual(1, Gathering.Count(s, Gathering.Wood));
            Assert.AreEqual(0, Gathering.Count(s, Gathering.Stone));
            Assert.IsFalse(Gathering.Build(s), "ikinci kez yok");
        }

        [Test]
        public void Kurallar_her_tur_icin_tanimli()
        {
            foreach (GatherKind k in Enum.GetValues(typeof(GatherKind)))
            {
                var r = Gathering.Rule(k);
                Assert.Greater(r.Hits, 0); Assert.Greater(r.Yield, 0);
                Assert.IsTrue(new[] { "axe", "hand", "pickaxe" }.Contains(r.Tool));
            }
        }
    }
}
