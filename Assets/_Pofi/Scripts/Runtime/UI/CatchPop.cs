using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.UI
{
    /// <summary>
    /// Ceviz sepete düşünce kısa "pıt" (Ceviz Yakala): sıcak ışıma halkası açılıp söner, dört köşeli parıltılar yukarı saçılıp
    /// yerçekimiyle düşerek döner ve küçülür, üstte "+N" süzülür. Altın cevizde daha çok ve altın renkli. Parçacık sistemi yok:
    /// birkaç UI Image, kendi kendini yok eder. Hareket azaltma açıksa yalnız ışıma ve yazı.
    /// </summary>
    public sealed class CatchPop : MonoBehaviour
    {
        private const float Life = 0.75f;
        private RectTransform _glow;
        private Image _glowImg;
        private Color _glowCol;
        private readonly List<RectTransform> _bits = new List<RectTransform>();
        private readonly List<Image> _bitImg = new List<Image>();
        private readonly List<Vector2> _vel = new List<Vector2>();
        private readonly List<float> _spin = new List<float>();
        private float _t;

        public static void Play(RectTransform layer, Vector2 anchor, Vector2 offset, bool golden, int points, int fontSize)
        {
            var rt = Ui.Rect(layer, "CatchPop", anchor, Vector2.zero, offset);
            rt.gameObject.AddComponent<CatchPop>().Build(golden);
            var lbl = Ui.Label(layer, "+" + points, fontSize, golden ? Theme.Hex("#FFD23F") : Color.white, anchor, new Vector2(240f, 110f),
                FontStyle.Bold, TextAnchor.MiddleCenter, offset + new Vector2(0f, 70f));
            lbl.raycastTarget = false;
            var sh = lbl.gameObject.AddComponent<Shadow>();
            sh.effectColor = new Color(0.35f, 0.18f, 0.02f, 0.75f); sh.effectDistance = new Vector2(0f, -4f);
            lbl.gameObject.AddComponent<FloatUp>();
        }

        private void Build(bool golden)
        {
            _glowCol = golden ? Theme.Hex("#FFD54A") : Theme.Hex("#FFF4C8");
            _glow = Ui.Rect(transform, "Glow", new Vector2(0.5f, 0.5f), golden ? new Vector2(340f, 190f) : new Vector2(280f, 150f));
            _glowImg = _glow.gameObject.AddComponent<Image>();
            _glowImg.sprite = PanelKit.Glow; _glowImg.raycastTarget = false;
            _glowImg.color = new Color(_glowCol.r, _glowCol.g, _glowCol.b, 0.9f);
            if (Theme.ReduceMotion) return;
            var n = golden ? 12 : 7;
            var rnd = new System.Random(Time.frameCount * 31 + (golden ? 7 : 0));
            for (var i = 0; i < n; i++)
            {
                var size = (golden ? 44f : 34f) + (float)rnd.NextDouble() * (golden ? 30f : 20f);
                var b = Ui.Rect(transform, "Spark", new Vector2(0.5f, 0.5f), new Vector2(size, size));
                var img = b.gameObject.AddComponent<Image>();
                img.sprite = GoldKit.Twinkle; img.raycastTarget = false;
                img.color = i % 3 == 0 ? Color.white : golden ? Theme.Hex("#FFC93A") : Theme.Hex("#FFF1B0");
                var a = Mathf.Lerp(18f, 162f, (i + (float)rnd.NextDouble() * 0.8f) / n) * Mathf.Deg2Rad;
                var sp = 420f + (float)rnd.NextDouble() * 320f;
                _bits.Add(b); _bitImg.Add(img);
                _vel.Add(new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * sp);
                _spin.Add(((float)rnd.NextDouble() * 2f - 1f) * 420f);
            }
        }

        private void Update()
        {
            var dt = Mathf.Min(Time.unscaledDeltaTime, 0.05f);
            _t += dt;
            var g = Mathf.Clamp01(_t / 0.38f);
            var s = Mathf.Lerp(0.35f, 1.45f, 1f - (1f - g) * (1f - g));
            _glow.localScale = new Vector3(s, s, 1f);
            _glowImg.color = new Color(_glowCol.r, _glowCol.g, _glowCol.b, 0.9f * (1f - g));
            var life = Mathf.Clamp01(_t / Life);
            for (var i = 0; i < _bits.Count; i++)
            {
                var v = _vel[i];
                v.y -= 1500f * dt;
                _vel[i] = v;
                var rt = _bits[i];
                rt.anchoredPosition += v * dt;
                rt.localRotation = Quaternion.Euler(0f, 0f, _spin[i] * _t);
                var k = 1f - life * 0.7f;
                rt.localScale = new Vector3(k, k, 1f);
                var c = _bitImg[i].color; c.a = life < 0.55f ? 1f : Mathf.Clamp01(1f - (life - 0.55f) / 0.45f); _bitImg[i].color = c;
            }
            if (_t >= Life) Destroy(gameObject);
        }
    }
}
