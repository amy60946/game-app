using System.Collections.Generic;
using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// Büyük ada (v6) süsleri 24 m'lik hücrelere ayrılır; kameradan uzak hücreler kapatılır (iPhone üçgen/çizim bütçesi).
    /// Kuşbakışında yarıçap büyür (bütün ada görünür, uzaktan bakıldığı için ayrıntı az fark edilir).
    /// </summary>
    public sealed class PropCuller : MonoBehaviour
    {
        public const float CellSize = 24f;
        /// <summary>Görünür yarıçap (m). MapScreen kuşbakışında büyütür.</summary>
        public static float Radius = 95f;
        private readonly Dictionary<long, Transform> _cells = new Dictionary<long, Transform>();
        private float _t;

        public Transform Cell(Transform parent, float x, float z)
        {
            var ci = Mathf.FloorToInt(x / CellSize); var cj = Mathf.FloorToInt(z / CellSize);
            var key = ((long)ci << 32) ^ (uint)cj;
            if (_cells.TryGetValue(key, out var c)) return c;
            c = new GameObject("cell_" + ci + "_" + cj).transform;
            c.SetParent(parent, false);
            c.localPosition = new Vector3((ci + 0.5f) * CellSize, 0f, (cj + 0.5f) * CellSize);
            _cells[key] = c;
            return c;
        }

        private void Update()
        {
            _t -= Time.unscaledDeltaTime;
            if (_t > 0f) return;
            _t = 0.25f;
            var cam = Camera.main;
            if (cam == null) return;
            var p = transform.InverseTransformPoint(cam.transform.position);
            var f = transform.InverseTransformDirection(cam.transform.forward);
            var look = new Vector2(p.x + f.x * 30f, p.z + f.z * 30f);   // önü (bakılan yer) merkez: arkadaki hücreler daha erken kapanır
            var r2 = Radius * Radius;
            foreach (var c in _cells.Values)
            {
                var lp = c.localPosition;
                var on = (new Vector2(lp.x, lp.z) - look).sqrMagnitude < r2;
                if (c.gameObject.activeSelf != on) c.gameObject.SetActive(on);
            }
        }
    }

    /// <summary>
    /// Kamera önünü açık tutar (geri bildirim 11, 22 Ekim 2026: patikada ağaçlar görüşü kapatıyordu): kamerayla pet arasındaki
    /// çizgiye giren ağaç/iri kaya titreşimli soldurmayla (Pofi/Toon _Fade) yumuşakça kaybolur, çizgiden çıkınca geri gelir.
    /// Soldurma yalnız o anda değişen nesnelerde MaterialPropertyBlock ile; tam görünürken blok kaldırılır (SRP toplu çizimi bozulmaz).
    /// </summary>
    public sealed class CameraClear : MonoBehaviour
    {
        private sealed class Entry { public Renderer[] R; public Vector2 C; public float Rad, Y0, Y1, Fade = 1f, Target = 1f; }
        private const float Cell = 8f;
        private readonly Dictionary<long, List<Entry>> _grid = new Dictionary<long, List<Entry>>();
        private readonly List<Entry> _active = new List<Entry>();
        private MapWorld _world;
        private MaterialPropertyBlock _mpb;
        private static readonly int FadeId = Shader.PropertyToID("_Fade");

        public void Init(MapWorld world) { _world = world; _mpb = new MaterialPropertyBlock(); }

        public void Add(Transform t)
        {
            var rs = t.GetComponentsInChildren<Renderer>(true);
            if (rs.Length == 0) return;
            var b = rs[0].bounds;
            for (var i = 1; i < rs.Length; i++) b.Encapsulate(rs[i].bounds);
            var e = new Entry { R = rs, C = new Vector2(b.center.x, b.center.z), Rad = Mathf.Max(b.extents.x, b.extents.z) * 0.8f, Y0 = b.min.y, Y1 = b.max.y };
            var key = Key(Mathf.FloorToInt(e.C.x / Cell), Mathf.FloorToInt(e.C.y / Cell));
            if (!_grid.TryGetValue(key, out var l)) _grid[key] = l = new List<Entry>();
            l.Add(e);
        }

        private static long Key(int i, int j) => ((long)i << 32) ^ (uint)j;

        private void LateUpdate()
        {
            var cam = Camera.main;
            if (cam == null || _world == null || _world.Walker == null) return;
            var a = cam.transform.position;
            var b = _world.Walker.transform.position + Vector3.up * 0.9f;
            // çizgi yakınındaki hücreler: hedefe yeni giren nesneler aday
            var mn = Vector2.Min(new Vector2(a.x, a.z), new Vector2(b.x, b.z)) - Vector2.one * 6f;
            var mx = Vector2.Max(new Vector2(a.x, a.z), new Vector2(b.x, b.z)) + Vector2.one * 6f;
            foreach (var e in _active) e.Target = 1f;
            var near = (a - b).sqrMagnitude < 30f * 30f;                       // kuşbakışında (uzak kamera) soldurma yok
            if (near)
            for (var i = Mathf.FloorToInt(mn.x / Cell); i <= Mathf.FloorToInt(mx.x / Cell); i++)
            for (var j = Mathf.FloorToInt(mn.y / Cell); j <= Mathf.FloorToInt(mx.y / Cell); j++)
            {
                if (!_grid.TryGetValue(Key(i, j), out var l)) continue;
                foreach (var e in l)
                {
                    if (!e.R[0].gameObject.activeInHierarchy) continue;
                    if (!Blocks(e, a, b)) continue;
                    e.Target = 0.15f;
                    if (!_active.Contains(e)) _active.Add(e);
                }
            }
            var k = 1f - Mathf.Exp(-9f * Time.deltaTime);
            for (var n = _active.Count - 1; n >= 0; n--)
            {
                var e = _active[n];
                e.Fade = Mathf.Abs(e.Fade - e.Target) < 0.01f ? e.Target : Mathf.Lerp(e.Fade, e.Target, k);
                if (e.Fade >= 0.999f)
                {
                    foreach (var r in e.R) if (r != null) r.SetPropertyBlock(null);
                    _active.RemoveAt(n);
                    continue;
                }
                _mpb.SetFloat(FadeId, e.Fade);
                foreach (var r in e.R) if (r != null) r.SetPropertyBlock(_mpb);
            }
        }

        /// <summary>Kamera–pet doğru parçası nesnenin dikey silindirinden (taban–tepe, yarıçap) geçiyor mu?</summary>
        private static bool Blocks(Entry e, Vector3 a, Vector3 b)
        {
            var ab = new Vector2(b.x - a.x, b.z - a.z); var l2 = ab.sqrMagnitude;
            var t = l2 < 1e-4f ? 0f : Mathf.Clamp01(Vector2.Dot(e.C - new Vector2(a.x, a.z), ab) / l2);
            if (t > 0.92f) return false;                                   // petin hemen yanındaki (arkasındaki) nesne kalır
            var p = new Vector2(a.x, a.z) + ab * t;
            if ((p - e.C).sqrMagnitude > (e.Rad + 0.35f) * (e.Rad + 0.35f)) return false;
            var y = Mathf.Lerp(a.y, b.y, t);
            return y > e.Y0 + 0.2f && y < e.Y1;
        }
    }

    /// <summary>Kıyı yengeci (madde 10, kullanıcı): pet yaklaşınca yan yan denize koşar ve kaybolur; pet uzaklaşınca bir süre sonra yerine döner.</summary>
    public sealed class CrabFlee : MonoBehaviour
    {
        private MapWorld _world;
        private Vector3 _home;
        private Vector2 _dir;
        private float _hidden, _scuttle;
        private enum State { Idle, Flee, Gone }
        private State _state;

        public void Init(MapWorld world) { _world = world; _home = transform.localPosition; }

        private void Update()
        {
            if (_world == null || _world.Walker == null) return;
            var parent = transform.parent;
            var wpos = parent != null ? parent.localPosition + transform.localPosition : transform.localPosition;
            var me = new Vector2(wpos.x, wpos.z);
            var pet = _world.Walker.Position;
            var dist = Vector2.Distance(me, pet);
            switch (_state)
            {
                case State.Idle:
                    // ara sıra yerinde kıpırdar
                    _scuttle += Time.deltaTime;
                    transform.localRotation = Quaternion.Euler(0f, transform.localEulerAngles.y + Mathf.Sin(_scuttle * 3f) * 0.3f, 0f);
                    if (dist < 3.5f)
                    {
                        // denize doğru: araziyi alçalan yöne, petten uzağa
                        var away = (me - pet).normalized;
                        var e = 1.5f;
                        var grad = new Vector2(_world.Terrain.Height(me.x + e, me.y) - _world.Terrain.Height(me.x - e, me.y),
                                               _world.Terrain.Height(me.x, me.y + e) - _world.Terrain.Height(me.x, me.y - e));
                        _dir = (away - grad.normalized * 1.5f).normalized;
                        if (_dir.sqrMagnitude < 0.01f) _dir = away;
                        _state = State.Flee;
                    }
                    break;
                case State.Flee:
                    var step = _dir * 2.4f * Time.deltaTime;
                    me += step;
                    var h = _world.Terrain.Height(me.x, me.y);
                    transform.localPosition += new Vector3(step.x, 0f, step.y);
                    var lp = transform.localPosition;
                    var py = parent != null ? parent.localPosition.y : 0f;
                    transform.localPosition = new Vector3(lp.x, h + 0.04f - py, lp.z);
                    // yengeç yan yürür: gövde yönü hareket yönüne dik
                    var yaw = Mathf.Atan2(_dir.x, _dir.y) * Mathf.Rad2Deg + 90f;
                    transform.localRotation = Quaternion.Euler(0f, yaw, Mathf.Sin(Time.time * 40f) * 4f);
                    if (h < -0.05f || Vector2.Distance(me, pet) > 14f)
                    {
                        _state = State.Gone; _hidden = 0f;
                        foreach (var r in GetComponentsInChildren<Renderer>()) r.enabled = false;
                    }
                    break;
                case State.Gone:
                    _hidden += Time.deltaTime;
                    if (_hidden > 25f && dist > 12f)
                    {
                        transform.localPosition = _home;
                        foreach (var r in GetComponentsInChildren<Renderer>()) r.enabled = true;
                        _state = State.Idle;
                    }
                    break;
            }
        }
    }

    /// <summary>Kamp ateşi (madde 4): canlı alev dilleri (Pofi/Flame, kodla) + titreşen sıcak ışık. Fener ışığı gibi değil: alçak, turuncu, kısa menzil.</summary>
    public sealed class Campfire : MonoBehaviour
    {
        private Light _light;
        private float _base;

        public static void Light(Transform fire, float scale)
        {
            var sh = Shader.Find("Pofi/Flame");
            if (sh != null)
            {
                var mat = new Material(sh);
                var mesh = FlameMesh();
                var rnd = new System.Random(4);
                for (var k = 0; k < 7; k++)
                {
                    var go = new GameObject("flame");
                    go.transform.SetParent(fire, false);
                    var a = k * 2.4f; var r = k == 0 ? 0f : 0.12f + 0.1f * (float)rnd.NextDouble();
                    var s = (k == 0 ? 1.25f : 0.7f + 0.35f * (float)rnd.NextDouble()) * scale;
                    go.transform.localPosition = new Vector3(Mathf.Cos(a) * r * scale, 0.08f * scale, Mathf.Sin(a) * r * scale);
                    go.transform.localScale = new Vector3(0.55f * s, 1.0f * s, 0.55f * s);
                    go.transform.localRotation = Quaternion.Euler(0f, (float)rnd.NextDouble() * 360f, 0f);
                    go.AddComponent<MeshFilter>().sharedMesh = mesh;
                    var mr = go.AddComponent<MeshRenderer>();
                    var m = new Material(mat); m.SetFloat("_Seed", k * 3.7f);
                    mr.sharedMaterial = m;
                    mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                    mr.receiveShadows = false;
                }
            }
            var lgo = new GameObject("fire_light");
            lgo.transform.SetParent(fire, false);
            lgo.transform.localPosition = new Vector3(0f, 0.6f * scale, 0f);
            var l = lgo.AddComponent<Light>();
            l.type = LightType.Point; l.color = new Color(1f, 0.58f, 0.25f); l.range = 7f * scale; l.intensity = 1.6f; l.shadows = LightShadows.None;
            var c = fire.gameObject.AddComponent<Campfire>(); c._light = l; c._base = l.intensity;
        }

        private void Update()
        {
            if (_light == null) return;
            var t = Time.time;
            _light.intensity = _base * (0.82f + 0.12f * Mathf.Sin(t * 13f) + 0.08f * Mathf.Sin(t * 29f + 1.3f) + 0.06f * Mathf.PerlinNoise(t * 5f, 0.3f));
        }

        private static Mesh _flame;

        /// <summary>Üç çapraz dikey düzlem (alev dili; gölgelendirici biçimi ve hareketi verir).</summary>
        private static Mesh FlameMesh()
        {
            if (_flame != null) return _flame;
            var v = new List<Vector3>(); var uv = new List<Vector2>(); var t = new List<int>();
            for (var q = 0; q < 3; q++)
            {
                var a = q * Mathf.PI / 3f; var dx = Mathf.Cos(a) * 0.5f; var dz = Mathf.Sin(a) * 0.5f;
                var b = v.Count;
                v.Add(new Vector3(-dx, 0f, -dz)); v.Add(new Vector3(dx, 0f, dz)); v.Add(new Vector3(dx, 1f, dz)); v.Add(new Vector3(-dx, 1f, -dz));
                uv.Add(new Vector2(0f, 0f)); uv.Add(new Vector2(1f, 0f)); uv.Add(new Vector2(1f, 1f)); uv.Add(new Vector2(0f, 1f));
                t.AddRange(new[] { b, b + 2, b + 1, b, b + 3, b + 2 });
            }
            _flame = new Mesh { name = "Flame" };
            _flame.SetVertices(v); _flame.SetUVs(0, uv); _flame.SetTriangles(t, 0);
            _flame.RecalculateBounds();
            return _flame;
        }
    }
}
