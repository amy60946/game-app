using System;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.UI
{
    /// <summary>
    /// Sahnenin üstünde süzülen 3B görünümlü "şeker" düğmeler, gösterge halkaları ve rozetler (14 Ekim 2026 arayüz kararı:
    /// panel yok, alt menü yok). Hepsi koddan üretilen dokularla çizilir; simgeler Resources/Icons'tan gelir.
    /// </summary>
    public static class Candy
    {
        public static readonly Color Orange = new Color(1f, 0.52f, 0.12f), Blue = new Color(0.2f, 0.65f, 0.96f),
            Green = new Color(0.32f, 0.78f, 0.3f), White = new Color(0.98f, 0.98f, 1f), Pink = new Color(1f, 0.42f, 0.62f);

        private static Sprite _body, _gloss, _ring;

        /// <summary>Gövde: yukarıdan aşağı koyulaşan, 9 dilimli yuvarlak (renk Image.color ile).</summary>
        private static Sprite Body => _body != null ? _body : (_body = Make((x, y, d) =>
        {
            var a = Mathf.Clamp01(60f - d + 0.5f);
            var shade = Mathf.Lerp(0.78f, 1f, y / 128f);                 // altta koyu
            var rim = Mathf.Clamp01((d - 55f) / 5f) * 0.12f;             // kenarda hafif koyu çizgi
            var v = Mathf.Clamp01(shade - rim);
            return new Color(v, v, v, a);
        }, true));

        /// <summary>Parlama: üst yarıda beyaz, yumuşak geçişli şerit (renklenmez).</summary>
        private static Sprite Gloss => _gloss != null ? _gloss : (_gloss = Make((x, y, d) =>
        {
            var a = Mathf.Clamp01(52f - d + 0.5f) * Mathf.SmoothStep(0f, 1f, (y - 64f) / 50f) * 0.55f;
            return new Color(1f, 1f, 1f, a);
        }, true));

        /// <summary>Halka (gösterge dolgusu için, Filled/Radial360).</summary>
        private static Sprite Ring => _ring != null ? _ring : (_ring = Make((x, y, d) =>
        {
            var a = Mathf.Clamp01(63f - d + 0.5f) * Mathf.Clamp01(d - 47f + 0.5f);
            return new Color(1f, 1f, 1f, a);
        }, false));

        private static Sprite Make(Func<int, int, float, Color> f, bool sliced)
        {
            const int size = 128;
            var tex = new Texture2D(size, size, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, filterMode = FilterMode.Bilinear };
            var px = new Color[size * size];
            for (var y = 0; y < size; y++)
            for (var x = 0; x < size; x++)
            {
                float d;
                if (sliced)
                {
                    var cx = Mathf.Clamp(x + 0.5f, 60f, size - 60f);
                    var cy = Mathf.Clamp(y + 0.5f, 60f, size - 60f);
                    d = Mathf.Sqrt((x + 0.5f - cx) * (x + 0.5f - cx) + (y + 0.5f - cy) * (y + 0.5f - cy));
                }
                else d = Mathf.Sqrt((x + 0.5f - 64f) * (x + 0.5f - 64f) + (y + 0.5f - 64f) * (y + 0.5f - 64f));
                px[y * size + x] = f(x, y, d);
            }
            tex.SetPixels(px);
            tex.Apply(false, true);
            return sliced
                ? Sprite.Create(tex, new Rect(0, 0, size, size), new Vector2(0.5f, 0.5f), 100f, 0, SpriteMeshType.FullRect, new Vector4(60, 60, 60, 60))
                : Sprite.Create(tex, new Rect(0, 0, size, size), new Vector2(0.5f, 0.5f), 100f);
        }

        private static Image Img(Transform parent, string name, Sprite sp, Color c, bool sliced)
        {
            var rt = Ui.Fill(parent, name);
            var img = rt.gameObject.AddComponent<Image>();
            img.sprite = sp; img.color = c; img.raycastTarget = false;
            if (sliced) img.type = Image.Type.Sliced;
            return img;
        }

        /// <summary>
        /// Şeker gövde: altta koyu dudak (3B kalınlık) + gövde + parlama. Sıra önemli: uGUI'de sonra gelen çocuk üstte çizilir.
        /// Gövde Image'ını döndürür (düğmenin hedef grafiği; renk değiştirmek için).
        /// </summary>
        internal static Image Shell(RectTransform rt, Color c)
        {
            var skin = Skin.ButtonFor(c, out var isCard);
            if (skin != null)
            {
                // v3 (Meshy parçası): renge en yakın parlak düğme ya da krem kart; 9 dilimli, öğe yüksekliğine ölçekli
                var h0 = rt.gameObject.AddComponent<Image>(); h0.color = new Color(1f, 1f, 1f, 0f);
                var b0 = Img(rt, "Body", skin, Color.white, true);
                Skin.Apply(b0, skin, rt.sizeDelta.y > 1f ? rt.sizeDelta.y : 120f);
                if (!isCard) { var ds = b0.gameObject.AddComponent<Shadow>(); ds.effectColor = new Color(0f, 0f, 0f, 0.25f); ds.effectDistance = new Vector2(0f, -6f); }
                return b0;
            }
            var hit = rt.gameObject.AddComponent<Image>();               // tıklama alanı (görünmez)
            hit.color = new Color(1f, 1f, 1f, 0f);
            var lip = Ui.Rect(rt, "Lip", Vector2.zero, Vector2.zero);
            lip.anchorMin = Vector2.zero; lip.anchorMax = Vector2.one;
            lip.offsetMin = new Vector2(0f, -9f); lip.offsetMax = new Vector2(0f, -9f);
            var li = lip.gameObject.AddComponent<Image>();
            li.sprite = Body; li.type = Image.Type.Sliced; li.color = new Color(c.r * 0.6f, c.g * 0.6f, c.b * 0.6f, 1f); li.raycastTarget = false;
            var drop = lip.gameObject.AddComponent<Shadow>();
            drop.effectColor = new Color(0f, 0f, 0f, 0.28f); drop.effectDistance = new Vector2(0f, -8f);
            var body = Img(rt, "Body", Body, c, true);
            var edge = body.gameObject.AddComponent<Outline>();
            edge.effectColor = new Color(1f, 1f, 1f, 0.85f); edge.effectDistance = new Vector2(3f, -3f);
            Img(rt, "Gloss", Gloss, Color.white, true);
            return body;
        }

        /// <summary>Yuvarlak düğme gövdesi: v3 beyaz halkalı krem disk (yoksa eski şeker gövde).</summary>
        internal static Image RoundShell(RectTransform rt, Color c)
        {
            var round = Skin.RoundButton;
            if (round == null) return Shell(rt, c);
            var hit = rt.gameObject.AddComponent<Image>(); hit.color = new Color(1f, 1f, 1f, 0f);
            var body = Img(rt, "Body", round, Color.white, false); body.preserveAspect = true;
            var ds = body.gameObject.AddComponent<Shadow>(); ds.effectColor = new Color(0f, 0f, 0f, 0.28f); ds.effectDistance = new Vector2(0f, -7f);
            return body;
        }

        private static Button Clickable(RectTransform rt, Image body, Action onClick)
        {
            var btn = rt.gameObject.AddComponent<Button>();
            btn.targetGraphic = body;   // basılınca gövde koyulaşır; tıklamayı görünmez "hit" alır
            var cols = btn.colors; cols.pressedColor = new Color(0.85f, 0.85f, 0.85f); cols.disabledColor = new Color(0.7f, 0.7f, 0.7f, 0.6f); btn.colors = cols;
            btn.onClick.AddListener(() => Audio.Sfx.Play(Audio.SfxKind.Tap));
            if (onClick != null) btn.onClick.AddListener(() => onClick());
            rt.gameObject.AddComponent<PressBounce>();
            return btn;
        }

        /// <summary>Kalın beyaz kenarlı, gölgeli yazı (sahne üstünde okunur).</summary>
        public static Text Caption(Transform parent, string text, int size, Vector2 anchor, Vector2 box, Vector2 offset = default) =>
            Caption(parent, text, size, anchor, box, offset, new Color(0.2f, 0.15f, 0.11f, 0.95f));

        /// <summary>Kalın beyaz yazı, verilen renkte kontur (panelin koyu tonu: yazı panelle bütünleşir).</summary>
        public static Text Caption(Transform parent, string text, int size, Vector2 anchor, Vector2 box, Vector2 offset, Color outline)
        {
            var t = Ui.Label(parent, text, size, Color.white, anchor, box, FontStyle.Bold, TextAnchor.MiddleCenter, offset);
            var o = t.gameObject.AddComponent<Outline>(); o.effectColor = outline; o.effectDistance = new Vector2(3f, -3f);
            var s = t.gameObject.AddComponent<Shadow>(); s.effectColor = new Color(0f, 0f, 0f, 0.35f); s.effectDistance = new Vector2(0f, -5f);
            t.raycastTarget = false;
            return t;
        }

        /// <summary>Yuvarlak simgeli şeker düğme; altında isteğe bağlı etiket.</summary>
        public static Button Round(Transform parent, Color c, string icon, float size, Vector2 anchor, Vector2 offset, Action onClick, string label = null)
        {
            var rt = Ui.Rect(parent, "Candy " + (label ?? icon), anchor, new Vector2(size, size), offset);
            var body = RoundShell(rt, c);
            var ic = Ui.IconImage(rt, icon, new Vector2(0.5f, 0.52f), size * (Skin.RoundButton != null ? 0.62f : 0.66f));
            if (ic != null) ic.gameObject.AddComponent<Shadow>().effectColor = new Color(0f, 0f, 0f, 0.25f);
            if (label != null) Caption(rt, label, Mathf.RoundToInt(size * 0.3f), new Vector2(0.5f, 0f), new Vector2(size * 2.4f, size * 0.42f), new Vector2(0f, -size * 0.2f));
            return Clickable(rt, body, onClick);
        }

        /// <summary>Yazılı şeker düğme (hap biçimi), isteğe bağlı solda simge.</summary>
        public static Button Pill(Transform parent, Color c, string text, Vector2 anchor, Vector2 size, Vector2 offset, Action onClick, string icon = null, int fontSize = 0)
        {
            var rt = Ui.Rect(parent, "Candy " + text, anchor, size, offset);
            var body = Shell(rt, c);
            var fs = fontSize > 0 ? fontSize : Mathf.RoundToInt(size.y * 0.5f);
            var tx = icon != null ? size.y * 0.35f : 0f;
            if (icon != null) Ui.IconImage(rt, icon, new Vector2(0f, 0.5f), size.y * 0.8f, new Vector2(size.y * 0.55f, 0f));
            var t = Caption(rt, text, fs, new Vector2(0.5f, 0.5f), size, new Vector2(tx, 2f));
            t.name = "Label";
            return Clickable(rt, body, onClick);
        }

        /// <summary>Gösterge halkası: beyaz disk, renkli dolgu halkası, ortada simge. Dolgu Image'ı döner (fillAmount 0..1).</summary>
        public static Image Gauge(Transform parent, Color c, string icon, float size, Vector2 anchor, Vector2 offset)
        {
            var rt = Ui.Rect(parent, "Gauge " + icon, anchor, new Vector2(size, size), offset);
            var back = rt.gameObject.AddComponent<Image>();
            back.sprite = Ring; back.color = new Color(1f, 1f, 1f, 0.45f); back.raycastTarget = false;
            var sh = rt.gameObject.AddComponent<Shadow>(); sh.effectColor = new Color(0f, 0f, 0f, 0.25f); sh.effectDistance = new Vector2(0f, -6f);
            var fill = Img(rt, "Fill", Ring, c, false);
            fill.type = Image.Type.Filled; fill.fillMethod = Image.FillMethod.Radial360; fill.fillOrigin = (int)Image.Origin360.Top; fill.fillClockwise = true;
            var disc = Ui.Rect(rt, "Disc", new Vector2(0.5f, 0.5f), new Vector2(size * 0.74f, size * 0.74f));
            var di = disc.gameObject.AddComponent<Image>(); di.raycastTarget = false;
            if (Skin.RoundButton != null) { di.sprite = Skin.RoundButton; di.preserveAspect = true; di.color = Color.white; }
            else { di.sprite = Body; di.type = Image.Type.Sliced; di.color = White; }
            Ui.IconImage(rt, icon, new Vector2(0.5f, 0.5f), size * 0.58f);
            return fill;
        }

        /// <summary>Yarı saydam rozet (ör. coin, pet adı): solda simge, sağda yazı. Yazıyı döndürür.</summary>
        public static Text Badge(Transform parent, string icon, string text, Vector2 anchor, Vector2 pivot, Vector2 offset, float height = 84f, float width = 260f)
        {
            var rt = Ui.Rect(parent, "Badge " + icon, anchor, new Vector2(width, height), offset);
            rt.pivot = pivot;
            var bg = rt.gameObject.AddComponent<Image>(); bg.raycastTarget = false;
            if (Skin.Track != null) { Skin.Apply(bg, Skin.Track, height); bg.color = new Color(1f, 1f, 1f, 0.94f); }
            else
            {
                bg.sprite = Body; bg.type = Image.Type.Sliced; bg.color = new Color(1f, 1f, 1f, 0.38f);
                var o = rt.gameObject.AddComponent<Outline>(); o.effectColor = new Color(1f, 1f, 1f, 0.8f); o.effectDistance = new Vector2(3f, -3f);
            }
            Ui.IconImage(rt, icon, new Vector2(0f, 0.5f), height * 0.86f, new Vector2(height * 0.5f, 0f));
            var t = Caption(rt, text, Mathf.RoundToInt(height * 0.5f), new Vector2(0.5f, 0.5f), new Vector2(width - height * 0.9f, height), new Vector2(height * 0.4f, 0f));
            return t;
        }

        public static readonly Color Gold = new Color(1f, 0.74f, 0.16f), Night = new Color(0.1f, 0.2f, 0.42f, 0.88f);

        /// <summary>
        /// Oyun HUD'u sol üst "pet kartı" (kullanıcı isteği 15 Ekim 2026: heyecan verici, 3B): altın halkalı portre madalyonu,
        /// mavi şeker isim plakası, madalyonun köşesinde 3B yıldız + seviye sayısı, plakanın altında parlak XP kapsülü.
        /// Döndürür: kök (dokunma hedefi). name/level/xp güncellenecek öğeler.
        /// </summary>
        public static RectTransform PetPlate(Transform parent, string petId, Color petColor, Vector2 offset, out Text name, out Text level, out Image xp)
        {
            var root = Ui.Rect(parent, "PetPlate", new Vector2(0f, 1f), new Vector2(560f, 170f), offset);
            root.pivot = new Vector2(0f, 1f);
            // isim plakası (madalyonun arkasından çıkar)
            var plate = Ui.Rect(root, "Plate", new Vector2(0f, 1f), new Vector2(400f, 82f), new Vector2(330f, -44f));
            Shell(plate, Blue).raycastTarget = false; plate.GetComponent<Image>().raycastTarget = false;
            name = Caption(plate, "", 40, new Vector2(0.5f, 0.5f), new Vector2(330f, 80f), new Vector2(26f, 2f), Deep(Blue));
            // XP kapsülü: koyu iz + altın dolgu + parlama
            // Dolgu izin içinde kenar boşluklu gerilir; Ui.SetBar sağ ucu (anchorMax.x) oynatır. Önceden dolgu sabit boyutlu
            // ve ortadan bağlıydı: SetBar'ın çapası onu sağa doğru uzatıyordu (kullanıcı: "XP uzamış görünüyor", 19 Ekim 2026).
            var track = Ui.Rect(root, "Xp", new Vector2(0f, 1f), new Vector2(300f, 36f), new Vector2(330f - 30f, -118f));
            var ti = track.gameObject.AddComponent<Image>(); ti.raycastTarget = false;
            var v3 = Skin.Track != null && Skin.FillOrange != null;
            if (v3) { Skin.Apply(ti, Skin.Track, 36f); ti.color = Color.white; }
            else { ti.sprite = Body; ti.type = Image.Type.Sliced; ti.color = Night; track.gameObject.AddComponent<Outline>().effectColor = new Color(1f, 1f, 1f, 0.8f); }
            var fillRt = Ui.Rect(track, "Fill", Vector2.zero, Vector2.zero);
            fillRt.anchorMin = Vector2.zero; fillRt.anchorMax = Vector2.one; fillRt.pivot = new Vector2(0f, 0.5f);
            fillRt.offsetMin = new Vector2(4f, 4f); fillRt.offsetMax = new Vector2(-4f, -4f);
            xp = fillRt.gameObject.AddComponent<Image>(); xp.raycastTarget = false;
            if (v3) { Skin.Apply(xp, Skin.FillOrange, 28f); xp.color = Color.white; }
            else
            {
                xp.sprite = Body; xp.type = Image.Type.Sliced; xp.color = Gold;
                Img(fillRt, "Gloss", Gloss, new Color(1f, 1f, 1f, 0.9f), true);
            }
            Caption(track, "XP", 24, new Vector2(1f, 0.5f), new Vector2(60f, 36f), new Vector2(-34f, 1f), Deep(Gold));
            // madalyon: altın halka + pet portresi
            var med = Ui.Rect(root, "Medal", new Vector2(0f, 1f), new Vector2(164f, 164f), new Vector2(82f, -82f));
            RoundShell(med, Gold).raycastTarget = false; med.GetComponent<Image>().raycastTarget = false;
            var inner = Ui.Rect(med, "In", new Vector2(0.5f, 0.5f), new Vector2(128f, 128f));
            var ii = inner.gameObject.AddComponent<Image>(); ii.sprite = Body; ii.type = Image.Type.Sliced; ii.color = Color.Lerp(petColor, Color.white, 0.55f); ii.raycastTarget = false;
            var pic = Ui.Portrait(petId);
            if (pic != null)
            {
                inner.gameObject.AddComponent<Mask>().showMaskGraphic = true;
                var p = Ui.Rect(inner, "Pic", new Vector2(0.5f, 0.5f), new Vector2(150f, 150f), new Vector2(0f, 8f));
                var pi = p.gameObject.AddComponent<Image>(); pi.sprite = pic; pi.preserveAspect = true; pi.raycastTarget = false;
            }
            // seviye yıldızı (madalyonun sağ altı)
            var star = Ui.IconImage(root, "ui_star", new Vector2(0f, 1f), 92f, new Vector2(150f, -134f));
            if (star != null) star.gameObject.AddComponent<Shadow>().effectDistance = new Vector2(0f, -5f);
            level = Caption(root, "", 38, new Vector2(0f, 1f), new Vector2(92f, 92f), new Vector2(150f, -132f), new Color(0.45f, 0.24f, 0f, 1f));
            return root;
        }

        /// <summary>Sağ üst coin göstergesi: koyu cam kapsül, soldan taşan iri 3B coin, kalın beyaz sayı.</summary>
        public static Text CoinPlate(Transform parent, Vector2 offset, float width = 280f) => ResourcePlate(parent, "ui_coin", offset, width);

        /// <summary>Sağ üst kaynak göstergesi (coin, Güneş Taşı): koyu kapsül, soldan taşan iri simge, kalın beyaz sayı.</summary>
        public static Text ResourcePlate(Transform parent, string icon, Vector2 offset, float width = 280f)
        {
            var root = Ui.Rect(parent, "Plate " + icon, new Vector2(1f, 1f), new Vector2(width, 92f), offset);
            root.pivot = new Vector2(1f, 1f);
            var bg = root.gameObject.AddComponent<Image>(); bg.raycastTarget = false;
            if (Skin.Track != null) { Skin.Apply(bg, Skin.Track, 92f); bg.color = Color.white; root.gameObject.AddComponent<Shadow>().effectDistance = new Vector2(0f, -6f); }
            else
            {
                bg.sprite = Body; bg.type = Image.Type.Sliced; bg.color = Night;
                var o = root.gameObject.AddComponent<Outline>(); o.effectColor = new Color(1f, 0.85f, 0.4f, 0.95f); o.effectDistance = new Vector2(3f, -3f);
                root.gameObject.AddComponent<Shadow>().effectDistance = new Vector2(0f, -6f);
                Img(root, "Gloss", Gloss, new Color(1f, 1f, 1f, 0.35f), true);
            }
            var coin = Ui.IconImage(root, icon, new Vector2(0f, 0.5f), 118f, new Vector2(8f, 0f));
            if (coin != null) coin.gameObject.AddComponent<Shadow>().effectDistance = new Vector2(0f, -5f);
            return Caption(root, "", 50, new Vector2(0.5f, 0.5f), new Vector2(width - 90f, 92f), new Vector2(34f, 2f), new Color(0.05f, 0.1f, 0.25f, 1f));
        }

        /// <summary>Koyu ton (yazı konturu, kuyruk): panel renginin %45'i.</summary>
        public static Color Deep(Color c) => new Color(c.r * 0.45f, c.g * 0.45f, c.b * 0.45f, 1f);

        /// <summary>
        /// Yazı paneli (tanıtım altyazısı, pet konuşması): şeker gövde, solda isteğe bağlı simge rozeti (beyaz disk),
        /// isteğe bağlı alt kuyruk; genişlik yazıya göre ayarlanır (en çok <paramref name="maxWidth"/>, sonra iki satır).
        /// </summary>
        public static CandyBanner Banner(Transform parent, Color c, string icon, Vector2 anchor, Vector2 offset, float maxWidth, int fontSize, bool tail)
        {
            var rt = Ui.Rect(parent, "Banner", anchor, new Vector2(400f, fontSize * 2.4f), offset);
            if (tail)
            {
                // kuyruk: gövdenin arkasında, alt ortada 45° dönük küçük kare (koyu dudak tonu + gövde rengi)
                var tl = Ui.Rect(rt, "Tail", new Vector2(0.5f, 0f), new Vector2(46f, 46f), new Vector2(0f, -4f));
                tl.localRotation = Quaternion.Euler(0f, 0f, 45f);
                var ti = tl.gameObject.AddComponent<Image>(); ti.sprite = Ui.Rounded; ti.type = Image.Type.Sliced; ti.color = c; ti.raycastTarget = false;
                var to = tl.gameObject.AddComponent<Shadow>(); to.effectColor = new Color(c.r * 0.6f, c.g * 0.6f, c.b * 0.6f, 1f); to.effectDistance = new Vector2(0f, -9f);
            }
            var shell = Ui.Fill(rt, "Shell");
            Shell(shell, c).raycastTarget = false;
            shell.GetComponent<Image>().raycastTarget = false;
            var b = rt.gameObject.AddComponent<CandyBanner>();
            b.Init(rt, c, icon, maxWidth, fontSize);
            return b;
        }

        /// <summary>Küçük etiket (ada yer adları): yarı saydam koyu gövde, beyaz kenar, beyaz konturlu yazı. Genişlik yazıya göre.</summary>
        public static Text Tag(Transform parent, string text, Color c, int fontSize, float height)
        {
            var rt = (RectTransform)parent;
            var bg = rt.gameObject.AddComponent<Image>();
            bg.sprite = Body; bg.type = Image.Type.Sliced; bg.color = c; bg.raycastTarget = false;
            var o = rt.gameObject.AddComponent<Outline>(); o.effectColor = new Color(1f, 1f, 1f, 0.9f); o.effectDistance = new Vector2(3f, -3f);
            var sh = rt.gameObject.AddComponent<Shadow>(); sh.effectColor = new Color(0f, 0f, 0f, 0.25f); sh.effectDistance = new Vector2(0f, -5f);
            var t = Caption(rt, text, fontSize, new Vector2(0.5f, 0.5f), new Vector2(1000f, height), new Vector2(0f, 1f), Deep(c));
            t.horizontalOverflow = HorizontalWrapMode.Overflow;
            rt.sizeDelta = new Vector2(t.preferredWidth + height * 0.9f, height);
            return t;
        }

        /// <summary>
        /// Mavi kurdele başlık (E dili, 22 Ekim 2026 onayı): v3 kurdelesi, uçlar sabit, orta bant yazı kadar uzar; yazı beyaz, koyu mavi kontur.
        /// Kurdele yoksa mavi etiket. Genişlik yazıya göre; yazıyı döndürür.
        /// </summary>
        public static Text Ribbon(Transform parent, string text, Vector2 anchor, Vector2 offset, float height = 120f, int fontSize = 46)
        {
            var rt = Ui.Rect(parent, "Ribbon", anchor, new Vector2(400f, height), offset);
            var band = Skin.RibbonBand;
            if (band == null) return Tag(rt, text, new Color(0.13f, 0.47f, 0.85f, 1f), fontSize, height * 0.6f);
            var img = rt.gameObject.AddComponent<Image>();
            img.sprite = band; img.type = Image.Type.Sliced; img.raycastTarget = false;
            img.pixelsPerUnitMultiplier = band.rect.height / Mathf.Max(1f, height);
            var t = Caption(rt, text, fontSize, new Vector2(0.5f, 0.6f), new Vector2(1200f, height * 0.6f), Vector2.zero, new Color(0.06f, 0.22f, 0.47f, 1f));
            t.horizontalOverflow = HorizontalWrapMode.Overflow;
            var ends = band.border.x / Mathf.Max(1f, img.pixelsPerUnitMultiplier);   // bir ucun ekrandaki genişliği
            rt.sizeDelta = new Vector2(Mathf.Max(t.preferredWidth + ends * 2f + 20f, ends * 2f + 60f), height);
            return t;
        }

        /// <summary>
        /// "Kapalı" işareti (ses/müzik kapalı; 24 Ekim 2026, kullanıcı: global oyunlardaki gibi): simgenin üstünden sol üstten
        /// sağ alta geçen kalın kırmızı çizgi, beyaz kenarlı ve hafif gölgeli (her zeminde okunur). Görünürlüğü çağıran ayarlar.
        /// </summary>
        public static GameObject OffSlash(Transform button, float length)
        {
            var t = Mathf.Max(8f, length * 0.14f);   // kırmızı çizgi kalınlığı
            var root = Ui.Rect(button, "Off", new Vector2(0.5f, 0.52f), new Vector2(length + 10f, t + 10f));
            root.localRotation = Quaternion.Euler(0f, 0f, -45f);
            var rim = root.gameObject.AddComponent<Image>();   // beyaz kenar
            rim.sprite = Ui.Rounded; rim.type = Image.Type.Sliced; rim.pixelsPerUnitMultiplier = 60f / ((t + 10f) * 0.5f);
            rim.color = Color.white; rim.raycastTarget = false;
            var sh = root.gameObject.AddComponent<Shadow>(); sh.effectColor = new Color(0.25f, 0.05f, 0.08f, 0.35f); sh.effectDistance = new Vector2(2f, -4f);
            var bar = Ui.Rect(root, "Red", new Vector2(0.5f, 0.5f), new Vector2(length, t));
            var red = bar.gameObject.AddComponent<Image>();
            red.sprite = Ui.Rounded; red.type = Image.Type.Sliced; red.pixelsPerUnitMultiplier = 60f / (t * 0.5f);
            red.color = new Color(0.9f, 0.16f, 0.22f); red.raycastTarget = false;
            var lip = bar.gameObject.AddComponent<Shadow>(); lip.effectColor = new Color(0.55f, 0.04f, 0.1f, 1f); lip.effectDistance = new Vector2(0f, -2f);
            return root.gameObject;
        }

        /// <summary>Kırmızı sayı rozeti (düğmenin sağ üstü).</summary>
        public static Text Count(Transform parent, float size = 46f)
        {
            var rt = Ui.Rect(parent, "Count", new Vector2(0.9f, 0.9f), new Vector2(size, size));
            var img = rt.gameObject.AddComponent<Image>(); img.sprite = Body; img.type = Image.Type.Sliced; img.color = new Color(1f, 0.23f, 0.36f); img.raycastTarget = false;
            var o = rt.gameObject.AddComponent<Outline>(); o.effectColor = Color.white; o.effectDistance = new Vector2(3f, -3f);
            var t = Ui.Label(rt, "", Mathf.RoundToInt(size * 0.6f), Color.white, new Vector2(0.5f, 0.5f), new Vector2(size, size), FontStyle.Bold);
            t.raycastTarget = false;
            return t;
        }
    }

    /// <summary>Candy.Banner yazı paneli: metni değiştirince boyutu yazıya göre yeniden ayarlar.</summary>
    public sealed class CandyBanner : MonoBehaviour
    {
        private RectTransform _rt, _iconRt;
        private Text _text;
        private float _maxWidth, _pad, _iconW;
        private int _font;

        public RectTransform Rect => _rt;

        internal void Init(RectTransform rt, Color c, string icon, float maxWidth, int font)
        {
            _rt = rt; _maxWidth = maxWidth; _font = font; _pad = font * 0.9f;
            var h = font * 2.4f;
            if (!string.IsNullOrEmpty(icon) && Ui.Icon(icon) != null)
            {
                // simge rozeti: beyaz disk, sol kenardan taşan
                _iconW = h * 0.95f;
                _iconRt = Ui.Rect(rt, "IconDisc", new Vector2(0f, 0.5f), new Vector2(_iconW * 1.08f, _iconW * 1.08f), new Vector2(_iconW * 0.3f, 2f));
                Candy.Shell(_iconRt, Candy.White).raycastTarget = false;
                _iconRt.GetComponent<Image>().raycastTarget = false;
                Ui.IconImage(_iconRt, icon, new Vector2(0.5f, 0.5f), _iconW * 0.78f);
            }
            _text = Candy.Caption(rt, "", font, new Vector2(0.5f, 0.5f), new Vector2(maxWidth, h), new Vector2(0f, 2f), Candy.Deep(c));
            _text.name = "Text";
            _text.lineSpacing = 0.95f;
        }

        public void SetText(string text)
        {
            _text.text = text;
            var h1 = _font * 2.4f;
            _text.horizontalOverflow = HorizontalWrapMode.Overflow;
            var pref = _text.preferredWidth;
            var inner = _maxWidth - _pad * 2f - _iconW * 0.75f;
            var lines = pref > inner ? 2 : 1;
            var w = Mathf.Min(_maxWidth, Mathf.Max(h1 * 2.2f, (lines == 1 ? pref : inner) + _pad * 2f + _iconW * 0.75f));
            var h = lines == 1 ? h1 : _font * 3.5f;
            _rt.sizeDelta = new Vector2(w, h);
            _text.horizontalOverflow = HorizontalWrapMode.Wrap;
            var tr = _text.rectTransform;
            tr.sizeDelta = new Vector2(w - _pad * 2f - _iconW * 0.75f, h - _font * 0.4f);
            tr.anchoredPosition = new Vector2(_iconW * 0.375f, 2f);
            if (_iconRt != null) _iconRt.anchoredPosition = new Vector2(_iconW * 0.3f, 2f);
        }
    }
}
