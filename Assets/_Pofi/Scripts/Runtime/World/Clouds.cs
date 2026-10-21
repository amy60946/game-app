using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// Kodla üretilen pofuduk 3B bulutlar (Pofi/Cloud): gürültüyle şişirilmiş küre "puf"lardan kümeler. Kredi gerektirmez.
    /// Kümeler yavaşça süzülür; bir halka boyunca yerleştirilir (ada çevresi ya da ev sahnesinin arkası).
    /// </summary>
    public sealed class Clouds : MonoBehaviour
    {
        private static Mesh _puff;
        private static Material _mat;
        private Vector3 _drift, _start;
        private bool _started, _fog;
        private float _phase;
        private Mesh _mesh;
        private Vector3 _scale = Vector3.one;

        /// <summary>Rüzgâr (birim/sn). Bulutlar bu yönde kayar, uzaklaşınca karşı taraftan yeniden girer.</summary>
        public static readonly Vector3 Wind = new Vector3(0.55f, 0f, 0.2f);

        private void OnDestroy() { if (_mesh != null) Destroy(_mesh); }

        /// <summary>Merkez çevresinde (yay açısı içinde) <paramref name="count"/> küme kurar.</summary>
        public static Transform Spawn(Transform parent, Vector3 center, float radius, int count, float yMin, float yMax, float size, int seed,
            float arcFrom = 0f, float arcTo = 360f, bool fog = false)
        {
            if (_mat == null)
            {
                var sh = Shader.Find("Pofi/Cloud");
                if (sh == null) return null;
                _mat = new Material(sh);
            }
            if (_puff == null) _puff = PuffMesh();
            var root = new GameObject("Clouds").transform;
            root.SetParent(parent, false);
            var rnd = new System.Random(seed);
            for (var c = 0; c < count; c++)
            {
                var a = Mathf.Deg2Rad * Mathf.Lerp(arcFrom, arcTo, (c + (float)rnd.NextDouble() * 0.7f) / count);
                var r = radius * (0.85f + (float)rnd.NextDouble() * 0.3f);
                var cl = new GameObject("Cloud" + c).transform;
                cl.SetParent(root, false);
                cl.localPosition = center + new Vector3(Mathf.Cos(a) * r, Mathf.Lerp(yMin, yMax, (float)rnd.NextDouble()), Mathf.Sin(a) * r);
                cl.localRotation = Quaternion.Euler(0f, (float)rnd.NextDouble() * 360f, 0f);
                var s = size * (0.7f + (float)rnd.NextDouble() * 0.6f);
                var puffs = 11 + rnd.Next(6);
                // Doğal kümülüs (22 Ekim 2026, gökyüzü fotoğraflarından esinle): ortak düz taban, ortası yüksek ve büyük loblar,
                // kenarlara doğru küçülen ve alçalan tutamlar; üstte birkaç küçük "karnabahar" lobu. Yer sisi yayvan ve alçak kalır.
                // Puflar tek ağa birleşir: bulut başına 1 çizim çağrısı.
                var parts = new CombineInstance[puffs];
                var tall = fog ? 0.25f : 0.55f + (float)rnd.NextDouble() * 0.6f;   // yayvan .. kule
                for (var k = 0; k < puffs; k++)
                {
                    var upper = !fog && k >= puffs - 3;                                     // son üçü tepe lobları
                    var u = upper ? ((float)rnd.NextDouble() * 2f - 1f) * 0.45f : ((k + 0.5f) / (fog ? puffs : puffs - 3) * 2f - 1f) + ((float)rnd.NextDouble() - 0.5f) * 0.2f;
                    var edge = 1f - 0.55f * Mathf.Abs(u);
                    var pr = s * (0.34f + (float)rnd.NextDouble() * 0.22f) * edge * (upper ? 0.75f : 1f);
                    var lift = s * tall * (1f - u * u) * (upper ? 0.9f : 0.35f + (float)rnd.NextDouble() * 0.25f);
                    var pos = new Vector3(u * s * 1.6f, Mathf.Max(lift, pr * 0.12f), ((float)rnd.NextDouble() * 2f - 1f) * s * 0.5f * edge);
                    var rot = Quaternion.Euler(0f, (float)rnd.NextDouble() * 360f, 0f);
                    parts[k] = new CombineInstance { mesh = _puff, transform = Matrix4x4.TRS(pos, rot, new Vector3(pr, pr * 0.85f, pr)) };
                }
                var mesh = new Mesh { name = "Cloud" };
                mesh.CombineMeshes(parts, true, true);
                cl.gameObject.AddComponent<MeshFilter>().sharedMesh = mesh;
                var mr = cl.gameObject.AddComponent<MeshRenderer>();
                mr.sharedMaterial = _mat;
                mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                mr.receiveShadows = false;
                var drift = cl.gameObject.AddComponent<Clouds>();
                // ortak rüzgâr (gökyüzündeki bulutlarla aynı yön); yüksektekiler biraz hızlı
                drift._drift = Wind * (0.8f + (float)rnd.NextDouble() * 0.4f) * Mathf.Lerp(0.85f, 1.2f, Mathf.InverseLerp(yMin, yMax, cl.localPosition.y));
                drift._scale = cl.localScale;
                drift._fog = fog;   // yer sisi: yerinde hafifçe salınır, uzaklaşmaz
                drift._phase = (float)rnd.NextDouble() * 6.28f;
                drift._mesh = mesh;
            }
            return root;
        }

        /// <summary>Gürültüyle şişirilmiş, altı hafif düz küre.</summary>
        private static Mesh PuffMesh()
        {
            var tmp = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            var src = tmp.GetComponent<MeshFilter>().sharedMesh;
            var v = src.vertices;
            for (var i = 0; i < v.Length; i++)
            {
                var n = v[i].normalized;
                var bump = Mathf.PerlinNoise(n.x * 2.3f + 3.1f, n.z * 2.3f + n.y * 1.7f) * 0.22f + Mathf.PerlinNoise(n.x * 6f, n.y * 6f + n.z * 3f) * 0.06f;
                var p = n * (0.5f + bump);
                if (p.y < -0.18f) p.y = -0.18f + (p.y + 0.18f) * 0.25f;   // alt düzlük
                v[i] = p;
            }
            var m = new Mesh { name = "CloudPuff" };
            m.vertices = v; m.triangles = src.triangles;
            m.RecalculateNormals();
            m.RecalculateBounds();
            Destroy(tmp);
            return m;
        }

        private void Update()
        {
            if (!_started) { _start = transform.localPosition; _started = true; }
            if (_fog)
            {
                var t = Time.time * 0.25f + _phase;
                transform.localPosition = _start + new Vector3(Mathf.Sin(t) * 0.8f, Mathf.Sin(t * 1.7f) * 0.15f, Mathf.Cos(t * 0.8f) * 0.5f);
                return;
            }
            transform.localPosition += _drift * Time.deltaTime;
            if ((transform.localPosition - _start).magnitude > 40f) transform.localPosition -= _drift.normalized * 80f;   // sonsuz süzülme
            // bulut yavaşça "nefes alır": loblar kaynıyormuş gibi hafif büyüyüp küçülür
            var b = Time.time * 0.12f + _phase;
            transform.localScale = Vector3.Scale(_scale, new Vector3(1f + Mathf.Sin(b) * 0.04f, 1f + Mathf.Sin(b * 1.3f + 1f) * 0.06f, 1f + Mathf.Cos(b * 0.9f) * 0.04f));
        }
    }
}
