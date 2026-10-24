using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json;

namespace Pofi.Logic.Island
{
    /// <summary>Arazi ayarları (regions.json → "terrain"). Uzunluklar metre; pet ~1,75 m.</summary>
    public sealed class TerrainDef
    {
        [JsonProperty("rx")] public float Rx = 31f;          // ada elipsi yarı genişlik (x)
        [JsonProperty("rz")] public float Rz = 27f;          // yarı derinlik (z)
        [JsonProperty("cz")] public float Cz = 5f;           // elips merkezinin z'si
        [JsonProperty("plaza")] public float[] Plaza = { 0f, -1f };   // patikaların buluştuğu meydan
        [JsonProperty("seed")] public int Seed = 7;
        [JsonProperty("hills")] public List<HillDef> Hills = new List<HillDef>();
    }

    public sealed class HillDef
    {
        [JsonProperty("x")] public float X;
        [JsonProperty("z")] public float Z;
        [JsonProperty("h")] public float H = 4f;      // tepe yüksekliği
        [JsonProperty("r")] public float R = 6f;      // yayılım (gauss sigma)
        [JsonProperty("snow")] public bool Snow;
    }

    public enum Surface { Water, Sand, Grass, Path, Rock, Snow }

    /// <summary>Zemin yüzey ağırlıkları (çimen = geri kalan).</summary>
    public struct SurfaceMix { public float Water, Sand, Path, Rock, Snow; }

    /// <summary>Haritaya serpiştirilen süs (palmiye, kaya, çalı…).</summary>
    public sealed class PropSpot
    {
        public string Asset;
        public float X, Z, Yaw, Size;
        public float Y = float.NaN;    // pişmiş adada taban yüksekliği (NaN: zeminden)
        public bool Scaled;            // true: Size = model ölçeği (v6 modelleri gerçek ölçüde); false: Size = taban genişliği
    }

    /// <summary>
    /// Prosedürel ada: yükseklik, yüzey türü (kum/çimen/patika/kaya/kar), yürünebilirlik, bina kapıları,
    /// A* yol bulma ve süs yerleşimi. Belirlenimci (aynı veri → aynı ada); Unity bunu yalnızca çizer.
    /// Su seviyesi y = 0.
    /// </summary>
    public sealed class IslandTerrain
    {
        public const float Cell = 0.5f;          // yol bulma ızgarası (m)
        public const float PathHalfWidth = 0.75f;
        public readonly float MinX, MaxX, MinZ, MaxZ;
        public IReadOnlyList<RegionDef> Regions { get; }
        public TerrainDef Def { get; }
        /// <summary>Pişmiş v6 adası (null: eski prosedürel ada). Yükseklik, yüzey, patika ve süsler buradan gelir.</summary>
        public BakedIsland Baked { get; }
        private readonly BakedField _field;

        private readonly List<(float ax, float az, float bx, float bz)> _paths = new List<(float, float, float, float)>();
        private readonly int _nx, _nz;
        private readonly bool[] _walk;

