using System.Collections.Generic;
using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// Kazanım efekti (XP takibi S4, 22 Ekim 2026; kullanıcı: "3B olsun, karakterin içine girsin, kazandım hissi"):
    /// kazanılan yerde küçük 3B parçalar doğar (XP = mavi yıldız, Güneş Taşı = altın kristal), ışık izleriyle yay çizerek
    /// pete uçar ve içine girer; ilk parça değince pet parlar (ışık lekesi + ayak halkası), hafifçe esner, ses + titreşim.
    /// Pet yürürken de hedef canlı izlenir. Parça sayısı miktarla artar ama sınırlıdır (ekran dolmasın).
    /// </summary>
    public static class GainFx
    {
        public enum Kind { Xp, Stone }

        public static readonly Color XpColor = new Color(0.35f, 0.72f, 1f), StoneColor = new Color(1f, 0.78f, 0.22f);
        private static Mesh _star, _gem, _quad;
        private static Material _xpMat, _stoneMat;
        private static readonly Dictionary<int, Material> Glows = new Dictionary<int, Material>();

        /// <summary>Parçaları <paramref name="from"/> (dünya) noktasından petin göğsüne uçurur. Bitince <paramref name="arrived"/>.</summary>
        public static void Play(Kind kind, int amount, Vector3 from, Transform pet, float petHeight, System.Action arrived = null)
        {
            if (pet == null) { arrived?.Invoke(); return; }
            var root = new GameObject("GainFx " + kind);
            var burst = root.AddComponent<GainBurst>();
            burst.Init(kind, pet, petHeight, arrived);
            var n = kind == Kind.Xp ? Mathf.Clamp(2 + amount / 10, 3, 9) : Mathf.Clamp(amount * 2, 2, 8);
            var rnd = new System.Random(amount * 7919 + n);
            for (var i = 0; i < n; i++)
            {
                var piece = Piece(kind, root.transform);
                var jitter = new Vector3((float)rnd.NextDouble() - 0.5f, (float)rnd.NextDouble() * 0.6f, (float)rnd.NextDouble() - 0.5f) * 0.9f;
                var side = new Vector3((float)rnd.NextDouble() * 2f - 1f, 0f, (float)rnd.NextDouble() * 2f - 1f) * 1.6f;
                piece.Init(burst, from + jitter, side, i * 0.07f, 0.7f + (float)rnd.NextDouble() * 0.2f);
                burst.Add();
            }
        }

        /// <summary>Petin çevresinde doğup içine akan parçalar (kaynak yeri belli olmayan kazanımlar: görev onayı, rozet).</summary>
        public static void AroundPet(Kind kind, int amount, Transform pet, float petHeight, System.Action arrived = null)
        {
            if (pet == null) { arrived?.Invoke(); return; }
            Play(kind, amount, pet.position + Vector3.up * (petHeight * 1.9f + 0.6f), pet, petHeight, arrived);
        }

        private static GainPiece Piece(Kind kind, Transform parent)
        {
            var go = new GameObject("Piece");
            go.transform.SetParent(parent, false);
            go.AddComponent<MeshFilter>().sharedMesh = kind == Kind.Xp ? Star : Gem;
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = kind == Kind.Xp ? XpMat : StoneMat;
            mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            mr.receiveShadows = false;
            // parçanın ışık hâlesi (kameraya dönük)
            var halo = Glow(go.transform, kind == Kind.Xp ? XpColor : StoneColor, 0.9f, false);
            halo.localScale = Vector3.one * 0.8f;
            return go.AddComponent<GainPiece>();
        }

        /// <summary>Kameraya dönük ışık dörtgeni (leke ya da halka).</summary>
        internal static Transform Glow(Transform parent, Color c, float intensity, bool ring)
        {
            var go = new GameObject(ring ? "Ring" : "Glow");
            go.transform.SetParent(parent, false);
            go.AddComponent<MeshFilter>().sharedMesh = Quad;
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = GlowMat(c, intensity, ring);
            mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            mr.receiveShadows = false;
            if (!ring) go.AddComponent<FaceCamera>();
            return go.transform;
        }

        private static Material GlowMat(Color c, float intensity, bool ring)
        {
            var key = (ColorUtility.ToHtmlStringRGB(c) + intensity.ToString("0.00") + ring).GetHashCode();
            if (Glows.TryGetValue(key, out var m) && m != null) return m;
            var sh = Shader.Find("Pofi/Glow");
            m = sh != null ? new Material(sh) : PetModels.NewMaterial(c, 0.9f);
            m.SetColor("_Color", c);
            m.SetFloat("_Intensity", intensity);
            m.SetFloat("_Ring", ring ? 1f : 0f);
            return Glows[key] = m;
        }

        private static Material XpMat { get { if (_xpMat == null) { _xpMat = PetModels.NewMaterial(XpColor, 0.95f); _xpMat.SetFloat("_Rim", 2.2f); } return _xpMat; } }
        private static Material StoneMat { get { if (_stoneMat == null) { _stoneMat = PetModels.NewMaterial(StoneColor, 0.95f); _stoneMat.SetFloat("_Rim", 2.2f); } return _stoneMat; } }

        // ------------------------------------------------------------------ biçimler

        /// <summary>Şişkin beş köşeli yıldız (ortası öne/arkaya kabarık; vinyl oyuncak gibi). Boy ~0.36 m.</summary>
        private static Mesh Star
        {
            get
            {
                if (_star != null) return _star;
                const float outer = 0.18f, inner = 0.085f, puff = 0.07f;
                var v = new List<Vector3>(); var t = new List<int>();
                for (var face = 0; face < 2; face++)
                {
                    var z = face == 0 ? -puff : puff;
                    for (var k = 0; k < 10; k++)
                    {
                        var a = Mathf.PI * 0.5f + k * Mathf.PI / 5f;
                        var r = k % 2 == 0 ? outer : inner;
                        var c = new Vector3(0f, 0f, z);
                        var p0 = new Vector3(Mathf.Cos(a) * r, Mathf.Sin(a) * r, 0f);
                        var a1 = Mathf.PI * 0.5f + (k + 1) * Mathf.PI / 5f;
                        var r1 = (k + 1) % 2 == 0 ? outer : inner;
                        var p1 = new Vector3(Mathf.Cos(a1) * r1, Mathf.Sin(a1) * r1, 0f);
                        var b = v.Count;
                        v.Add(c); v.Add(p0); v.Add(p1);   // her üçgen kendi köşeleri: sert yüzey ışığı (faset)
                        if (face == 0) { t.Add(b); t.Add(b + 2); t.Add(b + 1); } else { t.Add(b); t.Add(b + 1); t.Add(b + 2); }
                    }
                }
                _star = new Mesh { name = "GainStar" };
                _star.SetVertices(v); _star.SetTriangles(t, 0); _star.RecalculateNormals(); _star.RecalculateBounds();
                return _star;
            }
        }

        /// <summary>Uzun sekizyüzlü kristal (Güneş Taşı). Boy ~0.4 m.</summary>
        internal static Mesh GemMesh => Gem;

        private static Mesh Gem
        {
            get
            {
                if (_gem != null) return _gem;
                var top = new Vector3(0f, 0.2f, 0f); var bot = new Vector3(0f, -0.2f, 0f);
                var ring = new Vector3[6];
                for (var k = 0; k < 6; k++) { var a = k * Mathf.PI / 3f; ring[k] = new Vector3(Mathf.Cos(a) * 0.12f, 0.03f, Mathf.Sin(a) * 0.12f); }
                var v = new List<Vector3>(); var t = new List<int>();
                for (var k = 0; k < 6; k++)
                {
                    var p0 = ring[k]; var p1 = ring[(k + 1) % 6];
                    var b = v.Count; v.Add(top); v.Add(p1); v.Add(p0); t.Add(b); t.Add(b + 1); t.Add(b + 2);
                    b = v.Count; v.Add(bot); v.Add(p0); v.Add(p1); t.Add(b); t.Add(b + 1); t.Add(b + 2);
                }
                _gem = new Mesh { name = "GainGem" };
                _gem.SetVertices(v); _gem.SetTriangles(t, 0); _gem.RecalculateNormals(); _gem.RecalculateBounds();
                return _gem;
            }
        }

        private static Mesh Quad
        {
            get
            {
                if (_quad != null) return _quad;
                _quad = new Mesh { name = "GainQuad" };
                _quad.SetVertices(new List<Vector3> { new Vector3(-0.5f, -0.5f, 0f), new Vector3(0.5f, -0.5f, 0f), new Vector3(-0.5f, 0.5f, 0f), new Vector3(0.5f, 0.5f, 0f) });
                _quad.SetUVs(0, new List<Vector2> { new Vector2(0f, 0f), new Vector2(1f, 0f), new Vector2(0f, 1f), new Vector2(1f, 1f) });
                _quad.SetTriangles(new[] { 0, 2, 1, 1, 2, 3 }, 0);
                _quad.RecalculateBounds();
                return _quad;
            }
        }
    }

    /// <summary>Bir kazanımın parçalarını sayar: ilki pete değince parlama + ses, sonuncusu değince biter.</summary>
    public sealed class GainBurst : MonoBehaviour
    {
        private GainFx.Kind _kind;
        private Transform _pet;
        private float _height;
        private System.Action _arrived;
        private int _count, _landed;

        public Vector3 Target => _pet != null ? _pet.position + Vector3.up * (_height * 0.6f) : transform.position;

        public void Init(GainFx.Kind kind, Transform pet, float height, System.Action arrived)
        {
            _kind = kind; _pet = pet; _height = Mathf.Max(0.4f, height); _arrived = arrived;
            Audio.Sfx.Play(Audio.SfxKind.Whoosh);
        }

        public void Add() => _count++;

        public void Landed()
        {
            _landed++;
            if (_landed == 1 && _pet != null)
            {
                PetGlow.Play(_pet, _height, _kind == GainFx.Kind.Xp ? GainFx.XpColor : GainFx.StoneColor);
                Audio.Sfx.Play(_kind == GainFx.Kind.Xp ? Audio.SfxKind.Gain : Audio.SfxKind.Chime);
                Audio.Haptics.Medium();
            }
            if (_landed >= _count)
            {
                var a = _arrived; _arrived = null;
                a?.Invoke();
                Destroy(gameObject, 0.05f);
            }
        }
    }

    /// <summary>Tek parça: kısa gecikme, büyüyerek belirir, yay çizerek (hedef canlı) pete uçar, dönerek küçülür.</summary>
    public sealed class GainPiece : MonoBehaviour
    {
        private GainBurst _burst;
        private Vector3 _start, _side;
        private float _delay, _dur, _t;
        private Vector3 _spin;
        private bool _done;

        public void Init(GainBurst burst, Vector3 start, Vector3 side, float delay, float dur)
        {
            _burst = burst; _start = start; _side = side; _delay = delay; _dur = dur;
            transform.position = start;
            transform.localScale = Vector3.zero;
            _spin = new Vector3(Random.Range(-90f, 90f), Random.Range(240f, 420f), Random.Range(-60f, 60f));
        }

        private void Update()
        {
            if (_done) return;
            if (_delay > 0f) { _delay -= Time.deltaTime; return; }
            _t = Mathf.Min(1f, _t + Time.deltaTime / _dur);
            var end = _burst != null ? _burst.Target : _start;
            // önce kısa sıçrama (doğduğu yerde belirir), sonra pete doğru hızlanarak (ease-in) yay çizer
            var k = _t * _t * (3f - 2f * _t);
            k = k * k * 0.35f + k * 0.65f;
            var mid = (_start + end) * 0.5f + Vector3.up * (1.6f + Vector3.Distance(_start, end) * 0.25f) + _side;
            var a = Vector3.Lerp(_start, mid, k); var b = Vector3.Lerp(mid, end, k);
            transform.position = Vector3.Lerp(a, b, k);
            transform.Rotate(_spin * Time.deltaTime, Space.Self);
            var pop = Mathf.Clamp01(_t / 0.18f);
            var s = (1f - (1f - pop) * (1f - pop)) * (1.15f - 0.65f * Mathf.Clamp01((_t - 0.7f) / 0.3f));
            transform.localScale = Vector3.one * s;
            if (_t >= 1f)
            {
                _done = true;
                if (_burst != null) _burst.Landed();
                Destroy(gameObject);
            }
        }
    }

    /// <summary>Pet parlaması: göğüste ışık lekesi büyüyüp söner, ayakta halka açılır, pet kısa esner (yaylanır).</summary>
    public sealed class PetGlow : MonoBehaviour
    {
        private Transform _halo, _ring, _pet;
        private Vector3 _base;
        private float _t, _height;

        public static void Play(Transform pet, float height, Color c)
        {
            var old = pet.GetComponent<PetGlow>();
            if (old != null) { old._t = 0f; return; }
            var g = pet.gameObject.AddComponent<PetGlow>();
            g._pet = pet; g._height = height; g._base = pet.localScale;
            g._halo = GainFx.Glow(pet.parent, c, 1.4f, false);
            g._ring = GainFx.Glow(pet.parent, c, 1.2f, true);
        }

        private void Update()
        {
            _t += Time.deltaTime / 0.65f;
            var k = Mathf.Clamp01(_t);
            if (_halo != null)
            {
                _halo.position = _pet.position + Vector3.up * (_height * 0.6f);
                _halo.localScale = Vector3.one * _height * (1.4f + k * 1.6f) * Mathf.Sin(Mathf.Min(1f, k * 1.4f) * Mathf.PI) / Mathf.Max(0.001f, _pet.parent != null ? _pet.parent.lossyScale.x : 1f);
            }
            if (_ring != null)
            {
                _ring.position = _pet.position + Vector3.up * 0.06f;
                _ring.rotation = Quaternion.Euler(90f, 0f, 0f);
                _ring.localScale = Vector3.one * _height * (0.8f + k * 2.6f) * (1f - k) / Mathf.Max(0.001f, _pet.parent != null ? _pet.parent.lossyScale.x : 1f);
            }
            // esneme: önce basılır, sonra uzar, yerine oturur
            var sq = Mathf.Sin(k * Mathf.PI * 2f) * (1f - k) * 0.12f;
            _pet.localScale = new Vector3(_base.x * (1f + sq), _base.y * (1f - sq), _base.z * (1f + sq));
            if (k >= 1f)
            {
                _pet.localScale = _base;
                if (_halo != null) Destroy(_halo.gameObject);
                if (_ring != null) Destroy(_ring.gameObject);
                Destroy(this);
            }
        }
    }

    /// <summary>Kameraya dönük (billboard).</summary>
    public sealed class FaceCamera : MonoBehaviour
    {
        private void LateUpdate()
        {
            var cam = Camera.main;
            if (cam != null) transform.rotation = cam.transform.rotation;
        }
    }
}
