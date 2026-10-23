using System.Collections;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace Pofi.UI
{
    /// <summary>
    /// E4 uzun bas bilgi (23 Ekim 2026, kullanıcı onayı): düğmeye ya da simgeye 0,45 sn basılı tutunca üstünde kısa bilgi baloncuğu
    /// çıkar, bırakınca kaybolur. Uzun basış düğmenin işini yapmaz (yalnız bilgi). Yazı kısa: bir cümle.
    /// </summary>
    public sealed class LongPressInfo : MonoBehaviour, IPointerDownHandler, IPointerUpHandler, IPointerExitHandler
    {
        private const float Hold = 0.45f;
        public string Text;
        private float _down = -1f;
        private CandyBanner _bubble;
        private Button _button;
        private static Transform _layer;
        /// <summary>Test sayaçları (PofiDebug lp): kaç basış geldi, kaç baloncuk açıldı.</summary>
        public static int Downs, Shows;
        public bool Pressed => _down >= 0f;

        /// <summary>Bilgi katmanı (oyun kurulurken: üst kanvas).</summary>
        public static void UseLayer(Transform overlay) => _layer = overlay;

        public static LongPressInfo Add(GameObject go, string text)
        {
            if (go == null || string.IsNullOrEmpty(text)) return null;
            var l = go.GetComponent<LongPressInfo>();
            if (l == null) l = go.AddComponent<LongPressInfo>();
            l.Text = text;
            var g = go.GetComponent<Graphic>();
            if (g != null) g.raycastTarget = true;   // salt gösterge (coin rozeti) de basılı tutmayı duysun
            return l;
        }

        public void OnPointerDown(PointerEventData e) { _down = Time.unscaledTime; Downs++; }
        public void OnPointerUp(PointerEventData e) => Release();
        public void OnPointerExit(PointerEventData e) => Release();

        private void Update()
        {
            if (_down < 0f || _bubble != null || Time.unscaledTime - _down < Hold) return;
            Show();
        }

        private void Show()
        {
            var layer = _layer != null ? _layer : GetComponentInParent<Canvas>()?.transform;
            if (layer == null) return;
            _bubble = Candy.Banner(layer, Candy.Blue, null, Vector2.zero, Vector2.zero, 760f, 34, true);
            _bubble.SetText(Text);
            var root = (RectTransform)layer;
            var k = root.rect.width / Mathf.Max(1f, Screen.width);
            var sp = RectTransformUtility.WorldToScreenPoint(null, transform.position);
            var rt = _bubble.Rect;
            rt.anchorMin = rt.anchorMax = Vector2.zero;
            var h = ((RectTransform)transform).rect.height * transform.lossyScale.y / Mathf.Max(0.0001f, root.lossyScale.y);
            var x = Mathf.Clamp(sp.x * k, rt.sizeDelta.x * 0.5f + 20f, root.rect.width - rt.sizeDelta.x * 0.5f - 20f);
            var y = Mathf.Min(sp.y * k + h * 0.5f + rt.sizeDelta.y * 0.5f + 24f, root.rect.height - rt.sizeDelta.y * 0.5f - 20f);
            rt.anchoredPosition = new Vector2(x, y);
            rt.gameObject.AddComponent<PopIn>();
            var cg = rt.gameObject.AddComponent<CanvasGroup>(); cg.blocksRaycasts = false;
            _button = GetComponent<Button>();
            if (_button != null) _button.enabled = false;   // uzun basış düğmenin işini yapmasın
            Audio.Haptics.Light();
            Shows++;
        }

        /// <summary>Test: basılı tutulmuş gibi baloncuğu aç (çekimler için).</summary>
        public void DebugShow() { if (_bubble == null) Show(); }

        private void Release()
        {
            _down = -1f;
            if (_bubble != null) { Destroy(_bubble.gameObject); _bubble = null; }
            if (_button != null && isActiveAndEnabled) StartCoroutine(ReEnable());
        }

        private IEnumerator ReEnable()
        {
            yield return null;   // bırakma tıklaması geçsin
            if (_button != null) _button.enabled = true;
            _button = null;
        }

        private void OnDisable()
        {
            _down = -1f;
            if (_bubble != null) { Destroy(_bubble.gameObject); _bubble = null; }
            if (_button != null) { _button.enabled = true; _button = null; }
        }
    }
}
