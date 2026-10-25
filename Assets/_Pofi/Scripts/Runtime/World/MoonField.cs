using System.Collections.Generic;
using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// Ay zemininin yakın ayrıntısı (Gezegen Koşusu; kullanıcı, 25 Ekim 2026: "Ay zeminine ekstra zengin detaylar ekle, yoğunluk ada
    /// zemininden az olmasın"). Adadaki <see cref="GrassField"/> ile aynı yöntem: hücre ızgarasında sabit tohumlu dağıtım, parçalar tek
    /// birleşik ağda (Pofi/Bits, köşe rengi). Ada çimenin yerine Ay'da: regolit çakılları (kümeler), köşeli kayalar, küçük kraterler
    /// (kabarık kenar + koyu çukur), açık/koyu toz lekeleri, Ay arabası izleri ve mor/camgöbeği kristal kırıntıları.
    /// Yolun iki yanında 10 m'lik dilimler: yakın kuşak |x| 4,2–10 m sık (0,38 m hücre), orta kuşak 10–24 m seyrek ve iri (0,85 m).
    /// Dilim, koşucu yaklaşınca bir kez kurulur (karede en çok bir), geride kalınca havuza döner. Yükseklik zemin çarpıştırıcısından
    /// (katman <see cref="GroundLayer"/>); bulunamazsa <see cref="FlatY"/>.
    /// </summary>
    public sealed class MoonField : MonoBehaviour
    {
        public const int GroundLayer = 30;
        public const float Slice = 10f, AheadM = 80f, BehindM = 12f, FlatY = -0.08f;
        private const float NearCell = 0.38f, MidCell = 0.85f, NearFrom = 4.2f, NearTo = 10f, MidTo = 24f;

        private Material _mat;
        private Mesh _pebble, _rock, _rim, _blob, _shard, _track;
        private readonly Dictionary<int, GameObject> _live = new Dictionary<int, GameObject>();
        private readonly Stack<GameObject> _free = new Stack<GameObject>();
        private readonly List<int> _drop = new List<int>();
        private float _goal = 1e9f;
        /// <summary>Krater köprüsü aralığı (z): zemin bulunamazsa (krater çukuru) parça konmaz.</summary>
        public float CraterFrom = -1f, CraterTo = -1f;

        public void Init(float goal)
        {
            _goal = goal;
            var sh = Shader.Find("Pofi/Bits");
            if (sh == null) { enabled = false; return; }
            _mat = new Material(sh);
            _pebble = Pebble(); _rock = Rock(); _rim = CraterRim(); _blob = Blob(); _shard = Shard(); _track = Track();
        }

        /// <summary>Yeni koşu: tüm dilimler havuza.</summary>
        public void Clear(float goal)
        {
            _goal = goal;
            foreach (var kv in _live) { kv.Value.SetActive(false); _free.Push(kv.Value); }
            _live.Clear();
        }

        /// <summary>Koşucunun Z'sine göre önde eksik dilimi kur (karede en çok bir), geride kalanı havuza döndür.</summary>
        public void Tick(float z)
        {
            if (_mat == null) return;
            _drop.Clear();
            foreach (var kv in _live) if ((kv.Key + 1) * Slice < z - BehindM) _drop.Add(kv.Key);
            foreach (var k in _drop) { _live[k].SetActive(false); _free.Push(_live[k]); _live.Remove(k); }
            var from = Mathf.FloorToInt((z - BehindM) / Slice);
            var to = Mathf.FloorToInt(Mathf.Min(z + AheadM, _goal + 30f) / Slice);
            for (var i = Mathf.Max(-1, from); i <= to; i++)
            {
                if (_live.ContainsKey(i)) continue;
                _live[i] = Build(i);
                return;   // karede bir dilim: kare düşmesin
            }
        }

        private struct Placed { public Matrix4x4 M; public Color C; public Mesh Mesh; }

        private GameObject Build(int slice)
        {
            var go = _free.Count > 0 ? _free.Pop() : NewHolder();
            go.SetActive(true);
            go.name = "moon_slice_" + slice;
            var list = new List<Placed>(1600);
            var z0 = slice * Slice;
            for (var side = -1; side <= 1; side += 2)
            {
                Band(list, side, z0, NearFrom, NearTo, NearCell, true);
                Band(list, side, z0, NearTo, MidTo, MidCell, false);
                Tracks(list, side, slice, z0);
            }
            Merge(go.GetComponent<MeshFilter>().sharedMesh, go.transform, list);
            return go;
        }

        private GameObject NewHolder()
        {
            var go = new GameObject("moon_slice");
            go.transform.SetParent(transform, false);
            var m = new Mesh { name = "MoonBits", indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 };
            go.AddComponent<MeshFilter>().sharedMesh = m;
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = _mat;
            mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            mr.receiveShadows = true;
            return go;
        }

        /// <summary>Bir kuşak: her hücrede sabit tohumlu karar (aynı yer hep aynı görünür).</summary>
        private void Band(List<Placed> list, int side, float z0, float xFrom, float xTo, float cell, bool near)
        {
            var nx = Mathf.CeilToInt((xTo - xFrom) / cell);
            var nz = Mathf.CeilToInt(Slice / cell);
            for (var j = 0; j < nz; j++)
            for (var i = 0; i < nx; i++)
            {
                var gx = side * 1000 + i + (near ? 0 : 500); var gz = Mathf.FloorToInt(z0 / cell) + j;
                var h = Hash(gx, gz);
                var x = side * (xFrom + (i + 0.5f + (Hash(gx + 7, gz) - 0.5f) * 0.9f) * cell);
                var z = z0 + (j + 0.5f + (Hash(gx, gz + 7) - 0.5f) * 0.9f) * cell;
                var yaw = Quaternion.Euler(0f, h * 360f, 0f);
                // iri ölçekli seyreklik: açık "taşsız" düzlükler ile taşlı alanlar (adadaki çimsiz açıklıklar gibi)
                var rich = GrassField.Noise(x * 0.18f + 40f, z * 0.18f);
                var r1 = Hash(gx + 13, gz - 5);
                if (!Ground(x, z, out var y, out var nrm)) continue;
                var tilt = Quaternion.FromToRotation(Vector3.up, nrm);
                // toz lekesi: açık (yükselti) ve koyu (deniz) tonları — zemin tek renk kalmasın
                if (r1 < (near ? 0.10f : 0.16f))
                {
                    var dark = Hash(gx - 9, gz + 4) < 0.55f;
                    var col = dark ? new Color(0.36f, 0.34f, 0.5f, 0.42f) : new Color(0.86f, 0.84f, 0.95f, 0.38f);
                    var r = (near ? 0.35f : 0.8f) + Hash(gx + 5, gz + 5) * (near ? 0.6f : 1.4f);
                    list.Add(new Placed { M = Matrix4x4.TRS(new Vector3(x, y + 0.012f, z), tilt * yaw, new Vector3(r, 1f, r * (0.55f + h))), C = col.linear, Mesh = _blob });
                }
                // küçük krater: kabarık açık kenar + koyu çukur
                var r2 = Hash(gx - 31, gz + 77);
                if (r2 < (near ? 0.014f : 0.035f))
                {
                    var d = near ? 0.5f + h * 1.1f : 1.0f + h * 2.4f;
                    var rimTone = 0.78f + Hash(gx + 3, gz + 3) * 0.14f;
                    list.Add(new Placed { M = Matrix4x4.TRS(new Vector3(x, y - 0.01f, z), tilt * yaw, new Vector3(d, d * 0.9f, d)), C = new Color(rimTone, rimTone * 0.97f, rimTone + 0.08f, 1f).linear, Mesh = _rim });
                    list.Add(new Placed { M = Matrix4x4.TRS(new Vector3(x, y + 0.008f, z), tilt * yaw, new Vector3(d * 0.75f, 1f, d * 0.75f)), C = new Color(0.3f, 0.28f, 0.45f, 0.62f).linear, Mesh = _blob });
                    continue;
                }
                // regolit çakılı kümeleri (adadaki çakıllardan sık): gri-leylak, sıcak ve serin tonlar
                var pebbleChance = (near ? 0.5f : 0.22f) * Mathf.Lerp(0.35f, 1.2f, rich);
                var r3 = Hash(gx + 101, gz + 37);
                if (r3 < pebbleChance)
                {
                    var n = 1 + (int)(Hash(gx + 2, gz + 8) * (near ? 4f : 3f));
                    for (var k = 0; k < n; k++)
                    {
                        var ox = (Hash(gx + k * 7, gz) - 0.5f) * cell * 0.8f; var oz = (Hash(gx, gz + k * 11) - 0.5f) * cell * 0.8f;
                        var sz = (near ? 0.04f : 0.07f) + Hash(gx + k, gz - k) * (near ? 0.1f : 0.16f);
                        var tone = Hash(gz + k * 3, gx - k);
                        var col = tone < 0.6f ? Color.Lerp(new Color(0.56f, 0.54f, 0.68f), new Color(0.78f, 0.76f, 0.86f), tone / 0.6f)
                            : Color.Lerp(new Color(0.72f, 0.66f, 0.62f), new Color(0.5f, 0.46f, 0.52f), (tone - 0.6f) / 0.4f);
                        var px = x + ox; var pz = z + oz;
                        list.Add(new Placed { M = Matrix4x4.TRS(new Vector3(px, y - 0.008f, pz), tilt * yaw * Quaternion.Euler(0f, k * 70f, 0f),
                            new Vector3(sz, sz * (0.6f + tone * 0.6f), sz * (0.8f + r3))), C = col.linear, Mesh = _pebble });
                    }
                }
                // köşeli kaya (orta kuşakta daha çok ve iri)
                var r4 = Hash(gx + 57, gz - 91);
                if (r4 < (near ? 0.025f : 0.12f) * Mathf.Lerp(0.5f, 1.3f, rich))
                {
                    var sz = near ? 0.16f + h * 0.22f : 0.25f + h * 0.55f;
                    var tone = Hash(gx - 4, gz - 4);
                    var col = Color.Lerp(new Color(0.5f, 0.48f, 0.62f), new Color(0.7f, 0.68f, 0.8f), tone);
                    list.Add(new Placed { M = Matrix4x4.TRS(new Vector3(x, y - sz * 0.15f, z), tilt * yaw * Quaternion.Euler(r4 * 30f, 0f, h * 25f),
                        new Vector3(sz, sz * (0.55f + tone * 0.5f), sz * (0.8f + r1 * 0.5f))), C = col.linear, Mesh = _rock });
                }
                // kristal kırıntıları (adadaki çiçek öbeklerinin yerine renk vurgusu): seyrek, 3–5'li küme
                var r5 = Hash(gx - 77, gz + 13);
                if (r5 < (near ? 0.012f : 0.02f) * Mathf.Lerp(0.3f, 1.5f, 1f - rich))
                {
                    var cyan = Hash(gx + 23, gz + 29) < 0.4f;
                    var baseC = cyan ? new Color(0.36f, 0.86f, 0.95f) : new Color(0.68f, 0.5f, 1f);
                    var n = 3 + (int)(Hash(gx + 1, gz + 1) * 3f);
                    for (var k = 0; k < n; k++)
                    {
                        var ox = (Hash(gx + k * 5, gz + 3) - 0.5f) * 0.35f; var oz = (Hash(gx + 3, gz + k * 5) - 0.5f) * 0.35f;
                        var sz = (near ? 0.07f : 0.12f) + Hash(gx + k * 9, gz - k) * (near ? 0.12f : 0.2f);
                        var lean = Quaternion.Euler((Hash(gx + k, gz) - 0.5f) * 50f, k * 73f, (Hash(gx, gz + k) - 0.5f) * 50f);
                        var c = Color.Lerp(baseC, Color.white, Hash(gx - k, gz + k) * 0.25f);
                        list.Add(new Placed { M = Matrix4x4.TRS(new Vector3(x + ox, y - 0.02f, z + oz), tilt * lean, new Vector3(sz * 0.5f, sz, sz * 0.5f)), C = c.linear, Mesh = _shard });
                    }
                }
            }
        }

        /// <summary>Ay arabası izleri: yolun yanında paralel iki şerit, ara ara kesilir ve hafif kıvrılır.</summary>
        private void Tracks(List<Placed> list, int side, int slice, float z0)
        {
            var lane = Mathf.FloorToInt(z0 / 60f);   // iz 60 m boyunca aynı hatta
            if (Hash(side * 31 + lane, 7) < 0.35f) return;
            var bx = side * (6.2f + Hash(side * 17 + lane, 3) * 3.2f);
            for (var s = 0; s < 5; s++)
            {
                var z = z0 + s * 2f + 1f;
                if (Hash(slice * 5 + s, side + 50) < 0.12f) continue;   // ara ara kesilir
                var wig = Mathf.Sin(z * 0.11f + lane) * 0.5f;
                for (var w = -1; w <= 1; w += 2)
                {
                    var x = bx + wig + w * 0.62f;
                    if (!Ground(x, z, out var y, out var nrm)) continue;
                    list.Add(new Placed { M = Matrix4x4.TRS(new Vector3(x, y + 0.01f, z), Quaternion.FromToRotation(Vector3.up, nrm) * Quaternion.Euler(0f, Mathf.Cos(z * 0.11f + lane) * 3f, 0f), new Vector3(0.32f, 1f, 2.1f)),
                        C = new Color(0.38f, 0.36f, 0.52f, 0.5f).linear, Mesh = _track });
                }
            }
        }

        /// <summary>Zemin yüksekliği ve normali (yerel koordinat): çarpıştırıcı katmanına aşağı ışın; yoksa düz Ay zemini.</summary>
        private bool Ground(float x, float z, out float y, out Vector3 normal)
        {
            var origin = transform.TransformPoint(new Vector3(x, 30f, z));
            if (Physics.Raycast(origin, Vector3.down, out var hit, 80f, 1 << GroundLayer, QueryTriggerInteraction.Ignore))
            {
                y = transform.InverseTransformPoint(hit.point).y;
                normal = transform.InverseTransformDirection(hit.normal);
                if (normal.y < 0.55f) return false;   // dik yamaç: taş tutunmaz
                return true;
            }
            y = FlatY; normal = Vector3.up;
            return !(z > CraterFrom - 1f && z < CraterTo + 1f);   // krater üstünde düz zemin yok
        }

        // ------------------------------------------------------------------ ağlar (≈1 birim)

        private static Mesh Pebble()
        {
            var v = new List<Vector3> { new Vector3(0f, 0.32f, 0f) };
            var uv = new List<Vector2> { Vector2.zero };
            var t = new List<int>();
            const int n = 7;
            for (var i = 0; i < n; i++)
            {
                var a = i * Mathf.PI * 2f / n;
                var w = 0.82f + 0.18f * Mathf.Sin(i * 2.3f);
                v.Add(new Vector3(Mathf.Cos(a) * 0.36f * w, 0.24f, Mathf.Sin(a) * 0.36f * w)); uv.Add(Vector2.zero);
                v.Add(new Vector3(Mathf.Cos(a) * 0.5f * w, 0f, Mathf.Sin(a) * 0.5f * w)); uv.Add(Vector2.zero);
            }
            for (var i = 0; i < n; i++)
            {
                int a0 = 1 + i * 2, b0 = 1 + ((i + 1) % n) * 2;
                t.Add(0); t.Add(b0); t.Add(a0);
                t.Add(a0); t.Add(b0); t.Add(a0 + 1);
                t.Add(a0 + 1); t.Add(b0); t.Add(b0 + 1);
            }
            return Make("MoonPebble", v, uv, t);
        }

        /// <summary>Köşeli kaya: 5 kenarlı, eğik üst yüzlü düşük çokgen blok (sert ışık kırılımı).</summary>
        private static Mesh Rock()
        {
            var v = new List<Vector3>(); var uv = new List<Vector2>(); var t = new List<int>();
            const int n = 5;
            var top = new Vector3[n]; var bot = new Vector3[n];
            for (var i = 0; i < n; i++)
            {
                var a = i * Mathf.PI * 2f / n + 0.3f;
                var w = 0.8f + 0.2f * Mathf.Sin(i * 3.1f);
                bot[i] = new Vector3(Mathf.Cos(a) * 0.5f * w, 0f, Mathf.Sin(a) * 0.5f * w);
                top[i] = new Vector3(Mathf.Cos(a) * 0.32f * w, 0.55f + 0.18f * Mathf.Cos(a * 1.7f), Mathf.Sin(a) * 0.32f * w);
            }
            var apex = new Vector3(0.06f, 0.78f, -0.04f);
            for (var i = 0; i < n; i++)
            {
                var j = (i + 1) % n;
                Quad(v, uv, t, bot[i], bot[j], top[j], top[i]);
                Tri(v, uv, t, top[i], top[j], apex);
            }
            return Make("MoonRock", v, uv, t);
        }

        /// <summary>Krater kenarı: içte ve dışta zemine inen, ortada kabarık halka (yarıçap 0,5).</summary>
        private static Mesh CraterRim()
        {
            var v = new List<Vector3>(); var uv = new List<Vector2>(); var t = new List<int>();
            const int n = 16;
            for (var i = 0; i < n; i++)
            {
                var a = i * Mathf.PI * 2f / n;
                var c = new Vector3(Mathf.Cos(a), 0f, Mathf.Sin(a));
                v.Add(c * 0.34f + Vector3.down * 0.02f); v.Add(c * 0.42f + Vector3.up * 0.07f); v.Add(c * 0.5f + Vector3.down * 0.01f);
                uv.Add(Vector2.zero); uv.Add(Vector2.zero); uv.Add(Vector2.zero);
            }
            for (var i = 0; i < n; i++)
            {
                int a = i * 3, b = ((i + 1) % n) * 3;
                t.Add(a); t.Add(a + 1); t.Add(b); t.Add(b); t.Add(a + 1); t.Add(b + 1);
                t.Add(a + 1); t.Add(a + 2); t.Add(b + 1); t.Add(b + 1); t.Add(a + 2); t.Add(b + 2);
            }
            return Make("MoonRim", v, uv, t);
        }

        /// <summary>Leke: zemine yatık düzensiz disk, kenara doğru solar (Pofi/Bits uv.x = 1).</summary>
        private static Mesh Blob()
        {
            var v = new List<Vector3> { Vector3.zero };
            var uv = new List<Vector2> { new Vector2(1f, 0f) };
            var t = new List<int>();
            const int n = 10;
            for (var i = 0; i < n; i++)
            {
                var a = i * Mathf.PI * 2f / n;
                var w = 0.75f + 0.25f * Mathf.Sin(i * 1.7f + 0.5f);
                v.Add(new Vector3(Mathf.Cos(a) * 0.5f * w, 0f, Mathf.Sin(a) * 0.5f * w)); uv.Add(new Vector2(1f, 1f));
            }
            for (var i = 0; i < n; i++) { t.Add(0); t.Add(1 + (i + 1) % n); t.Add(1 + i); }
            return Make("MoonBlob", v, uv, t);
        }

        /// <summary>İz şeridi: 1 × 1 dikdörtgen, enine kenarlara doğru solar; boyuna tırtıllı (teker izi).</summary>
        private static Mesh Track()
        {
            var v = new List<Vector3>(); var uv = new List<Vector2>(); var t = new List<int>();
            const int n = 8;
            for (var i = 0; i <= n; i++)
            {
                var z = -0.5f + i / (float)n;
                var tread = i % 2 == 0 ? 0.5f : 0.38f;
                v.Add(new Vector3(-tread, 0f, z)); uv.Add(new Vector2(1f, 1f));
                v.Add(new Vector3(0f, 0f, z)); uv.Add(new Vector2(1f, 0.15f));
                v.Add(new Vector3(tread, 0f, z)); uv.Add(new Vector2(1f, 1f));
            }
            for (var i = 0; i < n; i++)
            {
                int a = i * 3, b = (i + 1) * 3;
                t.Add(a); t.Add(b); t.Add(a + 1); t.Add(a + 1); t.Add(b); t.Add(b + 1);
                t.Add(a + 1); t.Add(b + 1); t.Add(a + 2); t.Add(a + 2); t.Add(b + 1); t.Add(b + 2);
            }
            return Make("MoonTrack", v, uv, t);
        }

        /// <summary>Kristal kırıntısı: altıgen gövde + sivri uç (boy 1).</summary>
        private static Mesh Shard()
        {
            var v = new List<Vector3>(); var uv = new List<Vector2>(); var t = new List<int>();
            const int n = 6;
            var ring0 = new Vector3[n]; var ring1 = new Vector3[n];
            for (var i = 0; i < n; i++)
            {
                var a = i * Mathf.PI * 2f / n;
                ring0[i] = new Vector3(Mathf.Cos(a) * 0.45f, 0f, Mathf.Sin(a) * 0.45f);
                ring1[i] = new Vector3(Mathf.Cos(a) * 0.4f, 0.68f, Mathf.Sin(a) * 0.4f);
            }
            var tip = new Vector3(0f, 1f, 0f);
            for (var i = 0; i < n; i++)
            {
                var j = (i + 1) % n;
                Quad(v, uv, t, ring0[i], ring0[j], ring1[j], ring1[i]);
                Tri(v, uv, t, ring1[i], ring1[j], tip);
            }
            return Make("MoonShard", v, uv, t);
        }

        private static void Quad(List<Vector3> v, List<Vector2> uv, List<int> t, Vector3 a, Vector3 b, Vector3 c, Vector3 d)
        {
            var i = v.Count;
            v.Add(a); v.Add(b); v.Add(c); v.Add(d);
            for (var k = 0; k < 4; k++) uv.Add(Vector2.zero);
            t.Add(i); t.Add(i + 2); t.Add(i + 1); t.Add(i); t.Add(i + 3); t.Add(i + 2);
        }

        private static void Tri(List<Vector3> v, List<Vector2> uv, List<int> t, Vector3 a, Vector3 b, Vector3 c)
        {
            var i = v.Count;
            v.Add(a); v.Add(b); v.Add(c);
            for (var k = 0; k < 3; k++) uv.Add(Vector2.zero);
            t.Add(i); t.Add(i + 2); t.Add(i + 1);
        }

        private static Mesh Make(string name, List<Vector3> v, List<Vector2> uv, List<int> t)
        {
            var m = new Mesh { name = name };
            m.SetVertices(v); m.SetUVs(0, uv); m.SetTriangles(t, 0);
            m.RecalculateNormals();
            return m;
        }

        private static readonly Dictionary<Mesh, (Vector3[], Vector2[], int[])> Cache = new Dictionary<Mesh, (Vector3[], Vector2[], int[])>();

        /// <summary>Parçaları tek ağda birleştirir (yerel uzay); renk köşe rengine.</summary>
        private static void Merge(Mesh into, Transform holder, List<Placed> list)
        {
            var verts = new List<Vector3>(list.Count * 12); var uvs = new List<Vector2>(list.Count * 12);
            var cols = new List<Color>(list.Count * 12); var tris = new List<int>(list.Count * 30);
            var toLocal = holder.worldToLocalMatrix * holder.parent.localToWorldMatrix;   // dilimler dünyanın (koşu kökünün) yerel uzayında yerleşir
            Mesh last = null; Vector3[] src = null; Vector2[] suv = null; int[] stri = null;
            foreach (var p in list)
            {
                if (p.Mesh != last)
                {
                    last = p.Mesh;
                    if (!Cache.TryGetValue(last, out var arr)) Cache[last] = arr = (last.vertices, last.uv, last.triangles);
                    (src, suv, stri) = arr;
                }
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
            Cache.Clear();
            foreach (var o in new Object[] { _mat, _pebble, _rock, _rim, _blob, _shard, _track }) if (o != null) Destroy(o);
            foreach (var kv in _live) if (kv.Value != null) Destroy(kv.Value.GetComponent<MeshFilter>().sharedMesh);
            foreach (var g in _free) if (g != null) Destroy(g.GetComponent<MeshFilter>().sharedMesh);
        }
    }
}
