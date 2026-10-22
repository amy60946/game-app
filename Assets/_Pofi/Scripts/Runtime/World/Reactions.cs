using System.Collections.Generic;
using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// Dokununca tepki veren süsler (O4, 23 Ekim 2026): ağaç ve palmiye tabandan sallanır, çalı titrer, deniz yıldızı takla atar.
    /// Modellerin kökü zeminde (RealAssets.Footprint) olduğu için dönme tabandan olur. Sönümlü yay; boşta hiçbir şey yazmaz.
    /// </summary>
    public sealed class Wobble : MonoBehaviour
    {
        public enum Kind { Sway, Shake, Flip }
        private Kind _kind;
        private Quaternion _rest;
        private float _t = -1f, _amp, _dir;

        public static Wobble Add(Transform t, Kind kind)
        {
            var w = t.gameObject.AddComponent<Wobble>();
            w._kind = kind; w._rest = t.localRotation;
            w.enabled = false;
            return w;
        }

        /// <summary>Dokunuş: <paramref name="from"/> yönünden itilmiş gibi sallanır.</summary>
        public void Poke(Vector3 from)
        {
            var d = transform.position - from; d.y = 0f;
            _dir = d.sqrMagnitude > 0.0001f ? Mathf.Atan2(d.x, d.z) * Mathf.Rad2Deg : Random.Range(0f, 360f);
            _amp = _kind == Kind.Sway ? 7f : _kind == Kind.Shake ? 5f : 1f;
            _t = 0f;
            enabled = true;
            Audio.Sfx.Play(_kind == Kind.Flip ? Audio.SfxKind.Pop : Audio.SfxKind.Rustle);
            Audio.Haptics.Light();
        }

        private void Update()
        {
            if (_t < 0f) { enabled = false; return; }
            _t += Time.deltaTime;
            Quaternion q;
            if (_kind == Kind.Flip)
            {
                // zıplayıp kendi çevresinde bir tur döner, yere oturur
                var k = Mathf.Clamp01(_t / 0.6f);
                q = Quaternion.Euler(0f, 0f, Mathf.SmoothStep(0f, 360f, k));
                transform.localRotation = _rest * q;
                if (k >= 1f) { transform.localRotation = _rest; _t = -1f; }
                return;
            }
            var freq = _kind == Kind.Sway ? 7.5f : 26f;
            var decay = _kind == Kind.Sway ? 2.6f : 5.5f;
            var a = _amp * Mathf.Exp(-decay * _t) * Mathf.Sin(_t * freq);
            if (Mathf.Exp(-decay * _t) < 0.02f) { transform.localRotation = _rest; _t = -1f; return; }
            // itilme yönüne yatar (yerel eksende değil, dünya yatayında)
            var axis = Quaternion.Euler(0f, _dir, 0f) * Vector3.right;
            if (transform.parent != null) axis = transform.parent.InverseTransformDirection(axis);
            transform.localRotation = Quaternion.AngleAxis(a, axis) * _rest;
        }
    }

    /// <summary>Okti'nin kalp biçimli mürekkep bulutu (A1): başının üstünden yükselir, büyür ve söner; yanında üç küçük damla.</summary>
    public sealed class InkHeart : MonoBehaviour
    {
        private static Texture2D _tex;
        private static Material _mat;
        private readonly List<Transform> _drops = new List<Transform>();
        private Material _m;
        private float _t;

        public static void Spawn(Transform pet, float height)
        {
            if (pet == null) return;
            var root = new GameObject("ink_heart").transform;
            root.position = pet.position + Vector3.up * (height + 0.2f);
            var h = root.gameObject.AddComponent<InkHeart>();
            h._m = new Material(Mat());
            h.Quad(root, Vector3.zero, 0.9f);
            for (var i = 0; i < 3; i++)
            {
                var a = (i - 1) * 0.55f;
                h._drops.Add(h.Quad(root, new Vector3(Mathf.Sin(a) * 0.55f, -0.25f, 0f), 0.22f));
            }
        }

        private Transform Quad(Transform root, Vector3 at, float size)
        {
            var q = GameObject.CreatePrimitive(PrimitiveType.Quad);
            Destroy(q.GetComponent<Collider>());
            q.transform.SetParent(root, false);
            q.transform.localPosition = at; q.transform.localScale = Vector3.one * size;
            var r = q.GetComponent<MeshRenderer>(); r.sharedMaterial = _m;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
            return q.transform;
        }

        private void Update()
        {
            _t += Time.deltaTime / 1.3f;
            var cam = Camera.main;
            if (cam != null) transform.rotation = Quaternion.LookRotation(transform.position - cam.transform.position, Vector3.up);
            transform.position += Vector3.up * Time.deltaTime * 0.7f;
            var s = Mathf.Lerp(0.4f, 1.25f, 1f - Mathf.Pow(1f - Mathf.Clamp01(_t * 2.2f), 3f));
            transform.localScale = Vector3.one * s;
            foreach (var d in _drops) d.localPosition += Vector3.down * Time.deltaTime * 0.5f;
            _m.SetColor("_Color", new Color(1f, 1f, 1f, 0.9f * (1f - Mathf.Clamp01((_t - 0.55f) / 0.45f))));
            if (_t >= 1f) { Destroy(_m); Destroy(gameObject); }
        }

        private void OnDestroy() { if (_m != null) Destroy(_m); }

        private static Material Mat() => _mat != null ? _mat : _mat = SpriteMat(Tex());

        /// <summary>Saydam ışıksız efekt malzemesi (Pofi/Sprite; Resources/Shaders, derlemeye girer).</summary>
        internal static Material SpriteMat(Texture tex)
        {
            var sh = Shader.Find("Pofi/Sprite");
            var m = sh != null ? new Material(sh) : PetModels.NewMaterial(Color.white, 0.9f);
            if (tex != null) m.SetTexture("_MainTex", tex);
            return m;
        }

        /// <summary>Yumuşak kenarlı kalp (kodla çizilir; içi açık, kenarı koyu mürekkep mavisi).</summary>
        private static Texture2D Tex()
        {
            if (_tex != null) return _tex;
            const int n = 96;
            _tex = new Texture2D(n, n, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, name = "ink_heart" };
            var px = new Color32[n * n];
            for (var y = 0; y < n; y++)
                for (var x = 0; x < n; x++)
                {
                    // kalp eğrisi: (x² + y² − 1)³ − x² y³ ≤ 0
                    var u = (x - n * 0.5f) / (n * 0.36f); var v = (y - n * 0.45f) / (n * 0.36f);
                    var f = Mathf.Pow(u * u + v * v - 1f, 3f) - u * u * v * v * v;
                    var a = Mathf.Clamp01(-f * 6f);
                    var inner = Mathf.Clamp01(-f * 1.6f);
                    var col = Color.Lerp(new Color(0.3f, 0.5f, 0.95f), new Color(0.82f, 0.92f, 1f), inner);
                    px[y * n + x] = new Color(col.r, col.g, col.b, a);
                }
            _tex.SetPixels32(px); _tex.Apply();
            return _tex;
        }
    }

    /// <summary>Suya dokununca halka (O4): denizin yüzeyinde genişleyip sönen iki halka.</summary>
    public sealed class Ripple : MonoBehaviour
    {
        private static Mesh _ring;
        private Material _m;
        private float _t;

        public static void Spawn(Vector3 at)
        {
            for (var i = 0; i < 2; i++)
            {
                var go = new GameObject("ripple");
                go.transform.position = at + Vector3.up * 0.03f;
                var r = go.AddComponent<Ripple>();
                r._t = -i * 0.25f;
                var mf = go.AddComponent<MeshFilter>(); mf.sharedMesh = Ring();
                var mr = go.AddComponent<MeshRenderer>();
                r._m = InkHeart.SpriteMat(null);
                mr.sharedMaterial = r._m;
                mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; mr.receiveShadows = false;
                go.transform.localScale = Vector3.zero;
            }
            Audio.Sfx.Play(Audio.SfxKind.Pop);
        }

        private void Update()
        {
            _t += Time.deltaTime / 1.1f;
            if (_t < 0f) return;
            var s = Mathf.Lerp(0.3f, 2.6f, 1f - (1f - _t) * (1f - _t));
            transform.localScale = new Vector3(s, 1f, s);
            _m.SetColor("_Color", new Color(1f, 1f, 1f, 0.75f * (1f - _t)));
            if (_t >= 1f) Destroy(gameObject);
        }

        private void OnDestroy() { if (_m != null) Destroy(_m); }

        private static Mesh Ring()
        {
            if (_ring != null) return _ring;
            const int seg = 40; const float r0 = 0.86f, r1 = 1f;
            var v = new Vector3[seg * 2]; var t = new int[seg * 6];
            for (var i = 0; i < seg; i++)
            {
                var a = i * Mathf.PI * 2f / seg;
                v[i * 2] = new Vector3(Mathf.Cos(a) * r0, 0f, Mathf.Sin(a) * r0);
                v[i * 2 + 1] = new Vector3(Mathf.Cos(a) * r1, 0f, Mathf.Sin(a) * r1);
                var j = (i + 1) % seg;
                t[i * 6] = i * 2; t[i * 6 + 1] = j * 2 + 1; t[i * 6 + 2] = i * 2 + 1;
                t[i * 6 + 3] = i * 2; t[i * 6 + 4] = j * 2; t[i * 6 + 5] = j * 2 + 1;
            }
            _ring = new Mesh { name = "ripple", vertices = v, triangles = t };
            _ring.RecalculateNormals();
            return _ring;
        }
    }
}
