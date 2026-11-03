using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// Okti ile top oyunu (K2 B, kullanıcı 3 Kasım 2026; benchmark Nintendogs oyuncakla oynama, Pokémon Refresh, Talking Tom dokunuş
    /// tepkileri): kodla çizilen plaj topu Okti'nin başının üstünde belirir, Okti kollarıyla 3 kez sektirir (kaçırma yok, ~6 sn),
    /// sonunda top yere düşüp küçülür ve bir mürekkep kalbi yükselir. Adada (PetWalker.Bat) ve evde (Stage.Bat) aynı gösteri.
    /// Model dosyası yok (kredisiz); ParticleSystem yok.
    /// </summary>
    public sealed class BeachBall : MonoBehaviour
    {
        public const int Bounces = 3;
        private const float Lead = 0.45f, Period = 1.45f, Rise = 1.45f, Fall = 0.8f, Fade = 0.35f;

        private static Texture2D _tex;
        private Transform _anchor;
        private float _hands, _scale, _t, _radius;
        private int _hits;
        private System.Action _hit, _done;
        private Material _m;
        private Vector3 _spinAxis = Vector3.right;

        /// <summary>Toplam gösteri süresi (saniye).</summary>
        public static float Duration => Lead + Bounces * Period + Fall + Fade;

        /// <param name="anchor">Petin ayak noktası (yürüyünce top da gelir).</param>
        /// <param name="height">Petin boyu (dünya birimi): top kolların ucunda, başın biraz üstünde sekirtilir.</param>
        /// <param name="onHit">Her vuruşta (pet sevinç hareketi yapar).</param>
        /// <param name="done">Gösteri bitti (iptalde de çağrılır).</param>
        public static BeachBall Spawn(Transform anchor, float height, System.Action onHit, System.Action done)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            go.name = "beach_ball";
            var col = go.GetComponent<Collider>();
            if (col != null) Destroy(col);
            var b = go.AddComponent<BeachBall>();
            b._anchor = anchor; b._hit = onHit; b._done = done;
            b._scale = Mathf.Max(0.3f, height / 1.9f);
            b._hands = height * 0.95f;
            b._radius = 0.3f * b._scale;
            b._m = PetModels.NewMaterial(Color.white, 0.55f);
            b._m.SetTexture("_BaseMap", Tex());
            var r = go.GetComponent<MeshRenderer>();
            r.sharedMaterial = b._m;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.On;
            go.transform.localScale = Vector3.zero;
            b.Place(b._hands + 0.25f * b._scale);
            Audio.Sfx.Play(Audio.SfxKind.Pop);
            return b;
        }

        private void Place(float up)
        {
            if (_anchor == null) return;
            var fwd = _anchor.forward; fwd.y = 0f;
            if (fwd.sqrMagnitude < 0.01f) fwd = Vector3.forward;
            transform.position = _anchor.position + fwd.normalized * 0.28f * _scale + Vector3.up * up;
        }

        private void Update()
        {
            if (_anchor == null) { Finish(); return; }
            _t += Time.deltaTime;
            float up, size = _radius * 2f;
            if (_t < Lead)
            {
                var k = _t / Lead;
                size *= 1f - Mathf.Pow(1f - k, 3f);                       // açılır
                up = _hands + 0.25f * _scale * (1f - k);
            }
            else if (_t < Lead + Bounces * Period)
            {
                var b = (int)((_t - Lead) / Period);
                if (b >= _hits) { _hits = b + 1; Bat(); }
                var u = (_t - Lead - b * Period) / Period;
                up = _hands + Rise * _scale * 4f * u * (1f - u);         // kollardan yukarı, yine kollara
                if (u < 0.1f) size *= 0.88f + 0.12f * (u / 0.1f);   // vuruşta hafif basılma
            }
            else if (_t < Lead + Bounces * Period + Fall)
            {
                var u = (_t - Lead - Bounces * Period) / Fall;
                var ground = _radius;
                // son vuruştan sonra öne düşer, küçük bir sekme
                var drop = Mathf.Lerp(_hands, ground, u * u);
                up = u > 0.7f ? ground + Mathf.Sin((u - 0.7f) / 0.3f * Mathf.PI) * 0.25f * _scale : drop;
                if (u >= 0.7f && _hits <= Bounces) { _hits = Bounces + 1; Audio.Sfx.Play(Audio.SfxKind.Tap); }
            }
            else
            {
                var u = Mathf.Clamp01((_t - Lead - Bounces * Period - Fall) / Fade);
                up = _radius;
                size *= 1f - u;
                if (u >= 1f) { Finish(); return; }
            }
            Place(up);
            transform.localScale = Vector3.one * Mathf.Max(0.0001f, size);
            transform.Rotate(_spinAxis, 260f * Time.deltaTime, Space.World);
        }

        private void Bat()
        {
            Audio.Sfx.Play(Audio.SfxKind.Pop);
            Audio.Haptics.Light();
            _spinAxis = Quaternion.Euler(0f, Random.Range(0f, 360f), 0f) * Vector3.right;
            _hit?.Invoke();
        }

        private void Finish()
        {
            var done = _done; _done = null;
            if (_anchor != null) InkHeart.Spawn(_anchor, _hands + 0.2f * _scale);
            Audio.Sfx.Play(Audio.SfxKind.Sparkle);
            Destroy(gameObject);
            done?.Invoke();
        }

        private void OnDestroy()
        {
            if (_m != null) Destroy(_m);
            var done = _done; _done = null;
            done?.Invoke();
        }

        /// <summary>Altı dilimli plaj topu dokusu (kırmızı, sarı, mavi arasında beyaz; kutuplarda beyaz kapak).</summary>
        private static Texture2D Tex()
        {
            if (_tex != null) return _tex;
            const int w = 96, h = 48;
            _tex = new Texture2D(w, h, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Repeat, name = "beach_ball" };
            var gores = new[] { new Color(0.91f, 0.27f, 0.29f), Color.white, new Color(1f, 0.79f, 0.24f), Color.white, new Color(0.24f, 0.55f, 0.92f), Color.white };
            var px = new Color[w * h];
            for (var y = 0; y < h; y++)
                for (var x = 0; x < w; x++)
                {
                    var v = (y + 0.5f) / h;
                    var c = v < 0.07f || v > 0.93f ? Color.white : gores[x * gores.Length / w];
                    px[y * w + x] = c;
                }
            _tex.SetPixels(px); _tex.Apply();
            return _tex;
        }
    }
}