        public IslandTerrain(IReadOnlyList<RegionDef> regions, TerrainDef def, BakedIsland baked = null)
        {
            Regions = regions;
            Def = def ?? new TerrainDef();
            Baked = baked;
            _field = baked?.Field;
            if (_field != null)
            {
                MinX = _field.X0; MaxX = _field.X1; MinZ = _field.Z0; MaxZ = _field.Z1;
            }
            else
            {
                MinX = -Def.Rx - 9f; MaxX = Def.Rx + 9f;
                MinZ = Def.Cz - Def.Rz - 9f; MaxZ = Def.Cz + Def.Rz + 9f;
            }
            _nx = (int)Math.Ceiling((MaxX - MinX) / Cell) + 1;
            _nz = (int)Math.Ceiling((MaxZ - MinZ) / Cell) + 1;
            // tapınak terası (GB18): yükseklik katmanı yürüme ızgarasından önce bilinsin (basamaklar rampa, teras kenarı dik → yürünmez)
            var temple = baked?.Layout?.Props?.FirstOrDefault(p => p != null && p.Asset == "b_temple");
            if (temple != null) _temple = (temple.X, temple.Z, temple.Y);
            _walk = new bool[_nx * _nz];
            for (var j = 0; j < _nz; j++)
            for (var i = 0; i < _nx; i++)
                _walk[j * _nx + i] = ComputeWalkable(MinX + i * Cell, MinZ + j * Cell);

            if (_field != null)
            {
                // pişmiş ada: patikalar taslaktaki çoklu çizgiler (arazide rampa olarak zaten kazılı)
                foreach (var line in baked.Layout.Paths)
                    for (var k = 1; k < line.Count; k++)
                        if (line[k - 1].Length > 1 && line[k].Length > 1) _paths.Add((line[k - 1][0], line[k - 1][1], line[k][0], line[k][1]));
            }
            // Patikalar: dallanan yol ağı (en kısa bağlantı ağacı). Meydandan başlar; her adımda ağa en yakın kapı,
            // ağdaki en yakın noktadan yol bulmayla bağlanır (var olan patikalar tercih edilir) → köy gibi dallanır.
            var nodes = new List<(float x, float z)> { (PlazaX, PlazaZ) };
            var left = _field != null ? new List<RegionDef>() : regions.ToList();
            while (left.Count > 0)
            {
                RegionDef bestR = null; (float x, float z) bestN = default; var bestD = float.MaxValue;
                foreach (var r in left)
                {
                    var d0 = Door(r);
                    foreach (var n in nodes)
                    {
                        var d = Dist(n.x, n.z, d0.x, d0.z);
                        if (d < bestD) { bestD = d; bestR = r; bestN = n; }
                    }
                }
                left.Remove(bestR);
                var (dx, dz) = Door(bestR);
                var route = FindPath(bestN.x, bestN.z, dx, dz);
                if (route.Count == 0) continue;
                var (px, pz) = bestN;
                foreach (var w in route)
                {
                    _paths.Add((px, pz, w.x, w.z));
                    // ara noktalar da ağa katılır: sonraki yollar buradan dallanabilir
                    var segLen = Dist(px, pz, w.x, w.z);
                    for (var k = 4f; k < segLen; k += 4f) nodes.Add((px + (w.x - px) * k / segLen, pz + (w.z - pz) * k / segLen));
                    nodes.Add(w);
                    (px, pz) = w;
                }
            }

            // Süsler yerleşir ve engel olur: ağaç, kaya, çalı, çit… içinden geçilmez
            _props = _field != null ? BakedProps(baked.Layout) : BuildProps();
            foreach (var p in _props)
            {
                if (p.Asset == "b_temple") { BlockTempleSolids(p.X, p.Z); continue; }   // teras yürünür; salon, köşk, duvar, taş, fener engel
                var rad = ObstacleRadius(p);
                if (rad <= 0f) continue;
                var ci = (int)Math.Round((p.X - MinX) / Cell); var cj = (int)Math.Round((p.Z - MinZ) / Cell);
                if (ci >= 0 && cj >= 0 && ci < _nx && cj < _nz) _walk[cj * _nx + ci] = false;   // ince süslerde de merkez hücre
                for (var j = (int)((p.Z - rad - MinZ) / Cell); j <= (int)((p.Z + rad - MinZ) / Cell) + 1; j++)
                for (var i = (int)((p.X - rad - MinX) / Cell); i <= (int)((p.X + rad - MinX) / Cell) + 1; i++)
                {
                    if (i < 0 || j < 0 || i >= _nx || j >= _nz) continue;
                    if (Dist(MinX + i * Cell, MinZ + j * Cell, p.X, p.Z) <= rad) _walk[j * _nx + i] = false;
                }
            }
            if (_field != null) ResolveDoors();
        }

        private readonly List<PropSpot> _props;
        private Dictionary<string, (float x, float z)> _doors;

        /// <summary>
        /// Pişmiş adada kapı: yapının önü (yaw) yürünebilirse orası; değilse yapı çevresinde patikaya en yakın yürünebilir nokta
        /// (kumsal bölgelerinde ön su ya da yamaç olabilir). Yürüme ızgarası kurulduktan sonra bir kez hesaplanır.
        /// </summary>
        private void ResolveDoors()
        {
            var doors = new Dictionary<string, (float x, float z)>();
            foreach (var r in Regions)
            {
                var front = Door(r);
                if (Walkable(front.x, front.z)) { doors[r.Id] = front; continue; }
                var best = front; var bestD = float.MaxValue;
                for (var ring = 0; ring < 4; ring++)
                {
                    var rad = r.Size * 0.62f + 0.8f + ring * 0.8f;
                    for (var k = 0; k < 24; k++)
                    {
                        var a = k * (float)Math.PI * 2f / 24f;
                        var x = r.X + (float)Math.Sin(a) * rad; var z = r.Z - (float)Math.Cos(a) * rad;
                        if (!Walkable(x, z)) continue;
                        var d = PathDistance(x, z) + ring * 0.5f;
                        if (d < bestD) { bestD = d; best = (x, z); }
                    }
                    if (bestD < float.MaxValue) break;
                }
                doors[r.Id] = best;
            }
            _doors = doors;
        }

        private void BlockRect(float cx, float cz, float hx, float hz)
        {
            for (var j = (int)((cz - hz - MinZ) / Cell); j <= (int)((cz + hz - MinZ) / Cell) + 1; j++)
            for (var i = (int)((cx - hx - MinX) / Cell); i <= (int)((cx + hx - MinX) / Cell) + 1; i++)
                if (i >= 0 && j >= 0 && i < _nx && j < _nz) _walk[j * _nx + i] = false;
        }

