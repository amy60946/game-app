using System.Collections.Generic;
using Pofi.Logic.Home;
using Pofi.Logic.State;
using UnityEngine;

namespace Pofi.World
{
    /// <summary>Ev/dekor eşyalarının yer tutucu 3B modelleri; yerleşim ızgarası petin etrafına ve arkasına yayılır.</summary>
    public static class HomeProps
    {
        public const string RootName = "HomeProps";

        /// <summary>Gerçek modelin taban genişliği (m).</summary>
        private static readonly Dictionary<string, float> Footprints = new Dictionary<string, float>
        {
            ["home_bed"] = 1.2f, ["home_rug"] = 1.4f, ["home_lamp"] = 0.6f, ["home_bookshelf"] = 1.0f, ["home_aquarium"] = 0.8f,
            ["decor_umbrella"] = 1.4f, ["decor_sandcastle"] = 0.9f, ["decor_palm"] = 0.7f, ["decor_lanterns"] = 1.3f,
        };

        public static Vector3 CellToLocal(int x, int y, bool expanded)
        {
            var (w, h) = HomeLayout.Size(expanded);
            return new Vector3((x - (w - 1) / 2f) * 0.78f, 0f, (y - (h - 1) / 2f) * 0.72f + 0.7f);   // gerçek pet ~1,75 m
        }

        public static void Apply(Transform parent, IEnumerable<Placement> placements, bool expanded)
        {
            var old = parent.Find(RootName);
            if (old != null)
            {
                foreach (var r in old.GetComponentsInChildren<Renderer>())
                    foreach (var m in r.sharedMaterials) if (m != null && !RealAssets.IsShared(m)) Object.Destroy(m);
                Object.Destroy(old.gameObject);
            }
            var root = new GameObject(RootName).transform;
            root.SetParent(parent, false);
            foreach (var p in placements)
            {
                var t = new GameObject(p.ItemId).transform;
                t.SetParent(root, false);
                t.localPosition = CellToLocal((int)p.X, (int)p.Y, expanded);
                t.localRotation = Quaternion.Euler(0f, p.Rotation, 0f);
                if (Footprints.TryGetValue(p.ItemId, out var fp) && RealAssets.ItemFootprint(p.ItemId, t, fp, 180f) != null) continue;   // önü kameraya
                t.localScale = Vector3.one * 0.9f;
                Build(t, p.ItemId);
            }
            foreach (var c in root.GetComponentsInChildren<Collider>()) Object.Destroy(c);
        }

        private static Material M(Color c, float s = 0.4f) => PetModels.NewMaterial(c, s);
        private static Color H(string h) => ColorUtility.TryParseHtmlString(h, out var c) ? c : Color.magenta;

