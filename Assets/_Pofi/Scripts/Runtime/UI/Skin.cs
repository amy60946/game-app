using System.Collections.Generic;
using UnityEngine;

namespace Pofi.UI
{
    /// <summary>
    /// v3 arayüz parçaları (19 Ekim 2026, kullanıcı onaylı): Meshy ile üretilmiş çubuk, düğme, kart, yuvarlak düğme, şerit, tahta.
    /// Kaynak: Resources/UI (art/meshy/install_ui_v3.py). Parçalar 9 dilimli kullanılır; dosya yoksa null döner ve
    /// <see cref="Candy"/> eski, kodla çizilen görünüme döner.
    /// </summary>
    public static class Skin
    {
        private static readonly Dictionary<string, Sprite> Cache = new Dictionary<string, Sprite>();

        /// <summary>Kapsül (çubuk, düğme): sol/sağ uç yüksekliğin yarısı, üst/alt biraz az.</summary>
        public static Sprite Capsule(string name) => Load(name, (w, h) => new Vector4(h * 0.48f, h * 0.42f, h * 0.48f, h * 0.42f));

        /// <summary>Kart/panel: köşeler kısa kenarın beşte biri.</summary>
        public static Sprite Panel(string name) => Load(name, (w, h) => { var b = Mathf.Min(w, h) * 0.2f; return new Vector4(b, b, b, b); });

        /// <summary>Dilimsiz (yuvarlak düğme, şerit, yıldız, kapat).</summary>
        public static Sprite Plain(string name) => Load(name, null);

        public static Sprite Track => Capsule("track_dark");
        public static Sprite FillOrange => Capsule("fill_orange");
        public static Sprite FillBlue => Capsule("fill_blue");
        public static Sprite Card => Panel("card");
        public static Sprite RoundButton => Plain("round");
        public static Sprite Ribbon => Plain("ribbon");
        /// <summary>Başlık kurdelesi: kıvrık uçlar (genişliğin %27'si) korunur, orta bant yazıya göre uzar.</summary>
        public static Sprite RibbonBand => Load("ribbon", (w, h) => new Vector4(w * 0.27f, 0f, w * 0.27f, 0f), "ribbon#band");
        public static Sprite Plank => Capsule("plank");

        /// <summary>Renge en yakın düğme: yeşil, mavi, turuncu (altın dahil), pembe; açık renkler (beyaz, krem) kart.</summary>
        public static Sprite ButtonFor(Color c, out bool isCard)
        {
            isCard = false;
            Color.RGBToHSV(c, out var h, out var s, out var v);
            if (s < 0.25f && v > 0.8f) { isCard = true; return Card; }
            if (h > 0.2f && h < 0.45f) return Capsule("btn_green");
            if (h >= 0.45f && h < 0.75f) return Capsule("btn_blue");
            if (h >= 0.75f || h < 0.02f) return Capsule("btn_pink");
            return Capsule("btn_orange");
        }

        /// <summary>
        /// 9 dilimli parçayı öğenin yüksekliğine ölçekler: dokunun yüksekliği öğe yüksekliğine denk gelir, uçlar ezilmez
        /// (dokular 150–500 px; öğeler 30–140 birim).
        /// </summary>
        public static void Apply(UnityEngine.UI.Image img, Sprite s, float height)
        {
            img.sprite = s;
            img.type = s.border.sqrMagnitude > 0f ? UnityEngine.UI.Image.Type.Sliced : UnityEngine.UI.Image.Type.Simple;
            if (img.type == UnityEngine.UI.Image.Type.Sliced) img.pixelsPerUnitMultiplier = s.rect.height / Mathf.Max(1f, height);
            else img.preserveAspect = true;
        }

        private static Sprite Load(string name, System.Func<float, float, Vector4> border, string key = null)
        {
            key ??= name;
            if (Cache.TryGetValue(key, out var s)) return s;
            var tex = Resources.Load<Texture2D>("UI/" + name);
            if (tex != null)
            {
                tex.wrapMode = TextureWrapMode.Clamp;
                var b = border != null ? border(tex.width, tex.height) : Vector4.zero;
                s = Sprite.Create(tex, new Rect(0, 0, tex.width, tex.height), new Vector2(0.5f, 0.5f), 100f, 0, SpriteMeshType.FullRect, b);
            }
            Cache[key] = s;
            return s;
        }
    }
}