        // ------------------------------------------------------------------ tapınak terası (GB18, kullanıcı: "merdiven ve yeşillik engel gibi")
        // Taslak art/code3d/v6/kit3_v6.py temple(): yerel (x, y) = dünya (X + x, Z + y) (RealAssets.EnvScaled 180° kuralıyla aynı yön).
        // Teraslar: alt t1 (0, 1) 30 × 22 üst 1,0 m · üst t2 (0, 4,5) 21 × 13 üst 2,1 m. Basamaklar rampa: s1 önde (x 0, eni 5),
        // s3 sol önde (x −12,5, eni 3) yerden 1,0'a; s2 (x 0, eni 4) 1,0'dan 2,1'e. Basamak derinliği 4 × 0,45 = 1,8 m.
        private (float X, float Z, float Y)? _temple;
        private const float StepDepth = 1.8f;

        /// <summary>Nokta tapınak terası ya da basamağı üstünde mi (yerleşim: toplama noktası, sürpriz buraya konmaz)?</summary>
        public bool OnPlatform(float x, float z) => _temple.HasValue && TempleHeight(x, z, out _);

        private bool TempleHeight(float x, float z, out float h)
        {
            h = 0f;
            var t = _temple.Value; var lx = x - t.X; var ly = z - t.Z;
            if (Math.Abs(lx) > 16f || Math.Abs(ly) > 13f) return false;
            float? local = null;
            if (InRoundRect(lx, ly, 0f, 4.5f, 21f, 13f, 1.5f)) local = 2.1f;
            else if (Math.Abs(lx) <= 2f && ly >= -2f - StepDepth && ly <= -2f) local = 1.0f + (ly + 2f + StepDepth) / StepDepth * 1.1f;
            else if (InRoundRect(lx, ly, 0f, 1f, 30f, 22f, 2f)) local = 1.0f;
            else if (ly >= -10f - StepDepth && ly <= -10f && (Math.Abs(lx) <= 2.5f || Math.Abs(lx + 12.5f) <= 1.5f))
                local = -0.25f + (ly + 10f + StepDepth) / StepDepth * 1.25f;
            if (!local.HasValue) return false;
            h = t.Y + local.Value;
            return true;
        }

        private static bool InRoundRect(float x, float y, float cx, float cy, float w, float d, float r)
        {
            var dx = Math.Max(0f, Math.Abs(x - cx) - (w / 2f - r)); var dy = Math.Max(0f, Math.Abs(y - cy) - (d / 2f - r));
            return dx * dx + dy * dy <= r * r;
        }

        /// <summary>Teras üstündeki katı yapılar: salon, köşk (pagoda), yan salon, avlu duvarı, dikili taşlar, fenerler, çalılar, ön seki.</summary>
        private void BlockTempleSolids(float tx, float tz)
        {
            void Rect(float cx, float cy, float w, float d) => BlockRect(tx + cx, tz + cy, w / 2f + 0.3f, d / 2f + 0.3f);
            void Disc(float cx, float cy, float r)
            {
                for (var j = (int)((tz + cy - r - MinZ) / Cell); j <= (int)((tz + cy + r - MinZ) / Cell) + 1; j++)
                for (var i = (int)((tx + cx - r - MinX) / Cell); i <= (int)((tx + cx + r - MinX) / Cell) + 1; i++)
                    if (i >= 0 && j >= 0 && i < _nx && j < _nz && Dist(MinX + i * Cell, MinZ + j * Cell, tx + cx, tz + cy) <= r) _walk[j * _nx + i] = false;
            }
            Rect(0f, 6.5f, 11f, 6.5f);          // ana salon
            Rect(-10.5f, 6f, 6f, 6f);           // köşk
            Rect(11.5f, 4.5f, 6f, 5f);          // yan salon
            Rect(-14.5f, 2.75f, 0.6f, 17.5f);   // avlu duvarı: sol, arka, sağ
            Rect(0f, 11.5f, 29.6f, 0.6f);
            Rect(14.5f, 2.75f, 0.6f, 17.5f);
            Rect(-9f, -8.5f, 7f, 3.5f);         // ön küçük seki (alçak, süs)
            foreach (var (x, y, r) in new[] { (-6.5f, -3f, 1.0f), (-5.4f, -3.6f, 0.7f), (-7.4f, -4f, 0.6f), (6.5f, -4.5f, 0.9f), (3.5f, 9.6f, 1.0f),   // dikili taşlar
                         (-4.5f, 2.25f, 0.45f), (-1.5f, 2.25f, 0.45f), (1.5f, 2.25f, 0.45f), (4.5f, 2.25f, 0.45f),                                   // salon önü fenerleri
                         (9.5f, 1.3f, 0.45f), (13.5f, 1.3f, 0.45f), (-13.6f, 2.9f, 0.45f), (-7.4f, 2.9f, 0.45f),                                       // yan ve köşk fenerleri
                         (-3.5f, -8f, 0.9f), (4.5f, -8.5f, 0.8f) })                                                                                   // çalılar
                Disc(x, y, r);
        }

