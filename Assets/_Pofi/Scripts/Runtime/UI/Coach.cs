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
        private RectTransform _root, _finger, _ring, _ring2, _glow, _prop, _carry, _banner, _pill;
        private CanvasGroup _bannerCg, _pillCg;
        private bool _collapsible, _collapsed, _handOnly;
        private float _readFor;   // sesli okuma yoksa (önceden okunduysa) yazının en az kalma süresi
        private float _propS;
        private readonly System.Collections.Generic.List<(RectTransform Rt, Vector2 Off)> _props = new System.Collections.Generic.List<(RectTransform, Vector2)>();
        private Image _fingerImg, _ringImg, _ring2Img, _glowImg;
        private static readonly Color HintYellow = new Color(1f, 0.82f, 0.25f);
        private Func<Vector2> _from, _to;
        private Logic.App.TipGesture _gesture;
        private int _loops;
        private float _t, _life;
        private string _said;
        private static readonly System.Collections.Generic.HashSet<string> Spoken = new System.Collections.Generic.HashSet<string>();
        public string Id { get; private set; }

        // ---- K6 A (kullanıcı kararı, 2 Kasım 2026): herkes için "Geç" + Defter › Nasıl oynanır (Logic.App.Hints) ----
        /// <summary>İpuçları kapalı mı (GameBootstrap bağlar): kapalıyken ipucu kurulur ama görünmez ve konuşmaz; akış aynen sürer.</summary>
        public static Func<bool> Quiet = () => false;
        /// <summary>Çocuk "Geç" → "Kapat" dedi (GameBootstrap ayarı kapatır, açık ipuçlarını susturur, kısa bilgi verir). Boşsa "Geç" yok.</summary>
        public static Action HintsOffRequested;
        /// <summary>Metin tablosu (tr.json): coach.skip, coach.skip_ask, coach.skip_yes, coach.skip_no (düğme yazıları seslendirilmez).</summary>
        public static Func<string, string> Text = k => k;
        private CanvasGroup _cg, _skipCg, _askCg;
        private CandyBanner _bannerBox;
        private RectTransform _skip, _ask;
        private string _caption;
        private bool _silent, _asking;

        /// <param name="voice">Sesli okunacak cümle (varsayılan: altyazının kendisi; rehberde ödül eki okunmaz).</param>
        /// <param name="carry">Sürüklemede elin taşıdığı eşya (ör. elma): kaynaktan alınır, hedefe bırakılınca küçülüp kaybolur.</param>
        /// <param name="props">Dokunmada hedefin çevresinde sırayla beliren eşyalar (ör. Okti'ye dokun → Besle, Yıka, Giydir baloncukları).</param>
        public static Coach Show(RectTransform root, string id, string caption, Logic.App.TipGesture gesture, Func<Vector2> from, Func<Vector2> to = null, int loops = 3,
            string step = null, Sprite prop = null, string voice = null, Sprite carry = null, Sprite[] props = null)
        {
            var rt = Ui.Fill(root, "Coach " + id);
            var c = rt.gameObject.AddComponent<Coach>();
            var cg = rt.gameObject.AddComponent<CanvasGroup>(); cg.blocksRaycasts = false; cg.interactable = false;
            c._root = root; c.Id = id; c._gesture = gesture; c._from = from; c._to = to; c._loops = loops;
            c._cg = cg;
            var quiet = Quiet != null && Quiet();

            // altyazı: mavi şeker panel, solda işaret eden el rozeti; oyun yazı tarzı (beyaz, koyu kontur), genişlik yazıya göre
            // alt şerit (kullanıcı, 19 Ekim 2026: üstte Güneş Taşı ve coin'i kapatıyordu): ekranın alt ortası, Besle/Yıka ile
            // eylem tuşunun arası; kısa cümle
            var banner = Candy.Banner(rt, Candy.Blue, "ui_hand", new Vector2(0.5f, 0f), new Vector2(0f, 150f), 760f, 36, false);
            banner.SetText(caption);
            c._banner = banner.Rect;
            c._bannerBox = banner;
            c._caption = caption;
            banner.Rect.gameObject.AddComponent<PopIn>();
            c._said = voice ?? caption;
            // sesli okuma: köşede hoparlör (sıra rozeti köşedeyse onun altında, sağ kenarda), ipucu bir kez okunur
            if (!quiet) VoiceButton.Attach(banner.Rect, string.IsNullOrEmpty(step) ? (Vector2?)null : new Vector2(46f, -50f)).SetText(c._said);
            var spoke = !quiet && Spoken.Add(id + "|" + c._said) && Audio.Voice.Say(c._said);   // aynı ipucu oturumda bir kez kendiliğinden okunur (tekrar: hoparlör)
            Hover.On(banner.Rect, 5f, 0.02f);                                   // öğretici baloncuklar canlı (S5)
            // GB20-17 (kullanıcı, 2 Kasım 2026: "ekranda çok yazı var; el + ses kullan"; benchmark Khan Academy Kids, Lingokids, Toca):
            // kaydı olan ipucu okunurken yazı görünür, okuma bitince küçük hapa (el + adım) döner; hapa dokununca yazı açılır ve yeniden
            // okunur. Sesli okuma kapalıysa ya da kayıt yoksa yazı kalır (okuyamayan da okuyabilen de yönlenir).
            c._bannerCg = banner.Rect.gameObject.AddComponent<CanvasGroup>();
            c._collapsible = !quiet && Audio.Voice.Enabled && Audio.Voice.Has(c._said);
            var words = c._said.Split(' ').Length;
            c._readFor = spoke ? 1.2f : Mathf.Clamp(words * 0.42f, 2.2f, 4.5f);
            if (c._collapsible)
            {
                var pill = Candy.Round(rt, Candy.Blue, "ui_hand", 104f, new Vector2(0.5f, 0f), new Vector2(0f, 150f), c.Expand);
                c._pill = (RectTransform)pill.transform;
                c._pillCg = pill.gameObject.AddComponent<CanvasGroup>();
                c._pillCg.ignoreParentGroups = true;   // ipucu katmanı dokunmayı kapatır; hap dokunulur kalır (görünürlüğü üst grupları izler)
                if (!string.IsNullOrEmpty(step))
                {
                    var pb = Ui.Rect(c._pill, "Step", new Vector2(1f, 1f), new Vector2(84f, 48f), new Vector2(18f, 8f));
                    Candy.Shell(pb, Candy.Orange).raycastTarget = false;
                    Candy.Caption(pb, step, 26, new Vector2(0.5f, 0.5f), new Vector2(84f, 48f), new Vector2(0f, 2f));
                }
                c._pill.localScale = Vector3.zero;
                c._pill.gameObject.SetActive(false);
            }
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
            if (props != null)
            {
                // menü canlandırması: baloncuklar hedefin üstünde yay çizer (oyundaki Besle/Yıka/Giydir yerleriyle aynı)
                for (var i = 0; i < props.Length; i++)
                {
                    if (props[i] == null) continue;
                    var k = props.Length == 1 ? 0.5f : i / (float)(props.Length - 1);
                    var off = new Vector2(Mathf.Lerp(-170f, 170f, k), 150f + 80f * Mathf.Sin(k * Mathf.PI));
                    var b = Ui.Rect(rt, "Bubble" + i, Vector2.zero, new Vector2(118f, 118f));
                    // oyundaki gibi çerçevesiz simge + gösterge çerçevesi (beyaz daire yok, 24 Ekim 2026)
                    var ii = Ui.Rect(b, "Pic", new Vector2(0.5f, 0.5f), new Vector2(104f, 104f)).gameObject.AddComponent<Image>();
                    ii.sprite = props[i]; ii.preserveAspect = true; ii.raycastTarget = false;
                    GoldKit.Frame3D(ii);
                    b.localScale = Vector3.zero;
                    c._props.Add((b, off));
                }
            }
            if (carry != null)
            {
                // elin taşıdığı eşya (parmağın altında; el üstte çizilir)
                c._carry = Ui.Rect(rt, "Carry", Vector2.zero, new Vector2(130f, 130f));
                var ci = c._carry.gameObject.AddComponent<Image>(); ci.sprite = carry; ci.preserveAspect = true; ci.raycastTarget = false;
                var cs = c._carry.gameObject.AddComponent<Shadow>(); cs.effectColor = new Color(0f, 0f, 0f, 0.3f); cs.effectDistance = new Vector2(0f, -8f);
                c._carry.localScale = Vector3.zero;
            }
            // GB20-17 belirgin el (araştırma: hareketin başlaması dikkati çeker, Abrams & Christ 2003; animasyonlu el durağan simgeden
            // iyi, Nacher 2014): hedefin altında nabız gibi atan sarı ışık + her basışta dışa yayılan iki sarı halka
            c._glow = Ui.Rect(rt, "Glow", Vector2.zero, new Vector2(200f, 200f));
            c._glowImg = c._glow.gameObject.AddComponent<Image>(); c._glowImg.sprite = Ui.Rounded; c._glowImg.type = Image.Type.Sliced;
            c._glowImg.pixelsPerUnitMultiplier = 0.45f; c._glowImg.color = new Color(HintYellow.r, HintYellow.g, HintYellow.b, 0.3f); c._glowImg.raycastTarget = false;
            c._ring = Ui.Rect(rt, "Ring", Vector2.zero, new Vector2(150f, 150f));
            c._ringImg = c._ring.gameObject.AddComponent<Image>(); c._ringImg.sprite = Ui.Rounded; c._ringImg.type = Image.Type.Sliced;
            c._ringImg.pixelsPerUnitMultiplier = 0.8f; c._ringImg.color = new Color(1f, 1f, 1f, 0.35f); c._ringImg.raycastTarget = false;
            var ro = c._ring.gameObject.AddComponent<Outline>(); ro.effectColor = new Color(0.55f, 0.32f, 0.05f, 0.5f); ro.effectDistance = new Vector2(3f, -3f);
            c._ring2 = Ui.Rect(rt, "Ring2", Vector2.zero, new Vector2(150f, 150f));
            c._ring2Img = c._ring2.gameObject.AddComponent<Image>(); c._ring2Img.sprite = Ui.Rounded; c._ring2Img.type = Image.Type.Sliced;
            c._ring2Img.pixelsPerUnitMultiplier = 0.8f; c._ring2Img.color = Color.clear; c._ring2Img.raycastTarget = false;
            // işaret eden el (Resources/Icons/ui_hand.png, art/scripts/ui_hand.py); pivot = parmak ucu. Yoksa beyaz parmak ucu.
            var hand = Ui.Icon("ui_hand");
            c._finger = Ui.Rect(rt, "Finger", Vector2.zero, hand != null ? new Vector2(190f, 190f) : new Vector2(84f, 84f));
            c._fingerImg = c._finger.gameObject.AddComponent<Image>();
            if (hand != null)
            {
                c._finger.pivot = new Vector2(0.21f, 0.93f);   // v3 eldiven (art/meshy/install_ui_v3.py ölçer)
                c._fingerImg.sprite = hand; c._fingerImg.preserveAspect = true; c._fingerImg.raycastTarget = false;
                GoldKit.Frame3D(c._fingerImg, 1.4f);            // GB20-17: göstergelerdeki beyaz kenar + yumuşak gölge, her zeminde seçilir
            }
            else
            {
                c._fingerImg.sprite = Ui.Rounded; c._fingerImg.type = Image.Type.Sliced;
                c._fingerImg.pixelsPerUnitMultiplier = 1.4f; c._fingerImg.color = Color.white;
                var fo = c._finger.gameObject.AddComponent<Outline>(); fo.effectColor = new Color(1f, 0.55f, 0.1f); fo.effectDistance = new Vector2(4f, -4f);
                c._finger.gameObject.AddComponent<Shadow>().effectDistance = new Vector2(4f, -8f);
            }
            if (quiet) c.Silence();
            else
            {
                if (HintsOffRequested != null) c.AddSkip();
                Audio.Sfx.Play(Audio.SfxKind.Tap);
            }
            return c;
        }

        /// <summary>Görünmez ve sessiz olur (ipuçları kapandı); el döngüsü ve bitiş zamanı aynen sürer (bekleyen akışlar takılmaz).</summary>
        public void Silence()
        {
            _silent = true;
            _asking = false;
            _collapsible = false;
            if (_cg != null) _cg.alpha = 0f;
            if (_pill != null) _pill.gameObject.SetActive(false);
            if (_skip != null) Destroy(_skip.gameObject);
            if (_ask != null) Destroy(_ask.gameObject);
            _skip = _ask = null;
            Audio.Voice.StopIf(_said);
        }

        /// <summary>Ekrandaki bütün ipuçlarını susturur.</summary>
        public static void SilenceAll()
        {
            foreach (var c in FindObjectsByType<Coach>(FindObjectsSortMode.None)) if (c != null) c.Silence();
        }

        /// <summary>Balonun sol üst köşesinde küçük "Geç" (dokunulur kalır: ipucu katmanı dokunmayı kapatır).</summary>
        private void AddSkip()
        {
            if (_banner == null) return;
            var b = Candy.Pill(_banner, Candy.Orange, Text("coach.skip"), new Vector2(0f, 1f), new Vector2(120f, 50f), new Vector2(58f, 8f), AskSkip, null, 24);
            _skip = (RectTransform)b.transform;
            _skipCg = _skip.gameObject.AddComponent<CanvasGroup>();
            _skipCg.ignoreParentGroups = true;
        }

        /// <summary>"Geç": yanlışlıkla kapanmasın diye kısa soru (Kapat / Vazgeç); yazı balonu bu arada küçülmez.</summary>
        private void AskSkip()
        {
            if (_asking || _silent || _banner == null) return;
            _asking = true;
            Audio.Voice.StopIf(_said);
            Audio.Sfx.Play(Audio.SfxKind.Tap);
            _bannerBox?.SetText(Text("coach.skip_ask"));
            Audio.Voice.Say(Text("coach.skip_ask"));   // kaydı varsa okunur (yoksa sessiz)
            if (_skip != null) _skip.gameObject.SetActive(false);
            _ask = Ui.Rect(_banner, "SkipAsk", new Vector2(0.5f, 0f), new Vector2(420f, 70f), new Vector2(0f, -46f));
            _askCg = _ask.gameObject.AddComponent<CanvasGroup>();
            _askCg.ignoreParentGroups = true;
            Candy.Pill(_ask, Candy.Green, Text("coach.skip_yes"), new Vector2(0.27f, 0.5f), new Vector2(190f, 64f), Vector2.zero, ConfirmSkip, null, 26);
            Candy.Pill(_ask, Candy.White, Text("coach.skip_no"), new Vector2(0.73f, 0.5f), new Vector2(190f, 64f), Vector2.zero, CancelSkip, null, 26);
        }

        private void CancelSkip()
        {
            if (!_asking) return;
            _asking = false;
            _bannerBox?.SetText(_caption);
            if (_ask != null) Destroy(_ask.gameObject);
            _ask = null;
            if (_skip != null) _skip.gameObject.SetActive(true);
            _life = 0f;
        }

        private void ConfirmSkip()
        {
            if (!_asking) return;
            _asking = false;
            HintsOffRequested?.Invoke();
            Silence();
        }

        /// <summary>Dokunulur parçalar (Geç, Kapat/Vazgeç) üst grupların görünürlüğünü izler (hikâye sahnesi arayüzü gizlerken ortada kalmasın).</summary>
        private void FollowParents(CanvasGroup g)
        {
            if (g == null) return;
            var a = 1f;
            foreach (var p in g.transform.parent.GetComponentsInParent<CanvasGroup>()) { a *= p.alpha; if (p.ignoreParentGroups) break; }
            g.alpha = a;
            g.blocksRaycasts = g.interactable = a > 0.5f;
        }

        private Vector2 ToCanvas(Vector2 screen)
        {
            var k = _root.rect.width / Mathf.Max(1f, Screen.width);
            return screen * k;
        }

        // ---- K5 B (kullanıcı, 3 Kasım 2026): hafif ipucu basamakları (benchmark Andersen vd. CHI 2012, Apple "etkileşimle öğret") ----
        // Çocuk ekrana dokunurken el çekilir (kendisi deniyor); 7 sn hareketsizlikte el geri gelir. 2. gelişte el + parıltı,
        // 3. ve sonrakilerde cümle yeniden okunur. Altyazı/hap yerinde kalır.
        public const float IdleShow = 7f;
        private static float _lastInput = -99f;
        private int _attempt = 1;
        private bool _away;

        private void UpdateIdle()
        {
            if (Input.touchCount > 0 || Input.GetMouseButton(0)) _lastInput = Time.unscaledTime;
            var idle = Time.unscaledTime - _lastInput >= IdleShow;
            if (!_away && !idle && _life > 2.5f && _loops > 0 && !_asking)
            {
                _away = true;
                _finger.gameObject.SetActive(false); _ring.gameObject.SetActive(false); _ring2.gameObject.SetActive(false); _glow.gameObject.SetActive(false);
                if (_carry != null) _carry.gameObject.SetActive(false);
            }
            else if (_away && idle)
            {
                _away = false; _attempt++; _t = 0f;
                _finger.gameObject.SetActive(true); _ring.gameObject.SetActive(true); _ring2.gameObject.SetActive(true); _glow.gameObject.SetActive(true);
                if (_carry != null) _carry.gameObject.SetActive(true);
                if (_silent) return;
                if (_attempt == 2)
                {
                    // parıltı: hedefin çevresinde yıldızlar + daha parlak ışık
                    var sp = _from();
                    StarSparkles.Around(transform, new Vector2(sp.x / Mathf.Max(1f, Screen.width), sp.y / Mathf.Max(1f, Screen.height)), new Vector2(0.06f, 0.08f), 8, Id.Length * 13, 1.6f);
                    _glowImg.color = new Color(HintYellow.r, HintYellow.g, HintYellow.b, 0.5f);
                }
                else if (_collapsible && _collapsed) Expand();
                else Audio.Voice.Say(_said, true);
            }
        }

        private void Update()
        {
            _life += Time.unscaledDeltaTime;
            UpdateIdle();
            if (_asking) { _life = 0f; if (_bannerCg != null) _bannerCg.alpha = 1f; }   // soru açıkken yazı küçülmez
            UpdateCollapse();
            if (_skip != null) FollowParents(_skipCg);
            if (_ask != null) FollowParents(_askCg);
            if (_away) return;   // K5 B: çocuk dokunuyor, el bekler
            if (_loops <= 0)
            {
                _finger.gameObject.SetActive(false); _ring.gameObject.SetActive(false); _ring2.gameObject.SetActive(false); _glow.gameObject.SetActive(false);
                if (_carry != null) _carry.gameObject.SetActive(false);
                foreach (var (b, _) in _props) b.gameObject.SetActive(false);
                if (_life > 14f) Destroy(gameObject);
                return;
            }
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
                    if (_carry != null)
                    {
                        // eşya parmak ucunda: başta kaynaktan büyüyerek alınır, hedefte "hap" diye küçülüp kaybolur
                        float cs;
                        if (_t < 0.15f) cs = Mathf.SmoothStep(0f, 1f, _t / 0.15f);
                        else if (_t < 0.8f) cs = 1f + 0.05f * Mathf.Sin(_t * 30f);
                        else if (_t < 0.88f) cs = Mathf.Lerp(1f, 1.25f, (_t - 0.8f) / 0.08f);
                        else cs = Mathf.Lerp(1.25f, 0f, Mathf.Clamp01((_t - 0.88f) / 0.1f));
                        _carry.localScale = Vector3.one * cs;
                        _carry.anchoredPosition = p + new Vector2(-34f, 46f);
                    }
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
            // belirişte zıplama (0,9 → 1,12 → 1), sonra basış ritmi
            var pop = _life < 0.45f ? Mathf.Lerp(0.9f, 1f, _life / 0.45f) + Mathf.Sin(_life / 0.45f * Mathf.PI) * 0.12f : 1f;
            _finger.localScale = Vector3.one * Mathf.Lerp(1.1f, 0.94f, press) * pop;
            _ring.localScale = Vector3.one * Mathf.Lerp(0.6f, 1.25f, press);
            _ringImg.color = new Color(1f, 1f, 1f, 0.5f * press);
            // basışta dışa yayılan sarı halka (1,0 → 1,8, 0,8 sn'de söner); sürüklemede yalnız başta ve sonda
            var ph = (_t * 2f) % 1f;
            _ring2.anchoredPosition = _gesture == Logic.App.TipGesture.Tap ? p : (_t < 0.5f ? a : p);
            _ring2.localScale = Vector3.one * Mathf.Lerp(0.8f, 1.8f, ph);
            _ring2Img.color = new Color(HintYellow.r, HintYellow.g, HintYellow.b, 0.7f * (1f - ph) * (1f - ph));
            _glow.anchoredPosition = p;
            _glow.localScale = Vector3.one * (1f + Mathf.Sin(_life * 5f) * 0.12f);
            _glowImg.color = new Color(HintYellow.r, HintYellow.g, HintYellow.b, 0.22f + 0.1f * Mathf.Sin(_life * 5f));
            if (_props.Count > 0)
            {
                // basıştan sonra baloncuklar sırayla açılır, döngü sonunda kapanır
                for (var i = 0; i < _props.Count; i++)
                {
                    var (b, off) = _props[i];
                    var open = _t > 0.3f + i * 0.08f && _t < 0.92f;
                    var cur = b.localScale.x;
                    var s = Mathf.Lerp(cur, open ? 1f : 0f, 1f - Mathf.Exp(-14f * Time.unscaledDeltaTime));
                    b.localScale = Vector3.one * s;
                    b.anchoredPosition = a + off + new Vector2(0f, Mathf.Sin(_life * 3f + i) * 6f);
                }
            }
            if (_prop != null)
            {
                // her basışta eşya hafifçe zıplayarak büyür, hedefin (petin başının) üstünde durur
                _propS = Mathf.Lerp(_propS, press > 0.6f ? 1.15f : 0.95f, 1f - Mathf.Exp(-10f * Time.unscaledDeltaTime));
                _prop.localScale = Vector3.one * _propS;
                _prop.anchoredPosition = a + new Vector2(0f, 170f + Mathf.Sin(_life * 3f) * 8f);
            }
        }

        public void Done() { if (this != null) Destroy(gameObject); }

        /// <summary>Yalnız el (altyazı balonu yok): hedef zaten alt şeritteyse (ör. "Harika!" düğmesi) balon üstüne binmesin.</summary>
        public Coach HandOnly()
        {
            _handOnly = true;
            if (_banner != null) _banner.gameObject.SetActive(false);
            if (_pill != null) _pill.gameObject.SetActive(false);
            Audio.Voice.StopIf(_said);
            return this;
        }

        /// <summary>Okuma bitince yazı söner, yerinde küçük hap (el + adım) kalır; hapa dokununca yazı açılır ve yeniden okunur.</summary>
        private void UpdateCollapse()
        {
            if (!_collapsible || _handOnly || _banner == null) return;
            var dt = Time.unscaledDeltaTime;
            if (!_collapsed && _life > _readFor && !Audio.Voice.IsSpeaking(_said)) { _collapsed = true; _pill.gameObject.SetActive(true); }
            _bannerCg.alpha = Mathf.MoveTowards(_bannerCg.alpha, _collapsed ? 0f : 1f, dt * 4f);
            _banner.gameObject.SetActive(_bannerCg.alpha > 0.001f);
            if (_pill.gameObject.activeSelf)
            {
                var want = _collapsed ? 1f : 0f;
                var sc = Mathf.MoveTowards(_pill.localScale.x, want, dt * 5f);
                _pill.localScale = Vector3.one * sc;
                if (!_collapsed && sc <= 0.001f) _pill.gameObject.SetActive(false);
                // üst grupları izle (hikâye sahnesi adanın arayüzünü gizlerken hap ortada kalmasın)
                var a = 1f;
                foreach (var g in GetComponentsInParent<CanvasGroup>()) { if (g == _pillCg) continue; a *= g.alpha; if (g.ignoreParentGroups) break; }
                _pillCg.alpha = a;
                _pillCg.blocksRaycasts = _pillCg.interactable = a > 0.5f && _collapsed;
            }
        }

        /// <summary>Hapa dokunuldu: yazı yeniden açılır ve okunur.</summary>
        private void Expand()
        {
            if (!_collapsed) return;
            _collapsed = false;
            _banner.gameObject.SetActive(true);
            _life = 0f;
            _readFor = Audio.Voice.Say(_said, true) ? 1.2f : 3f;
            _loops = Mathf.Max(_loops, 2);
            Audio.Sfx.Play(Audio.SfxKind.Tap);
        }

        private void OnDestroy() => Audio.Voice.StopIf(_said);
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
