using System.Collections.Generic;
using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// Günün küçük sürprizleri (O3, 23 Ekim 2026): kumsalda şişe içinde not, yürüyüşe çıkmış yengeç ailesi, deniz kabukları,
    /// el sallayan deniz yıldızı; içeride kelebek ve tepede tur atan martı. Hepsi kodla (kredisiz). Dokununca küçük bir tepki
    /// verip kaybolur; ödül bir kez (Logic.Story.DailySurprises). Kaçırılırsa ceza yok. Dokunma için "surprise_N" collider.
    /// </summary>
    public sealed class SurpriseView : MonoBehaviour
    {
        public string Kind { get; private set; }
        private readonly List<Transform> _parts = new List<Transform>();
        private readonly List<Vector3> _base = new List<Vector3>();
        private float _t, _gone = -1f, _seed;
        private static readonly Dictionary<string, Material> Mats = new Dictionary<string, Material>();

        public static SurpriseView Create(Transform parent, int index, string kind, Vector3 local)
        {
            var root = new GameObject("surprise_" + index).transform;
            root.SetParent(parent, false);
            root.localPosition = local;
            root.localRotation = Quaternion.Euler(0f, (index * 137) % 360, 0f);
            var v = root.gameObject.AddComponent<SurpriseView>();
            v.Kind = kind; v._seed = index * 1.7f;
            var col = root.gameObject.AddComponent<SphereCollider>();
            col.radius = kind == "gull" ? 3.2f : kind == "butterfly" ? 1.2f : 1.0f;
            col.center = new Vector3(0f, kind == "gull" ? 4.5f : kind == "butterfly" ? 1.3f : 0.35f, 0f);
            v.Build();
            return v;
        }

        private static Material M(string key, Color c)
        {
            if (Mats.TryGetValue(key, out var m) && m != null) return m;
            return Mats[key] = PetModels.NewMaterial(c, 0.6f);
        }

        private Transform P(PrimitiveType type, Vector3 at, Vector3 scale, Material m, Transform parent = null, Quaternion? rot = null)
        {
            var go = GameObject.CreatePrimitive(type);
            Destroy(go.GetComponent<Collider>());
            go.transform.SetParent(parent != null ? parent : transform, false);
            go.transform.localPosition = at; go.transform.localScale = scale;
            if (rot.HasValue) go.transform.localRotation = rot.Value;
            go.GetComponent<MeshRenderer>().sharedMaterial = m;
            return go.transform;
        }

        private Transform Group(string name, Vector3 at)
        {
            var g = new GameObject(name).transform; g.SetParent(transform, false); g.localPosition = at;
            _parts.Add(g); _base.Add(at);
            return g;
        }

        private void Build()
        {
            switch (Kind)
            {
                case "bottle":
                {
                    // kumda yan yatmış yeşil şişe, tıpa, içinde kıvrık not
                    var g = Group("bottle", new Vector3(0f, 0.13f, 0f));
                    var glass = M("glass", new Color(0.56f, 0.86f, 0.74f));
                    P(PrimitiveType.Capsule, Vector3.zero, new Vector3(0.24f, 0.26f, 0.24f), glass, g, Quaternion.Euler(0f, 0f, 90f));
                    P(PrimitiveType.Cylinder, new Vector3(0.32f, 0f, 0f), new Vector3(0.1f, 0.09f, 0.1f), glass, g, Quaternion.Euler(0f, 0f, 90f));
                    P(PrimitiveType.Cylinder, new Vector3(0.43f, 0f, 0f), new Vector3(0.09f, 0.04f, 0.09f), M("cork", new Color(0.7f, 0.5f, 0.3f)), g, Quaternion.Euler(0f, 0f, 90f));
                    P(PrimitiveType.Cylinder, new Vector3(-0.02f, 0.01f, 0f), new Vector3(0.1f, 0.15f, 0.1f), M("paper", new Color(1f, 0.95f, 0.82f)), g, Quaternion.Euler(0f, 0f, 90f));
                    break;
                }
                case "crabs":
                {
                    // anne, baba ve yavru yengeç (yan yan yürür)
                    for (var i = 0; i < 3; i++)
                    {
                        var g = Group("crab" + i, new Vector3((i - 1) * 0.7f, 0f, 0f));
                        var s = i == 2 ? 0.6f : 1f;
                        var model = RealAssets.EnvScaled("p_crab", g, 1f * s, 90f);
                        if (model == null) Crab(g, s);
                    }
                    break;
                }
                case "shells":
                {
                    var pink = M("shell_pink", new Color(1f, 0.72f, 0.72f)); var cream = M("shell_cream", new Color(1f, 0.92f, 0.78f));
                    var lilac = M("shell_lilac", new Color(0.82f, 0.74f, 1f));
                    var g = Group("shells", Vector3.zero);
                    P(PrimitiveType.Sphere, new Vector3(-0.3f, 0.05f, 0.1f), new Vector3(0.26f, 0.1f, 0.22f), pink, g);
                    P(PrimitiveType.Sphere, new Vector3(0.25f, 0.05f, -0.15f), new Vector3(0.2f, 0.09f, 0.18f), cream, g);
                    P(PrimitiveType.Sphere, new Vector3(0.05f, 0.05f, 0.32f), new Vector3(0.18f, 0.08f, 0.16f), lilac, g);
                    P(PrimitiveType.Capsule, new Vector3(0.35f, 0.07f, 0.28f), new Vector3(0.1f, 0.12f, 0.1f), cream, g, Quaternion.Euler(0f, 0f, 70f));
                    break;
                }
                case "starfish":
                {
                    var g = Group("star", new Vector3(0f, 0.05f, 0f));
                    var model = RealAssets.EnvScaled("p_starfish", g, 1.3f, 0f);
                    if (model == null)
                    {
                        var m = M("starfish", new Color(1f, 0.55f, 0.35f));
                        for (var i = 0; i < 5; i++)
                        {
                            var a = i * 72f;
                            P(PrimitiveType.Capsule, Quaternion.Euler(0f, a, 0f) * new Vector3(0f, 0f, 0.16f), new Vector3(0.12f, 0.17f, 0.06f), m, g, Quaternion.Euler(90f, a, 0f));
                        }
                    }
                    break;
                }
                case "butterfly":
                {
                    var g = Group("butterfly", new Vector3(0f, 1.3f, 0f));
                    var wing = M("wing", new Color(1f, 0.62f, 0.2f)); var body = M("bbody", new Color(0.25f, 0.2f, 0.3f));
                    P(PrimitiveType.Capsule, Vector3.zero, new Vector3(0.05f, 0.09f, 0.05f), body, g, Quaternion.Euler(90f, 0f, 0f));
                    for (var i = 0; i < 2; i++)
                    {
                        var hinge = new GameObject("wing" + i).transform; hinge.SetParent(g, false);
                        P(PrimitiveType.Sphere, new Vector3((i == 0 ? -1f : 1f) * 0.13f, 0f, 0.02f), new Vector3(0.24f, 0.02f, 0.2f), wing, hinge);
                        P(PrimitiveType.Sphere, new Vector3((i == 0 ? -1f : 1f) * 0.1f, 0f, -0.12f), new Vector3(0.16f, 0.02f, 0.14f), wing, hinge);
                    }
                    break;
                }
                case "gull":
                {
                    var g = Group("gull", new Vector3(0f, 4.5f, 0f));
                    var white = M("gull", new Color(0.97f, 0.97f, 0.98f)); var grey = M("gull_wing", new Color(0.72f, 0.76f, 0.82f));
                    var bird = new GameObject("bird").transform; bird.SetParent(g, false); bird.localPosition = new Vector3(3f, 0f, 0f);
                    P(PrimitiveType.Capsule, Vector3.zero, new Vector3(0.28f, 0.34f, 0.28f), white, bird, Quaternion.Euler(90f, 0f, 0f));
                    P(PrimitiveType.Sphere, new Vector3(0f, 0.12f, 0.32f), Vector3.one * 0.24f, white, bird);
                    P(PrimitiveType.Capsule, new Vector3(0f, 0.1f, 0.48f), new Vector3(0.06f, 0.08f, 0.06f), M("beak", new Color(1f, 0.78f, 0.2f)), bird, Quaternion.Euler(90f, 0f, 0f));
                    for (var i = 0; i < 2; i++)
                    {
                        var hinge = new GameObject("wing" + i).transform; hinge.SetParent(bird, false);
                        P(PrimitiveType.Sphere, new Vector3((i == 0 ? -1f : 1f) * 0.45f, 0.05f, 0f), new Vector3(0.8f, 0.04f, 0.26f), grey, hinge);
                    }
                    break;
                }
            }
        }

        private void Crab(Transform g, float s)
        {
            var red = M("crab", new Color(0.95f, 0.38f, 0.3f));
            P(PrimitiveType.Sphere, new Vector3(0f, 0.1f * s, 0f), new Vector3(0.34f, 0.16f, 0.26f) * s, red, g);
            P(PrimitiveType.Sphere, new Vector3(0.22f * s, 0.12f * s, 0.1f * s), Vector3.one * 0.1f * s, red, g);
            P(PrimitiveType.Sphere, new Vector3(-0.22f * s, 0.12f * s, 0.1f * s), Vector3.one * 0.1f * s, red, g);
        }

        /// <summary>Dokunuldu: türüne göre kısa tepki, sonra kaybolur.</summary>
        public void React()
        {
            if (_gone >= 0f) return;
            _gone = 0f;
            var c = GetComponent<Collider>(); if (c != null) c.enabled = false;
            Audio.Sfx.Play(Kind == "bottle" ? Audio.SfxKind.Clink : Audio.SfxKind.Sparkle);
        }

        private void Update()
        {
            _t += Time.deltaTime;
            var t = _t + _seed;
            var g = _gone >= 0f ? (_gone += Time.deltaTime) : -1f;
            for (var i = 0; i < _parts.Count; i++)
            {
                var p = _parts[i]; var b = _base[i];
                switch (Kind)
                {
                    case "bottle":
                        // dalga kenarında hafifçe yuvarlanır
                        p.localRotation = Quaternion.Euler(Mathf.Sin(t * 1.4f) * 10f, 0f, 0f);
                        if (g >= 0f) { p.localPosition = b + Vector3.up * Mathf.Sin(Mathf.Min(g, 0.5f) / 0.5f * Mathf.PI) * 0.5f; p.localRotation = Quaternion.Euler(0f, g * 720f, 0f); }
                        break;
                    case "crabs":
                    {
                        // birlikte yan yan bir sağa bir sola; dokununca hızla kaçar
                        var off = g >= 0f ? g * 4f : Mathf.Sin(t * 0.7f) * 1.2f;
                        p.localPosition = b + new Vector3(0f, 0f, off) + Vector3.up * Mathf.Abs(Mathf.Sin(t * 14f + i)) * 0.03f;
                        p.localRotation = Quaternion.Euler(0f, 0f, Mathf.Sin(t * 30f + i) * 4f);
                        break;
                    }
                    case "shells":
                        p.localScale = Vector3.one * (g >= 0f ? Mathf.Max(0f, 1f - g * 2f) : 1f + Mathf.Sin(t * 2.2f) * 0.03f);
                        break;
                    case "starfish":
                        // el sallar gibi kalkıp iner
                        p.localRotation = Quaternion.Euler(g >= 0f ? 0f : Mathf.Max(0f, Mathf.Sin(t * 2.5f)) * 35f, t * 10f, Mathf.Sin(t * 5f) * 8f);
                        if (g >= 0f) p.localPosition = b + Vector3.up * Mathf.Sin(Mathf.Min(g, 0.6f) / 0.6f * Mathf.PI) * 0.6f;
                        break;
                    case "butterfly":
                    {
                        var r = g >= 0f ? 0.6f + g * 3f : 0.6f;
                        p.localPosition = b + new Vector3(Mathf.Cos(t * 1.1f) * r, Mathf.Sin(t * 2.3f) * 0.25f + (g >= 0f ? g * 2.5f : 0f), Mathf.Sin(t * 1.1f) * r);
                        p.localRotation = Quaternion.Euler(0f, -t * 1.1f * Mathf.Rad2Deg, 0f);
                        Flap(p, t * 22f, 70f);
                        break;
                    }
                    case "gull":
                    {
                        var a = t * 0.55f;
                        p.localRotation = Quaternion.Euler(0f, -a * Mathf.Rad2Deg, 0f);
                        p.localPosition = b + Vector3.up * (Mathf.Sin(t * 0.8f) * 0.4f + (g >= 0f ? g * 4f : 0f));
                        var bird = p.childCount > 0 ? p.GetChild(0) : null;
                        if (bird != null) { bird.localRotation = Quaternion.Euler(0f, 0f, -18f); Flap(bird, t * 9f, 30f); }
                        break;
                    }
                }
            }
            if (g >= 1.2f) Destroy(gameObject);
        }

        private static void Flap(Transform t, float phase, float deg)
        {
            for (var i = 0; i < t.childCount; i++)
            {
                var w = t.GetChild(i);
                if (!w.name.StartsWith("wing")) continue;
                var s = w.name == "wing0" ? 1f : -1f;
                w.localRotation = Quaternion.Euler(0f, 0f, s * Mathf.Sin(phase) * deg);
            }
        }
    }
}
