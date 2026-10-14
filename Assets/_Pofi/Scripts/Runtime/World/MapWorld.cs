using System.Collections.Generic;
using Pofi.Logic.Island;
using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// 3B ada haritası (M5): kum ada, çimen, deniz ve her bölge için yer tutucu yapı. Ana sahneden uzakta
    /// (x = 200) kurulur; harita ekranı kamerayı buraya taşır. Yapılar dokunma için Collider taşır.
    /// </summary>
    /// <summary>Yavaş dönen ve hafifçe süzülen nesne.</summary>
    public sealed class Spin : MonoBehaviour
    {
        private Vector3 _base;
        private void Start() => _base = transform.localPosition;
        private void Update()
        {
            transform.Rotate(0f, 90f * Time.deltaTime, 0f, Space.World);
            transform.localPosition = _base + Vector3.up * (Mathf.Sin(Time.time * 2.5f) * 0.06f);
        }
    }

    public sealed class MapWorld : MonoBehaviour
    {
        public static readonly Vector3 Origin = new Vector3(200f, 0f, 0f);

        public readonly Dictionary<string, Transform> Regions = new Dictionary<string, Transform>();
        /// <summary>Bölge etiketinin yapı tabanından yüksekliği (gerçek modeller daha uzun olabilir).</summary>
        public readonly Dictionary<string, float> LabelHeights = new Dictionary<string, float>();

        /// <summary>Bölge → Meshy modeli (Resources/Env) ve haritadaki taban genişliği (m).</summary>
        private static readonly Dictionary<string, (string asset, float size)> RealRegions = new Dictionary<string, (string, float)>
        {
            { "region_home", ("b_home", 1.5f) }, { "region_shop", ("b_shop", 1.5f) }, { "region_task_board", ("b_task_board", 1.3f) },
            { "region_swim_cove", ("b_swim", 1.6f) }, { "region_surf_beach", ("b_surf", 1.4f) }, { "region_game_hut", ("b_game_hut", 1.5f) },
            { "region_ski_hill", ("b_ski_hill", 1.7f) }, { "region_garden", ("b_garden", 1.5f) }, { "region_pier", ("b_pier", 1.6f) },
            { "region_cave", ("b_cave", 1.6f) }, { "region_festival", ("b_festival", 1.6f) }, { "region_mountain", ("b_mountain", 2.0f) },
            { "region_lighthouse", ("b_lighthouse", 1.3f) },
        };

        /// <summary>Haritayı süsleyen küçük nesneler: ad, x, z, taban genişliği, dönüş.</summary>
        private static readonly (string asset, float x, float z, float size, float yaw)[] Props =
        {
            ("p_rock", -4.6f, -0.4f, 0.6f, 20f), ("p_rock", 4.7f, 1.6f, 0.5f, 140f), ("p_bush", -1.2f, -1.9f, 0.5f, 0f),
            ("p_bush", 1.3f, -1.9f, 0.5f, 90f), ("p_flowers", -0.6f, -0.2f, 0.5f, 0f), ("p_flowers", 2.2f, 1.2f, 0.45f, 60f),
            ("p_lantern", 0.9f, -1.2f, 0.35f, 200f), ("p_lantern", -0.9f, -1.2f, 0.35f, 160f), ("p_crates", 3.3f, -2.4f, 0.5f, 210f),
            ("p_boat", 5.4f, -2.8f, 0.9f, 120f), ("p_sign", 0.0f, -0.4f, 0.4f, 190f), ("p_fence", 2.0f, -0.1f, 0.6f, 180f),
            ("palm", -4.4f, 2.0f, 0.9f, 0f), ("palm", 4.6f, -0.5f, 0.9f, 70f), ("palm", 1.9f, 3.5f, 0.8f, 30f),
        };

        /// <summary>Gerçek model varsa kurar; yoksa false (yer tutucu şekle dönülür).</summary>
        private bool BuildReal(Transform root, string regionId, bool unlocked)
        {
            Transform model = null;
            if (regionId == "region_coconut_grove")
            {
                var a = RealAssets.Env("palm", root, 1.5f);
                var b = RealAssets.Env("palm", root, 1.15f);
                if (a == null) return false;
                a.localPosition = new Vector3(-0.25f, 0f, 0.15f);
                if (b != null) { b.localPosition = new Vector3(0.3f, 0f, -0.2f); b.localRotation = Quaternion.Euler(0f, 120f, 0f); }
                model = root;
            }
            else if (RealRegions.TryGetValue(regionId, out var info))
                model = RealAssets.EnvFootprint(info.asset, root, info.size, 205f);   // ön yüz kameraya, hafif çapraz
            if (model == null) return false;
            if (!unlocked) RealAssets.Tint(root, new Color(0.62f, 0.64f, 0.72f));
            return true;
        }

        private void BuildProps()
        {
            foreach (var p in Props)
            {
                var t = RealAssets.EnvFootprint(p.asset, transform, p.size, p.yaw);
                if (t != null) t.localPosition = new Vector3(p.x, -0.02f, p.z);
            }
        }
        private readonly List<Material> _mats = new List<Material>();
        private Material _lockedMat;

        public static MapWorld Create(IReadOnlyList<RegionView> views)
        {
            var go = new GameObject("MapWorld");
            go.transform.position = Origin;
            var w = go.AddComponent<MapWorld>();
            w.Build(views);
            return w;
        }

        private Material M(Color c, float smooth = 0.35f)
        {
            var m = PetModels.NewMaterial(c, smooth);
            _mats.Add(m);
            return m;
        }

        private static Color Hex(string h) => ColorUtility.TryParseHtmlString(h, out var c) ? c : Color.magenta;

        private void Build(IReadOnlyList<RegionView> views)
        {
            Prim(PrimitiveType.Cylinder, transform, new Vector3(0f, -0.2f, 1f), new Vector3(40f, 0.05f, 40f), M(new Color(0.25f, 0.72f, 0.95f), 0.85f), false);
            Prim(PrimitiveType.Sphere, transform, new Vector3(0f, -0.36f, 0.9f), new Vector3(11.6f, 0.6f, 9.6f), M(new Color(1f, 0.86f, 0.6f), 0.1f), false);
            Prim(PrimitiveType.Sphere, transform, new Vector3(0f, -0.25f, 1.0f), new Vector3(10.2f, 0.5f, 8.2f), M(new Color(0.48f, 0.82f, 0.42f), 0.15f), false);
            _lockedMat = M(new Color(0.72f, 0.74f, 0.8f), 0.2f);
            BuildProps();

            foreach (var v in views)
            {
                var r = v.Region;
                var root = new GameObject(r.Id).transform;
                root.SetParent(transform, false);
                root.localPosition = new Vector3(r.X, -0.02f, r.Z);
                if (!BuildReal(root, r.Id, v.Unlocked))
                    BuildShape(root, r.Shape, v.Unlocked ? M(Hex(r.Color)) : _lockedMat, v.Unlocked);
                LabelHeights[r.Id] = Mathf.Max(1.15f, RealAssets.WorldBounds(root).max.y - root.position.y + 0.1f);
                var col = root.gameObject.AddComponent<BoxCollider>();
                col.center = new Vector3(0f, 0.5f, 0f);
                col.size = new Vector3(1.3f, 1.2f, 1.3f);
                Regions[r.Id] = root;
            }
        }

        private void BuildShape(Transform t, string shape, Material m, bool unlocked)
        {
            var white = unlocked ? M(Color.white) : _lockedMat;
            var dark = unlocked ? M(new Color(0.45f, 0.3f, 0.2f)) : _lockedMat;
            var green = unlocked ? M(new Color(0.3f, 0.75f, 0.35f)) : _lockedMat;
            Prim(PrimitiveType.Cylinder, t, new Vector3(0f, 0.02f, 0f), new Vector3(1.2f, 0.04f, 1.2f), unlocked ? M(new Color(1f, 0.92f, 0.75f)) : _lockedMat, true);
            switch (shape)
            {
                case "house":
                    Prim(PrimitiveType.Cube, t, new Vector3(0f, 0.3f, 0f), new Vector3(0.7f, 0.5f, 0.6f), white, true);
                    Prim(PrimitiveType.Cube, t, new Vector3(0f, 0.66f, 0f), new Vector3(0.55f, 0.55f, 0.66f), m, true).transform.localRotation = Quaternion.Euler(0f, 0f, 45f);
                    Prim(PrimitiveType.Cube, t, new Vector3(0f, 0.2f, -0.31f), new Vector3(0.18f, 0.3f, 0.02f), dark, true);
                    break;
                case "board":
                    Prim(PrimitiveType.Cylinder, t, new Vector3(-0.3f, 0.35f, 0f), new Vector3(0.06f, 0.35f, 0.06f), dark, true);
                    Prim(PrimitiveType.Cylinder, t, new Vector3(0.3f, 0.35f, 0f), new Vector3(0.06f, 0.35f, 0.06f), dark, true);
                    Prim(PrimitiveType.Cube, t, new Vector3(0f, 0.6f, 0f), new Vector3(0.8f, 0.45f, 0.06f), m, true);
                    break;
                case "palm":
                    for (var i = 0; i < 2; i++)
                    {
                        var p = new Vector3(i == 0 ? -0.2f : 0.25f, 0f, i == 0 ? 0.1f : -0.15f);
                        Prim(PrimitiveType.Cylinder, t, p + new Vector3(0f, 0.45f, 0f), new Vector3(0.08f, 0.45f, 0.08f), dark, true);
                        Prim(PrimitiveType.Sphere, t, p + new Vector3(0f, 0.95f, 0f), new Vector3(0.6f, 0.18f, 0.6f), m, true);
                    }
                    break;
                case "pool":
                    Prim(PrimitiveType.Cylinder, t, new Vector3(0f, 0.06f, 0f), new Vector3(1.0f, 0.06f, 1.0f), white, true);
                    Prim(PrimitiveType.Cylinder, t, new Vector3(0f, 0.08f, 0f), new Vector3(0.85f, 0.06f, 0.85f), m, true);
                    break;
                case "hill":
                    Prim(PrimitiveType.Sphere, t, new Vector3(0f, 0.2f, 0f), new Vector3(1.2f, 1.2f, 1.1f), m, true);
                    Prim(PrimitiveType.Sphere, t, new Vector3(0f, 0.68f, 0f), new Vector3(0.5f, 0.3f, 0.5f), white, true);
                    break;
                case "garden":
                    for (var i = 0; i < 3; i++)
                        Prim(PrimitiveType.Cube, t, new Vector3(-0.32f + i * 0.32f, 0.1f, 0f), new Vector3(0.24f, 0.12f, 0.8f), dark, true);
                    for (var i = 0; i < 3; i++)
                        Prim(PrimitiveType.Sphere, t, new Vector3(-0.32f + i * 0.32f, 0.25f, 0f), new Vector3(0.18f, 0.18f, 0.18f), green, true);
                    break;
                case "pier":
                    Prim(PrimitiveType.Cube, t, new Vector3(0.25f, 0.12f, 0f), new Vector3(1.0f, 0.06f, 0.4f), dark, true);
                    Prim(PrimitiveType.Cylinder, t, new Vector3(0.7f, 0.1f, 0.18f), new Vector3(0.06f, 0.2f, 0.06f), dark, true);
                    Prim(PrimitiveType.Cylinder, t, new Vector3(0.7f, 0.1f, -0.18f), new Vector3(0.06f, 0.2f, 0.06f), dark, true);
                    break;
                case "tent":
                    Prim(PrimitiveType.Cylinder, t, new Vector3(0f, 0.22f, 0f), new Vector3(0.8f, 0.22f, 0.8f), white, true);
                    Prim(PrimitiveType.Capsule, t, new Vector3(0f, 0.55f, 0f), new Vector3(0.8f, 0.35f, 0.8f), m, true);
                    break;
                case "tower":
                    Prim(PrimitiveType.Cylinder, t, new Vector3(0f, 0.6f, 0f), new Vector3(0.36f, 0.6f, 0.36f), white, true);
                    Prim(PrimitiveType.Cylinder, t, new Vector3(0f, 0.75f, 0f), new Vector3(0.38f, 0.1f, 0.38f), m, true);
                    Prim(PrimitiveType.Sphere, t, new Vector3(0f, 1.3f, 0f), new Vector3(0.3f, 0.3f, 0.3f), m, true);
                    break;
                default:
                    Prim(PrimitiveType.Cube, t, new Vector3(0f, 0.3f, 0f), new Vector3(0.6f, 0.6f, 0.6f), m, true);
                    break;
            }
        }

        /// <summary>Günlük keşif parıltısı: dönen küçük yıldız; dokunma için "sparkle_N" adlı collider.</summary>
        public Transform AddSparkle(int index, float x, float z)
        {
            var root = new GameObject("sparkle_" + index).transform;
            root.SetParent(transform, false);
            root.localPosition = new Vector3(x, 0.35f, z);
            var gold = M(new Color(1f, 0.85f, 0.2f), 0.9f);
            Prim(PrimitiveType.Cube, root, Vector3.zero, new Vector3(0.22f, 0.22f, 0.22f), gold, true).transform.localRotation = Quaternion.Euler(45f, 0f, 45f);
            Prim(PrimitiveType.Sphere, root, Vector3.zero, Vector3.one * 0.16f, M(Color.white, 0.9f), false);
            var col = root.gameObject.AddComponent<SphereCollider>();
            col.radius = 0.5f;
            root.gameObject.AddComponent<Spin>();
            return root;
        }

        private static GameObject Prim(PrimitiveType type, Transform parent, Vector3 pos, Vector3 scale, Material m, bool shadows)
        {
            var go = GameObject.CreatePrimitive(type);
            go.transform.SetParent(parent, false);
            go.transform.localPosition = pos;
            go.transform.localScale = scale;
            var r = go.GetComponent<Renderer>();
            r.sharedMaterial = m;
            if (!shadows) r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            Destroy(go.GetComponent<Collider>());
            return go;
        }

        private void OnDestroy()
        {
            foreach (var m in _mats) if (m != null) Destroy(m);
        }
    }
}
