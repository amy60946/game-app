using System.Collections.Generic;
using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// Yazısız yol gösterme (N1 + N3, 23 Ekim 2026, kullanıcı onayı). N1: petten hedefe doğru zemine yatık, parlak ok dizisi;
    /// ışık dalgası 1,4 sn'de bir ileri akar. N3: hedefin üstünde aşağıyı gösteren, 0,6 sn'de bir zıplayan büyük ok.
    /// Yalnız rehberli adımda ve çocuk bir süre hareketsiz kalınca açılır (MapScreen); yürürken kalır ve yolu günceller, varınca söner.
    /// Parçacık modülü kullanılmaz: kodla çizilmiş dokulu dörtgenler.
    /// </summary>
    public sealed class PathGuide : MonoBehaviour
    {
        // Akış haritası yorumu (25 Ekim 2026, kullanıcı: "oklar görünmüyor; daha geniş ve daha kalın olsun"): ok 1,7 kat büyük,
        // kollar kalın + koyu turuncu kenar (açık zeminde de seçilir), aralık 2,1 m
        private const int MaxArrows = 10;
        private const float Step = 2.1f, StartAt = 1.8f, StopShort = 2.4f, ArrowSize = 1.65f;
        private readonly List<Transform> _arrows = new List<Transform>();
        private readonly List<Material> _mats = new List<Material>();
        private Transform _marker;
        private Material _markerMat;
        private MapWorld _world;
        private Vector2 _target;
        private float _t, _fade;
        private bool _on;
        private static Texture2D _arrowTex, _downTex;

        public bool Active => _on;
        public Vector2 Target => _target;

        public static PathGuide Create(MapWorld world)
        {
            var go = new GameObject("PathGuide");
            go.transform.SetParent(world.transform, false);
            var g = go.AddComponent<PathGuide>();
            g._world = world;
            for (var i = 0; i < MaxArrows; i++)
            {
                var q = Quad(go.transform, "Arrow" + i, ArrowTex(), out var m);
                q.gameObject.SetActive(false);
                g._arrows.Add(q); g._mats.Add(m);
            }
            g._marker = Quad(go.transform, "Marker", DownTex(), out g._markerMat);
            g._marker.gameObject.SetActive(false);
            return g;
        }

        public void Show(Vector2 target) { _target = target; _on = true; }
        public void Hide() { _on = false; }

        /// <summary>Her karede: petin bulunduğu yerden hedefe dizilir (yol değişince oklar da kayar).</summary>
        public void Tick(Vector2 from, Camera cam, float dt)
        {
            _t += dt;
            _fade = Mathf.MoveTowards(_fade, _on ? 1f : 0f, dt / 0.4f);
            var d = _target - from;
            var len = d.magnitude;
            if (_fade <= 0f || len < 0.01f)
            {
                foreach (var a in _arrows) if (a.gameObject.activeSelf) a.gameObject.SetActive(false);
                if (_marker.gameObject.activeSelf) _marker.gameObject.SetActive(false);
                return;
            }
            var dir = d / len;
            var yaw = Mathf.Atan2(dir.x, dir.y) * Mathf.Rad2Deg;
            var n = Mathf.Clamp(Mathf.FloorToInt((len - StartAt - StopShort) / Step) + 1, 0, MaxArrows);
            var gold = Color.white;   // renk dokuda (altın + kenar)
            for (var i = 0; i < _arrows.Count; i++)
            {
                var a = _arrows[i];
                var show = i < n;
                if (a.gameObject.activeSelf != show) a.gameObject.SetActive(show);
                if (!show) continue;
                var p = from + dir * (StartAt + i * Step);
                var h = _world.Terrain.Height(p.x, p.y);
                if (h < -0.05f) { a.gameObject.SetActive(false); continue; }   // denizde ok yok
                a.localPosition = new Vector3(p.x, h + 0.09f, p.y);
                a.localRotation = Quaternion.Euler(90f, yaw, 0f);
                a.localScale = Vector3.one * ArrowSize;
                // ışık dalgası: arkadan öne akar (1,4 sn)
                var ph = Mathf.Repeat(_t / 1.4f - i * 0.11f, 1f);
                var wave = Mathf.Pow(Mathf.Max(0f, Mathf.Cos(ph * Mathf.PI * 2f)), 3f);
                var c = gold; c.a = (0.55f + 0.45f * wave) * _fade;
                _mats[i].color = c;
            }
            // hedef oku: billboard, zıplar (0,6 sn)
            if (!_marker.gameObject.activeSelf) _marker.gameObject.SetActive(true);
            var ty = _world.Terrain.Height(_target.x, _target.y);
            var bounce = Mathf.Abs(Mathf.Sin(_t * Mathf.PI / 0.6f));
            _marker.localPosition = new Vector3(_target.x, ty + 3.1f + bounce * 0.45f, _target.y);
            if (cam != null) _marker.rotation = Quaternion.LookRotation(_marker.position - cam.transform.position, Vector3.up);
            _marker.localScale = Vector3.one * (1.6f + 0.1f * bounce);
            var mc = gold; mc.a = _fade; _markerMat.color = mc;
        }

        private static Transform Quad(Transform parent, string name, Texture2D tex, out Material mat)
        {
            var q = GameObject.CreatePrimitive(PrimitiveType.Quad);
            Destroy(q.GetComponent<Collider>());
            q.name = name;
            q.transform.SetParent(parent, false);
            var r = q.GetComponent<MeshRenderer>();
            mat = InkHeart.SpriteMat(tex);
            mat = new Material(mat);   // her okun kendi saydamlığı
            r.sharedMaterial = mat;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
            return q.transform;
        }

        /// <summary>Zemindeki ok: kalın köşeli V (chevron), içi açık altın, koyu turuncu kenar, ucu ileri (+y).</summary>
        private static Texture2D ArrowTex()
        {
            if (_arrowTex != null) return _arrowTex;
            const int n = 128;
            _arrowTex = new Texture2D(n, n, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, name = "guide_arrow" };
            var px = new Color32[n * n];
            var fill = new Color(1f, 0.84f, 0.3f); var core = new Color(1f, 0.97f, 0.75f); var edge = new Color(0.78f, 0.36f, 0.04f);
            for (var y = 0; y < n; y++)
                for (var x = 0; x < n; x++)
                {
                    var u = (x + 0.5f) / n * 2f - 1f; var v = (y + 0.5f) / n * 2f - 1f;
                    var arm = Mathf.Abs(v - (0.5f - Mathf.Abs(u) * 1.0f));   // iki kol, uç yukarıda
                    var inside = Mathf.Abs(u) < 0.9f && v > -0.85f && v < 0.85f;
                    if (!inside) { px[y * n + x] = new Color(1f, 1f, 1f, 0f); continue; }
                    var body = Mathf.Clamp01((0.3f - arm) * 14f);           // kalın kol
                    var rim = Mathf.Clamp01((0.38f - arm) * 14f);           // koyu kenar
                    var glow = Mathf.Clamp01((0.55f - arm) * 2.5f) * 0.3f;
                    var c = Color.Lerp(edge, Color.Lerp(fill, core, Mathf.Clamp01((0.14f - arm) * 10f)), body);
                    c.a = Mathf.Max(rim, glow);
                    px[y * n + x] = c;
                }
            _arrowTex.SetPixels32(px); _arrowTex.Apply();
            return _arrowTex;
        }

        /// <summary>Hedef oku: aşağıyı gösteren kalın ok, beyaz kenar.</summary>
        private static Texture2D DownTex()
        {
            if (_downTex != null) return _downTex;
            const int n = 96;
            _downTex = new Texture2D(n, n, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, name = "guide_down" };
            var px = new Color32[n * n];
            for (var y = 0; y < n; y++)
                for (var x = 0; x < n; x++)
                {
                    var u = (x + 0.5f) / n * 2f - 1f; var v = (y + 0.5f) / n * 2f - 1f;
                    // gövde (üstte dikdörtgen) + baş (altta üçgen, uç aşağıda)
                    var body = Mathf.Abs(u) < 0.26f && v > 0.0f && v < 0.85f;
                    var head = v <= 0.05f && v > -0.85f && Mathf.Abs(u) < (v + 0.85f) * 0.78f;
                    var inArrow = body || head;
                    var edgeBody = Mathf.Abs(u) < 0.36f && v > -0.05f && v < 0.95f;
                    var edgeHead = v <= 0.12f && v > -0.97f && Mathf.Abs(u) < (v + 0.97f) * 0.8f;
                    var inEdge = edgeBody || edgeHead;
                    Color c = inArrow ? new Color(1f, 0.8f, 0.25f, 1f) : inEdge ? new Color(1f, 1f, 1f, 1f) : new Color(1f, 1f, 1f, 0f);
                    if (inArrow && v > 0.55f) c = Color.Lerp(c, new Color(1f, 0.93f, 0.6f), 0.5f);   // üstte parıltı
                    px[y * n + x] = c;
                }
            _downTex.SetPixels32(px); _downTex.Apply();
            return _downTex;
        }
    }
}
