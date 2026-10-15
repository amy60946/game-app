using UnityEngine;

namespace Pofi.UI
{
    /// <summary>
    /// iPhone çentiği / Dynamic Island ve ev çubuğu için güvenli alan (yatay oyun): kök RectTransform'u Screen.safeArea'nın
    /// yatay sınırlarına daraltır, dikeyde yalnız alttaki ev çubuğu payı bırakılır. WebGL/editörde güvenli alan tüm ekran → etkisiz.
    /// </summary>
    public sealed class SafeArea : MonoBehaviour
    {
        private Rect _last;
        private int _w, _h;

        private void OnEnable() => Apply();
        private void Update()
        {
            if (Screen.safeArea != _last || Screen.width != _w || Screen.height != _h) Apply();
        }

        private void Apply()
        {
            _last = Screen.safeArea; _w = Screen.width; _h = Screen.height;
            if (_w <= 0 || _h <= 0) return;
            var rt = (RectTransform)transform;
            var min = _last.position; var max = _last.position + _last.size;
            // alt pay en fazla ekran yüksekliğinin %6'sı (ev çubuğu); üstte (yatayda çentik yok) tam yükseklik
            rt.anchorMin = new Vector2(min.x / _w, Mathf.Min(min.y / _h, 0.06f));
            rt.anchorMax = new Vector2(max.x / _w, 1f);
            rt.offsetMin = Vector2.zero; rt.offsetMax = Vector2.zero;
        }
    }
}
