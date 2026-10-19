using System.Collections.Generic;
using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// Petin çevresinde çim telleri (Pofi/Grass) ve patika ayrıntıları (Pofi/Bits: çakıl, toprak lekesi).
    /// Telefonu yormamak için yalnız ~10 m yarıçapta çizilir; pet 3 m yürüyünce alan yeniden kurulur. Uzakta zemin dokusu yeterli.
    /// Öbekler tek bir birleşik ağda çizilir: GPU instancing derlemede ayıklanıyordu (kodla kurulan malzeme instancing
    /// kullanmadığı için Unity varyantı siliyor → çim hiç görünmüyordu).
    /// Kullanıcı geri bildirimi (19 Ekim 2026): çim ince (kıl gibi), kısa ve sık; ara ara çimsiz açıklıklar; patikada taş, kum, toprak.
    /// </summary>
    public sealed class GrassField : MonoBehaviour
    {
        private const float Radius = 10f, Cell = 0.32f, Rebuild = 3f, BitCell = 0.55f;
        private MapWorld _world;
        private Mesh _clump, _pebble, _blob;
        private Material _mat, _bitsMat;
        private Mesh _field, _bits;
        private Transform _holder, _bitsHolder;
        private Vector2 _center = new Vector2(float.MaxValue, 0f);

        public void Init(MapWorld world)
        {
            _world = world;
            var sh = Shader.Find("Pofi/Grass");
            if (sh == null) { enabled = false; return; }
            _mat = new Material(sh);
            _clump = Clump();
            _field = Layer("GrassMesh", _mat, out _holder);
            var bsh = Shader.Find("Pofi/Bits");
            if (bsh != null)
            {
                _bitsMat = new Material(bsh);
                _pebble = Pebble();
                _blob = Blob();
                _bits = Layer("PathBits", _bitsMat, out _bitsHolder);
            }
        }

        private Mesh Layer(string name, Material mat, out Transform holder)
        {
            var m = new Mesh { name = name, indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 };
            m.MarkDynamic();
            var go = new GameObject(name);
            go.transform.SetParent(transform, false);
            holder = go.transform;
            go.AddComponent<MeshFilter>().sharedMesh = m;
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = mat;
            mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            mr.receiveShadows = true;
            return m;
        }

        /// <summary>Bir öbek: 14 kıl gibi ince tel, rastgele yön ve boy (0,08–0,17 m).</summary>
        private static Mesh Clump()
        {
            var rnd = new System.Random(11);
            var v = new List<Vector3>(); var uv = new List<Vector2>(); var t = new List<int>();
            for (var b = 0; b < 14; b++)
            {
                var a = (float)rnd.NextDouble() * Mathf.PI * 2f;
                var r = Mathf.Sqrt((float)rnd.NextDouble()) * 0.17f;
                var root = new Vector3(Mathf.Cos(a) * r, 0f, Mathf.Sin(a) * r);
                var face = (float)rnd.NextDouble() * Mathf.PI;
                var side = new Vector3(Mathf.Cos(face), 0f, Mathf.Sin(face)) * 0.009f;
                var h = 0.08f + (float)rnd.NextDouble() * 0.09f;
                var lean = new Vector3((float)rnd.NextDouble() - 0.5f, 0f, (float)rnd.NextDouble() - 0.5f) * 0.07f;
                var i0 = v.Count;
                v.Add(root - side); v.Add(root + side); v.Add(root + lean + Vector3.up * h);
                uv.Add(new Vector2(0f, 0f)); uv.Add(new Vector2(1f, 0f)); uv.Add(new Vector2(0.5f, 1f));
                t.Add(i0); t.Add(i0 + 1); t.Add(i0 + 2);
            }
            return Make("GrassClump", v, uv, t);
        }

        /// <summary>Çakıl taşı: basık, düşük çokgenli yuvarlak (8 dilim × 2 kat), yaklaşık 1 birim çap.</summary>
        private static Mesh Pebble()
        {
            var v = new List<Vector3> { new Vector3(0f, 0.32f, 0f) };
            var uv = new List<Vector2> { new Vector2(0f, 1f) };
            var t = new List<int>();
            const int n = 8;
            for (var i = 0; i < n; i++)
            {
                var a = i * Mathf.PI * 2f / n;
                var w = 0.85f + 0.15f * Mathf.Sin(i * 2.3f);
                v.Add(new Vector3(Mathf.Cos(a) * 0.35f * w, 0.24f, Mathf.Sin(a) * 0.35f * w)); uv.Add(new Vector2(0f, 0.8f));
                v.Add(new Vector3(Mathf.Cos(a) * 0.5f * w, 0f, Mathf.Sin(a) * 0.5f * w)); uv.Add(new Vector2(0f, 0.4f));
            }
            for (var i = 0; i < n; i++)
            {
                int a0 = 1 + i * 2, b0 = 1 + ((i + 1) % n) * 2;
                t.Add(0); t.Add(b0); t.Add(a0);
                t.Add(a0); t.Add(b0); t.Add(a0 + 1);
                t.Add(a0 + 1); t.Add(b0); t.Add(b0 + 1);
            }
            return Make("Pebble", v, uv, t);
        }

        /// <summary>Toprak/kum lekesi: zemine yatık düzensiz disk (ortası koyu, kenarı zemine karışır).</summary>
        private static Mesh Blob()
        {
            var v = new List<Vector3> { Vector3.zero };
            var uv = new List<Vector2> { new Vector2(1f, 0f) };   // u: lekeyse 1 (renk kenara doğru solar)
            var t = new List<int>();
            const int n = 10;
            for (var i = 0; i < n; i++)
            {
                var a = i * Mathf.PI * 2f / n;
                var w = 0.75f + 0.25f * Mathf.Sin(i * 1.7f + 0.5f);
                v.Add(new Vector3(Mathf.Cos(a) * 0.5f * w, 0f, Mathf.Sin(a) * 0.5f * w)); uv.Add(new Vector2(1f, 1f));
            }
            for (var i = 0; i < n; i++) { t.Add(0); t.Add(1 + (i + 1) % n); t.Add(1 + i); }
            return Make("Blob", v, uv, t);
        }

        private static Mesh Make(string name, List<Vector3> v, List<Vector2> uv, List<int> t)
        {
            var m = new Mesh { name = name };
            m.SetVertices(v); m.SetUVs(0, uv); m.SetTriangles(t, 0);
            m.RecalculateNormals();
            return m;
        }

        private void Update()
        {
            if (_world == null || _world.Walker == null || _clump == null) return;
            var p = _world.Walker.Position;
            if (Vector2.Distance(p, _center) > Rebuild) Build(p);
        }

        private struct Placed { public Matrix4x4 M; public Color C; public Mesh Mesh; }

        private void Build(Vector2 c)
        {
            _center = c;
            var t = _world.Terrain;
            var grass = new List<Placed>();
            var steps = Mathf.CeilToInt(Radius / Cell);
            for (var j = -steps; j <= steps; j++)
            for (var i = -steps; i <= steps; i++)
            {
                // ızgaraya sabit tohumlu sapma: aynı yerde hep aynı öbek (yeniden kurulunca titremez)
                var gx = Mathf.Floor(c.x / Cell) + i; var gz = Mathf.Floor(c.y / Cell) + j;
                var hsh = Hash(gx, gz);
                var x = (gx + 0.5f + (hsh - 0.5f) * 0.9f) * Cell;
                var z = (gz + 0.5f + (Hash(gz, gx) - 0.5f) * 0.9f) * Cell;
                var dx = x - c.x; var dz = z - c.y;
                if (dx * dx + dz * dz > Radius * Radius) continue;
                var mix = t.MixAt(x, z);
                var g = 1f - Mathf.Max(Mathf.Max(mix.Sand, mix.Path), Mathf.Max(mix.Rock, Mathf.Max(mix.Snow, mix.Water)));
                if (g < 0.6f) continue;
                // çimsiz açıklıklar: iri ölçekli gürültü; kenarında seyrek ve kısa çim
                var bare = Noise(x * 0.42f, z * 0.42f);
                if (bare < 0.24f) continue;
                var edge = Mathf.Clamp01((bare - 0.24f) / 0.14f);
                if (Hash(gx + 3, gz - 5) > edge) continue;
                if (t.BuildingAt(x, z) != null) continue;
                var pos = _world.transform.TransformPoint(new Vector3(x, t.Height(x, z) - 0.01f, z));
                var s = 0.85f + hsh * 0.4f;
                var tall = (0.75f + Hash(gx + 7, gz) * 0.5f) * Mathf.Lerp(0.6f, 1f, edge);
                var tint = 0.86f + Hash(gx - 2, gz + 9) * 0.22f;
                grass.Add(new Placed { M = Matrix4x4.TRS(pos, Quaternion.Euler(0f, hsh * 360f, 0f), new Vector3(s, s * tall, s)), C = new Color(tint, tint, tint * 0.95f, 1f), Mesh = _clump });
            }
            Merge(_field, _holder, grass);
            if (_bits != null) Merge(_bits, _bitsHolder, Bits(c, t));
        }

        /// <summary>Patika ve kumda çakıl taşları ve toprak/kum lekeleri; çim kenarında birkaç taş.</summary>
        private List<Placed> Bits(Vector2 c, Logic.Island.IslandTerrain t)
        {
            var list = new List<Placed>();
            var steps = Mathf.CeilToInt(Radius / BitCell);
            for (var j = -steps; j <= steps; j++)
            for (var i = -steps; i <= steps; i++)
            {
                var gx = Mathf.Floor(c.x / BitCell) + i; var gz = Mathf.Floor(c.y / BitCell) + j;
                var h1 = Hash(gx + 101, gz + 37);
                var x = (gx + 0.5f + (Hash(gx, gz + 51) - 0.5f) * 0.9f) * BitCell;
                var z = (gz + 0.5f + (Hash(gz + 13, gx) - 0.5f) * 0.9f) * BitCell;
                var dx = x - c.x; var dz = z - c.y;
                if (dx * dx + dz * dz > Radius * Radius) continue;
                var mix = t.MixAt(x, z);
                if (mix.Water > 0.3f || mix.Snow > 0.5f || t.BuildingAt(x, z) != null) continue;
                var path = mix.Path; var sand = mix.Sand;
                var y = t.Height(x, z);
                var yaw = Quaternion.Euler(0f, h1 * 360f, 0f);
                if (path > 0.45f && h1 < 0.5f)
                {
                    // toprak birikintisi (koyu kahve) ya da kum (açık) lekesi
                    var dark = Hash(gx - 9, gz + 4) < 0.6f;
                    var col = dark ? new Color(0.45f, 0.33f, 0.22f, 0.55f) : new Color(0.86f, 0.76f, 0.58f, 0.5f);
                    var r = 0.25f + Hash(gx + 5, gz + 5) * 0.35f;
                    list.Add(new Placed { M = Matrix4x4.TRS(Pos(x, y + 0.012f, z), yaw, new Vector3(r, 1f, r * (0.6f + h1))), C = col, Mesh = _blob });
                }
                var pebbleChance = path > 0.45f ? 0.55f : sand > 0.5f ? 0.12f : (path > 0.15f || mix.Rock > 0.3f) ? 0.35f : 0.03f;
                var h2 = Hash(gx - 31, gz + 77);
                if (h2 < pebbleChance)
                {
                    // 1–3 çakıl kümesi: gri, bej, kahve tonları
                    var n = 1 + (int)(Hash(gx + 2, gz + 8) * 3f);
                    for (var k = 0; k < n; k++)
                    {
                        var ox = (Hash(gx + k * 7, gz) - 0.5f) * 0.3f; var oz = (Hash(gx, gz + k * 11) - 0.5f) * 0.3f;
                        var sz = 0.04f + Hash(gx + k, gz - k) * 0.08f;
                        var tone = Hash(gz + k * 3, gx - k);
                        var col = tone < 0.5f ? Color.Lerp(new Color(0.62f, 0.62f, 0.6f), new Color(0.78f, 0.77f, 0.73f), tone * 2f)
                            : Color.Lerp(new Color(0.72f, 0.62f, 0.5f), new Color(0.55f, 0.45f, 0.36f), (tone - 0.5f) * 2f);
                        list.Add(new Placed { M = Matrix4x4.TRS(Pos(x + ox, t.Height(x + ox, z + oz) - 0.005f, z + oz), yaw * Quaternion.Euler(0f, k * 70f, 0f),
                            new Vector3(sz, sz * (0.7f + tone * 0.6f), sz * (0.8f + h2))), C = col, Mesh = _pebble });
                    }
                }
            }
            return list;
        }

        private Vector3 Pos(float x, float y, float z) => _world.transform.TransformPoint(new Vector3(x, y, z));

        /// <summary>Yerleştirilen parçaları tek ağda birleştirir (dünya → katman nesnesinin yerel uzayı); renk köşe rengine yazılır.</summary>
        private static void Merge(Mesh into, Transform holder, List<Placed> list)
        {
            var verts = new List<Vector3>(); var uvs = new List<Vector2>(); var cols = new List<Color>(); var tris = new List<int>();
            var toLocal = holder.worldToLocalMatrix;
            Mesh last = null; Vector3[] src = null; Vector2[] suv = null; int[] stri = null;
            foreach (var p in list)
            {
                if (p.Mesh != last) { last = p.Mesh; src = last.vertices; suv = last.uv; stri = last.triangles; }
                var mm = toLocal * p.M;
                var b = verts.Count;
                for (var i = 0; i < src.Length; i++) { verts.Add(mm.MultiplyPoint3x4(src[i])); uvs.Add(suv[i]); cols.Add(p.C); }
                for (var i = 0; i < stri.Length; i++) tris.Add(b + stri[i]);
            }
            into.Clear();
            into.SetVertices(verts); into.SetUVs(0, uvs); into.SetColors(cols); into.SetTriangles(tris, 0);
            into.RecalculateNormals();
            into.RecalculateBounds();
        }

        /// <summary>Yumuşak değer gürültüsü (0..1): ızgara köşelerindeki sabit tohumlu değerlerin pürüzsüz karışımı.</summary>
        private static float Noise(float x, float z)
        {
            var ix = Mathf.Floor(x); var iz = Mathf.Floor(z);
            var fx = x - ix; var fz = z - iz;
            fx = fx * fx * (3f - 2f * fx); fz = fz * fz * (3f - 2f * fz);
            var a = Mathf.Lerp(Hash(ix + 500, iz), Hash(ix + 501, iz), fx);
            var b = Mathf.Lerp(Hash(ix + 500, iz + 1), Hash(ix + 501, iz + 1), fx);
            return Mathf.Lerp(a, b, fz);
        }

        private static float Hash(float x, float z)
        {
            unchecked
            {
                var h = (uint)((int)x * 73856093 ^ (int)z * 19349663);
                h = (h ^ (h >> 13)) * 1274126177u;
                return (h & 0xFFFF) / 65535f;
            }
        }

        private void OnDestroy()
        {
            foreach (var o in new Object[] { _mat, _bitsMat, _clump, _pebble, _blob, _field, _bits })
                if (o != null) Destroy(o);
        }
    }
}
