using System.Collections.Generic;
using Pofi.Logic.Island;
using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// 3B ada haritası (M5): kum ada, çimen, deniz ve her bölge için yer tutucu yapı. Ana sahneden uzakta
    /// (x = 200) kurulur; harita ekranı kamerayı buraya taşır. Yapılar dokunma için Collider taşır.
    /// </summary>
    public sealed class MapWorld : MonoBehaviour
    {
        public static readonly Vector3 Origin = new Vector3(200f, 0f, 0f);

        public readonly Dictionary<string, Transform> Regions = new Dictionary<string, Transform>();
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

            foreach (var v in views)
            {
                var r = v.Region;
                var root = new GameObject(r.Id).transform;
                root.SetParent(transform, false);
                root.localPosition = new Vector3(r.X, -0.02f, r.Z);
                var mat = v.Unlocked ? M(Hex(r.Color)) : _lockedMat;
                BuildShape(root, r.Shape, mat, v.Unlocked);
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