        private static List<PropSpot> BakedProps(BakedLayout layout) =>
            layout.Props.Where(p => p != null && !string.IsNullOrEmpty(p.Asset))
                .Select(p => new PropSpot { Asset = p.Asset, X = p.X, Z = p.Z, Y = p.Y, Yaw = p.Yaw, Size = p.S, Scaled = p.Fp == 0 }).ToList();

        /// <summary>Süsün yerde kapladığı yarıçap (yerleşim aralığı için): ölçekli v6 modelinde engel yarıçapı, eskilerde taban genişliği.</summary>
        public static float Footprint(PropSpot p) => p.Scaled ? ObstacleRadius(p) + 0.6f : p.Size;

        /// <summary>Süsün yürüme engeli yarıçapı (m).</summary>
        public static float ObstacleRadius(PropSpot p)
        {
            switch (p.Asset)
            {
                // v6 (ölçekli modeller): gövde/taş yarıçapı
                case "t_round0": case "t_round1": case "t_round2": case "t_round3": case "t_birch": case "t_cypress":
                case "t_pine0": case "t_pine1": case "t_pine2": case "t_pine_snow":
                case "t_palm_tall0": case "t_palm_tall1": case "t_palm_tall2": return 0.5f;
                case "t_bush": return Math.Min(0.8f, p.Size * 0.4f);
                case "r_boulder": case "r_boulder_b": case "r_pebble": return Math.Min(1.6f, p.Size * 0.45f);
                case "p_campfire": return 1.3f;
                case "p_log_v6": case "p_stump_v6": return 0.45f;
                case "p_driftwood": return 0.6f;
                case "p_trail_pole": return 0.15f;
                case "p_snow_lump": case "p_starfish": case "p_crab": case "p_pool": case "b_temple": return 0f;
                case "palm": return 0.45f;
                case "p_tree": return 0.5f;
                case "p_lantern": case "p_sign": return 0.3f;
                case "p_flowers": return p.Size * 0.3f;
                default: return p.Size * 0.42f;   // kaya, çalı, çit, sandık
            }
        }

        /// <summary>Patika parçaları (çizim ve süs yerleşimi için).</summary>
        public IReadOnlyList<(float ax, float az, float bx, float bz)> Paths => _paths;

        private float[] PlazaArr => Baked?.Layout?.Plaza ?? Def.Plaza;
        public float PlazaX => PlazaArr != null && PlazaArr.Length > 0 ? PlazaArr[0] : 0f;
        public float PlazaZ => PlazaArr != null && PlazaArr.Length > 1 ? PlazaArr[1] : 0f;

        // ------------------------------------------------------------------ şekil

        /// <summary>Kıyı ölçüsü: &lt; 1 kara, &gt; 1 deniz (kıyı çizgisi gürültüyle dalgalı).</summary>
        public float Coast(float x, float z)
        {
            if (_field != null) return _field.Height(x, z) < 0f ? 1.1f : 0.5f;
            var nx = x / Def.Rx;
            var nz = (z - Def.Cz) / Def.Rz;
            var c = (float)Math.Sqrt(nx * nx + nz * nz);
            var ang = (float)Math.Atan2(nz, nx);
            var wobble = 0.05f * (float)Math.Sin(ang * 3f + Def.Seed) + 0.035f * (float)Math.Sin(ang * 7f + Def.Seed * 2.3f)
                         + 0.04f * (Noise(x * 0.08f, z * 0.08f) - 0.5f);
            return c + wobble;
        }

        /// <summary>Bina ve tepe etkisi olmadan doğal zemin.</summary>
        private float BaseHeight(float x, float z)
        {
            var c = Coast(x, z);
            var h = Lerp(-1.6f, 0.2f, SmoothStep(1.07f, 0.95f, c));          // deniz tabanı → kumsal
            h += SmoothStep(0.93f, 0.78f, c) * 0.7f;                           // çimen düzlüğü
            var inland = SmoothStep(0.86f, 0.6f, c);
            h += inland * (Noise(x * 0.11f + 3f, z * 0.11f) - 0.5f) * 1.3f;      // yumuşak engebe
            h += inland * (Noise(x * 0.33f, z * 0.33f + 9f) - 0.5f) * 0.25f;
            // kumsalda küçük kum tepecikleri (rüzgâr yönünde uzamış)
            var beach = SmoothStep(0.84f, 0.9f, c) * SmoothStep(1.0f, 0.95f, c);
            var dune = (float)Math.Sin(x * 0.9f + z * 0.35f) * 0.5f + 0.5f;
            var dune2 = (float)Math.Sin(z * 0.6f - x * 0.2f);
            h += beach * 0.16f * dune * dune2 * dune2;
            return h;
        }

