using System.Linq;
using NUnit.Framework;
using Pofi.Logic.Island;
using Pofi.Logic.Progression;

namespace Pofi.Tests.Logic
{
    public class IslandTerrainTests
    {
        private static IslandTerrain _t;
        private static IslandTerrain T
        {
            get
            {
                if (_t != null) return _t;
                return _t = TestData.Terrain();   // oyundaki gibi: pişmiş v6 adası
            }
        }

        [Test]
        public void Ada_kara_ve_deniz_dogru()
        {
            Assert.Greater(T.Height(T.PlazaX, T.PlazaZ), 0.3f, "meydan karada");
            Assert.Less(T.Height(T.MaxX - 1f, T.MinZ + 1f), 0f, "köşe denizde");
            Assert.AreEqual(Surface.Water, T.SurfaceAt(T.MinX + 1f, T.MinZ + 1f));
        }

        [Test]
        public void Bolgeler_karada_kapilar_yurunebilir_ve_meydandan_ulasilir()
        {
            foreach (var r in T.Regions)
            {
                if (!r.Water) Assert.Greater(T.PadHeight(r), 0.2f, r.Id + " karada");
                var (dx, dz) = T.Door(r);
                Assert.IsTrue(T.Walkable(dx, dz), r.Id + " kapısı yürünebilir");
                Assert.IsNull(T.BuildingAt(dx, dz), r.Id + " kapısı bina içinde değil");
                var path = T.FindPath(T.PlazaX, T.PlazaZ, dx, dz);
                Assert.Greater(path.Count, 0, r.Id + " meydandan ulaşılır");
                var last = path[path.Count - 1];
                Assert.Less(IslandTerrain.Dist(last.x, last.z, dx, dz), 0.6f, r.Id + " yol kapıda biter");
            }
        }

        [Test]
        public void Bina_ici_yurunemez_ve_yol_binalardan_gecmez()
        {
            var home = T.Regions.First(r => r.Id == "region_home");
            Assert.IsFalse(T.Walkable(home.X, home.Z));
            var a = T.Door(T.Regions.First(r => r.Id == "region_cave"));
            var b = T.Door(T.Regions.First(r => r.Id == "region_lighthouse"));
            var path = T.FindPath(a.x, a.z, b.x, b.z);
            Assert.Greater(path.Count, 0);
            var (px, pz) = a;
            foreach (var p in path) { Assert.IsTrue(T.LineWalkable(px, pz, p.x, p.z)); (px, pz) = p; }
        }

        [Test]
        public void Suya_dokununca_en_yakin_karaya_gider()
        {
            var w = T.NearestWalkable(0f, T.MinZ + 6f, 20f);
            Assert.IsFalse(float.IsNaN(w.x));
            Assert.IsTrue(T.Walkable(w.x, w.z));
        }

        [Test]
        public void Susler_belirlenimci_karada_ve_yapilardan_uzak()
        {
            var a = T.Props(); var b = T.Props();
            Assert.Greater(a.Count, 30);
            Assert.AreEqual(a.Count, b.Count);
            for (var i = 0; i < a.Count; i++) { Assert.AreEqual(a[i].Asset, b[i].Asset); Assert.AreEqual(a[i].X, b[i].X); }
            foreach (var p in a)
            {
                Assert.Greater(T.Height(p.X, p.Z), -1.6f, p.Asset + " karada ya da kıyı sığlığında");
                if (p.Asset == "p_pool") continue;   // koy havuzu Yüzme Koyu'nun kendisi
                foreach (var r in T.Regions) Assert.Greater(IslandTerrain.Dist(p.X, p.Z, r.X, r.Z), r.Size * 0.6f, p.Asset + " / " + r.Id);
            }
        }

        [Test]
        public void Suslerin_icinden_gecilmez()
        {
            foreach (var p in T.Props())
                if (IslandTerrain.ObstacleRadius(p) > 0f) Assert.IsFalse(T.Walkable(p.X, p.Z), p.Asset + " engel olmalı");
        }

        [Test]
        public void Patikalar_dallanir_tek_merkezden_yildiz_degil()
        {
            // meydandan çıkan patika sayısı az (köy yolu dallanır); yıldız biçimi 8+ olurdu
            var fromPlaza = T.Paths.Count(p => IslandTerrain.Dist(p.ax, p.az, T.PlazaX, T.PlazaZ) < 0.6f);
            Assert.LessOrEqual(fromPlaza, 6);
        }

        [Test]
        public void Patikalar_var_ve_yuzey_turleri_cesitli()
        {
            Assert.Greater(T.Paths.Count, 10);
            var kinds = new System.Collections.Generic.HashSet<Surface>();
            for (var x = T.MinX; x < T.MaxX; x += 1.5f)
            for (var z = T.MinZ; z < T.MaxZ; z += 1.5f) kinds.Add(T.SurfaceAt(x, z));
            foreach (var k in new[] { Surface.Water, Surface.Sand, Surface.Grass, Surface.Path, Surface.Snow, Surface.Rock }) Assert.IsTrue(kinds.Contains(k), k.ToString());
        }

        [Test]
        public void Pismis_adadaki_her_susun_modeli_ve_gercek_boyu_var()
        {
            var sizes = EnvSizes.Parse(TestData.ReadText("env_v6_sizes.json"));
            var env = System.IO.Path.Combine(System.IO.Directory.GetParent(TestData.PathOfData()).FullName, "Env");
            foreach (var a in T.Props().Select(p => p.Asset).Distinct())
            {
                Assert.IsTrue(System.IO.File.Exists(System.IO.Path.Combine(env, a, a + ".fbx")), a + " modeli Resources/Env'de");
                if (T.Props().First(p => p.Asset == a).Scaled) Assert.Greater(sizes.TryGetValue(a, out var h) ? h : 0f, 0f, a + " gerçek boyu");
            }
        }

        [Test]
        public void Pismis_ada_taslakla_ayni_olcekte()
        {
            Assert.IsNotNull(T.Baked, "oyun v6 pişmiş adayı kullanır");
            Assert.AreEqual(-100f, T.MinX, 0.01f); Assert.AreEqual(100f, T.MaxX, 0.01f);
            Assert.Greater(T.Height(9f, 25f), 25f, "ortadaki kaya tepe yüksek");
            Assert.Greater(T.Height(-44f, 54f), 30f, "karlı zirve");
            Assert.AreEqual(Surface.Water, T.SurfaceAt(-28f, 6f), "göl");
            Assert.IsFalse(T.Walkable(-28f, 6f), "göle girilmez");
            Assert.AreEqual(Surface.Snow, T.SurfaceAt(-44f, 50f));
            Assert.Greater(T.Props().Count, 1000);
            // karlı patika baştan sona yürünebilir (kayak alanından zirveye)
            var ski = T.Door(T.Regions.First(r => r.Id == "region_ski_hill"));
            var p = T.FindPath(ski.x, ski.z, -41f, 56.5f);
            Assert.Greater(p.Count, 0, "karlı patika");
            // toplama noktaları ve kulübe yeri büyük adada da bulunur (meydana yakın)
            var nodes = Gathering.Place(T);
            Assert.AreEqual(26, nodes.Count, "5 kütük, 6 çalı, 10 taş, 5 ceviz");
            foreach (var n in nodes.Where(n => n.Kind == GatherKind.Coconut))
                Assert.Less(T.Height(n.X, n.Z), Gathering.BeachTop, "ceviz deniz kıyısında: " + n.X + "," + n.Z);
            var site = Gathering.HutSite(T);
            Assert.IsTrue(T.Walkable(site.x, site.z));
        }
    }
}
