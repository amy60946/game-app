using System;
using System.Collections.Generic;
using System.Linq;

namespace Pofi.Logic.Island
{
    /// <summary>Adada toplanabilir/işlenebilir nesne türü.</summary>
    public enum GatherKind { Log, Bush, Rock, Coconut, BigLog }

    /// <summary>Haritadaki bir toplama noktası (yeri adadan belirlenimci).</summary>
    public sealed class GatherNode
    {
        public int Index;
        public GatherKind Kind;
        public float X, Z, Yaw;
    }

    /// <summary>Tür kuralı: hangi alet, kaç vuruş, ne kadar malzeme.</summary>
    public sealed class GatherRule
    {
        public GatherKind Kind;
        public string Tool;        // "axe" | "hand" | "pickaxe" (eylem düğmesi ve nesne üstü simge)
        public int Hits;           // kaç vuruşta biter
        public string Material;    // "wood" | "branch" | "stone" | "coconut" (hindistan cevizi envantere yiyecek olarak girer)
        public int Yield;          // bitince kaç malzeme
    }

    /// <summary>Kayıtta tutulan toplama durumu.</summary>
    [Serializable]
    public sealed class GatherState
    {
        public Dictionary<string, int> Materials = new Dictionary<string, int>();
        public Dictionary<int, long> HarvestedUtcTicks = new Dictionary<int, long>();   // nokta → toplandığı an (yeniden çıkma için)
        public bool HutBuilt;
        public int Total;                                                                // toplam toplanan malzeme (rozet/görev için)
    }

    /// <summary>
    /// Küçük ada aksiyonları (kullanıcı isteği 15 Ekim 2026, madde 3-4): kütüğü baltayla birkaç kez kes → odun,
    /// çalıdan dal topla, taşı kazmayla kır → taş; malzemelerle meydanın yanında "Kulübe" inşa et.
    /// Noktalar adaya belirlenimci yerleşir; toplanan nokta <see cref="Respawn"/> sonra yeniden çıkar.
    /// Yeni aksiyonlar ileride aynı yapıya eklenecek (tür + kural + tarif).
    /// </summary>
    public static class Gathering
    {
        public const string Wood = "wood", Branch = "branch", Stone = "stone", Coconut = "coconut";
        /// <summary>Yerden toplanan hindistan cevizi envanterde bu yiyecek olur (Kıskaç'ın isteği, kullanıcı 24 Ekim 2026).</summary>
        public const string CoconutItem = "food_coconut";
        public static readonly TimeSpan Respawn = TimeSpan.FromMinutes(8);
        public const int HutXp = 40;
        /// <summary>Kumsalın en yüksek yeri (m): yerdeki cevizler bunun altında, deniz kıyısında çıkar.</summary>
        public const float BeachTop = 2.6f;

        public static readonly GatherRule[] Rules =
        {
            new GatherRule { Kind = GatherKind.Log, Tool = "axe", Hits = 3, Material = Wood, Yield = 2 },
            new GatherRule { Kind = GatherKind.Bush, Tool = "hand", Hits = 1, Material = Branch, Yield = 2 },
            new GatherRule { Kind = GatherKind.Rock, Tool = "pickaxe", Hits = 2, Material = Stone, Yield = 1 },
            new GatherRule { Kind = GatherKind.Coconut, Tool = "hand", Hits = 1, Material = Coconut, Yield = 1 },
            // büyük kütük (kullanıcı GB18): daha çok vuruş, daha çok odun
            new GatherRule { Kind = GatherKind.BigLog, Tool = "axe", Hits = 6, Material = Wood, Yield = 5 },
        };

        /// <summary>Çantadaki malzeme mi (odun/dal/taş)? Hindistan cevizi malzeme değil, yiyecektir.</summary>
        public static bool IsMaterial(string m) => m == Wood || m == Branch || m == Stone;

        /// <summary>Kulübe tarifi (sıra ekranda da bu).</summary>
        public static readonly (string material, int count)[] HutRecipe = { (Wood, 6), (Branch, 4), (Stone, 3) };