        private float HillHeight(float x, float z, out float snowWeight)
        {
            float h = 0f;
            snowWeight = 0f;
            foreach (var hill in Def.Hills)
            {
                var dx = x - hill.X; var dz = z - hill.Z;
                var g = (float)Math.Exp(-(dx * dx + dz * dz) / (2f * hill.R * hill.R));
                var bumpy = 1f + (Noise(x * 0.3f + hill.X, z * 0.3f) - 0.5f) * 0.25f;
                h += hill.H * g * bumpy;
                if (hill.Snow) snowWeight = Math.Max(snowWeight, g);
            }
            return h;
        }

        /// <summary>Yerin yüksekliği (m). Bina tabanları düzleştirilmiş, patikalar hafif yumuşatılmış.</summary>
        public float Height(float x, float z)
        {
            if (_field != null)
            {
                var hf = _field.Height(x, z);   // bina yastıkları ızgarada pişmiş
                return _temple.HasValue && TempleHeight(x, z, out var ht) ? Math.Max(hf, ht) : hf;
            }
            var h = BaseHeight(x, z) + HillHeight(x, z, out _);
            foreach (var r in Regions)
            {
                if (r.Water) continue;
                var d = Dist(x, z, r.X, r.Z);
                var rad = r.Size * 0.62f;
                var w = SmoothStep(rad * 1.6f, rad, d);
                if (w <= 0f) continue;
                h = Lerp(h, PadHeight(r), w);
            }
            return h;
        }

        /// <summary>Bölge tabanının yüksekliği (doğal zeminin merkezdeki değeri, kıyıda en az 0,3).</summary>
        public float PadHeight(RegionDef r) => _field != null ? (r.Water ? 0f : Math.Max(0.3f, _field.Height(r.X, r.Z)))
            : Math.Max(0.3f, BaseHeight(r.X, r.Z) + HillHeight(r.X, r.Z, out _));

        /// <summary>Göl (pişmiş adada): yürünmez, su yüzeyi <see cref="BakedLayout.LakeDef.Level"/>.</summary>
        /// <summary>Çiçek yoğunluğu 0..1 (pişmiş ada sürüm 2): mavi çan çiçeği ve turuncu çiçek. Eski adada 0.</summary>
        public float Bluebell(float x, float z) => _field != null ? _field.Get(BakedField.Layer.Bluebell, x, z) : 0f;
        public float OrangeFlower(float x, float z) => _field != null ? _field.Get(BakedField.Layer.Orange, x, z) : 0f;

        public bool InLake(float x, float z) => _field != null && _field.Get(BakedField.Layer.Lake, x, z) > 0.4f;

        public float Slope(float x, float z)
        {
            const float e = 0.35f;
            var dx = (Height(x + e, z) - Height(x - e, z)) / (2f * e);
            var dz = (Height(x, z + e) - Height(x, z - e)) / (2f * e);
            return (float)Math.Sqrt(dx * dx + dz * dz);
        }

        public Surface SurfaceAt(float x, float z)
        {
            var h = Height(x, z);
            if (_field != null)
            {
                if (h < 0f || InLake(x, z)) return Surface.Water;
                if (_field.Get(BakedField.Layer.Snow, x, z) > 0.5f) return Surface.Snow;
                if (_field.Get(BakedField.Layer.Rock, x, z) > 0.5f) return Surface.Rock;
                if (_field.Get(BakedField.Layer.Path, x, z) > 0.5f) return Surface.Path;
                if (_field.Get(BakedField.Layer.Sand, x, z) > 0.5f) return Surface.Sand;
                return Surface.Grass;
            }
            if (h < 0f) return Surface.Water;
            HillHeight(x, z, out var snow);
            if (snow > 0.35f && h > 1.6f) return Surface.Snow;
            if (Slope(x, z) > 0.95f) return Surface.Rock;
            if (PathDistance(x, z) < PathHalfWidth) return Surface.Path;
            if (h < 0.45f || Coast(x, z) > 0.93f) return Surface.Sand;
            return Surface.Grass;
        }

        /// <summary>Yumuşak yüzey karışımı (0..1 ağırlıklar): zemin dokusunda basamaksız geçiş için. Kalan = çimen.</summary>
        public SurfaceMix MixAt(float x, float z)
        {
            var h = Height(x, z);
            if (_field != null)
                return new SurfaceMix
                {
                    Water = Math.Max(SmoothStep(0.05f, -0.2f, h), _field.Get(BakedField.Layer.Lake, x, z)),
                    Sand = _field.Get(BakedField.Layer.Sand, x, z), Path = _field.Get(BakedField.Layer.Path, x, z),
                    Rock = _field.Get(BakedField.Layer.Rock, x, z), Snow = _field.Get(BakedField.Layer.Snow, x, z),
                };
            var c = Coast(x, z);
            HillHeight(x, z, out var snowW);
            var m = new SurfaceMix
            {
                Water = SmoothStep(0.05f, -0.2f, h),
                Sand = Math.Max(SmoothStep(0.6f, 0.3f, h), SmoothStep(0.89f, 0.95f, c)),
                Snow = SmoothStep(0.25f, 0.5f, snowW) * SmoothStep(1.2f, 2.0f, h),
                Rock = SmoothStep(0.75f, 1.15f, Slope(x, z)),
            };
            if (h > 0.1f)
            {
                var d = PathDistance(x, z) + (Noise(x * 0.9f + 5f, z * 0.9f) - 0.5f) * 0.35f;   // kenar hafif düzensiz
                m.Path = SmoothStep(PathHalfWidth + 0.3f, PathHalfWidth - 0.25f, d);
            }
            return m;
        }

