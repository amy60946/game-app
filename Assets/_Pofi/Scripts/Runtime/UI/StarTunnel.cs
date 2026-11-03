using UnityEngine;
using UnityEngine.UI;

namespace Pofi.UI
{
    /// <summary>
    /// Yıldız Kapısı geçişi (K4 A, 3 Kasım 2026): ekran kısa sürede aydınlık laciverde döner, yıldız çizgileri ortadan dışa akar
    /// (hızlanarak uzar), sonra koşu ekranının üstünden söner. İlk geçiş en çok 1,5 sn, sonrakiler 0,8 sn (Minecraft Nether'in 4 sn
    /// beklemesi çocuk için uzun bulundu). Ortası hiç kararmaz, ani yüksek ses yok: tek yumuşak "whoosh". Dokunmayı engeller.
    /// </summary>
    public sealed class StarTunnel : MonoBehaviour
    {
        private const int Streaks = 64;
        private RectTransform _root;
        private Image _bg;
        private readonly RectTransform[] _s = new RectTransform[Streaks];
        private readonly Vector2[] _dir = new Vector2[Streaks];
        private readonly float[] _r = new float[Streaks], _v = new float[Streaks];
        private float _t, _len;
        private System.Action _mid;
        private bool _midDone;
        private const float Out = 0.35f;

        /// <param name="seconds">Geçiş süresi (söndürme hariç).</param>
        /// <param name="midpoint">Ekran tamamen kapanınca (sürenin %70'i): sayfa burada değişir.</param>
        public static void Play(Transform overlay, float seconds, System.Action midpoint)
        {
            var root = Ui.Fill(overlay, "StarTunnel");
            var t = root.gameObject.AddComponent<StarTunnel>();
            t._root = root; t._len = Mathf.Max(0.5f, seconds); t._mid = midpoint;
            t._bg = root.gameObject.AddComponent<Image>();
            t._bg.color = new Color(0.22f, 0.3f, 0.66f, 0f);
            t._bg.raycastTarget = true;
            var rnd = new System.Random(7);
            for (var i = 0; i < Streaks; i++)
            {
                var a = (float)(rnd.NextDouble() * Mathf.PI * 2f);
                t._dir[i] = new Vector2(Mathf.Cos(a), Mathf.Sin(a));
                t._r[i] = (float)rnd.NextDouble() * 0.25f;
                t._v[i] = 0.6f + (float)rnd.NextDouble() * 0.9f;
                var s = Ui.Rect(root, "s", new Vector2(0.5f, 0.5f), new Vector2(8f, 8f));
                s.localRotation = Quaternion.Euler(0f, 0f, a * Mathf.Rad2Deg);
                var img = s.gameObject.AddComponent<Image>();
                img.color = i % 5 == 0 ? new Color(1f, 0.9f, 0.55f, 0f) : i % 3 == 0 ? new Color(0.7f, 0.88f, 1f, 0f) : new Color(1f, 1f, 1f, 0f);
                img.raycastTarget = false;
                t._s[i] = s;
            }
            Audio.Sfx.Play(Audio.SfxKind.Whoosh);
        }

        private void Update()
        {
            _t += Time.unscaledDeltaTime;
            var k = _t / _len;
            var w = _root.rect.width; var h = _root.rect.height;
            var diag = Mathf.Sqrt(w * w + h * h) * 0.5f;
            // arka plan: ilk %35'te açılır, söndürmede kapanır
            var fade = _t > _len ? 1f - Mathf.Clamp01((_t - _len) / Out) : 1f;
            _bg.color = new Color(0.22f, 0.3f, 0.66f, Mathf.Clamp01(k / 0.35f) * fade);
            var speed = Mathf.Lerp(0.3f, 2.4f, Mathf.Clamp01(k));
            for (var i = 0; i < Streaks; i++)
            {
                _r[i] += Time.unscaledDeltaTime * _v[i] * speed;
                if (_r[i] > 1.05f) _r[i] -= 1f;
                var r = _r[i] * _r[i];                         // ortada yavaş, kenarda hızlı (derinlik)
                var len = 8f + 260f * r * Mathf.Clamp01(k);
                _s[i].anchoredPosition = _dir[i] * r * diag;
                _s[i].sizeDelta = new Vector2(len, Mathf.Lerp(3f, 9f, r));
                var img = _s[i].GetComponent<Image>();
                var c = img.color; c.a = Mathf.Clamp01(k * 3f) * Mathf.Clamp01(r * 4f) * fade; img.color = c;
            }
            if (!_midDone && k >= 0.7f) { _midDone = true; var m = _mid; _mid = null; m?.Invoke(); _root.SetAsLastSibling(); }
            if (_t > _len + Out) Destroy(_root.gameObject);
        }
    }
}
