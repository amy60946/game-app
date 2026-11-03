using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// Oyun Kulübesi'nin Yıldız Kapısı (K4 A, kullanıcı 3 Kasım 2026; benchmark Super Mario 64 tablosu: gidilecek yerin önizlemesi
    /// korkuyu yok eder; Spyro taş kemerleri, Mario Galaxy gözlemevi, Disney Dreamlight Valley diyar kapıları). Kulübenin önünde
    /// yuvarlak taş kemer; içinde gidilecek dünyanın aydınlık resmi (uzak yıldızlar, büyük Dünya, Ay ufku — ortası hiç kararmaz,
    /// girdap yok). Okti yaklaşınca kemer taşları sırayla yanar, uzaklaşınca söner; "Gir"de yüzey dalgalanır (<see cref="Ripple"/>),
    /// ardından kısa yıldız tüneli (UI/StarTunnel). Çatıda küçük teleskop silueti (uzaktan görünür). Kemerin üstünde üç küçük
    /// pul: ortadaki yanar (bugünkü dünya), yanlardaki sönük (ileride Mısır gibi yeni dünyalar). Hepsi kodla, ParticleSystem yok.
    /// </summary>
    public sealed class StarGate : MonoBehaviour
    {
        public const float Radius = 1.35f, NearDist = 8f;
        private const int Stones = 14;
        private static readonly Color StoneCol = new Color(0.79f, 0.71f, 0.55f), LitCol = new Color(1f, 0.88f, 0.52f), GlowCol = new Color(1f, 0.82f, 0.35f);

        private static Texture2D _tex;
        private MapWorld _world;
        private readonly Material[] _stoneMats = new Material[Stones];
        private readonly Transform[] _glows = new Transform[Stones];
        private Transform _disk, _halo;
        private Material _diskMat;
        private readonly System.Collections.Generic.List<Material> _mats = new System.Collections.Generic.List<Material>();
        private Material Mat(Color c, float smooth) { var m = PetModels.NewMaterial(c, smooth); _mats.Add(m); return m; }
        private float _lit, _ripple = -1f, _t;
        private bool _told, _open = true;

        /// <summary>Okti kapıya ilk kez yaklaştı (bu oturumda bir kez; MapScreen Mavi'ye tek cümle söyletir).</summary>
        public System.Action Approached;

        /// <summary>Kapıyı bölgenin kapı noktasına kurar (bölge kökünün çocuğu; yapı modeli kurulduktan sonra).</summary>
        /// <param name="open">Kulübe açık mı (Sv3): kilitliyken kapı görünür ama yanmaz, Mavi konuşmaz (GB21-7).</param>
        public static StarGate Build(MapWorld world, Transform root, float doorX, float doorZ, float centerX, float centerZ, float roofY, bool open = true)
        {
            var dir = new Vector2(doorX - centerX, doorZ - centerZ);
            if (dir.sqrMagnitude < 0.01f) dir = Vector2.up;
            dir.Normalize();
            var gx = doorX - dir.x * 0.9f; var gz = doorZ - dir.y * 0.9f;   // Okti kapı noktasında, kemerin hemen önünde durur
            var go = new GameObject("star_gate");
            go.transform.SetParent(root, false);
            go.transform.localPosition = new Vector3(gx - centerX, world.Terrain.Height(gx, gz) - root.localPosition.y, gz - centerZ);
            go.transform.localRotation = Quaternion.LookRotation(new Vector3(dir.x, 0f, dir.y));   // +z dışarı (Okti'ye doğru)
            var g = go.AddComponent<StarGate>();
            g._world = world; g._open = open;
            g.BuildArch();
            g.BuildTelescope(root, roofY, dir);
            return g;
        }

        private void BuildArch()
        {
            var cy = Radius + 0.12f;
            // iç resim (Pofi/Sprite: ışıksız, aydınlık) + arkasında yumuşak ışık
            _halo = GainFx.Glow(transform, new Color(0.55f, 0.75f, 1f), 0.55f, false);
            _halo.localPosition = new Vector3(0f, cy, -0.05f); _halo.localScale = Vector3.one * Radius * 2.9f;
            var q = GameObject.CreatePrimitive(PrimitiveType.Quad);
            q.name = "gate_view";
            Destroy(q.GetComponent<Collider>());
            q.transform.SetParent(transform, false);
            q.transform.localPosition = new Vector3(0f, cy, 0f);
            q.transform.localRotation = Quaternion.Euler(0f, 180f, 0f);
            q.transform.localScale = Vector3.one * (Radius * 2f - 0.22f);
            _diskMat = InkHeart.SpriteMat(Tex());
            var qr = q.GetComponent<MeshRenderer>(); qr.sharedMaterial = _diskMat;
            qr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; qr.receiveShadows = false;
            _disk = q.transform;
            // kemer taşları: halka boyunca, tangent yönünde basık yuvarlak taşlar
            for (var i = 0; i < Stones; i++)
            {
                var a = i / (float)Stones * Mathf.PI * 2f + Mathf.PI * 0.5f;
                var s = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                s.name = "gate_stone" + i;
                Destroy(s.GetComponent<Collider>());
                s.transform.SetParent(transform, false);
                s.transform.localPosition = new Vector3(Mathf.Cos(a) * Radius, cy + Mathf.Sin(a) * Radius, 0f);
                s.transform.localRotation = Quaternion.Euler(0f, 0f, a * Mathf.Rad2Deg + 90f);
                s.transform.localScale = new Vector3(0.62f, 0.4f, 0.42f) * (i % 2 == 0 ? 1f : 0.92f);
                var m = Mat(StoneCol * (0.92f + 0.08f * Mathf.Sin(i * 2.3f)), 0.25f);
                s.GetComponent<MeshRenderer>().sharedMaterial = m;
                _stoneMats[i] = m;
                var gl = GainFx.Glow(s.transform.parent, GlowCol, 0.9f, false);
                gl.localPosition = s.transform.localPosition + Vector3.forward * 0.25f;
                gl.localScale = Vector3.zero;
                _glows[i] = gl;
            }
            // iki ayak taşı + üstte üç pul (ortadaki yanık: bugünkü dünya; yanlardaki sönük: yakında)
            foreach (var side in new[] { -1f, 1f })
            {
                var f = GameObject.CreatePrimitive(PrimitiveType.Cube);
                Destroy(f.GetComponent<Collider>());
                f.transform.SetParent(transform, false);
                f.transform.localPosition = new Vector3(side * (Radius * 0.62f), 0.12f, 0f);
                f.transform.localScale = new Vector3(0.7f, 0.3f, 0.6f);
                f.GetComponent<MeshRenderer>().sharedMaterial = Mat(StoneCol * 0.85f, 0.2f);
            }
            for (var i = -1; i <= 1; i++)
            {
                var a = Mathf.PI * 0.5f + i * 0.42f;
                var p = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                Destroy(p.GetComponent<Collider>());
                p.transform.SetParent(transform, false);
                p.transform.localPosition = new Vector3(Mathf.Cos(a) * (Radius + 0.42f), cy + Mathf.Sin(a) * (Radius + 0.42f), 0f);
                p.transform.localRotation = Quaternion.Euler(90f, 0f, 0f);
                p.transform.localScale = new Vector3(0.3f, 0.04f, 0.3f);
                var on = i == 0;
                p.GetComponent<MeshRenderer>().sharedMaterial = Mat(on ? new Color(0.42f, 0.7f, 1f) : new Color(0.55f, 0.55f, 0.6f), 0.6f);
                if (on) { var gl = GainFx.Glow(transform, new Color(0.6f, 0.82f, 1f), 0.7f, false); gl.localPosition = p.transform.localPosition + Vector3.forward * 0.1f; gl.localScale = Vector3.one * 0.7f; }
            }
        }

        /// <summary>Çatıda küçük pirinç teleskop: üç ayak + gökyüzüne bakan tüp.</summary>
        private void BuildTelescope(Transform root, float roofY, Vector2 dir)
        {
            var t = new GameObject("telescope").transform;
            t.SetParent(root, false);
            t.localPosition = new Vector3(-dir.x * 0.6f, roofY - 0.25f, -dir.y * 0.6f);
            t.localRotation = Quaternion.LookRotation(new Vector3(dir.x, 0f, dir.y));
            var brass = Mat(new Color(0.78f, 0.58f, 0.25f), 0.7f);
            var dark = Mat(new Color(0.3f, 0.24f, 0.2f), 0.3f);
            void Part(PrimitiveType pt, Vector3 pos, Vector3 rot, Vector3 scale, Material m)
            {
                var g = GameObject.CreatePrimitive(pt);
                Destroy(g.GetComponent<Collider>());
                g.transform.SetParent(t, false);
                g.transform.localPosition = pos; g.transform.localRotation = Quaternion.Euler(rot); g.transform.localScale = scale;
                g.GetComponent<MeshRenderer>().sharedMaterial = m;
            }
            for (var i = 0; i < 3; i++)
            {
                var yaw = i * 120f;
                var off = Quaternion.Euler(0f, yaw, 0f) * new Vector3(0f, 0f, 0.22f);
                Part(PrimitiveType.Cylinder, new Vector3(off.x, 0.3f, off.z), new Vector3(-18f, yaw, 0f) , new Vector3(0.05f, 0.32f, 0.05f), dark);
            }
            Part(PrimitiveType.Cylinder, new Vector3(0f, 0.72f, 0.1f), new Vector3(55f, 0f, 0f), new Vector3(0.17f, 0.5f, 0.17f), brass);
            Part(PrimitiveType.Cylinder, new Vector3(0f, 1.0f, 0.5f), new Vector3(55f, 0f, 0f), new Vector3(0.24f, 0.06f, 0.24f), brass);
        }

        /// <summary>"Gir": yüzey dalgalanır, taşlar parlar (geçişin başı).</summary>
        public void Ripple() { _ripple = 0f; _lit = 1f; }

        private void Update()
        {
            _t += Time.deltaTime;
            var w = _world != null ? _world.Walker : null;
            var near = _open && w != null && Vector3.Distance(w.transform.position, transform.position) < NearDist;
            if (!_open) return;   // kilitli: renkleri bölgenin gri tonu belirler, ışık yok
            if (near && !_told) { _told = true; Approached?.Invoke(); }
            _lit = Mathf.MoveTowards(_lit, near ? 1f : 0f, Time.deltaTime / 1.4f);
            for (var i = 0; i < Stones; i++)
            {
                // sırayla yanar: alttan iki yana, tepede buluşur
                var order = Mathf.Min(i, Stones - i) / (Stones * 0.5f);
                var k = Mathf.Clamp01((_lit - order * 0.6f) / 0.4f);
                if (_stoneMats[i] != null) _stoneMats[i].SetColor("_BaseColor", Color.Lerp(StoneCol, LitCol, k));
                if (_glows[i] != null) _glows[i].localScale = Vector3.one * 0.75f * k * (1f + 0.08f * Mathf.Sin(_t * 3f + i));
            }
            var pulse = 1f + 0.04f * Mathf.Sin(_t * 1.6f) * _lit;
            if (_ripple >= 0f)
            {
                _ripple += Time.deltaTime;
                pulse *= 1f + 0.1f * Mathf.Sin(_ripple * 14f) * Mathf.Exp(-_ripple * 2.2f);
                if (_ripple > 2f) _ripple = -1f;
            }
            if (_disk != null) _disk.localScale = Vector3.one * (Radius * 2f - 0.22f) * pulse;
            if (_halo != null) _halo.localScale = Vector3.one * Radius * (2.4f + 0.7f * _lit) * pulse;
        }

        private void OnDestroy()
        {
            foreach (var m in _mats) if (m != null) Destroy(m);
            if (_diskMat != null) Destroy(_diskMat);
        }

        /// <summary>Kapının içindeki dünya resmi: alacakaranlık mavisi gök + yıldızlar, büyük Dünya, Ay ufku (yuvarlak, yumuşak kenar).</summary>
        private static Texture2D Tex()
        {
            if (_tex != null) return _tex;
            const int n = 256;
            _tex = new Texture2D(n, n, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, name = "star_gate_view" };
            var px = new Color[n * n];
            var rnd = new System.Random(4242);
            var stars = new Vector3[70];
            for (var i = 0; i < stars.Length; i++) stars[i] = new Vector3((float)rnd.NextDouble(), 0.35f + 0.65f * (float)rnd.NextDouble(), 0.6f + 1.6f * (float)rnd.NextDouble());
            var earth = new Vector2(0.64f, 0.68f); const float er = 0.19f;
            for (var y = 0; y < n; y++)
                for (var x = 0; x < n; x++)
                {
                    var u = (x + 0.5f) / n; var v = (y + 0.5f) / n;
                    // gök: üstte koyu mavi değil, aydınlık lacivert → mor → ufukta açık mavi (ortası kararmasın)
                    var sky = Color.Lerp(new Color(0.42f, 0.6f, 0.95f), new Color(0.2f, 0.27f, 0.62f), Mathf.SmoothStep(0.25f, 1f, v));
                    sky = Color.Lerp(sky, new Color(0.45f, 0.33f, 0.72f), 0.25f * Mathf.Sin(v * Mathf.PI));
                    var c = sky;
                    foreach (var s in stars)
                    {
                        var dd = (new Vector2(u, v) - new Vector2(s.x, s.y)).magnitude * n;
                        if (dd < s.z) c = Color.Lerp(c, Color.white, 1f - dd / s.z);
                    }
                    // Dünya: okyanus + kıta lekeleri + bulut, gün ışığı kenarı ve ince atmosfer
                    var de = (new Vector2(u, v) - earth).magnitude;
                    if (de < er * 1.12f)
                    {
                        var atm = Mathf.Clamp01(1f - (de - er) / (er * 0.12f));
                        c = Color.Lerp(c, new Color(0.7f, 0.9f, 1f), de > er ? atm * 0.7f : 0f);
                        if (de <= er)
                        {
                            var lx = (u - earth.x) / er; var ly = (v - earth.y) / er;
                            var land = Mathf.Sin(lx * 7.1f + 1.3f) * Mathf.Cos(ly * 5.3f - 0.4f) + 0.6f * Mathf.Sin((lx + ly) * 11f);
                            var e = land > 0.55f ? new Color(0.36f, 0.7f, 0.38f) : new Color(0.2f, 0.52f, 0.9f);
                            var cloud = Mathf.Sin(lx * 13f + ly * 3f) * Mathf.Sin(ly * 9f - lx * 2f);
                            if (cloud > 0.55f) e = Color.Lerp(e, Color.white, 0.75f);
                            var shade = Mathf.Clamp01(0.55f + 0.6f * (-lx * 0.5f + ly * 0.6f + 0.4f));
                            c = e * Mathf.Lerp(0.6f, 1.08f, shade);
                            c.a = 1f;
                        }
                    }
                    // Ay ufku: altta kavisli açık gri yüzey + küçük kraterler
                    var hz = 0.24f + 0.07f * Mathf.Cos((u - 0.5f) * 2.4f);
                    if (v < hz)
                    {
                        var g = Mathf.Lerp(0.86f, 0.7f, (hz - v) / hz);
                        var moon = new Color(g, g, g * 1.04f);
                        var cr = Mathf.Sin(u * 37f) * Mathf.Sin(v * 51f);
                        if (cr > 0.8f) moon *= 0.86f;
                        c = Color.Lerp(moon, new Color(0.95f, 0.95f, 1f), Mathf.Clamp01((v - hz + 0.012f) / 0.012f) * 0.6f);
                    }
                    // yuvarlak kesim, yumuşak kenar
                    var dc = (new Vector2(u, v) - new Vector2(0.5f, 0.5f)).magnitude;
                    c.a = Mathf.Clamp01((0.5f - dc) / 0.015f);
                    px[y * n + x] = c;
                }
            _tex.SetPixels(px); _tex.Apply();
            return _tex;
        }
    }
}
