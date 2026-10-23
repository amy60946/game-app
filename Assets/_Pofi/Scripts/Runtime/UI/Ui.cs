using System;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace Pofi.UI
{
    /// <summary>
    /// Koddan uGUI kurma yardımcıları. Sahne dosyası düzenlenmediği için (bkz. CLAUDE.md "kod olarak proje")
    /// tüm ekranlar bu fonksiyonlarla kurulur. Yatay: yükseklik 1080 birim, genişlik ekrana göre (en az ~1920).
    /// </summary>
    public static class Ui
    {
        private static Font _font;
        private static Sprite _rounded;

        /// <summary>Oyun yazı tipi: Baloo 2 ExtraBold (OFL, Resources/Fonts; v3 kararı 19 Ekim 2026). Yoksa Unity'nin yerleşik yazı tipi.</summary>
        public static Font Font => _font != null ? _font : (_font = Resources.Load<Font>("Fonts/Baloo2-ExtraBold") ?? Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf"));

        /// <summary>Özel yazı tipi zaten kalın: Unity'nin yapay kalınlığı uygulanmaz (harfler topaklanmasın).</summary>
        public static FontStyle StyleFor(FontStyle s) => Font != null && Font.name != "LegacyRuntime" && s == FontStyle.Bold ? FontStyle.Normal : s;

        /// <summary>Yuvarlak köşeli, 9 dilimli beyaz sprite (renk Image.color ile verilir).</summary>
        public static Sprite Rounded
        {
            get
            {
                if (_rounded != null) return _rounded;
                const int size = 128, r = 60;
                var tex = new Texture2D(size, size, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, filterMode = FilterMode.Bilinear };
                var px = new Color32[size * size];
                for (var y = 0; y < size; y++)
                for (var x = 0; x < size; x++)
                {
                    var cx = Mathf.Clamp(x + 0.5f, r, size - r);
                    var cy = Mathf.Clamp(y + 0.5f, r, size - r);
                    var d = Mathf.Sqrt((x + 0.5f - cx) * (x + 0.5f - cx) + (y + 0.5f - cy) * (y + 0.5f - cy));
                    var a = Mathf.Clamp01(r - d + 0.5f);
                    px[y * size + x] = new Color32(255, 255, 255, (byte)(a * 255));
                }
                tex.SetPixels32(px);
                tex.Apply(false, true);
                _rounded = Sprite.Create(tex, new Rect(0, 0, size, size), new Vector2(0.5f, 0.5f), 100f, 0, SpriteMeshType.FullRect, new Vector4(r, r, r, r));
                return _rounded;
            }
        }

        private static readonly System.Collections.Generic.Dictionary<string, Sprite> Portraits = new System.Collections.Generic.Dictionary<string, Sprite>();

        /// <summary>Petin konsept portresi (Resources/Portraits/pet_XX, art/scripts/render.py hero). Yoksa null.</summary>
        public static Sprite Portrait(string petId)
        {
            if (string.IsNullOrEmpty(petId)) return null;
            if (Portraits.TryGetValue(petId, out var s)) return s;
            var tex = Resources.Load<Texture2D>("Portraits/" + petId);
            s = tex == null ? null : Sprite.Create(tex, new Rect(0, 0, tex.width, tex.height), new Vector2(0.5f, 0.5f), 100f);
            Portraits[petId] = s;
            return s;
        }

        private static readonly System.Collections.Generic.Dictionary<string, Sprite> Icons = new System.Collections.Generic.Dictionary<string, Sprite>();

        /// <summary>Eşya/koleksiyon simgesi (Resources/Icons/&lt;id&gt;.png, şeffaf). Yoksa null.</summary>
        public static Sprite Icon(string id)
        {
            if (string.IsNullOrEmpty(id)) return null;
            if (Icons.TryGetValue(id, out var s)) return s;
            var tex = Resources.Load<Texture2D>("Icons/" + id);
            s = tex == null ? null : Sprite.Create(tex, new Rect(0, 0, tex.width, tex.height), new Vector2(0.5f, 0.5f), 100f);
            Icons[id] = s;
            return s;
        }

        private static readonly System.Collections.Generic.Dictionary<string, Sprite> Arts = new System.Collections.Generic.Dictionary<string, Sprite>();

        /// <summary>Resources altındaki görsel (ör. "Games/card_body"); yoksa null.</summary>
        public static Sprite Art(string path)
        {
            if (string.IsNullOrEmpty(path)) return null;
            if (Arts.TryGetValue(path, out var s)) return s;
            var tex = Resources.Load<Texture2D>(path);
            s = tex == null ? null : Sprite.Create(tex, new Rect(0, 0, tex.width, tex.height), new Vector2(0.5f, 0.5f), 100f);
            Arts[path] = s;
            return s;
        }

        /// <summary>Resources görseliyle Image (raycast kapalı); yoksa null.</summary>
        public static Image ArtImage(Transform parent, string path, Vector2 anchor, Vector2 size, Vector2 offset = default, bool keepAspect = true)
        {
            var sp = Art(path);
            if (sp == null) return null;
            var rt = Rect(parent, path, anchor, size, offset);
            var img = rt.gameObject.AddComponent<Image>();
            img.sprite = sp; img.preserveAspect = keepAspect; img.raycastTarget = false;
            return img;
        }

        /// <summary>Simge görüntüsü; simge yoksa null (çağıran yer tutucu çizer). tint: gri/siluet için.</summary>
        public static RectTransform IconImage(Transform parent, string id, Vector2 anchor, float size, Vector2 offset = default, Color? tint = null)
        {
            var sp = Icon(id);
            if (sp == null) return null;
            var rt = Rect(parent, "Icon " + id, anchor, new Vector2(size, size), offset);
            var img = rt.gameObject.AddComponent<Image>();
            img.sprite = sp;
            img.preserveAspect = true;
            img.raycastTarget = false;
            if (tint.HasValue) img.color = tint.Value;
            return rt;
        }

        /// <summary>Portre görüntüsü (yuvarlak arka planlı). Portre yoksa yalnızca renkli daire.</summary>
        public static RectTransform PortraitIcon(Transform parent, string petId, Color bg, Vector2 anchor, float size, Vector2 offset = default)
        {
            var rt = Rect(parent, "Portrait " + petId, anchor, new Vector2(size, size), offset);
            Panel(rt, bg, size / 2f);
            var sp = Portrait(petId);
            if (sp != null)
            {
                var pic = Rect(rt, "Pic", new Vector2(0.5f, 0.5f), new Vector2(size * 1.25f, size * 1.25f), new Vector2(0f, size * 0.06f));
                var img = pic.gameObject.AddComponent<Image>();
                img.sprite = sp;
                img.preserveAspect = true;
                img.raycastTarget = false;
            }
            return rt;
        }

        public static Canvas CreateCanvas(string name, int order)
        {
            var go = new GameObject(name);
            var canvas = go.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvas.sortingOrder = order;
            var scaler = go.AddComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1920f, 1080f);
            scaler.matchWidthOrHeight = 1f;   // yatay oyun: yükseklik her zaman 1080 birim, genişlik ekrana göre (16:9 → 1920, iPhone → ~2340)
            go.AddComponent<GraphicRaycaster>();
            return canvas;
        }

        public static void EnsureEventSystem()
        {
            if (EventSystem.current != null) return;
            var go = new GameObject("EventSystem");
            go.AddComponent<EventSystem>();
            go.AddComponent<StandaloneInputModule>();
        }

        /// <summary>Ebeveyni tamamen kaplayan boş dikdörtgen.</summary>
        public static RectTransform Fill(Transform parent, string name)
        {
            var go = new GameObject(name, typeof(RectTransform));
            go.transform.SetParent(parent, false);
            var rt = (RectTransform)go.transform;
            rt.anchorMin = Vector2.zero; rt.anchorMax = Vector2.one;
            rt.offsetMin = rt.offsetMax = Vector2.zero;
            return rt;
        }

        /// <summary>Çapa noktası (0–1) ve piksel boyutuyla yerleştirilmiş dikdörtgen.</summary>
        public static RectTransform Rect(Transform parent, string name, Vector2 anchor, Vector2 size, Vector2 offset = default)
        {
            var go = new GameObject(name, typeof(RectTransform));
            go.transform.SetParent(parent, false);
            var rt = (RectTransform)go.transform;
            rt.anchorMin = rt.anchorMax = anchor;
            rt.sizeDelta = size;
            rt.anchoredPosition = offset;
            return rt;
        }

        public static Image Panel(RectTransform rt, Color color, float radius)
        {
            var img = rt.gameObject.AddComponent<Image>();
            img.sprite = Rounded;
            img.type = Image.Type.Sliced;
            img.pixelsPerUnitMultiplier = 60f / Mathf.Max(4f, radius);
            img.color = color;
            return img;
        }

        public static Text Label(Transform parent, string text, int size, Color color, Vector2 anchor, Vector2 box,
            FontStyle style = FontStyle.Normal, TextAnchor align = TextAnchor.MiddleCenter, Vector2 offset = default)
        {
            var rt = Rect(parent, "Text", anchor, box, offset);
            var t = rt.gameObject.AddComponent<Text>();
            t.font = Font;
            t.text = text;
            t.fontSize = size;
            t.fontStyle = StyleFor(style);
            t.color = color;
            t.alignment = align;
            t.horizontalOverflow = HorizontalWrapMode.Wrap;
            t.verticalOverflow = VerticalWrapMode.Overflow;
            t.raycastTarget = false;
            return t;
        }

        public static Button Button(Transform parent, Theme th, string text, Vector2 anchor, Vector2 size, Action onClick,
            bool primary = true, Vector2 offset = default, int fontSize = 52, bool scaleSize = true, Color? color = null)
        {
            // Yaş bandı ölçeği (A: iri) yalnızca serbest yerleşimde; yan yana dizilen düğmelerde (scaleSize=false) taşmasın.
            var rt = Rect(parent, "Button " + text, anchor, scaleSize ? size * th.Scale : size, offset);
            var img = Candy.Shell(rt, color ?? (primary ? th.Primary : th.Secondary));   // 3B şeker görünüm (14 Ekim 2026); E dili: ana düğme yeşil verilebilir
            var btn = rt.gameObject.AddComponent<Button>();
            btn.targetGraphic = img;
            var colors = btn.colors;
            colors.pressedColor = new Color(0.85f, 0.85f, 0.85f);
            colors.disabledColor = new Color(0.75f, 0.75f, 0.75f, 0.6f);
            btn.colors = colors;
            var label = Label(rt, text, th.Font(fontSize), primary ? th.PrimaryText : th.SecondaryText, new Vector2(0.5f, 0.5f), rt.sizeDelta, FontStyle.Bold);
            label.name = "Label";
            if (primary) { var o = label.gameObject.AddComponent<Outline>(); o.effectColor = new Color(0.45f, 0.2f, 0f, 0.7f); o.effectDistance = new Vector2(2f, -2f); }
            btn.onClick.AddListener(() => Audio.Sfx.Play(Audio.SfxKind.Tap));
            if (onClick != null) btn.onClick.AddListener(() => onClick());
            rt.gameObject.AddComponent<PressBounce>();
            return btn;
        }

        public static InputField Input(Transform parent, Theme th, string placeholder, Vector2 anchor, Vector2 size, int limit,
            InputField.ContentType type, int fontSize = 64)
        {
            var rt = Rect(parent, "Input", anchor, size * th.Scale);
            var img = Panel(rt, Color.white, th.Radius);
            var outline = rt.gameObject.AddComponent<Outline>();
            outline.effectColor = new Color(th.Primary.r, th.Primary.g, th.Primary.b, 0.6f);
            outline.effectDistance = new Vector2(4f, -4f);
            var field = rt.gameObject.AddComponent<InputField>();
            field.targetGraphic = img;
            var inner = Fill(rt, "Area");
            inner.offsetMin = new Vector2(30f, 10f); inner.offsetMax = new Vector2(-30f, -10f);
            var ph = Label(inner, placeholder, th.Font(fontSize), new Color(th.SubtleText.r, th.SubtleText.g, th.SubtleText.b, 0.5f), new Vector2(0.5f, 0.5f), inner.rect.size);
            Stretch(ph.rectTransform);
            ph.fontStyle = FontStyle.Italic;
            var txt = Label(inner, "", th.Font(fontSize), th.Text, new Vector2(0.5f, 0.5f), inner.rect.size, FontStyle.Bold);
            Stretch(txt.rectTransform);
            txt.supportRichText = false;
            txt.horizontalOverflow = HorizontalWrapMode.Overflow;
            field.textComponent = txt;
            field.placeholder = ph;
            field.characterLimit = limit;
            field.contentType = type;
            field.lineType = InputField.LineType.SingleLine;
            field.caretWidth = 4;
            field.customCaretColor = true;
            field.caretColor = th.Primary;
            return field;
        }

        /// <summary>Yuvarlak çubuk gösterge (0–1). Dolu kısım rengi değere göre ayarlanabilir.</summary>
        public static Image Bar(Transform parent, Vector2 anchor, Vector2 size, Color back, Color fill, float radius, Vector2 offset = default)
        {
            var rt = Rect(parent, "Bar", anchor, size, offset);
            Panel(rt, back, radius).raycastTarget = false;
            var fillRt = Fill(rt, "Fill");
            fillRt.anchorMax = new Vector2(1f, 1f);
            var img = Panel(fillRt, fill, radius);
            img.raycastTarget = false;
            return img;
        }

        /// <summary>Bar dolumunu ayarlar (sliced görüntüde fillAmount çalışmadığı için genişlik değiştirilir).</summary>
        public static void SetBar(Image fill, float value01)
        {
            var rt = fill.rectTransform;
            var v = Mathf.Clamp01(value01);
            rt.anchorMax = new Vector2(Mathf.Max(0.12f, v), 1f);   // çok küçükte bile yuvarlak uç görünsün
            fill.enabled = v > 0.001f;
        }

        /// <summary>
        /// Dikey kaydırılabilir liste. İçerik kutusu (Content) döner; öğeler yukarıdan aşağı <see cref="VerticalLayoutGroup"/> ile dizilir.
        /// </summary>
        public static RectTransform ScrollList(Transform parent, Vector2 anchorMin, Vector2 anchorMax, float spacing, int columns = 1, Vector2 cell = default)
        {
            var view = Rect(parent, "Scroll", Vector2.zero, Vector2.zero);
            view.anchorMin = anchorMin; view.anchorMax = anchorMax;
            view.offsetMin = view.offsetMax = Vector2.zero;
            var bg = view.gameObject.AddComponent<Image>();
            bg.color = new Color(1f, 1f, 1f, 0.001f);   // sürükleme için tıklanabilir alan
            view.gameObject.AddComponent<RectMask2D>();
            var scroll = view.gameObject.AddComponent<ScrollRect>();
            scroll.horizontal = false;
            scroll.movementType = ScrollRect.MovementType.Elastic;
            scroll.scrollSensitivity = 30f;

            var content = new GameObject("Content", typeof(RectTransform)).GetComponent<RectTransform>();
            content.SetParent(view, false);
            content.anchorMin = new Vector2(0f, 1f); content.anchorMax = new Vector2(1f, 1f);
            content.pivot = new Vector2(0.5f, 1f);
            content.offsetMin = content.offsetMax = Vector2.zero;
            if (columns <= 1)
            {
                var v = content.gameObject.AddComponent<VerticalLayoutGroup>();
                v.spacing = spacing;
                v.padding = new RectOffset(24, 24, 16, 40);
                v.childAlignment = TextAnchor.UpperCenter;
                v.childControlWidth = true; v.childForceExpandWidth = true;
                v.childControlHeight = false; v.childForceExpandHeight = false;
            }
            else
            {
                var g = content.gameObject.AddComponent<GridLayoutGroup>();
                g.cellSize = cell;
                g.spacing = new Vector2(spacing, spacing);
                g.padding = new RectOffset(24, 24, 16, 40);
                g.constraint = GridLayoutGroup.Constraint.FixedColumnCount;
                g.constraintCount = columns;
                g.childAlignment = TextAnchor.UpperCenter;
            }
            content.gameObject.AddComponent<ContentSizeFitter>().verticalFit = ContentSizeFitter.FitMode.PreferredSize;
            scroll.content = content;
            scroll.viewport = view;
            return content;
        }

        /// <summary>Listeye sabit yükseklikli satır ekler (genişlik listeye uyar).</summary>
        public static RectTransform Row(Transform content, string name, float height)
        {
            var rt = new GameObject(name, typeof(RectTransform)).GetComponent<RectTransform>();
            rt.SetParent(content, false);
            rt.sizeDelta = new Vector2(0f, height);
            var le = rt.gameObject.AddComponent<LayoutElement>();
            le.preferredHeight = height;
            le.minHeight = height;
            return rt;
        }

        /// <summary>Bir dikdörtgeni ebeveyninin göreli bölgesine yerleştirir (0–1 köşeler).</summary>
        public static RectTransform Area(Transform parent, string name, Vector2 min, Vector2 max)
        {
            var rt = Fill(parent, name);
            rt.anchorMin = min; rt.anchorMax = max;
            return rt;
        }

        public static void Clear(Transform t)
        {
            for (var i = t.childCount - 1; i >= 0; i--) UnityEngine.Object.Destroy(t.GetChild(i).gameObject);
        }

        public static void Stretch(RectTransform rt)
        {
            rt.anchorMin = Vector2.zero; rt.anchorMax = Vector2.one;
            rt.offsetMin = rt.offsetMax = Vector2.zero;
        }

        public static void SetText(Button b, string text)
        {
            var t = b.GetComponentInChildren<Text>();
            if (t != null) t.text = text;
        }
    }

    /// <summary>
    /// Basınca ezilir (biraz alçalır ve yayılır), bırakınca yaylanıp hafifçe aşarak yerine oturur (A3, 23 Ekim 2026).
    /// Ses ve titreşim düğmenin kendi eyleminden gelir; burada yalnız biçim.
    /// </summary>
    public sealed class PressBounce : MonoBehaviour, IPointerDownHandler, IPointerUpHandler, IPointerExitHandler
    {
        private bool _down;
        private float _sq, _v;   // ezilme: 1 basılı, 0 serbest; bırakınca yayla eksiye aşar (uzama)
        /// <summary>En son basılan düğmenin ekran noktası ve zamanı (P1: pencere bu noktadan büyüyerek açılır).</summary>
        public static Vector2 LastPos;
        public static float LastTime = -10f;

        public void OnPointerDown(PointerEventData e)
        {
            _down = !Theme.ReduceMotion;
            LastPos = e.position; LastTime = Time.unscaledTime;
        }
        public void OnPointerUp(PointerEventData e) => _down = false;
        public void OnPointerExit(PointerEventData e) => _down = false;

        private void Update()
        {
            var dt = Mathf.Min(Time.unscaledDeltaTime, 0.05f);
            _v += ((_down ? 1f : 0f) - _sq) * 520f * dt - _v * 17f * dt;
            _sq += _v * dt;
            if (!_down && Mathf.Abs(_sq) < 0.002f && Mathf.Abs(_v) < 0.02f) { _sq = 0f; _v = 0f; }
            var target = 1f - 0.06f * _sq;
            var s = Mathf.Lerp(transform.localScale.x, target, 1f - Mathf.Exp(-26f * Time.unscaledDeltaTime));
            transform.localScale = new Vector3(s, s * (1f - 0.05f * _sq), 1f);
        }
    }

    /// <summary>
    /// Değer değişince kısa "zıplama" (coin, Güneş Taşı, gösterge dolunca; kullanıcı, 19 Ekim 2026: süreçlere küçük animasyonlar).
    /// Basma tepkisi (PressBounce) taşımayan öğelerde kullanılır.
    /// </summary>
    public sealed class Bump : MonoBehaviour
    {
        private float _t = 1f, _amount;

        public static void Play(Transform t, float amount = 0.22f)
        {
            if (t == null || Theme.ReduceMotion) return;
            var b = t.GetComponent<Bump>() ?? t.gameObject.AddComponent<Bump>();
            b._t = 0f; b._amount = amount;
        }

        private void Update()
        {
            if (_t >= 1f) return;
            _t = Mathf.Min(1f, _t + Time.unscaledDeltaTime / 0.38f);
            var s = 1f + _amount * Mathf.Sin(_t * Mathf.PI) * (1f - 0.4f * _t);
            transform.localScale = new Vector3(s, s, 1f);
        }
    }
}
