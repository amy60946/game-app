using Pofi.Logic.Island;
using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// Adadaki toplama noktası (kütük / çalı / taş) ya da kulübe yeri: modeli taşır, vuruşta sallanır ve yonga saçar,
    /// bitince küçülüp kaybolur, yeniden çıkınca büyüyerek belirir. Dokunma için "gather_N" / "gather_site" adlı çarpıştırıcı.
    /// Modeller: g_log (kodla, art/code3d/gather_art.py), p_bush, p_rock (Meshy), g_site / g_hut (art/code3d/house_cottage.py).
    /// </summary>
    public sealed class GatherSpot : MonoBehaviour
    {
        public int Index { get; private set; }
        public GatherKind Kind { get; private set; }
        public bool IsSite { get; private set; }
        /// <summary>Yürüme engeli yarıçapı (pet içinden geçmesin).</summary>
        public float Radius { get; private set; }
        /// <summary>Simgenin duracağı yükseklik (model tepesi).</summary>
        public float Top { get; private set; }

        private Transform _model;
        private float _shake, _scaleT = 1f, _scaleFrom = 1f, _scaleTo = 1f, _scaleDur = 0.3f;
        private bool _hideAtEnd;
        private Color _chip;

        private static Material _chipWood, _chipLeaf, _chipStone, _dust;

        public static GatherSpot Create(Transform parent, GatherNode n, Vector3 local)
        {
            var root = new GameObject("gather_" + n.Index).transform;
            root.SetParent(parent, false);
            root.localPosition = local;
            var s = root.gameObject.AddComponent<GatherSpot>();
            s.Index = n.Index; s.Kind = n.Kind;
            switch (n.Kind)
            {
                case GatherKind.Log: s._model = RealAssets.EnvFootprint("g_log", root, 1.6f, n.Yaw); s.Radius = 0.75f; s._chip = new Color(0.86f, 0.62f, 0.36f); break;
                case GatherKind.Bush: s._model = RealAssets.EnvFootprint("p_bush", root, 1.3f, n.Yaw); s.Radius = 0.6f; s._chip = new Color(0.36f, 0.72f, 0.3f); break;
                default: s._model = RealAssets.EnvFootprint("p_rock", root, 1.1f, n.Yaw); s.Radius = 0.55f; s._chip = new Color(0.62f, 0.6f, 0.56f); break;
            }
            if (s._model == null) s._model = Placeholder(root, n.Kind);
            s.Fit();
            return s;
        }

        /// <summary>Kulübe yeri: inşaat alanı ya da (bitmişse) kulübe; kapısı <paramref name="yaw"/> yönüne bakar.</summary>
        public static GatherSpot CreateSite(Transform parent, Vector3 local, float yaw, bool built)
        {
            var root = new GameObject("gather_site").transform;
            root.SetParent(parent, false);
            root.localPosition = local;
            root.localRotation = Quaternion.Euler(0f, yaw, 0f);
            var s = root.gameObject.AddComponent<GatherSpot>();
            s.IsSite = true; s.Index = -1;
            s.SetSiteModel(built);
            return s;
        }

        private void SetSiteModel(bool built)
        {
            if (_model != null) Destroy(_model.gameObject);
            _model = RealAssets.EnvFootprint(built ? "g_hut" : "g_site", transform, built ? 4.2f : 3.2f, 0f);
            if (_model == null) _model = Placeholder(transform, GatherKind.Log);
            Radius = built ? 2.1f : 0f;          // inşaat alanından geçilebilir, kulübeden geçilmez
            Fit();
        }

        private void Fit()
        {
            var b = RealAssets.WorldBounds(_model);
            Top = Mathf.Max(0.6f, b.max.y - transform.position.y);
            var col = gameObject.GetComponent<SphereCollider>() ?? gameObject.AddComponent<SphereCollider>();
            col.radius = Mathf.Max(0.8f, Mathf.Max(b.extents.x, b.extents.z));
            col.center = new Vector3(0f, Top * 0.45f, 0f);
        }

        private static Transform Placeholder(Transform parent, GatherKind k)
        {
            var go = GameObject.CreatePrimitive(k == GatherKind.Log ? PrimitiveType.Capsule : PrimitiveType.Sphere);
            Destroy(go.GetComponent<Collider>());
            go.transform.SetParent(parent, false);
            go.transform.localScale = k == GatherKind.Log ? new Vector3(0.6f, 0.8f, 0.6f) : Vector3.one * 0.9f;
            go.transform.localPosition = new Vector3(0f, 0.4f, 0f);
            if (k == GatherKind.Log) go.transform.localRotation = Quaternion.Euler(0f, 0f, 90f);
            return go.transform;
        }

        /// <summary>Vuruş: sallanma + yonga/yaprak/taş parçacıkları.</summary>
        public void Hit()
        {
            _shake = 1f;
            Chips(Kind == GatherKind.Bush ? 7 : 6);
        }

        /// <summary>Son vuruş: küçülüp kaybolur.</summary>
        public void Vanish()
        {
            Chips(10);
            Animate(1f, 0f, 0.35f, hide: true);
        }

        /// <summary>Yeniden çıkma: büyüyerek belirir.</summary>
        public void PopIn()
        {
            gameObject.SetActive(true);
            Animate(0f, 1f, 0.45f, hide: false);
        }

        /// <summary>İnşa: alan kaybolur, kulübe toz bulutuyla büyüyerek yükselir.</summary>
        public void BuildHut()
        {
            SetSiteModel(true);
            Animate(0.05f, 1f, 0.9f, hide: false);
            for (var i = 0; i < 10; i++)
            {
                var a = i * Mathf.PI * 2f / 10f;
                Puff(transform.position + new Vector3(Mathf.Cos(a) * 2.2f, 0.3f, Mathf.Sin(a) * 2.2f), 0.9f + (i % 3) * 0.25f);
            }
        }

        private void Animate(float from, float to, float dur, bool hide)
        {
            _scaleFrom = from; _scaleTo = to; _scaleDur = dur; _scaleT = 0f; _hideAtEnd = hide;
            _model.localScale = Vector3.one * Mathf.Max(0.001f, from) * BaseScale;
        }

        private float _baseScale = -1f;
        private float BaseScale { get { if (_baseScale < 0f) _baseScale = _model.localScale.x; return _baseScale; } }

        private void Update()
        {
            if (_model == null) return;
            var bs = BaseScale;
            if (_scaleT < 1f)
            {
                _scaleT = Mathf.Min(1f, _scaleT + Time.deltaTime / _scaleDur);
                var k = _scaleTo > _scaleFrom ? BackOut(_scaleT) : _scaleT * _scaleT;
                var s = Mathf.LerpUnclamped(_scaleFrom, _scaleTo, k);
                _model.localScale = Vector3.one * Mathf.Max(0.001f, s) * bs;
                if (_scaleT >= 1f && _hideAtEnd) { _model.localScale = Vector3.one * bs; gameObject.SetActive(false); return; }
            }
            if (_shake > 0f)
            {
                _shake = Mathf.Max(0f, _shake - Time.deltaTime * 4f);
                var w = Mathf.Sin(Time.time * 55f) * _shake;
                _model.localRotation = Quaternion.Euler(w * 6f, _model.localRotation.eulerAngles.y, w * 4f);
                if (_scaleT >= 1f) _model.localScale = Vector3.one * bs * (1f + _shake * 0.06f);
            }
        }

        private static float BackOut(float t) { const float c = 1.70158f; t -= 1f; return t * t * ((c + 1f) * t + c) + 1f; }

        // ------------------------------------------------------------------ parçacıklar

        private void Chips(int n)
        {
            var m = ChipMaterial();
            for (var i = 0; i < n; i++)
            {
                var go = GameObject.CreatePrimitive(Kind == GatherKind.Bush ? PrimitiveType.Sphere : PrimitiveType.Cube);
                Destroy(go.GetComponent<Collider>());
                go.GetComponent<Renderer>().sharedMaterial = m;
                go.GetComponent<Renderer>().shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                go.transform.position = transform.position + Vector3.up * (Top * 0.6f) + Random.insideUnitSphere * 0.25f;
                var sz = Kind == GatherKind.Bush ? 0.12f : 0.1f;
                go.transform.localScale = Kind == GatherKind.Bush ? new Vector3(sz * 1.6f, sz * 0.3f, sz) : Vector3.one * sz;
                go.transform.rotation = Random.rotation;
                var v = Random.insideUnitSphere * 2.2f; v.y = Random.Range(2.5f, 4.2f);
                go.AddComponent<ChipFly>().Velocity = v;
            }
        }

        private Material ChipMaterial()
        {
            switch (Kind)
            {
                case GatherKind.Bush: return _chipLeaf != null ? _chipLeaf : _chipLeaf = PetModels.NewMaterial(_chip, 0.2f);
                case GatherKind.Rock: return _chipStone != null ? _chipStone : _chipStone = PetModels.NewMaterial(_chip, 0.2f);
                default: return _chipWood != null ? _chipWood : _chipWood = PetModels.NewMaterial(_chip, 0.2f);
            }
        }

        private static void Puff(Vector3 at, float size)
        {
            if (_dust == null) _dust = PetModels.NewMaterial(new Color(0.96f, 0.93f, 0.86f), 0.1f);
            var go = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            Destroy(go.GetComponent<Collider>());
            go.GetComponent<Renderer>().sharedMaterial = _dust;
            go.GetComponent<Renderer>().shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            go.transform.position = at;
            go.AddComponent<PuffGrow>().Size = size;
        }
    }

    /// <summary>Uçan yonga: yerçekimiyle düşer, döner, küçülerek kaybolur.</summary>
    public sealed class ChipFly : MonoBehaviour
    {
        public Vector3 Velocity;
        private float _t;
        private Vector3 _spin, _scale;
        private void Start() { _spin = Random.insideUnitSphere * 720f; _scale = transform.localScale; }
        private void Update()
        {
            _t += Time.deltaTime;
            Velocity += Vector3.down * 9.8f * Time.deltaTime;
            transform.position += Velocity * Time.deltaTime;
            transform.Rotate(_spin * Time.deltaTime);
            transform.localScale = _scale * Mathf.Clamp01(1.2f - _t / 0.7f);
            if (_t > 0.75f) Destroy(gameObject);
        }
    }

    /// <summary>Toz bulutu: büyür, yükselir, söner (küçülür).</summary>
    public sealed class PuffGrow : MonoBehaviour
    {
        public float Size = 1f;
        private float _t;
        private void Update()
        {
            _t += Time.deltaTime / 0.9f;
            var s = Size * Mathf.Sin(Mathf.Clamp01(_t) * Mathf.PI) * (0.6f + _t * 0.6f);
            transform.localScale = Vector3.one * Mathf.Max(0.001f, s);
            transform.position += Vector3.up * Time.deltaTime * 0.8f;
            if (_t >= 1f) Destroy(gameObject);
        }
    }
}
