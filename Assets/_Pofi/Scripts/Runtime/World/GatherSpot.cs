using Pofi.Logic.Island;
using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// Adadaki toplama noktası (kütük / çalı / taş) ya da kulübe yeri: modeli taşır, vuruşta sallanır ve yonga saçar,
    /// bitince küçülüp kaybolur, yeniden çıkınca büyüyerek belirir. Dokunma için "gather_N" / "gather_site" adlı çarpıştırıcı.
    /// Modeller (kodla, art/code3d/assets_town.py + export_game.py): p_log, p_bush, p_rock, p_site, b_hut.
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
                case GatherKind.Log: s._model = RealAssets.EnvFootprint("p_log", root, 1.6f, n.Yaw); s.Radius = 0.75f; s._chip = new Color(0.86f, 0.62f, 0.36f); break;
                case GatherKind.Bush: s._model = RealAssets.EnvFootprint("p_bush", root, 1.3f, n.Yaw); s.Radius = 0.6f; s._chip = new Color(0.36f, 0.72f, 0.3f); break;
                case GatherKind.Coconut:   // yerde hindistan cevizi (GB17): üstünden geçilir, engel değil
                    s._model = RealAssets.EnvFootprint("p_coconut", root, 0.75f, n.Yaw); s.Radius = 0f; s._chip = new Color(0.55f, 0.36f, 0.2f);
                    if (s._model == null) s._model = Nuts(root, n.Yaw);
                    break;
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
            _model = RealAssets.EnvFootprint(built ? "b_hut" : "p_site", transform, built ? 4.2f : 3.2f, 0f);
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

        /// <summary>Model yoksa: iki kahverengi ceviz (biri yarık, beyaz içli) — kodla.</summary>
        private static Transform Nuts(Transform parent, float yaw)
        {
            var root = new GameObject("nuts").transform;
            root.SetParent(parent, false);
            root.localRotation = Quaternion.Euler(0f, yaw, 0f);
            var husk = PetModels.NewMaterial(new Color(0.48f, 0.3f, 0.16f), 0.25f);
            var flesh = PetModels.NewMaterial(new Color(0.97f, 0.95f, 0.88f), 0.3f);
            void Ball(Vector3 at, float r, Material m, Vector3 squash)
            {
                var go = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                Destroy(go.GetComponent<Collider>());
                go.transform.SetParent(root, false);
                go.transform.localPosition = at;
                go.transform.localScale = Vector3.Scale(Vector3.one * r * 2f, squash);
                go.GetComponent<MeshRenderer>().sharedMaterial = m;
            }
            Ball(new Vector3(-0.12f, 0.12f, 0f), 0.13f, husk, new Vector3(1f, 0.9f, 1.1f));
            Ball(new Vector3(0.14f, 0.1f, 0.06f), 0.12f, husk, new Vector3(1.05f, 0.85f, 1f));
            Ball(new Vector3(0.15f, 0.17f, 0.06f), 0.085f, flesh, new Vector3(1f, 0.25f, 1f));   // yarık cevizin beyaz içi
            return root;
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
            Chips(Kind == GatherKind.Bush ? 7 : Kind == GatherKind.Coconut ? 3 : 6);
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

        // ------------------------------------------------------------------ O2 şantiye (23 Ekim 2026)
        // Teslim edilen her odun, dal ve taş yerdeki yığına eklenir; köşe direkleri malzeme geldikçe yükselir, malzeme tamamsa
        // üst kirişler de yerinde durur. Sayılar sayaç panelinde değil, gözle görülür.
        private Transform _stack;
        private int _pw = -1, _pb = -1, _ps = -1;
        private float _stackPop;
        private static Material _logMat, _endMat, _barkMat, _stoneMat;

        public void SetProgress(int wood, int branch, int stone, float progress)
        {
            if (!IsSite || Radius > 0f) return;   // kulübe yapıldıysa yığın yok
            wood = Mathf.Min(wood, 6); branch = Mathf.Min(branch, 4); stone = Mathf.Min(stone, 3);
            if (wood == _pw && branch == _pb && stone == _ps) return;
            var grew = _pw >= 0 && (wood > _pw || branch > _pb || stone > _ps);
            _pw = wood; _pb = branch; _ps = stone;
            if (_stack != null) Destroy(_stack.gameObject);
            _stack = new GameObject("stack").transform;
            _stack.SetParent(transform, false);
            if (_logMat == null)
            {
                _logMat = PetModels.NewMaterial(new Color(0.62f, 0.4f, 0.22f), 0.35f);
                _endMat = PetModels.NewMaterial(new Color(0.93f, 0.78f, 0.52f), 0.35f);
                _barkMat = PetModels.NewMaterial(new Color(0.45f, 0.3f, 0.18f), 0.3f);
                _stoneMat = PetModels.NewMaterial(new Color(0.66f, 0.67f, 0.7f), 0.4f);
            }
            // odun: 3-2-1 piramit (sol arka)
            int[] row = { 0, 0, 0, 1, 1, 2 };
            float[] col = { -1f, 0f, 1f, -0.5f, 0.5f, 0f };
            for (var i = 0; i < wood; i++)
            {
                var at = new Vector3(-2.1f, 0.16f + row[i] * 0.27f, 0.7f + col[i] * 0.3f);
                Piece(PrimitiveType.Cylinder, at, Quaternion.Euler(0f, 0f, 90f), new Vector3(0.28f, 0.48f, 0.28f), _logMat);
                Piece(PrimitiveType.Cylinder, at + new Vector3(0.49f, 0f, 0f), Quaternion.Euler(0f, 0f, 90f), new Vector3(0.24f, 0.01f, 0.24f), _endMat);
            }
            // dal demeti (sağ arka): çapraz duran ince dallar
            for (var i = 0; i < branch; i++)
                Piece(PrimitiveType.Cylinder, new Vector3(2.0f + (i - 1.5f) * 0.12f, 0.12f + i * 0.05f, 0.8f), Quaternion.Euler(0f, 25f * (i % 2 == 0 ? 1f : -1f), 86f),
                    new Vector3(0.08f, 0.55f, 0.08f), _barkMat);
            // taşlar (önde): yassı yuvarlak
            for (var i = 0; i < stone; i++)
                Piece(PrimitiveType.Sphere, new Vector3((i - 1f) * 0.5f, 0.15f, -2.0f), Quaternion.Euler(0f, i * 40f, 0f),
                    new Vector3(0.48f, 0.3f, 0.42f) * (1f - i * 0.08f), _stoneMat);
            // köşe direkleri ve tamamlanınca üst kirişler
            var h = Mathf.Lerp(0.15f, 2.1f, Mathf.Clamp01(progress));
            for (var i = 0; i < 4; i++)
            {
                var x = (i % 2 == 0 ? -1f : 1f) * 1.25f; var z = (i < 2 ? -1f : 1f) * 1.25f;
                Piece(PrimitiveType.Cylinder, new Vector3(x, h * 0.5f, z), Quaternion.identity, new Vector3(0.16f, h * 0.5f, 0.16f), _logMat);
            }
            if (progress >= 0.999f)
                for (var i = 0; i < 4; i++)
                {
                    var along = i % 2 == 0; var off = (i < 2 ? -1f : 1f) * 1.25f;
                    Piece(PrimitiveType.Cylinder, along ? new Vector3(0f, h, off) : new Vector3(off, h, 0f),
                        Quaternion.Euler(along ? 0f : 90f, 0f, along ? 90f : 0f), new Vector3(0.12f, 1.33f, 0.12f), _logMat);
                }
            if (grew) { _stackPop = 1f; Puff(transform.position + new Vector3(0f, 0.4f, 0f), 1.1f); }
        }

        private void Piece(PrimitiveType type, Vector3 at, Quaternion rot, Vector3 scale, Material m)
        {
            var go = GameObject.CreatePrimitive(type);
            Destroy(go.GetComponent<Collider>());
            go.transform.SetParent(_stack, false);
            go.transform.localPosition = at; go.transform.localRotation = rot; go.transform.localScale = scale;
            var r = go.GetComponent<MeshRenderer>(); r.sharedMaterial = m;
        }

        /// <summary>İnşa: alan kaybolur, kulübe toz bulutuyla büyüyerek yükselir.</summary>
        public void BuildHut()
        {
            if (_stack != null) { Destroy(_stack.gameObject); _stack = null; }
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
            if (_stackPop > 0f && _stack != null)
            {
                // yeni parça gelince yığın kısa bir "pop" yapar (ezilip yaylanır)
                _stackPop = Mathf.Max(0f, _stackPop - Time.deltaTime / 0.45f);
                var k = Mathf.Sin((1f - _stackPop) * Mathf.PI * 2f) * _stackPop * 0.12f;
                _stack.localScale = new Vector3(1f + k, 1f - k, 1f + k);
            }
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
