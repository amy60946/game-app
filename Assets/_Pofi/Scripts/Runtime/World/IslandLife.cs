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
