using Pofi.Logic.Story;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.UI
{
    /// <summary>
    /// Giriş filmi (F, 23 Ekim 2026, kullanıcı onayı): yeni çocuk oyuna 5 sahnelik kısa filmle başlar (≈25 sn). Siyah bantlar,
    /// tam ekran 3B görsel yavaşça kayar ve yakınlaşır (Ken Burns), sahneler yumuşak geçer; altyazı saniyede 40 harfle belirir.
    /// Her yere dokununca cümle tamamlanır / sıradaki gelir; cümleler kendiliğinden de ilerler. "Atla" filmi geçer, son cümlede "Haydi!".
    /// Metin yaş grubuna göre (StoryDirector.Text): 5 yaş ve altı ile 6–8 kısa metin, 9–12 ile 13 ve üstü uzun metin. Defter'den yeniden izlenir.
    /// </summary>
    public sealed class FilmPlayer : MonoBehaviour
    {
        // sahne görseli, Ken Burns başlangıç/bitiş (ölçek, yatay %, dikey %), o sahnedeki cümle sayısı (story.json "intro" satırları sırayla)
        private static readonly (string Img, float S0, float X0, float Y0, float S1, float X1, float Y1, int Lines)[] Shots =
        {
            ("film_1_ada", 1f, 0f, 0f, 1.1f, -2f, -1f, 2),
            ("film_2_firtina", 1.08f, 1f, 0f, 1f, 0f, 0f, 1),
            ("film_3_sis", 1f, 0f, 0f, 1.08f, 1.5f, 1f, 1),
            ("film_4_misafir", 1.06f, -1.5f, 0f, 1f, 0f, 0f, 1),
            ("load_okti", 1f, 0f, 0f, 1.07f, 0f, -1.5f, 1),
        };
        private const float ShotSeconds = 8f, Hold = 2.6f;

        public static bool Playing { get; private set; }
        private static FilmPlayer _current;

        /// <summary>Oynayan filmi bitir (ekran değişince filmin üstte kalmaması için); bitiş işi (izlendi) yine çalışır.</summary>
        public static void Stop() { if (_current != null) Destroy(_current.gameObject); }

        private StoryScene _scene;
        private Logic.Profile.AgeBand _band;
        private string _petName;
        private System.Action _done;
        private RectTransform _root, _stageRt;
        private RectTransform[] _layers = new RectTransform[2];
        private Image[] _imgs = new Image[2];
        private CanvasGroup[] _fades = new CanvasGroup[2];
        private int _layer, _shot = -1, _lineInShot, _line = -1;
        private float _shotT, _wait;
        private VoiceButton _voice;
        private string _full = "";
        private float _shown;
        private bool _typing;
        private Text _sub;
        private Button _go;
        private Theme _th;
        private float _barH;
        private RectTransform _barTop, _barBottom;

        public static void Play(Transform overlay, Theme th, StoryScene intro, Logic.Profile.AgeBand band, string petName, string skipText, string goText, System.Action done)
        {
            if (intro == null || intro.Lines.Count == 0) { done?.Invoke(); return; }
            var root = Ui.Fill(overlay, "Film");
            root.SetAsLastSibling();
            var p = root.gameObject.AddComponent<FilmPlayer>();
            p._root = root; p._th = th; p._scene = intro; p._band = band; p._petName = petName ?? ""; p._done = done;
            p.Build(skipText, goText);
            Playing = true; _current = p; Audio.Music.Scene(true);
            p.NextLine();
        }

        private void Build(string skipText, string goText)
        {
            var bg = _root.gameObject.AddComponent<Image>(); bg.color = Color.black;
            var tap = _root.gameObject.AddComponent<Button>(); tap.transition = Selectable.Transition.None; tap.targetGraphic = bg;
            tap.onClick.AddListener(Tap);
            _stageRt = Ui.Fill(_root, "Stage");
            for (var i = 0; i < 2; i++)
            {
                _layers[i] = Ui.Fill(_stageRt, "Shot" + i);
                _imgs[i] = _layers[i].gameObject.AddComponent<Image>(); _imgs[i].raycastTarget = false; _imgs[i].preserveAspect = false;
                _fades[i] = _layers[i].gameObject.AddComponent<CanvasGroup>(); _fades[i].alpha = 0f; _fades[i].blocksRaycasts = false;
            }
            // altyazı: alt bandın hemen üstünde, koyu geçiş üstünde büyük beyaz yazı
            var shade = Ui.Rect(_root, "Shade", new Vector2(0.5f, 0f), Vector2.zero);
            shade.anchorMin = new Vector2(0f, 0f); shade.anchorMax = new Vector2(1f, 0.42f); shade.sizeDelta = Vector2.zero;
            var sg = shade.gameObject.AddComponent<RawImage>(); sg.raycastTarget = false; sg.texture = Fade(); sg.color = new Color(0f, 0f, 0f, 0.62f);
            _sub = Ui.Label(_root, "", _th.Font(52), Color.white, new Vector2(0.5f, 0f), new Vector2(1700f, 220f), FontStyle.Bold, TextAnchor.MiddleCenter, new Vector2(0f, 230f));
            _sub.horizontalOverflow = HorizontalWrapMode.Wrap;
            _voice = VoiceButton.Attach(_sub.rectTransform);   // sesli okuma hoparlörü altyazının sağ üstünde
            var sh = _sub.gameObject.AddComponent<Shadow>(); sh.effectColor = new Color(0f, 0f, 0f, 0.6f); sh.effectDistance = new Vector2(0f, -4f);
            _barTop = Bar(true); _barBottom = Bar(false);
            var skip = Ui.Button(_root, _th, skipText, new Vector2(1f, 1f), new Vector2(220f, 76f), Finish, false, new Vector2(-160f, -60f), 34, false);
            skip.transform.SetAsLastSibling();
            _go = Ui.Button(_root, _th, goText, new Vector2(0.5f, 0f), new Vector2(380f, 124f), Finish, true, new Vector2(0f, 104f), 56, false);
            _go.gameObject.SetActive(false);
        }

        private RectTransform Bar(bool top)
        {
            var b = Ui.Rect(_root, top ? "BarTop" : "BarBottom", new Vector2(0.5f, top ? 1f : 0f), Vector2.zero);
            b.anchorMin = new Vector2(0f, top ? 1f : 0f); b.anchorMax = new Vector2(1f, top ? 1f : 0f);
            b.pivot = new Vector2(0.5f, top ? 1f : 0f); b.sizeDelta = Vector2.zero;
            var img = b.gameObject.AddComponent<Image>(); img.color = Color.black; img.raycastTarget = false;
            return b;
        }

        private void Tap()
        {
            if (_go.gameObject.activeSelf) return;
            if (_typing) { _typing = false; _shown = _full.Length; _sub.text = _full; _wait = 0f; return; }
            NextLine();
        }

        private void NextLine()
        {
            _line++;
            if (_line >= _scene.Lines.Count) { ShowGo(); return; }
            // sahne değişimi: o sahnenin cümleleri bittiyse sıradaki görsel
            if (_shot < 0 || _lineInShot >= Shots[Mathf.Min(_shot, Shots.Length - 1)].Lines)
            {
                if (_shot < Shots.Length - 1) SetShot(_shot + 1);
                _lineInShot = 0;
            }
            _lineInShot++;
            var l = _scene.Lines[_line];
            _full = StoryDirector.Text(l, _band).Replace("{pet}", _petName);
            _shown = 0f; _typing = true; _sub.text = ""; _wait = 0f;
            _voice.SetText(_full);
            Audio.Voice.Say(_full, true);
            Audio.Sfx.Play(Audio.SfxKind.Tap);
        }

        private void ShowGo()
        {
            if (_go.gameObject.activeSelf) return;
            _go.gameObject.SetActive(true);
            Bump.Play(_go.transform, 0.3f);
            _line = _scene.Lines.Count - 1;
        }

        private void SetShot(int i)
        {
            _shot = i; _shotT = 0f; _layer ^= 1;
            var art = Ui.Art("Art/" + Shots[i].Img);
            _imgs[_layer].sprite = art;
            _imgs[_layer].color = art != null ? Color.white : new Color(0.1f, 0.15f, 0.3f);
            _layers[_layer].SetAsLastSibling();
            _fades[_layer].alpha = 0f;
            Apply(_layer, 0f);
        }

        private void Apply(int layer, float t)
        {
            var s = Shots[Mathf.Max(0, _shot)];
            var e = Mathf.SmoothStep(0f, 1f, t);
            var k = Mathf.Lerp(s.S0, s.S1, e);
            var x = Mathf.Lerp(s.X0, s.X1, e) / 100f; var y = Mathf.Lerp(s.Y0, s.Y1, e) / 100f;
            var rt = _layers[layer];
            var W = _root.rect.width; var H = _root.rect.height;
            // görsel ekranı kaplar (16:9 görsel, daha geniş ekranda yükseklik taşar)
            var art = _imgs[layer].sprite;
            var aspect = art != null ? art.rect.width / art.rect.height : 16f / 9f;
            var w = Mathf.Max(W, H * aspect); var h = w / aspect;
            rt.anchorMin = rt.anchorMax = new Vector2(0.5f, 0.5f);
            rt.sizeDelta = new Vector2(w, h);
            rt.localScale = Vector3.one * k;
            rt.anchoredPosition = new Vector2(x * w, y * h);
        }

        private void Update()
        {
            var dt = Time.unscaledDeltaTime;
            _barH = Mathf.MoveTowards(_barH, 96f, dt * 300f);
            _barTop.sizeDelta = new Vector2(0f, _barH); _barBottom.sizeDelta = new Vector2(0f, _barH);
            if (_shot >= 0)
            {
                _shotT += dt / ShotSeconds;
                Apply(_layer, Mathf.Clamp01(_shotT));
                _fades[_layer].alpha = Mathf.MoveTowards(_fades[_layer].alpha, 1f, dt / 0.7f);
                if (_fades[_layer].alpha >= 1f) _fades[_layer ^ 1].alpha = 0f;
            }
            if (_typing)
            {
                _shown += dt * 40f;
                var n = Mathf.Min(_full.Length, (int)_shown);
                _sub.text = _full.Substring(0, n);
                if (n >= _full.Length) _typing = false;
                return;
            }
            if (_go.gameObject.activeSelf) return;
            _wait += dt;
            var hold = Mathf.Max(Hold, StoryDirector.AutoAdvance(_band));
            if (_wait > hold && !Audio.Voice.IsSpeaking(_full)) NextLine();   // anlatıcı cümlesini bitirmeden sahne geçmez
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

        private static Texture2D _fade;

        private static Texture2D Fade()
        {
            if (_fade != null) return _fade;
            _fade = new Texture2D(1, 32, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp };
            for (var y = 0; y < 32; y++) { var a = 1f - y / 31f; _fade.SetPixel(0, y, new Color(1f, 1f, 1f, a * a)); }
            _fade.Apply();
            return _fade;
        }
    }
}