        /// <summary>En yakın patikaya uzaklık (meydan → her bölge kapısı).</summary>
        public float PathDistance(float x, float z)
        {
            var best = 1000f;
            foreach (var p in _paths)
            {
                var d = SegmentDistance(x, z, p.ax, p.az, p.bx, p.bz);
                if (d < best) best = d;
            }
            return best;
        }

        // ------------------------------------------------------------------ bölgeler

        /// <summary>Bölge yapısının dönüşü (derece): 0 = önü güneye (−z, kuşbakışı kameraya) bakar.</summary>
        public static float FacingDeg(RegionDef r) => r.Yaw;

        /// <summary>Kapı noktası: yapının önünde, tabanın hemen dışında.</summary>
        public (float x, float z) Door(RegionDef r)
        {
            if (_doors != null && _doors.TryGetValue(r.Id, out var cached)) return cached;
            var a = r.Yaw * (float)Math.PI / 180f;
            var depth = r.Size * 0.62f + 0.8f;
            // önü −z; yaw saat yönünde döndürür (Unity Y ekseni gibi)
            return (r.X - (float)Math.Sin(a) * depth, r.Z - (float)Math.Cos(a) * depth);
        }

        /// <summary>Nokta bir yapının tabanının içinde mi (yürünemez)?</summary>
        public RegionDef BuildingAt(float x, float z)
        {
            foreach (var r in Regions)
                if (Dist(x, z, r.X, r.Z) < r.Size * 0.5f) return r;
            return null;
        }

        // ------------------------------------------------------------------ yürüme

        private bool ComputeWalkable(float x, float z)
        {
            var h = Height(x, z);
            if (h < 0.15f) return false;                                      // kuru kumda kal: dalgalar ve kıyı köpüğü ~0,1 m (pet suyun üstünde görünmesin)
            if (InLake(x, z)) return false;
            if (BuildingAt(x, z) != null) return false;
            return Slope(x, z) < 1.1f;
        }

        public bool Walkable(float x, float z)
        {
            var i = (int)Math.Round((x - MinX) / Cell);
            var j = (int)Math.Round((z - MinZ) / Cell);
            if (i < 0 || j < 0 || i >= _nx || j >= _nz) return false;
            return _walk[j * _nx + i];
        }

        /// <summary>En yakın yürünebilir nokta (dokunulan yer suya/binaya denk gelirse).</summary>
        public (float x, float z) NearestWalkable(float x, float z, float maxRadius = 8f)
        {
            if (Walkable(x, z)) return (x, z);
            for (var rad = Cell; rad <= maxRadius; rad += Cell)
            {
                var steps = Math.Max(8, (int)(rad * 8f));
                var bestD = float.MaxValue; (float, float) best = (float.NaN, float.NaN);
                for (var k = 0; k < steps; k++)
                {
                    var a = k * 2f * (float)Math.PI / steps;
                    var px = x + (float)Math.Cos(a) * rad; var pz = z + (float)Math.Sin(a) * rad;
                    if (!Walkable(px, pz)) continue;
                    var d = Dist(px, pz, x, z);
                    if (d < bestD) { bestD = d; best = (px, pz); }
                }
                if (!float.IsNaN(best.Item1)) return best;
            }
            return (float.NaN, float.NaN);
        }

