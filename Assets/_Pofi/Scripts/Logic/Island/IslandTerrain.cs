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

    /// <summary>Haritaya serpiştirilen süs (palmiye, kaya, çalı…).</summary>
    public sealed class PropSpot
    {
        public string Asset;
        public float X, Z, Yaw, Size;
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

        private readonly List<(float ax, float az, float bx, float bz)> _paths = new List<(float, float, float, float)>();
        private readonly int _nx, _nz;
        private readonly bool[] _walk;

        public IslandTerrain(IReadOnlyList<RegionDef> regions, TerrainDef def)
        {
            Regions = regions;
            Def = def ?? new TerrainDef();
            MinX = -Def.Rx - 9f; MaxX = Def.Rx + 9f;
            MinZ = Def.Cz - Def.Rz - 9f; MaxZ = Def.Cz + Def.Rz + 9f;
            _nx = (int)Math.Ceiling((MaxX - MinX) / Cell) + 1;
            _nz = (int)Math.Ceiling((MaxZ - MinZ) / Cell) + 1;
            _walk = new bool[_nx * _nz];
            for (var j = 0; j < _nz; j++)
            for (var i = 0; i < _nx; i++)
                _walk[j * _nx + i] = ComputeWalkable(MinX + i * Cell, MinZ + j * Cell);

            // Patikalar: meydandan her kapıya yol bulmayla (yakından uzağa; sonrakiler var olan patikaları tercih eder → doğal ağ)
            foreach (var r in regions.OrderBy(r => Dist(PlazaX, PlazaZ, r.X, r.Z)))
            {
                var (dx, dz) = Door(r);
                var route = FindPath(PlazaX, PlazaZ, dx, dz);
                if (route.Count == 0) continue;
                var (px, pz) = (PlazaX, PlazaZ);
                foreach (var w in route) { _paths.Add((px, pz, w.x, w.z)); (px, pz) = w; }
            }
        }

        /// <summary>Patika parçaları (çizim ve süs yerleşimi için).</summary>
        public IReadOnlyList<(float ax, float az, float bx, float bz)> Paths => _paths;

        public float PlazaX => Def.Plaza != null && Def.Plaza.Length > 0 ? Def.Plaza[0] : 0f;
        public float PlazaZ => Def.Plaza != null && Def.Plaza.Length > 1 ? Def.Plaza[1] : 0f;

        // ------------------------------------------------------------------ şekil

        /// <summary>Kıyı ölçüsü: &lt; 1 kara, &gt; 1 deniz (kıyı çizgisi gürültüyle dalgalı).</summary>
        public float Coast(float x, float z)
        {
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
        public float PadHeight(RegionDef r) => Math.Max(0.3f, BaseHeight(r.X, r.Z) + HillHeight(r.X, r.Z, out _));

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
            if (h < 0f) return Surface.Water;
            HillHeight(x, z, out var snow);
            if (snow > 0.35f && h > 1.6f) return Surface.Snow;
            if (Slope(x, z) > 0.95f) return Surface.Rock;
            if (PathDistance(x, z) < PathHalfWidth) return Surface.Path;
            if (h < 0.45f || Coast(x, z) > 0.93f) return Surface.Sand;
            return Surface.Grass;
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
            if (h < 0.05f) return false;
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
            while (open.Count > 0 && closed.Count < 40000)
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
        public List<PropSpot> Props()
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
            Scatter("palm", 16, 2.2f, Beach, 2.5f);
            Scatter("palm", 8, 2.0f, Inland, 3f);
            Scatter("p_rock", 10, 1.4f, (x, z) => Beach(x, z) || SurfaceAt(x, z) == Surface.Rock);
            Scatter("p_bush", 14, 1.2f, Inland);
            Scatter("p_flowers", 14, 1.0f, Inland);
            Scatter("p_fence", 4, 1.6f, Inland, 2f);
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
