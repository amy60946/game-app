using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// Uzakta süzülen küçük kuş sürüleri (kredisiz, kodla). Her sürü adanın çevresinde, denizin üstünde alçaktan geniş bir çember
    /// çizer; kuşlar V düzeninde uçar, kanat çırpar ve arada süzülür. Siluet düz renkli (Pofi/Flat), gölge yok.
    /// Yükseklik bilerek düşük: yürüyüş kamerası aşağı baktığı için ufka yakın uçan kuşlar görünür.
    /// </summary>
    public sealed class Birds : MonoBehaviour
    {
        private static Mesh _wing;
        private static Material _mat;

        private Vector3 _center;
        private float _radius, _height, _speed, _angle, _dir;
        private Transform[] _birds;
        private Transform[,] _wings;
        private Vector3[] _slots;
        private float[] _phase;

        /// <summary>Merkez çevresinde <paramref name="flocks"/> sürü kurar (her biri 3–5 kuş).</summary>
        public static Transform Spawn(Transform parent, Vector3 center, float radius, int flocks, int seed)
        {
            if (_mat == null)
            {
                var sh = Shader.Find("Pofi/Flat");
                if (sh == null) return null;
                _mat = new Material(sh);
                _mat.SetColor("_Color", new Color(0.24f, 0.3f, 0.42f));
            }
            if (_wing == null) _wing = WingMesh();
            var root = new GameObject("Birds").transform;
            root.SetParent(parent, false);
            var rnd = new System.Random(seed);
            for (var f = 0; f < flocks; f++)
            {
                var go = new GameObject("Flock" + f);
                go.transform.SetParent(root, false);
                var b = go.AddComponent<Birds>();
                b._center = center;
                b._radius = radius * (0.85f + (float)rnd.NextDouble() * 0.35f);
                b._height = 6f + (float)rnd.NextDouble() * 5f;
                b._speed = 3.2f + (float)rnd.NextDouble() * 1.4f;
                b._angle = (float)rnd.NextDouble() * Mathf.PI * 2f;
                b._dir = rnd.Next(2) == 0 ? 1f : -1f;
                var n = 3 + rnd.Next(3);
                b._birds = new Transform[n];
                b._wings = new Transform[n, 2];
                b._slots = new Vector3[n];
                b._phase = new float[n];
                for (var i = 0; i < n; i++)
                {
                    // V düzeni: lider önde, diğerleri iki yana ve geriye
                    var side = i == 0 ? 0f : (i % 2 == 0 ? 1f : -1f);
                    var row = (i + 1) / 2;
                    b._slots[i] = new Vector3(side * row * 1.5f, ((float)rnd.NextDouble() - 0.5f) * 0.8f, -row * 1.2f);
                    b._phase[i] = (float)rnd.NextDouble() * 10f;
                    var bird = new GameObject("Bird" + i).transform;
                    bird.SetParent(go.transform, false);
                    bird.localScale = Vector3.one * (0.9f + (float)rnd.NextDouble() * 0.3f);
                    b._birds[i] = bird;
                    for (var w = 0; w < 2; w++)
                    {
                        var wing = new GameObject(w == 0 ? "L" : "R").transform;
                        wing.SetParent(bird, false);
                        wing.localScale = new Vector3(w == 0 ? -1f : 1f, 1f, 1f);
                        wing.gameObject.AddComponent<MeshFilter>().sharedMesh = _wing;
                        var mr = wing.gameObject.AddComponent<MeshRenderer>();
                        mr.sharedMaterial = _mat;
                        mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                        mr.receiveShadows = false;
                        b._wings[i, w] = wing;
                    }
                }
            }
            return root;
        }

        /// <summary>Tek kanat: omuzdan uca incelen, hafif geriye kıvrık ince levha (sağ kanat; sol için x aynalanır).</summary>
        private static Mesh WingMesh()
        {
            var v = new[]
            {
                new Vector3(0f, 0f, 0.1f), new Vector3(0f, 0f, -0.12f),
                new Vector3(0.32f, 0.04f, 0.06f), new Vector3(0.3f, 0.04f, -0.12f),
                new Vector3(0.62f, 0f, -0.1f),
            };
            var t = new[] { 0, 2, 1, 1, 2, 3, 2, 4, 3 };
            var m = new Mesh { name = "BirdWing" };
            m.vertices = v; m.triangles = t;
            m.RecalculateNormals();
            m.bounds = new Bounds(Vector3.zero, Vector3.one * 2f);
            return m;
        }

        private void Update()
        {
            var dt = Time.deltaTime;
            _angle += _dir * _speed / _radius * dt;
            var time = Time.time;
            var pos = _center + new Vector3(Mathf.Cos(_angle) * _radius, _height + Mathf.Sin(time * 0.3f + _radius) * 0.8f, Mathf.Sin(_angle) * _radius);
            var heading = new Vector3(-Mathf.Sin(_angle) * _dir, 0f, Mathf.Cos(_angle) * _dir);
            var rot = Quaternion.LookRotation(heading, Vector3.up) * Quaternion.Euler(0f, 0f, -_dir * 8f);   // dönüşe hafif yatış
            for (var i = 0; i < _birds.Length; i++)
            {
                var b = _birds[i];
                var t = time + _phase[i];
                b.localPosition = pos + rot * (_slots[i] + new Vector3(0f, Mathf.Sin(t * 0.9f) * 0.25f, 0f));
                b.localRotation = rot;
                // 2,4 sn çırp, 1,6 sn süzül (kanatlar hafif yukarıda)
                var cycle = Mathf.Repeat(t, 4f);
                var flap = cycle < 2.4f ? Mathf.Sin(t * 9f) * 32f : 10f;
                _wings[i, 0].localRotation = Quaternion.Euler(0f, 0f, -flap);
                _wings[i, 1].localRotation = Quaternion.Euler(0f, 0f, flap);
            }
        }
    }
}
