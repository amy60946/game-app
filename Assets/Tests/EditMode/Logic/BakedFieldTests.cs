using System;
using System.IO;
using NUnit.Framework;
using Pofi.Logic.Island;

namespace Pofi.Tests.Logic
{
    /// <summary>island_v6.bytes biçimi: sürüm 1 (5 katman) ve sürüm 2 (+ iki çiçek katmanı, 22 Ekim 2026).</summary>
    public class BakedFieldTests
    {
        private static byte[] Make(byte version, int layers, byte fill)
        {
            const int nx = 3, nz = 3; var n = nx * nz;
            var ms = new MemoryStream(); var w = new BinaryWriter(ms);
            w.Write(new[] { (byte)'P', (byte)'V', (byte)'6', version });
            w.Write(nx); w.Write(nz); w.Write(0f); w.Write(0f); w.Write(1f);
            for (var i = 0; i < n; i++) w.Write((short)150);
            for (var k = 0; k < layers; k++) for (var i = 0; i < n; i++) w.Write(k >= 5 ? fill : (byte)0);
            return ms.ToArray();
        }

        [Test]
        public void Version1_HasNoFlowers()
        {
            var f = BakedField.Parse(Make(1, 5, 0));
            Assert.AreEqual(1.5f, f.Height(1f, 1f), 1e-4f);
            Assert.AreEqual(0f, f.Get(BakedField.Layer.Bluebell, 1f, 1f));
        }

        [Test]
        public void Version2_ReadsFlowerLayers()
        {
            var f = BakedField.Parse(Make(2, 7, 255));
            Assert.AreEqual(1f, f.Get(BakedField.Layer.Bluebell, 1f, 1f), 1e-4f);
            Assert.AreEqual(1f, f.Get(BakedField.Layer.Orange, 0.5f, 0.5f), 1e-4f);
            Assert.AreEqual(0f, f.Get(BakedField.Layer.Lake, 1f, 1f));
        }

        [Test]
        public void Version2_TruncatedFails()
        {
            var d = Make(2, 5, 0);   // sürüm 2 ama çiçek katmanları yok
            Assert.Throws<FormatException>(() => BakedField.Parse(d));
        }

        [Test]
        public void GameIsland_HasFlowerFields()
        {
            var t = TestData.Terrain();
            var any = false;
            for (var x = -60f; x < 60f && !any; x += 1f)
            for (var z = -40f; z < 40f && !any; z += 1f)
                any = t.Bluebell(x, z) > 0.3f;
            Assert.IsTrue(any, "pişmiş adada çan çiçeği tarlası olmalı");
        }
    }
}
