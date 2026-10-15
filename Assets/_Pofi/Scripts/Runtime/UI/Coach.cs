using System;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.UI
{
    /// <summary>
    /// Tanıtım ipucu (onboarding): büyük altyazı balonu + hareketli işaret eden el. Dokunma: hedefte 3 kez
    /// basar; sürükleme: başlangıçtan hedefe 3 kez gider-gelir; kaydırma: ekranın ortasından dışa kayar. Girdiyi engellemez
    /// (çocuk aynı anda hareketi yapabilir). Konumlar ekran pikseli olarak verilir (her karede yeniden okunur: hedef hareket edebilir).
    /// </summary>
    public sealed class Coach : MonoBehaviour
    {
        private RectTransform _root, _finger, _ring, _prop;
        private float _propS;
        private Image _fingerImg, _ringImg;
        private Func<Vector2> _from, _to;
        private Logic.App.TipGesture _gesture;
        private int _loops;
        private float _t, _life;
        public string Id { get; private set; }

        public static Coach Show(RectTransform root, string id, string caption, Logic.App.TipGesture gesture, Func<Vector2> from, Func<Vector2> to = null, int loops = 3,
            string step = null, Sprite prop = null)
        {
            var rt = Ui.Fill(root, "Coach " + id);
            var c = rt.gameObject.AddComponent<Coach>();
            var cg = rt.gameObject.AddComponent<CanvasGroup>(); cg.blocksRaycasts = false; cg.interactable = false;
            c._root = root; c.Id = id; c._gesture = gesture; c._from = from; c._to = to; c._loops = loops;

            // altyazı: mavi şeker panel, solda işaret eden el rozeti; oyun yazı tarzı (beyaz, koyu kontur), genişlik yazıya göre
            // üst şerit: seviye rozeti ile coin arasında (ekranın ortası, pet ve yol açık kalır); kısa cümle
            var banner = Candy.Banner(rt, Candy.Blue, "ui_hand", new Vector2(0.5f, 1f), new Vector2(0f, -70f), 760f, 36, false);
            banner.SetText(caption);
            banner.Rect.gameObject.AddComponent<PopIn>();
            if (!string.IsNullOrEmpty(step))
            {
                // sıra göstergesi ("3/7"): çocuk kaçıncı adımda olduğunu görür
                var badge = Ui.Rect(banner.Rect, "Step", new Vector2(1f, 1f), new Vector2(92f, 54f), new Vector2(-6f, 14f));
                Candy.Shell(badge, Candy.Orange).raycastTarget = false;
                badge.GetComponent<Image>().raycastTarget = false;
                Candy.Caption(badge, step, 30, new Vector2(0.5f, 0.5f), new Vector2(92f, 54f), new Vector2(0f, 2f));
            }
            if (prop != null)
            {
                // canlandırma: dokununca hedefin üstünde beliren eşya (ör. pete dokun → şapka)
                c._prop = Ui.Rect(rt, "Prop", Vector2.zero, new Vector2(150f, 150f));
                var pi = c._prop.gameObject.AddComponent<Image>(); pi.sprite = prop; pi.preserveAspect = true; pi.raycastTarget = false;
                c._prop.gameObject.AddComponent<Shadow>().effectDistance = new Vector2(0f, -6f);
                c._prop.localScale = Vector3.zero;
            }
            // dokunma halkası
            c._ring = Ui.Rect(rt, "Ring", Vector2.zero, new Vector2(150f, 150f));
            c._ringImg = c._ring.gameObject.AddComponent<Image>(); c._ringImg.sprite = Ui.Rounded; c._ringImg.type = Image.Type.Sliced;
            c._ringImg.pixelsPerUnitMultiplier = 0.8f; c._ringImg.color = new Color(1f, 1f, 1f, 0.35f);
            // işaret eden el (Resources/Icons/ui_hand.png, art/scripts/ui_hand.py); pivot = parmak ucu. Yoksa beyaz parmak ucu.
            var hand = Ui.Icon("ui_hand");
            c._finger = Ui.Rect(rt, "Finger", Vector2.zero, hand != null ? new Vector2(190f, 190f) : new Vector2(84f, 84f));
            c._fingerImg = c._finger.gameObject.AddComponent<Image>();
            if (hand != null)
            {
                c._finger.pivot = new Vector2(0.36f, 0.86f);
                c._fingerImg.sprite = hand; c._fingerImg.preserveAspect = true; c._fingerImg.raycastTarget = false;
            }
            else
            {
                c._fingerImg.sprite = Ui.Rounded; c._fingerImg.type = Image.Type.Sliced;
                c._fingerImg.pixelsPerUnitMultiplier = 1.4f; c._fingerImg.color = Color.white;
                var fo = c._finger.gameObject.AddComponent<Outline>(); fo.effectColor = new Color(1f, 0.55f, 0.1f); fo.effectDistance = new Vector2(4f, -4f);
                c._finger.gameObject.AddComponent<Shadow>().effectDistance = new Vector2(4f, -8f);
            }
            Audio.Sfx.Play(Audio.SfxKind.Tap);
            return c;
        }

        private Vector2 ToCanvas(Vector2 screen)
        {
            var k = _root.rect.width / Mathf.Max(1f, Screen.width);
            return screen * k;
        }

        private void Update()
        {
            _life += Time.unscaledDeltaTime;
            if (_loops <= 0) { _finger.gameObject.SetActive(false); _ring.gameObject.SetActive(false); if (_life > 14f) Destroy(gameObject); return; }
            _t += Time.unscaledDeltaTime / 1.6f;
            if (_t >= 1f) { _t = 0f; _loops--; }
            var a = ToCanvas(_from());
            Vector2 p; float press;
            switch (_gesture)
            {
                case Logic.App.TipGesture.Tap:
                    p = a;
                    press = Mathf.PingPong(_t * 4f, 1f);                     // iki kez bas
                    break;
                case Logic.App.TipGesture.Drag:
                    var b = ToCanvas(_to != null ? _to() : _from());
                    var m = Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(0.15f, 0.8f, _t));
                    p = Vector2.Lerp(a, b, m);
                    press = _t < 0.15f ? _t / 0.15f : _t > 0.85f ? 1f - (_t - 0.85f) / 0.15f : 1f;
                    break;
                default:                                                    // kaydırma: ortadan dışa
                    var d = ToCanvas(_to != null ? _to() : _from() + new Vector2(0f, Screen.height * 0.25f));
                    p = Vector2.Lerp(a, d, Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(0.1f, 0.85f, _t)));
                    press = 1f;
                    break;
            }
            // el basarken parmak ucu hedefe iner, kalkarken biraz geri çekilir
            _finger.anchoredPosition = p + new Vector2(10f, -14f) * (1f - press);
            _ring.anchoredPosition = p;
            _finger.localScale = Vector3.one * Mathf.Lerp(1.08f, 0.94f, press);
            _ring.localScale = Vector3.one * Mathf.Lerp(0.6f, 1.25f, press);
            _ringImg.color = new Color(1f, 1f, 1f, 0.45f * press);
            if (_prop != null)
            {
                // her basışta eşya hafifçe zıplayarak büyür, hedefin (petin başının) üstünde durur
                _propS = Mathf.Lerp(_propS, press > 0.6f ? 1.15f : 0.95f, 1f - Mathf.Exp(-10f * Time.unscaledDeltaTime));
                _prop.localScale = Vector3.one * _propS;
                _prop.anchoredPosition = a + new Vector2(0f, 170f + Mathf.Sin(_life * 3f) * 8f);
            }
        }

        public void Done() { if (this != null) Destroy(gameObject); }
    }

    /// <summary>Açılışta hafif zıplayarak büyüme (0,8 → 1).</summary>
    public sealed class PopIn : MonoBehaviour
    {
        private float _t;
        private void OnEnable() { _t = 0f; transform.localScale = Vector3.one * 0.8f; }
        private void Update()
        {
            if (_t >= 1f) return;
            _t = Mathf.Min(1f, _t + Time.unscaledDeltaTime / 0.28f);
            var k = 1f + Mathf.Sin(_t * Mathf.PI) * 0.06f;                 // küçük taşma
            transform.localScale = Vector3.one * Mathf.Lerp(0.8f, 1f, 1f - (1f - _t) * (1f - _t)) * k;
        }
    }
}