        public static GatherRule Rule(GatherKind k) => Rules.First(r => r.Kind == k);

        /// <summary>
        /// Toplama noktaları: kütük ve çalı çimende, taş çimende/kumsalda/kayalıkta (kullanıcı, 24 Ekim 2026: kulübeye yetecek taş
        /// bulunamıyordu → 10 taş), hindistan cevizi kıyı kumunda; rota (GB19): kulübe malzemesi kulübe yerinin, cevizler Kıskaç'ın dükkânının, bir büyük kütük kamp ateşinin yanında, kalanı adaya dağılır.
        /// Sıra (kütük, çalı, taş, ceviz) kayıttaki nokta numaralarını korur: yeni tür hep sona eklenir.
        /// </summary>
        /// <summary>Kulübe yerinin çevresinde toplama noktası konmayan yarıçap (sis örtüsü + şantiye, m).</summary>
        public const float SiteClear = 8.5f;

        public static List<GatherNode> Place(IslandTerrain t, int logs = 5, int bushes = 6, int rocks = 10, int coconuts = 5, int bigLogs = 3)
        {
            var list = new List<GatherNode>();
            var props = t.Props();
            var site = HutSite(t);
            var rng = new Random(t.Def.Seed * 977 + 3);
            bool Free(float x, float z)
            {
                if (!t.Walkable(x, z) || t.BuildingAt(x, z) != null || t.OnPlatform(x, z)) return false;   // tapınak terasına konmaz
                if (t.PathDistance(x, z) < IslandTerrain.PathHalfWidth + 0.9f) return false;
                if (t.Regions.Any(r => IslandTerrain.Dist(x, z, r.X, r.Z) < r.Size * 0.8f + 1.5f)) return false;
                if (props.Any(p => IslandTerrain.Dist(x, z, p.X, p.Z) < IslandTerrain.Footprint(p) + 1.2f)) return false;
                if (IslandTerrain.Dist(x, z, site.x, site.z) < SiteClear) return false;   // kulübe yerinin sisi ve şantiyesi boş kalsın
                return list.All(n => IslandTerrain.Dist(x, z, n.X, n.Z) > 3.2f);
            }
            // Rota (GB19, kullanıcı: "oradan oraya gitmesin"): her şey kullanıldığı yerin yakınında. Önce yakın halkaya istenen kadar
            // (halkanın içinden örneklenir, yoğun), kalan sayı tüm adaya dağılır.
            void Near(GatherKind kind, int count, float cx, float cz, float radius, Func<float, float, bool> where)
            {
                var placed = 0;
                for (var tries = 0; placed < count && tries < 4000; tries++)
                {
                    var a = rng.NextDouble() * Math.PI * 2; var r = radius * Math.Sqrt(rng.NextDouble());
                    var x = cx + (float)(Math.Cos(a) * r); var z = cz + (float)(Math.Sin(a) * r);
                    if (x < t.MinX || x > t.MaxX || z < t.MinZ || z > t.MaxZ || !where(x, z) || !Free(x, z)) continue;
                    list.Add(new GatherNode { Index = list.Count, Kind = kind, X = x, Z = z, Yaw = (float)rng.NextDouble() * 360f });
                    placed++;
                }
            }
            void Scatter(GatherKind kind, int count, Func<float, float, bool> where)
            {
                var placed = list.Count(n => n.Kind == kind);
                for (var tries = 0; placed < count && tries < 3000; tries++)
                {
                    var x = t.MinX + (float)rng.NextDouble() * (t.MaxX - t.MinX);
                    var z = t.MinZ + (float)rng.NextDouble() * (t.MaxZ - t.MinZ);
                    if (!where(x, z) || !Free(x, z)) continue;
                    list.Add(new GatherNode { Index = list.Count, Kind = kind, X = x, Z = z, Yaw = (float)rng.NextDouble() * 360f });
                    placed++;
                }
            }
            bool Grass(float x, float z) => t.SurfaceAt(x, z) == Surface.Grass;
            bool Stony(float x, float z) => t.SurfaceAt(x, z) == Surface.Sand || t.SurfaceAt(x, z) == Surface.Rock || t.SurfaceAt(x, z) == Surface.Grass;
            // kulübe tarifi (6 odun, 4 dal, 3 taş) kulübe yerinin 20 m içinde fazlasıyla çıkar
            Near(GatherKind.Log, Math.Min(3, logs), site.x, site.z, 20f, Grass);
            Scatter(GatherKind.Log, logs, Grass);
            Near(GatherKind.Bush, Math.Min(3, bushes), site.x, site.z, 20f, Grass);
            Scatter(GatherKind.Bush, bushes, Grass);
            Near(GatherKind.Rock, Math.Min(4, rocks), site.x, site.z, 22f, Stony);
            Scatter(GatherKind.Rock, rocks, Stony);
            // ceviz: yalnız deniz kıyısındaki alçak kum (kanyon/patika kumu değil, ≤ 2,6 m); üçü Kıskaç'ın dükkânına yakın kumsalda
            bool Beach(float x, float z) => t.SurfaceAt(x, z) == Surface.Sand && t.Height(x, z) < BeachTop;
            var shop = t.Regions.FirstOrDefault(r => r.Id == "region_shop");
            if (shop != null) Near(GatherKind.Coconut, Math.Min(3, coconuts), shop.X, shop.Z, 42f, Beach);
            Scatter(GatherKind.Coconut, coconuts, (x, z) => Beach(x, z) && t.PathDistance(x, z) < IslandTerrain.PathHalfWidth + 6f);
            Scatter(GatherKind.Coconut, coconuts, Beach);
            // büyük kütük: biri kamp ateşinin yanında (harlamak için odun orada), biri kulübe yerinde, kalanı adada
            bool Flat(float x, float z) => Grass(x, z) && t.Slope(x, z) < 0.35f;   // geniş, düzce çimen
            var spots = t.Baked?.Layout?.Spots;
            if (spots != null && spots.TryGetValue("camp", out var camp) && camp != null && camp.Length >= 2 && bigLogs > 0)
                Near(GatherKind.BigLog, 1, camp[0], camp[1], 16f, Flat);
            Near(GatherKind.BigLog, Math.Min(1, bigLogs - list.Count(n => n.Kind == GatherKind.BigLog)), site.x, site.z, 22f, Flat);
            Scatter(GatherKind.BigLog, bigLogs, Flat);
            return list;
        }

