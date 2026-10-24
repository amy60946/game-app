using System.Collections.Generic;
using Pofi.Logic.Story;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.UI
{
    /// <summary>
    /// Hikâye sahnesi sunumu (Ö4/H1, 23 Ekim 2026; görünüş seçimi v4 taslaklarında S1/S2):
    /// <see cref="Mode.Cinema"/> = üst/alt bant, alt boyda krem kutu, ad etiketi (S1); <see cref="Mode.Island"/> = ada hafif kısılır,
    /// konuşan alttan yükselir, yanında balon, son satırda tek büyük düğme (S2). Her yere dokununca: yazı tamamlanır / sıradaki satır.
    /// "Atla" sahneyi geçer. 5 yaş ve altında satırlar kendiliğinden ilerler. Metin yaş grubuna göre (StoryDirector.Text).
    /// </summary>
    public sealed class StoryPlayer : MonoBehaviour
    {
        public enum Mode { Cinema, Island }
        public static bool Playing { get; private set; }
        /// <summary>Konuşan değişince (K: adadaki 3B adalı kendisi tepki verir).</summary>
        public static event System.Action<string> Speaker;
        private static StoryPlayer _current;

        /// <summary>Oynayan sahneyi bitir (ada ekranı kapanırken: sahne başka pencerenin üstünde kalmasın).</summary>
        public static void Stop() { if (_current != null) Destroy(_current.gameObject); }

        private StoryScene _scene;
        private StoryBook _book;
        private Mode _mode;
        private Logic.Profile.AgeBand _band;
        private string _petName, _petId;
        private System.Action _done;
        private int _i = -1;
        private string _full = "";
        private float _shown, _auto, _wait;
        private bool _typing;
        private Theme _th;
        private RectTransform _root, _barTop, _barBottom, _box, _bubble, _portrait, _name;
        private Text _text, _nameText;
        private Image _portraitImg;
        private Button _go;
        private VoiceButton _voice;
        private float _bars, _rise;
        private string _lastWho, _goText, _skipText;

        private static readonly Dictionary<string, string> PortraitIcons = new Dictionary<string, string>
        {
            { "kiskac", "res_crab" }, { "mavi", "res_seagull" }, { "tosbi", "res_turtle" }, { "pitir", "decor_palm" }, { "hisir", "decor_palm" },
        };

        /// <summary>
        /// Adalının konuşma portresi (24 Ekim 2026): oyundaki 3B modelden çizilmiş Resources/Portraits/res_&lt;kim&gt;
        /// (art/scripts/resident_portraits.py: Kıskaç, Mavi, Pus); yoksa eski simge. Anlatıcı ve Okti için null.
        /// </summary>
        public static Sprite ResidentPortrait(string who)
        {
            if (string.IsNullOrEmpty(who) || who == "narrator" || who == "okti") return null;
            var pic = Ui.Portrait("res_" + who);
            if (pic != null) return pic;
            return PortraitIcons.TryGetValue(who, out var icon) ? Ui.Icon(icon) : null;
        }

        public static void Play(Transform overlay, Theme th, StoryBook book, StoryScene scene, Mode mode, Logic.Profile.AgeBand band,
            string petName, string petId, string goText, string skipText, System.Action done)
        {
            if (scene == null || scene.Lines.Count == 0) { done?.Invoke(); return; }
            var root = Ui.Fill(overlay, "Story");
            var p = root.gameObject.AddComponent<StoryPlayer>();
            p._th = th; p._book = book; p._scene = scene; p._mode = mode; p._band = band;
            p._petName = petName; p._petId = petId; p._done = done; p._root = root; p._goText = goText; p._skipText = skipText;
            p.Build();
            Playing = true; _current = p; Audio.Music.Scene(true);
            p.Next();
        }

        private void Build()
        {
            // her yere dokun: ilerle (aynı zamanda adaya dokunuşu keser)
            var hit = _root.gameObject.AddComponent<Image>();
            hit.color = _mode == Mode.Island ? new Color(0.02f, 0.06f, 0.16f, 0.22f) : new Color(0f, 0f, 0f, 0.12f);
            var tap = _root.gameObject.AddComponent<Button>(); tap.transition = Selectable.Transition.None; tap.targetGraphic = hit;
            tap.onClick.AddListener(Tap);
            // konuşma kutusu ekranın ALT kenarında (kullanıcı, 24 Ekim 2026: "baloncuklar ekranın ortasında çıkıyor, alt kenara al");
            // konuşan karakter kutunun yanında, alt köşede ayakta: adalılar solda, Okti sağda. Ada ortası açık kalır.
            if (_mode == Mode.Cinema) { _barTop = Bar(true); _barBottom = Bar(false); }
            _box = Ui.Rect(_root, "Box", new Vector2(0.5f, 0f), new Vector2(1300f, 200f), new Vector2(0f, BoxBottom + 100f));
            Ui.Panel(_box, new Color(1f, 0.97f, 0.88f, 0.98f), 36f).raycastTarget = false;
            _box.gameObject.AddComponent<Shadow>().effectDistance = new Vector2(0f, -6f);
            _text = Ui.Label(_box, "", _th.Font(_mode == Mode.Cinema ? 46 : 44), Theme.Hex("#4A2C0A"), new Vector2(0.5f, 0.45f), new Vector2(1200f, 160f), FontStyle.Bold, TextAnchor.MiddleLeft);
            _bubble = _box;
            if (_mode == Mode.Island)
            {
                _go = Ui.Button(_root, _th, _goText, new Vector2(0.5f, 0f), new Vector2(340f, 112f), Finish, true, new Vector2(0f, 300f), 52, false);
                _go.gameObject.SetActive(false);
            }
            _text.horizontalOverflow = HorizontalWrapMode.Wrap;
            _voice = VoiceButton.Attach(_box);   // sesli okuma hoparlörü kutunun köşesinde
            _portrait = Ui.Rect(_root, "Portrait", new Vector2(0f, 0f), new Vector2(PortraitSize, PortraitSize));
            _portrait.pivot = new Vector2(0.5f, 0f);
            _portraitImg = _portrait.gameObject.AddComponent<Image>(); _portraitImg.preserveAspect = true; _portraitImg.raycastTarget = false;
            _portrait.SetAsLastSibling();   // karakter kutunun kenarının önünde durur
            _name = Ui.Rect(_mode == Mode.Cinema ? _box : _bubble, "Name", new Vector2(0f, 1f), new Vector2(320f, 64f), new Vector2(200f, 0f));
            Ui.Panel(_name, Theme.Hex("#E14652"), 18f).raycastTarget = false;
            _nameText = Ui.Label(_name, "", _th.Font(38), Color.white, new Vector2(0.5f, 0.5f), new Vector2(300f, 60f), FontStyle.Bold);
            var skip = Ui.Button(_root, _th, _skipText, new Vector2(1f, 1f), new Vector2(200f, 72f), Finish, false, new Vector2(-150f, _mode == Mode.Cinema ? -55f : -150f), 34, false);
            skip.transform.SetAsLastSibling();
        }

        private const float PortraitSize = 440f;
        /// <summary>Kutunun alt kenarı: sinemada alt bandın biraz üstü, adada ekranın dibi.</summary>
        private float BoxBottom => _mode == Mode.Cinema ? 36f : 26f;

        /// <summary>Kutuyu tam metne göre boyutlar: tek satır sığarsa genişlik yazı kadar, sığmazsa en geniş ve satır sayısı kadar yükseklik.</summary>
        private void Fit(RectTransform box, float maxW, float minW, float padX, float padY, float minH)
        {
            var tr = _text.rectTransform;
            _text.text = _full;
            _text.horizontalOverflow = HorizontalWrapMode.Overflow;
            var pref = _text.preferredWidth;
            var w = Mathf.Clamp(pref + padX * 2f, minW, maxW);
            tr.sizeDelta = new Vector2(w - padX * 2f, 10f);
            _text.horizontalOverflow = HorizontalWrapMode.Wrap;
            var h = Mathf.Max(minH, _text.preferredHeight + padY * 2f);
            box.sizeDelta = new Vector2(w, h);
            tr.anchorMin = tr.anchorMax = new Vector2(0.5f, 0.5f);
            tr.anchoredPosition = new Vector2(0f, -4f);
            tr.sizeDelta = new Vector2(w - padX * 2f, h - padY * 2f + 8f);
            _text.text = "";
        }

        private RectTransform Bar(bool top)
        {
            var b = Ui.Rect(_root, top ? "BarTop" : "BarBottom", new Vector2(0.5f, top ? 1f : 0f), Vector2.zero);
            b.anchorMin = new Vector2(0f, top ? 1f : 0f); b.anchorMax = new Vector2(1f, top ? 1f : 0f);
            b.pivot = new Vector2(0.5f, top ? 1f : 0f); b.anchoredPosition = Vector2.zero; b.sizeDelta = Vector2.zero;
            var img = b.gameObject.AddComponent<Image>(); img.color = Color.black; img.raycastTarget = false;
            return b;
        }

        private void Tap()
        {
            if (_typing) { _typing = false; _shown = _full.Length; _text.text = _full; _wait = 0f; return; }
            if (_go != null && _go.gameObject.activeSelf) return;   // son satır: tek düğme
            Next();
        }

        private void Next()
        {
            _i++;
            if (_i >= _scene.Lines.Count) { Finish(); return; }
            var l = _scene.Lines[_i];
            _full = StoryDirector.Text(l, _band).Replace("{pet}", _petName);
            _shown = 0f; _typing = true; _text.text = ""; _wait = 0f;
            _voice.SetText(_full);
            Audio.Voice.Say(_full, true);   // önceden kaydedilmiş ses (anlatıcı / Okti / adalı); kaydı yoksa önceki satırın sesi de susar
            var narrator = l.Who == "narrator";
            _name.gameObject.SetActive(!narrator);
            _nameText.text = narrator ? "" : _book.NameOf(l.Who).Replace("{pet}", _petName);
            var okti = l.Who == "okti";
            _name.GetComponent<Image>().color = okti ? Theme.Hex("#2E6FE0") : Theme.Hex("#E14652");
            _text.fontStyle = narrator ? FontStyle.Italic : FontStyle.Bold;
            _text.alignment = narrator ? TextAnchor.MiddleCenter : TextAnchor.MiddleLeft;
            var pic = okti ? Ui.Portrait(_petId) : ResidentPortrait(l.Who);
            _portraitImg.sprite = pic;
            _portrait.gameObject.SetActive(pic != null);
            // konuşan alt köşede: adalı solda, Okti sağda; yeni konuşan alttan yükselir
            _portrait.anchorMin = _portrait.anchorMax = new Vector2(okti ? 1f : 0f, 0f);
            if (_lastWho != l.Who) { _rise = 0f; Speaker?.Invoke(l.Who); }
            _lastWho = l.Who;
            // kutu yazının ihtiyacı kadar (kullanıcı, 23 Ekim 2026: "gereksiz yer kaplamasın"), alt kenarda; karakter varsa onun
            // yanına kayar (üst üste binmez). Genişlik ekrana göre: karakterin yeri kadar boşluk bırakılır.
            var rootW = Mathf.Max(1200f, _root.rect.width);
            var side = pic == null ? 0f : PortraitSize * 0.78f;
            var maxW = Mathf.Min(1500f, rootW - side - 120f);
            Fit(_box, maxW, 420f, 56f, 34f, 130f);
            var x = pic == null ? 0f : (okti ? -1f : 1f) * Mathf.Min(side * 0.5f + 30f, (rootW - _box.sizeDelta.x) * 0.5f - 40f);
            _box.anchoredPosition = new Vector2(x, BoxBottom + _box.sizeDelta.y * 0.5f);
            if (_go != null)
            {
                _go.gameObject.SetActive(false);
                ((RectTransform)_go.transform).anchoredPosition = new Vector2(x + _box.sizeDelta.x * 0.5f - 190f, BoxBottom + _box.sizeDelta.y + 70f);
            }
            Audio.Sfx.Play(Audio.SfxKind.Tap);
        }

        private void Update()
        {
            var dt = Time.unscaledDeltaTime;
            _bars = Mathf.MoveTowards(_bars, 1f, dt / 0.35f);
            if (_barTop != null) { var h = Mathf.SmoothStep(0f, 120f, _bars); _barTop.sizeDelta = new Vector2(0f, h); _barBottom.sizeDelta = new Vector2(0f, h); }
            _rise = Mathf.MoveTowards(_rise, 1f, dt / 0.35f);
            var k = 1f - Mathf.Pow(1f - _rise, 3f);
            var okti = _lastWho == "okti";
            _portrait.anchoredPosition = new Vector2((okti ? -1f : 1f) * (PortraitSize * 0.5f + 24f), -18f - (1f - k) * PortraitSize);   // tamamı ekranda
            if (_typing)
            {
                _shown += dt * 40f;   // saniyede 40 harf
                var n = Mathf.Min(_full.Length, (int)_shown);
                _text.text = _full.Substring(0, n);
                if (n >= _full.Length) _typing = false;
            }
            else
            {
                _wait += dt;
                if (_go != null && _i == _scene.Lines.Count - 1 && !_go.gameObject.activeSelf && _wait > 0.3f) { _go.gameObject.SetActive(true); Bump.Play(_go.transform, 0.3f); }
                var auto = StoryDirector.AutoAdvance(_band);
                if (auto > 0f && _wait > auto && !Audio.Voice.IsSpeaking(_full)) Next();   // okuma bitmeden geçmez
            }
        }

        private void Finish()
        {
            if (_done == null) return;
            var d = _done; _done = null;
            Playing = false;
            Audio.Voice.StopIf(_full);
            Destroy(gameObject);
            d();
        }

        private void OnDestroy()
        {
            Audio.Voice.StopIf(_full);
            Audio.Music.Scene(false);
            Playing = false;
            if (_current == this) _current = null;
            if (_done != null) { var d = _done; _done = null; d(); }
        }
    }
}