        private static void Build(Transform t, string id)
        {
            switch (id)
            {
                case "home_bed":
                    P(PrimitiveType.Cube, t, new Vector3(0f, 0.15f, 0f), new Vector3(0.7f, 0.3f, 1.0f), M(H("#8C5A3C")));
                    P(PrimitiveType.Cube, t, new Vector3(0f, 0.32f, 0.05f), new Vector3(0.66f, 0.08f, 0.9f), M(H("#7AB8F5")));
                    P(PrimitiveType.Sphere, t, new Vector3(0f, 0.38f, 0.38f), new Vector3(0.5f, 0.12f, 0.2f), M(Color.white));
                    break;
                case "home_rug":
                    P(PrimitiveType.Cylinder, t, new Vector3(0f, 0.01f, 0f), new Vector3(1.0f, 0.01f, 0.8f), M(H("#FF6FAE"), 0.1f));
                    break;
                case "home_lamp":
                    P(PrimitiveType.Cylinder, t, new Vector3(0f, 0.4f, 0f), new Vector3(0.05f, 0.4f, 0.05f), M(H("#30304A")));
                    P(PrimitiveType.Cylinder, t, new Vector3(0f, 0.85f, 0f), new Vector3(0.3f, 0.12f, 0.3f), M(H("#FFE38A"), 0.9f));
                    break;
                case "home_bookshelf":
                    P(PrimitiveType.Cube, t, new Vector3(0f, 0.55f, 0f), new Vector3(0.8f, 1.1f, 0.3f), M(H("#A0703F")));
                    string[] books = { "#E8453C", "#2F80ED", "#FFC400", "#2FB55A" };
                    for (var i = 0; i < 4; i++)
                        P(PrimitiveType.Cube, t, new Vector3(-0.27f + i * 0.18f, 0.75f, -0.1f), new Vector3(0.12f, 0.3f, 0.2f), M(H(books[i])));
                    break;
                case "home_aquarium":
                    P(PrimitiveType.Cube, t, new Vector3(0f, 0.2f, 0f), new Vector3(0.8f, 0.4f, 0.4f), M(H("#5E3A22")));
                    P(PrimitiveType.Cube, t, new Vector3(0f, 0.6f, 0f), new Vector3(0.78f, 0.4f, 0.38f), M(H("#8EDCFF"), 0.95f));
                    P(PrimitiveType.Sphere, t, new Vector3(0.1f, 0.62f, -0.1f), new Vector3(0.12f, 0.08f, 0.05f), M(H("#FF8A2A")));
                    break;
                case "decor_umbrella":
                    P(PrimitiveType.Cylinder, t, new Vector3(0f, 0.6f, 0f), new Vector3(0.04f, 0.6f, 0.04f), M(Color.white));
                    P(PrimitiveType.Sphere, t, new Vector3(0f, 1.2f, 0f), new Vector3(1.2f, 0.3f, 1.2f), M(H("#FF5A7A")));
                    break;
                case "decor_sandcastle":
                    P(PrimitiveType.Cube, t, new Vector3(0f, 0.15f, 0f), new Vector3(0.7f, 0.3f, 0.7f), M(H("#F2D27A"), 0.1f));
                    for (var i = 0; i < 4; i++)
                        P(PrimitiveType.Cylinder, t, new Vector3(i % 2 == 0 ? -0.3f : 0.3f, 0.4f, i < 2 ? -0.3f : 0.3f), new Vector3(0.18f, 0.25f, 0.18f), M(H("#F2D27A"), 0.1f));
                    break;
                case "decor_palm":
                    P(PrimitiveType.Cylinder, t, new Vector3(0f, 0.7f, 0f), new Vector3(0.12f, 0.7f, 0.12f), M(H("#8C5A3C")));
                    P(PrimitiveType.Sphere, t, new Vector3(0f, 1.45f, 0f), new Vector3(1.1f, 0.3f, 1.1f), M(H("#46D063")));
                    break;
                case "decor_lanterns":
                    string[] cols = { "#FF5A7A", "#FFC83D", "#3DC9FF" };
                    for (var i = 0; i < 3; i++)
                    {
                        P(PrimitiveType.Cylinder, t, new Vector3(-0.35f + i * 0.35f, 0.4f, 0f), new Vector3(0.03f, 0.4f, 0.03f), M(H("#30304A")));
                        P(PrimitiveType.Sphere, t, new Vector3(-0.35f + i * 0.35f, 0.85f, 0f), new Vector3(0.2f, 0.25f, 0.2f), M(H(cols[i]), 0.9f));
                    }
                    break;
                default:
                    P(PrimitiveType.Cube, t, new Vector3(0f, 0.25f, 0f), new Vector3(0.5f, 0.5f, 0.5f), M(H("#9B7BFF")));
                    break;
            }
        }

        private static void P(PrimitiveType type, Transform parent, Vector3 pos, Vector3 scale, Material m)
        {
            var go = GameObject.CreatePrimitive(type);
            go.transform.SetParent(parent, false);
            go.transform.localPosition = pos;
            go.transform.localScale = scale;
            go.GetComponent<Renderer>().sharedMaterial = m;
        }
    }
}
