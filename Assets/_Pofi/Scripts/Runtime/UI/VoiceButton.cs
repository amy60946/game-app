using Pofi.Audio;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.UI
{
    /// <summary>
    /// Sesli okuma hoparlörü (23 Ekim 2026, kullanıcı onayı: "önerinle ilerleyelim"): konuşma balonunun sağ üst köşesinde küçük
    /// mavi şeker düğme; yalnız kaydı olan bir metin gösterilirken görünür. Dokununca susturur (sesli okuma kapanır), yeniden
    /// dokununca açar ve o cümleyi baştan okur. Kapalıyken üstü çizili (müzik düğmesiyle aynı dil). Okurken hafifçe nefes alır.
    /// Üstteki CanvasGroup dokunmayı kapatsa da (ipucu paneli) düğme dokunulur kalır; görünürlüğü balonunkini izler.
    /// </summary>
    public sealed class VoiceButton : MonoBehaviour
    {
        private string _text;
        private GameObject _slash;
        private CanvasGroup _cg, _follow;
        private RectTransform _rt;
        private float _t;

        public const float Size = 78f;

        /// <summary><paramref name="host"/>: balon/panel; düğme onun sağ üst köşesine, biraz dışa taşarak oturur.</summary>
        public static VoiceButton Attach(RectTransform host, Vector2? offset = null)
        {
            var b = Candy.Round(host, Candy.Blue, null, Size, new Vector2(1f, 1f), offset ?? new Vector2(-8f, -4f), null);
            b.name = "VoiceButton";
            var v = b.gameObject.AddComponent<VoiceButton>();
            v._rt = (RectTransform)b.transform;
            if (Ui.Icon("ui_voice") != null) Ui.IconImage(b.transform, "ui_voice", new Vector2(0.5f, 0.5f), Size * 0.66f);
            v._slash = Candy.OffSlash(b.transform, Size * 0.86f);   // müzik düğmesiyle aynı kırmızı "kapalı" çizgisi
            v._slash.SetActive(!Voice.Enabled);   // ilk karede (Update'ten önce) kapalı çizgisi yanlışlıkla görünmesin
            v._cg = b.gameObject.AddComponent<CanvasGroup>();
            v._cg.ignoreParentGroups = true;   // ipucu paneli dokunmayı kapatır; hoparlör yine dokunulur
            v._follow = host.GetComponentInParent<CanvasGroup>();
            b.onClick.AddListener(v.Toggle);
            b.transform.SetAsLastSibling();
            v.SetText(null);
            return v;
        }

        /// <summary>Gösterilen metin değişti: kaydı varsa düğme görünür.</summary>
        public void SetText(string text)
        {
            _text = text;
            if (_slash != null) _slash.SetActive(!Voice.Enabled);
            gameObject.SetActive(Voice.Has(text));
        }

        private void Toggle()
        {
            Voice.SetEnabled(!Voice.Enabled, _text);
            Sfx.Play(SfxKind.Tap);
            Bump.Play(transform, 0.2f);
        }

        private void Update()
        {
            // balon solarken/kapanırken düğme de (üst grubu yok saydığı için kendisi izler)
            var a = _follow != null && _follow != _cg ? _follow.alpha : 1f;
            _cg.alpha = a;
            _cg.blocksRaycasts = _cg.interactable = a > 0.5f;
            _slash.SetActive(!Voice.Enabled);
            _t += Time.unscaledDeltaTime;
            var s = Voice.IsSpeaking(_text) ? 1f + Mathf.Sin(_t * 7f) * 0.06f : 1f;
            _rt.localScale = Vector3.one * Mathf.Lerp(_rt.localScale.x, s, 0.3f);
        }
    }
}
