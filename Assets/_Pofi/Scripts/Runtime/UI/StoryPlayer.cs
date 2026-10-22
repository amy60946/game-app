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
        private float _bars, _rise;
        private string _lastWho, _goText, _skipText;

        private static readonly Dictionary<string, string> PortraitIcons = new Dictionary<string, string>
        {
            { "kiskac", "res_crab" }, { "mavi", "res_seagull" }, { "tosbi", "res_turtle" }, { "pitir", "decor_palm" }, { "hisir", "decor_palm" },
        };

        public static void Play(Transform overlay, Theme th, StoryBook book, StoryScene scene, Mode mode, Logic.Profile.AgeBand band,
            string petName, string petId, string goText, string skipText, System.Action done)
        {
            if (scene == null || scene.Lines.Count == 0) { done?.Invoke(); return; }
            var root = Ui.Fill(overlay, "Story");
            var p = root.gameObject.AddComponent<StoryPlayer>();
            p._th = th; p._book = book; p._scene = scene; p._mode = mode; p._band = band;
            p._petName = petName; p._petId = petId; p._done = done; p._root = root; p._goText = goText; p._skipText = skipText;
            p.Build();
            Playing = true;
            p.Next();
        }

        private void Build()
        {
            // her yere dokun: ilerle (aynı zamanda adaya dokunuşu keser)
            var hit = _root.gameObject.AddComponent<Image>();
            hit.color = _mode == Mode.Island ? new Color(0.02f, 0.06f, 0.16f, 0.22f) : new Color(0f, 0f, 0f, 0.12f);
            var tap = _root.gameObject.AddComponent<Button>(); tap.transition = Selectable.Transition.None; tap.targetGraphic = hit;
            tap.onClick.AddListener(Tap);
            if (_mode == Mode.Cinema)
            {
                _barTop = Bar(true); _barBottom = Bar(false);
                _box = Ui.Rect(_root, "Box", new Vector2(0.5f, 0f), new Vector2(1640f, 250f), new Vector2(0f, 270f));
                Ui.Panel(_box, new Color(1f, 0.97f, 0.88f, 0.98f), 34f).raycastTarget = false;
                _text = Ui.Label(_box, "", _th.Font(48), Theme.Hex("#4A2C0A"), new Vector2(0.5f, 0.45f), new Vector2(1520f, 190f), FontStyle.Bold, TextAnchor.MiddleLeft);
            }
            else
            {
                _bubble = Ui.Rect(_root, "Bubble", new Vector2(0.5f, 0f), new Vector2(900f, 230f), new Vector2(0f, 520f));
                Ui.Panel(_bubble, new Color(1f, 0.97f, 0.88f, 0.98f), 44f).raycastTarget = false;
                _text = Ui.Label(_bubble, "", _th.Font(46), Theme.Hex("#4A2C0A"), new Vector2(0.5f, 0.45f), new Vector2(820f, 180f), FontStyle.Bold, TextAnchor.MiddleLeft);
                _go = Ui.Button(_root, _th, _goText, new Vector2(0.5f, 0f), new Vector2(360f, 120f), Finish, true, new Vector2(0f, 120f), 54, false);
                _go.gameObject.SetActive(false);
            }
            _text.horizontalOverflow = HorizontalWrapMode.Wrap;
            _portrait = Ui.Rect(_root, "Portrait", new Vector2(0f, 0f), new Vector2(520f, 520f));
            _portrait.pivot = new Vector2(0.5f, 0f);
            _portraitImg = _portrait.gameObject.AddComponent<Image>(); _portraitImg.preserveAspect = true; _portraitImg.raycastTarget = false;
            _portrait.SetSiblingIndex(_mode == Mode.Cinema ? 1 : _root.childCount - 1);
            _name = Ui.Rect(_mode == Mode.Cinema ? _box : _bubble, "Name", new Vector2(0f, 1f), new Vector2(320f, 64f), new Vector2(200f, 0f));
            Ui.Panel(_name, Theme.Hex("#E14652"), 18f).raycastTarget = false;
            _nameText = Ui.Label(_name, "", _th.Font(38), Color.white, new Vector2(0.5f, 0.5f), new Vector2(300f, 60f), FontStyle.Bold);
            var skip = Ui.Button(_root, _th, _skipText, new Vector2(1f, 1f), new Vector2(200f, 72f), Finish, false, new Vector2(-150f, _mode == Mode.Cinema ? -55f : -150f), 34, false);
            skip.transform.SetAsLastSibling();
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
            var narrator = l.Who == "narrator";
            _name.gameObject.SetActive(!narrator);
            _nameText.text = narrator ? "" : _book.NameOf(l.Who).Replace("{pet}", _petName);
            var okti = l.Who == "okti";
            _name.GetComponent<Image>().color = okti ? Theme.Hex("#2E6FE0") : Theme.Hex("#E14652");
            _text.fontStyle = narrator ? FontStyle.Italic : FontStyle.Bold;
            _text.alignment = narrator ? TextAnchor.MiddleCenter : TextAnchor.MiddleLeft;
            Sprite pic = null;
            if (okti) pic = Ui.Portrait(_petId);
            else if (PortraitIcons.TryGetValue(l.Who ?? "", out var icon)) pic = Ui.Icon(icon);
            _portraitImg.sprite = pic;
            _portrait.gameObject.SetActive(pic != null);
            // konuşan solda (adalı) ya da sağda (Okti); yeni konuşan alttan yükselir
            _portrait.anchorMin = _portrait.anchorMax = new Vector2(okti ? 0.82f : 0.18f, 0f);
            if (_lastWho != l.Who) _rise = 0f;
            _lastWho = l.Who;
            if (_mode == Mode.Island)
            {
                _bubble.anchoredPosition = new Vector2(pic == null ? 0f : okti ? -260f : 260f, 520f);
                if (_go != null) _go.gameObject.SetActive(false);
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
            _portrait.anchoredPosition = new Vector2(0f, (_mode == Mode.Cinema ? 250f : -40f) - (1f - k) * 520f);
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
                if (auto > 0f && _wait > auto) Next();
            }
        }

        private void Finish()
        {
            if (_done == null) return;
            var d = _done; _done = null;
            Playing = false;
            Destroy(gameObject);
            d();
        }

        private void OnDestroy()
        {
            Playing = false;
            if (_done != null) { var d = _done; _done = null; d(); }
        }
    }
}