        /// <summary>
        /// A* yol (8 yön, 0,5 m ızgara), görüş hattıyla sadeleştirilmiş ara noktalar. Başlangıç dahil değil, hedef dahil.
        /// Yol yoksa boş liste.
        /// </summary>
        public List<(float x, float z)> FindPath(float fx, float fz, float tx, float tz)
        {
            var result = new List<(float x, float z)>();
            var t = NearestWalkable(tx, tz);
            if (float.IsNaN(t.x)) return result;
            var f = NearestWalkable(fx, fz, 3f);
            if (float.IsNaN(f.x)) f = (fx, fz);
            int I(float x) => Clamp((int)Math.Round((x - MinX) / Cell), 0, _nx - 1);
            int J(float z) => Clamp((int)Math.Round((z - MinZ) / Cell), 0, _nz - 1);
            int si = I(f.x), sj = J(f.z), gi = I(t.x), gj = J(t.z);
            var start = sj * _nx + si; var goal = gj * _nx + gi;
            if (start == goal) { result.Add(t); return result; }

            var g = new Dictionary<int, float> { [start] = 0f };
            var came = new Dictionary<int, int>();
            var open = new SortedSet<(float f, int id)>(Comparer<(float f, int id)>.Create((a, b) => a.f != b.f ? a.f.CompareTo(b.f) : a.id.CompareTo(b.id)));
            open.Add((Heur(si, sj, gi, gj), start));
            var closed = new HashSet<int>();
            var found = false;
            while (open.Count > 0 && closed.Count < (_field != null ? 160000 : 40000))   // büyük ada: uzun yollar
            {
                var cur = open.Min; open.Remove(cur);
                if (cur.id == goal) { found = true; break; }
                if (!closed.Add(cur.id)) continue;
                int ci = cur.id % _nx, cj = cur.id / _nx;
                for (var dj = -1; dj <= 1; dj++)
                for (var di = -1; di <= 1; di++)
                {
                    if (di == 0 && dj == 0) continue;
                    int ni = ci + di, nj = cj + dj;
                    if (ni < 0 || nj < 0 || ni >= _nx || nj >= _nz) continue;
                    var nid = nj * _nx + ni;
                    if (!_walk[nid] || closed.Contains(nid)) continue;
                    if (di != 0 && dj != 0 && (!_walk[cj * _nx + ni] || !_walk[nj * _nx + ci])) continue;   // köşe kesme
                    var step = (di != 0 && dj != 0 ? 1.4142f : 1f) * Cell;
                    var mx = MinX + ni * Cell; var mz = MinZ + nj * Cell;
                    if (PathDistance(mx, mz) > PathHalfWidth) step *= 1.7f;     // patikayı tercih et (yeni yollar var olanlara katılır)
                    var ng = g[cur.id] + step;
                    if (g.TryGetValue(nid, out var old) && old <= ng) continue;
                    g[nid] = ng; came[nid] = cur.id;
                    open.Add((ng + Heur(ni, nj, gi, gj), nid));
                }
            }
            if (!found) return result;

            var cells = new List<int>();
            for (var c = goal; c != start; c = came[c]) cells.Add(c);
            cells.Reverse();
            var pts = cells.Select(c => (MinX + (c % _nx) * Cell, MinZ + (c / _nx) * Cell)).ToList();
            pts[pts.Count - 1] = t;
            // sadeleştir: görüş hattı açıksa ara noktaları atla
            var from = f;
            var k2 = 0;
            while (k2 < pts.Count)
            {
                var far = k2;
                for (var m = pts.Count - 1; m > k2; m--)
                    if (LineWalkable(from.x, from.z, pts[m].Item1, pts[m].Item2)) { far = m; break; }
                result.Add(pts[far]);
                from = pts[far];
                k2 = far + 1;
            }
            return result;
        }

        private float Heur(int ai, int aj, int bi, int bj)
        {
            var dx = Math.Abs(ai - bi); var dz = Math.Abs(aj - bj);
            return (Math.Max(dx, dz) + 0.4142f * Math.Min(dx, dz)) * Cell;
        }

        public bool LineWalkable(float ax, float az, float bx, float bz)
        {
            var d = Dist(ax, az, bx, bz);
            var n = Math.Max(1, (int)(d / (Cell * 0.5f)));
            for (var i = 1; i <= n; i++)
            {
                var k = i / (float)n;
                if (!Walkable(ax + (bx - ax) * k, az + (bz - az) * k)) return false;
            }
            return true;
        }

        // ------------------------------------------------------------------ süsler

        /// <summary>Belirlenimci süs yerleşimi: kumsalda palmiye/kaya, çimende çalı/çiçek, patika boyunca fener, iskelede sandık/kayık.</summary>
        public List<PropSpot> Props() => new List<PropSpot>(_props);

