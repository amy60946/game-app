using UnityEngine;
using UnityEngine.UI;

namespace Pofi.UI
{
    /// <summary>
    /// Düğmeden doğan pencere (P1, 23 Ekim 2026): pencere dokunulan düğmenin içinden büyüyerek açılır (0,28 sn, hafif aşma),
    /// çarpıya basınca aynı noktaya küçülerek kapanır. Düğme dışından açılan (yönlendirme) pencerelerde yalnız hafif büyüme.
    /// </summary>
    public sealed class WindowGrow : MonoBehaviour
    {
        private RectTransform _rt;
        private CanvasGroup _group;
        private Vector2 _from;
        private float _t, _dir = 1f;
        private System.Action _done;

        public static WindowGrow Open(RectTransform root, Vector2? screenPoint)
        {
            var g = root.gameObject.AddComponent<WindowGrow>();
            g._rt = root;
            g._group = root.GetComponent<CanvasGroup>() ?? root.gameObject.AddComponent<CanvasGroup>();
            g._from = Vector2.zero;
            if (screenPoint.HasValue && root.parent is RectTransform parent)
            {
                var canvas = root.GetComponentInParent<Canvas>();
                var cam = canvas != null && canvas.renderMode != RenderMode.ScreenSpaceOverlay ? canvas.worldCamera : null;
                if (RectTransformUtility.ScreenPointToLocalPointInRectangle(parent, screenPoint.Value, cam, out var local))
                    g._from = local - parent.rect.center;
            }
            if (Theme.ReduceMotion) { g._t = 1f; g.Apply(1f); }
            else g.Apply(0f);
            return g;
        }

        /// <summary>Kapanış: aynı noktaya küçülüp söner, sonra <paramref name="done"/>.</summary>
        public void Close(System.Action done)
        {
            if (Theme.ReduceMotion || _dir < 0f) { done?.Invoke(); return; }
            _done = done; _dir = -1f; _t = 1f;
            _group.blocksRaycasts = false;
        }

        private void Update()
        {
            if (_dir > 0f && _t >= 1f) return;
            _t = Mathf.Clamp01(_t + _dir * Time.unscaledDeltaTime / (_dir > 0f ? 0.28f : 0.18f));
            Apply(_t);
            if (_dir < 0f && _t <= 0f) { var d = _done; _done = null; d?.Invoke(); }
        }

        private void Apply(float t)
        {
            // açılışta aşarak (back-out), kapanışta düz
            var k = _dir > 0f ? BackOut(t) : t;
            var s = Mathf.LerpUnclamped(0.12f, 1f, k);
            _rt.localScale = new Vector3(s, s, 1f);
            _rt.anchoredPosition = Vector2.LerpUnclamped(_from, Vector2.zero, k);
            _group.alpha = Mathf.Clamp01(t * 2.2f);
        }

        private static float BackOut(float t) { const float c = 1.3f; t -= 1f; return t * t * ((c + 1f) * t + c) + 1f; }
    }

    /// <summary>
    /// Pencerede Okti (P4, 23 Ekim 2026): pencerenin sol alt kenarından başını uzatır, hafifçe nefes alır, ara sıra göz kırpar gibi
    /// büzülür; başarı/coin sesinde sevinçle zıplar, dokununca kıkırdar. Liste ekranı bile bir arkadaşla yapılan iş gibi hisseder.
    /// </summary>
    public sealed class OktiPeek : MonoBehaviour
    {
        private RectTransform _face;
        private float _t, _joy, _in;

        public static OktiPeek Add(RectTransform root, string petId)
        {
            var sprite = Ui.Portrait(petId);
            if (sprite == null) return null;
            var holder = Ui.Rect(root, "OktiPeek", new Vector2(0f, 0f), new Vector2(240f, 240f), new Vector2(150f, -60f));
            var p = holder.gameObject.AddComponent<OktiPeek>();
            p._face = Ui.Rect(holder, "Face", new Vector2(0.5f, 0.5f), new Vector2(240f, 240f));
            var img = p._face.gameObject.AddComponent<Image>(); img.sprite = sprite; img.preserveAspect = true;
            var mask = holder.gameObject.AddComponent<RectMask2D>();
            _ = mask;
            var btn = p._face.gameObject.AddComponent<Button>(); btn.targetGraphic = img; btn.transition = Selectable.Transition.None;
            btn.onClick.AddListener(() => { p._joy = 0.6f; Audio.Sfx.Play(Audio.SfxKind.Pop); });
            Audio.Sfx.Played += p.OnSfx;
            return p;
        }

        private void OnDestroy() => Audio.Sfx.Played -= OnSfx;

        private void OnSfx(Audio.SfxKind k)
        {
            if (k == Audio.SfxKind.Success || k == Audio.SfxKind.Coin || k == Audio.SfxKind.Gain || k == Audio.SfxKind.Sparkle) _joy = 1f;
        }

        private void Update()
        {
            var dt = Time.unscaledDeltaTime;
            _t += dt;
            _in = Mathf.MoveTowards(_in, 1f, dt / 0.5f);
            _joy = Mathf.Max(0f, _joy - dt / 0.8f);
            var rise = Mathf.SmoothStep(0f, 1f, _in) * 95f;                       // pencere kenarından yükselir
            var hop = Mathf.Sin((1f - _joy) * Mathf.PI * 2f) * _joy * 60f;          // sevinç zıplaması
            var breath = Mathf.Sin(_t * 2.1f) * 4f;
            var blink = Mathf.Repeat(_t, 4.3f) < 0.12f ? 0.9f : 1f;                 // göz kırpar gibi kısa büzülme
            _face.anchoredPosition = new Vector2(0f, -120f + rise + hop + breath);
            _face.localScale = new Vector3(1f + (1f - blink) * 0.5f, blink, 1f);
            _face.localRotation = Quaternion.Euler(0f, 0f, Mathf.Sin(_t * 1.3f) * 4f + _joy * Mathf.Sin(_t * 20f) * 8f);
        }
    }
}
