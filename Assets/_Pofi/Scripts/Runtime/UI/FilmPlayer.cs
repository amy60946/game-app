using Pofi.Logic.Story;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.UI
{
    /// <summary>
    /// Giriş filmi (F, 23 Ekim 2026, kullanıcı onayı): yeni çocuk oyuna 5 sahnelik kısa filmle başlar (≈25 sn). 3B görsel
    /// yavaşça kayar ve yakınlaşır (Ken Burns), sahneler yumuşak geçer; altyazı saniyede 40 harfle belirir.
    /// Ekrana sığdırma (kullanıcı 24 Ekim 2026: "sahneler ekrandan taşmasın, eksik görünmesin"): görsel her ekran oranında TAM görünür
    /// (iPhone 19,5:9, 16:9, iPad 4:3); Ken Burns görselin içinde kalır (en çok tam sığan boy), altyazı görselin altındaki şeritte, "Atla"
    /// görselin dışında. Kalan yer aynı görselin bulanık kopyasıyla dolar (Art/Soft, art/scripts/film_soft.py).
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
        private const float Aspect = 1376f / 768f, SkipW = 220f;   // film görselleri 1376×768

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
        private Image[] _imgs = new Image[2], _softs = new Image[2];
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
        private RectTransform _shade;
        private float _lw, _lh, _strip, _areaW, _areaH;   // yerleşim: ekran boyu, altyazı şeridi, görselin sığacağı alan
        private Vector2 _areaC;

        public static void Play(Transform overlay, Theme th, StoryScene intro, Logic.Profile.AgeBand band, string petName, string skipText, string goText, System.Action done)
        {
            if (intro == null || intro.Lines.Count == 0) { done?.Invoke(); return; }
            var root = Ui.Fill(overlay, "Film");
            root.SetAsLastSibling();
            var p = root.gameObject.AddComponent<FilmPlayer>();
            p._root = root; p._th = th; p._scene = intro; p._band = band; p._petName = petName ?? ""; p._done = done;
            p.Build(skipText, goText);
            p.Layout();
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
                // her sahne katmanı: arkada ekranı kaplayan bulanık kopya + önde tam sığan görsel (gölgeli), birlikte söner
                _layers[i] = Ui.Fill(_stageRt, "Shot" + i);
                _softs[i] = Ui.Rect(_layers[i], "Soft", new Vector2(0.5f, 0.5f), Vector2.zero).gameObject.AddComponent<Image>(); _softs[i].raycastTarget = false;
                _imgs[i] = Ui.Rect(_layers[i], "Main", new Vector2(0.5f, 0.5f), Vector2.zero).gameObject.AddComponent<Image>(); _imgs[i].raycastTarget = false; _imgs[i].preserveAspect = false;
                var ds = _imgs[i].gameObject.AddComponent<Shadow>(); ds.effectColor = new Color(0f, 0f, 0f, 0.45f); ds.effectDistance = new Vector2(0f, -10f);
                _fades[i] = _layers[i].gameObject.AddComponent<CanvasGroup>(); _fades[i].alpha = 0f; _fades[i].blocksRaycasts = false;
            }
            // altyazı: görselin altındaki şeritte, koyu geçiş üstünde büyük beyaz yazı (yeri ve boyu Layout'ta)
            _shade = Ui.Rect(_root, "Shade", new Vector2(0.5f, 0f), Vector2.zero);
            _shade.anchorMin = new Vector2(0f, 0f); _shade.anchorMax = new Vector2(1f, 0.3f); _shade.sizeDelta = Vector2.zero;
            var sg = _shade.gameObject.AddComponent<RawImage>(); sg.raycastTarget = false; sg.texture = Fade(); sg.color = new Color(0f, 0f, 0f, 0.5f);
            _sub = Ui.Label(_root, "", _th.Font(52), Color.white, new Vector2(0.5f, 0f), new Vector2(1700f, 200f), FontStyle.Bold, TextAnchor.MiddleCenter, new Vector2(0f, 120f));
            _sub.horizontalOverflow = HorizontalWrapMode.Wrap; _sub.verticalOverflow = VerticalWrapMode.Truncate;
            _voice = VoiceButton.Attach(_sub.rectTransform);   // sesli okuma hoparlörü altyazının sağ üstünde
            var sh = _sub.gameObject.AddComponent<Shadow>(); sh.effectColor = new Color(0f, 0f, 0f, 0.6f); sh.effectDistance = new Vector2(0f, -4f);
            var skip = Ui.Button(_root, _th, skipText, new Vector2(1f, 1f), new Vector2(220f, 76f), Finish, false, new Vector2(-160f, -60f), 34, false);
            skip.transform.SetAsLastSibling();
            _go = Ui.Button(_root, _th, goText, new Vector2(0.5f, 0f), new Vector2(380f, 124f), Finish, true, new Vector2(0f, 104f), 56, false);
            _go.gameObject.SetActive(false);
        }

        /// <summary>Ekran boyuna göre yerleşim: altyazı şeridi altta, görsel kalan alana tam sığar; "Atla" görselin köşesine binmez.</summary>
        private void Layout()
        {
            var W = _root.rect.width; var H = _root.rect.height;
            if (W <= 0f || H <= 0f || (Mathf.Approximately(W, _lw) && Mathf.Approximately(H, _lh))) return;
            _lw = W; _lh = H;
            _strip = Mathf.Clamp(H * 0.22f, 170f, 260f);
            const float side = 28f; var top = 28f;
            _areaW = W - 2f * side; _areaH = H - _strip - top;
            // yanlarda "Atla"ya yer yoksa (16:9, iPad 4:3) görsel biraz aşağı iner; geniş iPhone'da düğme yan boşlukta durur
            if ((W - Mathf.Min(_areaW, _areaH * Aspect)) * 0.5f < SkipW + 60f) { top = 108f; _areaH = H - _strip - top; }
            _areaC = new Vector2(0f, _strip + _areaH * 0.5f - H * 0.5f);
            var sub = _sub.rectTransform;
            sub.sizeDelta = new Vector2(Mathf.Min(1700f, W - 160f), _strip - 40f);
            sub.anchoredPosition = new Vector2(0f, _strip * 0.5f);
            ((RectTransform)_go.transform).anchoredPosition = new Vector2(0f, _strip * 0.5f);
            _shade.anchorMax = new Vector2(1f, Mathf.Clamp01((_strip + 90f) / H));
            if (_full.Length > 0) FitSub(_full);
            if (_shot >= 0) for (var i = 0; i < 2; i++) Apply(i, Mathf.Clamp01(_shotT));
        }

        /// <summary>Altyazı yazı boyu tam cümleye göre bir kez seçilir (yazılırken boyu değişip zıplamasın); şeride sığana dek küçülür.</summary>
        private void FitSub(string text)
        {
            var max = _th.Font(52); var box = _sub.rectTransform.rect;
            var size = max;
            for (; size > 30; size -= 2)
            {
                _sub.fontSize = size;
                var st = _sub.GetGenerationSettings(new Vector2(box.width, 0f));
                if (_sub.cachedTextGeneratorForLayout.GetPreferredHeight(text, st) / Mathf.Max(0.01f, _sub.pixelsPerUnit) <= box.height) break;
            }
            _sub.fontSize = size;
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
            FitSub(_full);
            _shown = 0f; _typing = true; _sub.text = ""; _wait = 0f;
            _voice.SetText(_full);
            Audio.Voice.Say(_full, true);
            Audio.Sfx.Play(Audio.SfxKind.Tap);
        }

        private void ShowGo()
        {
            if (_go.gameObject.activeSelf) return;
            _go.gameObject.SetActive(true);
            _sub.gameObject.SetActive(false);   // "Haydi!" altyazı şeridinde, yazının yerine (üst üste binmesin)
            Bump.Play(_go.transform, 0.3f);
            _line = _scene.Lines.Count - 1;
        }

        private void SetShot(int i)
        {
            _shot = i; _shotT = 0f; _layer ^= 1;
            var art = Ui.Art("Art/" + Shots[i].Img);
            _imgs[_layer].sprite = art;
            _imgs[_layer].color = art != null ? Color.white : new Color(0.1f, 0.15f, 0.3f);
            var soft = Ui.Art("Art/Soft/" + Shots[i].Img);
            _softs[_layer].sprite = soft;
            _softs[_layer].color = soft != null ? Color.white : new Color(0.04f, 0.06f, 0.12f);
            _layers[_layer].SetAsLastSibling();
            _fades[_layer].alpha = 0f;
            Apply(_layer, 0f);
        }

        private void Apply(int layer, float t)
        {
            var s = Shots[Mathf.Max(0, _shot)];
            var e = Mathf.SmoothStep(0f, 1f, t);
            // Ken Burns görselin içinde kalır: 1–1,1 yakınlaşma → tam sığan boyun %94–100'ü; kayma yalnız boş payda (görsel hiç kesilmez)
            var k = Mathf.Clamp(0.94f + (Mathf.Lerp(s.S0, s.S1, e) - 1f) * 0.6f, 0.9f, 1f);
            var art = _imgs[layer].sprite;
            var aspect = art != null ? art.rect.width / art.rect.height : Aspect;
            var fw = Mathf.Min(_areaW, _areaH * aspect); var fh = fw / aspect;
            var w = fw * k; var h = fh * k;
            var mx = (_areaW - w) * 0.5f; var my = (_areaH - h) * 0.5f;
            var x = Mathf.Clamp(Mathf.Lerp(s.X0, s.X1, e) / 100f * fw, -mx, mx);
            var y = Mathf.Clamp(Mathf.Lerp(s.Y0, s.Y1, e) / 100f * fh, -my, my);
            var rt = _imgs[layer].rectTransform;
            rt.sizeDelta = new Vector2(w, h);
            rt.anchoredPosition = _areaC + new Vector2(x, y);
            // arkada bulanık kopya ekranı kaplar, öndekiyle birlikte hafifçe kayar
            var sr = _softs[layer].rectTransform;
            var cw = Mathf.Max(_lw, _lh * aspect) * 1.06f;
            sr.sizeDelta = new Vector2(cw, cw / aspect);
            sr.anchoredPosition = new Vector2(x, y) * 0.5f;
        }

        private void Update()
        {
            var dt = Time.unscaledDeltaTime;
            Layout();   // ekran dönerse / boyut değişirse
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