        private List<PropSpot> BuildProps()
        {
            var list = new List<PropSpot>();
            var rng = new Random(Def.Seed * 131 + 17);
            bool Free(float x, float z, float gap)
            {
                if (PathDistance(x, z) < PathHalfWidth + 0.6f) return false;
                foreach (var r in Regions) if (Dist(x, z, r.X, r.Z) < r.Size * 0.75f + gap) return false;
                foreach (var p in list) if (Dist(x, z, p.X, p.Z) < Math.Max(p.Size, gap) + 0.6f) return false;
                return true;
            }
            void Scatter(string asset, int count, float size, Func<float, float, bool> where, float gap = 0.8f)
            {
                var placed = 0;
                for (var tries = 0; placed < count && tries < count * 60; tries++)
                {
                    var x = MinX + (float)rng.NextDouble() * (MaxX - MinX);
                    var z = MinZ + (float)rng.NextDouble() * (MaxZ - MinZ);
                    if (!where(x, z) || !Free(x, z, gap)) continue;
                    var s = size * (0.8f + (float)rng.NextDouble() * 0.45f);
                    list.Add(new PropSpot { Asset = asset, X = x, Z = z, Yaw = (float)rng.NextDouble() * 360f, Size = s });
                    placed++;
                }
            }
            bool Beach(float x, float z) { var c = Coast(x, z); var h = Height(x, z); return c > 0.86f && c < 0.97f && h > 0.1f; }
            bool Inland(float x, float z) => SurfaceAt(x, z) == Surface.Grass && Coast(x, z) < 0.85f;

            // patika boyunca fenerler (meydana yakın yarıda)
            foreach (var p in _paths)
            {
                var len = Dist(p.ax, p.az, p.bx, p.bz);
                if (len < 6f) continue;
                var k = 0.45f;
                var px = p.ax + (p.bx - p.ax) * k; var pz = p.az + (p.bz - p.az) * k;
                var nx = -(p.bz - p.az) / len; var nz = (p.bx - p.ax) / len;
                var lx = px + nx * (PathHalfWidth + 0.7f); var lz = pz + nz * (PathHalfWidth + 0.7f);
                if (Height(lx, lz) > 0.2f && Regions.All(r => Dist(lx, lz, r.X, r.Z) > r.Size * 0.75f) && list.All(q => Dist(q.X, q.Z, lx, lz) > 4f))
                    list.Add(new PropSpot { Asset = "p_lantern", X = lx, Z = lz, Yaw = 0f, Size = 0.7f });
            }
            // yoğunluk (kullanıcı isteği 15 Ekim 2026: daha çok ağaç, palmiye ve süs; modeller iPhone bütçesine göre hafif)
            Scatter("palm", 26, 2.2f, Beach, 2.2f);
            Scatter("palm", 12, 2.0f, Inland, 2.6f);
            Scatter("p_tree", 14, 2.4f, Inland, 2.6f);
            Scatter("p_rock", 16, 1.4f, (x, z) => Beach(x, z) || SurfaceAt(x, z) == Surface.Rock);
            Scatter("p_bush", 24, 1.2f, Inland);
            Scatter("p_flowers", 26, 1.0f, Inland, 0.6f);
            Scatter("p_fence", 6, 1.6f, Inland, 2f);
            Scatter("p_boat", 2, 2.0f, (x, z) => { var c = Coast(x, z); return c > 0.9f && c < 0.97f && Height(x, z) > 0.05f; }, 4f);
            var pier = Regions.FirstOrDefault(r => r.Water);
            if (pier != null)
            {
                var (dx, dz) = Door(pier);
                list.Add(new PropSpot { Asset = "p_crates", X = dx + 2.2f, Z = dz + 0.4f, Yaw = 200f, Size = 1.3f });
                list.Add(new PropSpot { Asset = "p_sign", X = PlazaX + 2.2f, Z = PlazaZ + 1.6f, Yaw = 190f, Size = 0.9f });
            }
            return list;
        }

        // ------------------------------------------------------------------ yardımcılar

        private static int Clamp(int v, int a, int b) => v < a ? a : v > b ? b : v;
        private static float Lerp(float a, float b, float t) => a + (b - a) * (t < 0f ? 0f : t > 1f ? 1f : t);
        public static float SmoothStep(float edge0, float edge1, float x)
        {
            var t = (x - edge0) / (edge1 - edge0);
            t = t < 0f ? 0f : t > 1f ? 1f : t;
            return t * t * (3f - 2f * t);
        }
        public static float Dist(float ax, float az, float bx, float bz) => (float)Math.Sqrt((ax - bx) * (ax - bx) + (az - bz) * (az - bz));

        private static float SegmentDistance(float px, float pz, float ax, float az, float bx, float bz)
        {
            var vx = bx - ax; var vz = bz - az;
            var l2 = vx * vx + vz * vz;
            var t = l2 <= 1e-6f ? 0f : ((px - ax) * vx + (pz - az) * vz) / l2;
            t = t < 0f ? 0f : t > 1f ? 1f : t;
            return Dist(px, pz, ax + vx * t, az + vz * t);
        }

        /// <summary>Değer gürültüsü (0..1), tohumla belirlenimci.</summary>
        private float Noise(float x, float z)
        {
            var x0 = (int)Math.Floor(x); var z0 = (int)Math.Floor(z);
            var fx = x - x0; var fz = z - z0;
            var u = fx * fx * (3f - 2f * fx); var v = fz * fz * (3f - 2f * fz);
            var a = Hash(x0, z0); var b = Hash(x0 + 1, z0); var c = Hash(x0, z0 + 1); var d = Hash(x0 + 1, z0 + 1);
            return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
        }

        private float Hash(int x, int z)
        {
            unchecked
            {
                var h = (uint)(x * 374761393 + z * 668265263 + Def.Seed * 982451653);
                h = (h ^ (h >> 13)) * 1274126177u;
                h ^= h >> 16;
                return (h & 0xFFFFFF) / (float)0xFFFFFF;
            }
        }
    }
}