        /// <summary>
        /// Kulübenin yeri. Pişmiş adada elle seçilmiş "hut" noktası (GB19, kullanıcı: "kulübeyi uygun bir yere al"): meydanın
        /// doğusunda düz çimen, patikadan ve binalardan uzak, Ev Görevleri panosuna 12 m, kamp ateşine giden yolun üstünde; rehber
        /// rotası tek yönde akar. Nokta yoksa meydanın yanında yürünebilir, patika ve binalardan uzak düz bir çimen aranır.
        /// </summary>
        public static (float x, float z) HutSite(IslandTerrain t)
        {
            var spots = t.Baked?.Layout?.Spots;
            if (spots != null && spots.TryGetValue("hut", out var hs) && hs != null && hs.Length >= 2) return (hs[0], hs[1]);
            var best = (x: t.PlazaX + 6f, z: t.PlazaZ - 4f); var bestScore = float.MaxValue;
            var props = t.Props();
            for (var ring = 5f; ring <= 16f; ring += 1.5f)
                for (var a = 0; a < 24; a++)
                {
                    var ang = a * Math.PI * 2 / 24;
                    var x = t.PlazaX + (float)Math.Cos(ang) * ring; var z = t.PlazaZ + (float)Math.Sin(ang) * ring;
                    if (t.SurfaceAt(x, z) != Surface.Grass || !t.Walkable(x, z) || t.BuildingAt(x, z) != null) continue;
                    if (t.PathDistance(x, z) < IslandTerrain.PathHalfWidth + 2.6f) continue;
                    if (t.Regions.Any(r => IslandTerrain.Dist(x, z, r.X, r.Z) < r.Size * 0.8f + 3f)) continue;
                    if (props.Any(p => IslandTerrain.Dist(x, z, p.X, p.Z) < IslandTerrain.Footprint(p) + 2.4f)) continue;
                    // düzlük: çevredeki yükseklik farkı az olsun
                    var h = t.Height(x, z); var slope = 0f;
                    for (var k = 0; k < 8; k++)
                    {
                        var b = k * Math.PI / 4;
                        slope += Math.Abs(t.Height(x + (float)Math.Cos(b) * 1.8f, z + (float)Math.Sin(b) * 1.8f) - h);
                    }
                    var score = slope * 10f + ring * 0.3f;
                    if (score < bestScore) { bestScore = score; best = (x, z); }
                }
            return best;
        }

