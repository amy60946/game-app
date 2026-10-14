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
                var data = TestData.Load();
                var map = new IslandMap(TestData.ReadText("regions.json"), new LevelTable(data.Levels));
                return _t = new IslandTerrain(map.Regions, map.Terrain);
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
                Assert.Greater(T.Height(p.X, p.Z), 0f, p.Asset + " karada");
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
            // meydandan çıkan patika sayısı az (en kısa bağlantı ağacı); yıldız biçimi 8+ olurdu
            var fromPlaza = T.Paths.Count(p => IslandTerrain.Dist(p.ax, p.az, T.PlazaX, T.PlazaZ) < 0.6f);
            Assert.LessOrEqual(fromPlaza, 4);
        }

        [Test]
        public void Patikalar_var_ve_yuzey_turleri_cesitli()
        {
            Assert.Greater(T.Paths.Count, 10);
            var kinds = new System.Collections.Generic.HashSet<Surface>();
            for (var x = T.MinX; x < T.MaxX; x += 1.5f)
            for (var z = T.MinZ; z < T.MaxZ; z += 1.5f) kinds.Add(T.SurfaceAt(x, z));
            foreach (var k in new[] { Surface.Water, Surface.Sand, Surface.Grass, Surface.Path, Surface.Snow }) Assert.IsTrue(kinds.Contains(k), k.ToString());
        }
    }
}
