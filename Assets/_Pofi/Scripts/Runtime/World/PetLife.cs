using System.Collections.Generic;
using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// Yer tutucu pete hayat: göz kırpma, kulak/kuyruk/anten salınımı, uyurken kapalı göz ve yavaş nefes.
    /// Parçaları adlarından bulur (PetModels: eye_*, ear_*, tail*, antenna_*, flipper_*, wing_*). Gerçek modelde Animator devralır.
    /// </summary>
    public sealed class PetLife : MonoBehaviour
    {
        public bool Sleeping;

        private readonly List<(Transform t, Quaternion rest, float phase, float amp, Vector3 axis)> _swing = new List<(Transform, Quaternion, float, float, Vector3)>();
        private readonly List<(Transform t, Vector3 rest)> _eyes = new List<(Transform, Vector3)>();
        private float _blinkAt, _blink;

        private void Start()
        {
            var i = 0;
            foreach (Transform c in transform)
            {
                var n = c.name;
                if (n.StartsWith("eye_") || n.StartsWith("glint_")) _eyes.Add((c, c.localScale));
                else if (n.StartsWith("ear_") && !n.StartsWith("ear_in")) _swing.Add((c, c.localRotation, i++ * 0.7f, 6f, Vector3.forward));
                else if (n.StartsWith("tail")) _swing.Add((c, c.localRotation, i++ * 0.5f, 10f, Vector3.up));
                else if (n.StartsWith("antenna_")) _swing.Add((c, c.localRotation, i++ * 0.9f, 12f, Vector3.forward));
                else if (n.StartsWith("flipper_") || n.StartsWith("wing_") || n.StartsWith("arm_")) _swing.Add((c, c.localRotation, i++ * 1.3f, 5f, Vector3.forward));
                else if (n.StartsWith("trunk_")) _swing.Add((c, c.localRotation, i++ * 0.4f, 4f, Vector3.right));
            }
            _blinkAt = Time.time + Random.Range(1.5f, 4f);
        }

        private void Update()
        {
            if (UI.Theme.ReduceMotion && !Sleeping) return;
            var speed = Sleeping ? 0.5f : 2.2f;
            foreach (var s in _swing)
            {
                var a = Mathf.Sin(Time.time * speed + s.phase) * s.amp * (Sleeping ? 0.3f : 1f);
                s.t.localRotation = s.rest * Quaternion.AngleAxis(a, s.axis);
            }
            // göz kırpma (uyurken kapalı)
            if (!Sleeping && Time.time >= _blinkAt)
            {
                _blink = 0.16f;
                _blinkAt = Time.time + Random.Range(2.5f, 5.5f);
            }
            _blink = Mathf.Max(0f, _blink - Time.deltaTime);
            var open = Sleeping ? 0.12f : _blink > 0f ? 0.15f : 1f;
            foreach (var e in _eyes) e.t.localScale = new Vector3(e.rest.x, e.rest.y * open, e.rest.z);
        }
    }

    /// <summary>Ada sakinleri (FR-ISL-2): kumda yan yan yürüyen yengeç ve gökyüzünde süzülen martı. Hafif, ortam için.</summary>
    public sealed class Ambient : MonoBehaviour
    {
        private Transform _crab, _gull;
        private readonly List<Material> _mats = new List<Material>();

        public static Ambient Create(Transform parent)
        {
            var go = new GameObject("Ambient");
            go.transform.SetParent(parent, false);
            var a = go.AddComponent<Ambient>();
            a.Build();
            return a;
        }

        private Material M(Color c) { var m = PetModels.NewMaterial(c, 0.5f); _mats.Add(m); return m; }

        private void Build()
        {
            _crab = new GameObject("crab").transform;
            _crab.SetParent(transform, false);
            var red = M(new Color(0.93f, 0.33f, 0.25f));
            var dark = M(new Color(0.1f, 0.1f, 0.12f));
            P(PrimitiveType.Sphere, _crab, new Vector3(0f, 0.07f, 0f), new Vector3(0.22f, 0.1f, 0.16f), red);
            P(PrimitiveType.Sphere, _crab, new Vector3(-0.15f, 0.09f, -0.06f), Vector3.one * 0.07f, red);
            P(PrimitiveType.Sphere, _crab, new Vector3(0.15f, 0.09f, -0.06f), Vector3.one * 0.07f, red);
            P(PrimitiveType.Sphere, _crab, new Vector3(-0.04f, 0.14f, -0.06f), Vector3.one * 0.03f, dark);
            P(PrimitiveType.Sphere, _crab, new Vector3(0.04f, 0.14f, -0.06f), Vector3.one * 0.03f, dark);

            _gull = new GameObject("seagull").transform;
            _gull.SetParent(transform, false);
            var white = M(Color.white);
            var grey = M(new Color(0.7f, 0.75f, 0.8f));
            P(PrimitiveType.Sphere, _gull, Vector3.zero, new Vector3(0.12f, 0.1f, 0.22f), white);
            P(PrimitiveType.Cube, _gull, new Vector3(-0.17f, 0.02f, 0f), new Vector3(0.24f, 0.015f, 0.1f), grey).name = "wingL";
            P(PrimitiveType.Cube, _gull, new Vector3(0.17f, 0.02f, 0f), new Vector3(0.24f, 0.015f, 0.1f), grey).name = "wingR";
        }

        private static GameObject P(PrimitiveType t, Transform parent, Vector3 pos, Vector3 scale, Material m)
        {
            var go = GameObject.CreatePrimitive(t);
            go.transform.SetParent(parent, false);
            go.transform.localPosition = pos;
            go.transform.localScale = scale;
            go.GetComponent<Renderer>().sharedMaterial = m;
            Object.Destroy(go.GetComponent<Collider>());
            return go;
        }

        private void Update()
        {
            var t = Time.time;
            // yengeç: adacığın önünde sağa sola yan yürüyüş, arada durur
            var x = Mathf.PingPong(t * 0.25f, 2.2f) - 1.1f;
            _crab.localPosition = new Vector3(x, 0f, -1.05f + Mathf.Sin(t * 0.7f) * 0.05f);
            _crab.localRotation = Quaternion.Euler(0f, 0f, Mathf.Sin(t * 12f) * 3f);
            // martı: geniş daire, kanat çırpma
            var a = t * 0.25f;
            _gull.localPosition = new Vector3(Mathf.Cos(a) * 2.2f, 2.3f + Mathf.Sin(t * 0.8f) * 0.15f, 2.5f + Mathf.Sin(a) * 1.2f);
            _gull.localRotation = Quaternion.LookRotation(new Vector3(-Mathf.Sin(a), 0f, Mathf.Cos(a))) * Quaternion.Euler(0f, 0f, 10f);
            var flap = Mathf.Sin(t * 8f) * 25f;
            _gull.Find("wingL").localRotation = Quaternion.Euler(0f, 0f, flap);
            _gull.Find("wingR").localRotation = Quaternion.Euler(0f, 0f, -flap);
        }

        private void OnDestroy()
        {
            foreach (var m in _mats) if (m != null) Destroy(m);
        }
    }
}