        public static int Count(GatherState s, string material) => s.Materials.TryGetValue(material, out var n) ? n : 0;

        /// <summary>Nokta şu an toplanabilir mi (hiç toplanmamış ya da yeniden çıkmış)?</summary>
        public static bool Available(GatherState s, int index, DateTime nowUtc) =>
            !s.HarvestedUtcTicks.TryGetValue(index, out var at) || nowUtc.Ticks - at >= Respawn.Ticks;

        /// <summary>Noktanın son vuruşu: malzeme eklenir, nokta beklemeye alınır. Toplanamıyorsa 0.</summary>
        public static int Harvest(GatherState s, GatherNode node, DateTime nowUtc)
        {
            if (!Available(s, node.Index, nowUtc)) return 0;
            var rule = Rule(node.Kind);
            s.HarvestedUtcTicks[node.Index] = nowUtc.Ticks;
            if (!IsMaterial(rule.Material)) return rule.Yield;   // ceviz: çağıran envantere ekler (malzeme sayılmaz)
            s.Materials[rule.Material] = Count(s, rule.Material) + rule.Yield;
            s.Total += rule.Yield;
            return rule.Yield;
        }

        /// <summary>
        /// Şantiye (O2): kulübe yerindeki malzeme yığınının doluluğu (0..1). Toplanan malzeme yığına eklenmiş gibi görünür;
        /// yapı bitince 1.
        /// </summary>
        public static float HutProgress(GatherState s)
        {
            if (s.HutBuilt) return 1f;
            var need = HutRecipe.Sum(r => r.count);
            var have = HutRecipe.Sum(r => Math.Min(Count(s, r.material), r.count));
            return need > 0 ? (float)have / need : 0f;
        }

        /// <summary>Şantiye evresi: 0 boş arsa, 1 temel, 2 iskele, 3 duvarlar (malzeme tamam, "Kulübe yap" hazır), 4 bitti.</summary>
        public static int HutStage(GatherState s)
        {
            if (s.HutBuilt) return 4;
            var p = HutProgress(s);
            if (p >= 1f) return 3;
            return p >= 0.5f ? 2 : p > 0f ? 1 : 0;
        }

        /// <summary>Kulübe için eksik malzeme kalmadı mı?</summary>
        public static bool CanBuild(GatherState s) => !s.HutBuilt && HutRecipe.All(r => Count(s, r.material) >= r.count);

        /// <summary>Kulübe için hâlâ eksik olan malzeme mi (rehber yalnız bunlara götürür)?</summary>
        public static bool Lacking(GatherState s, string material) =>
            !s.HutBuilt && HutRecipe.Any(r => r.material == material && Count(s, material) < r.count);

        /// <summary>Kulübeyi inşa et: tarif kadar malzeme düşer. Yetmiyorsa false.</summary>
        public static bool Build(GatherState s)
        {
            if (!CanBuild(s)) return false;
            foreach (var (m, n) in HutRecipe) s.Materials[m] = Count(s, m) - n;
            s.HutBuilt = true;
            return true;
        }
    }
}
