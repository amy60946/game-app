using Pofi.Logic.Profile;
using UnityEngine;

namespace Pofi.UI
{
    /// <summary>
    /// Yaş grubuna göre görünüm: K (5 ve altı) ve A (6–8) iri, yuvarlak, sıcak renkli; B (9–12) dengeli; C (13 ve üstü) sade ve kompakt.
    /// Sayılar <see cref="AgeBandProfile"/>'dan, renkler buradan gelir.
    /// </summary>
    public sealed class Theme
    {
        public AgeBand Band;
        public float Scale = 1f;          // yazı ve düğme ölçeği
        public float Radius = 40f;        // köşe yuvarlaklığı (referans çözünürlükte piksel)
        public Color Primary, PrimaryText, Secondary, SecondaryText, Panel, Text, SubtleText, Sky, Danger;

        /// <summary>Oyuncu ayarı "Yazı boyutu" (1 = normal). Yalnızca yazıya uygulanır.</summary>
        public float TextScale = 1f;

        /// <summary>Oyuncu ayarı "Hareketi azalt": zıplama, nefes ve parçacık efektleri kısılır.</summary>
        public static bool ReduceMotion;

        public int Font(int size) => Mathf.RoundToInt(size * Scale * TextScale);

        public static Theme Default => For(AgeBand.B);

        public static Theme For(AgeBand band)
        {
            var p = AgeBandProfile.For(band);
            var t = new Theme { Band = band, Scale = p.ButtonScale, Panel = new Color(1f, 1f, 1f, 0.94f), Danger = Hex("#E8453C") };
            switch (band)
            {
                case AgeBand.K:
                case AgeBand.A:
                    t.Radius = 56f;
                    t.Primary = Hex("#FF8A2A"); t.PrimaryText = Color.white;
                    t.Secondary = Hex("#FFE3B8"); t.SecondaryText = Hex("#7A3B00");
                    t.Text = Hex("#5A2E0C"); t.SubtleText = Hex("#9A6A44");
                    t.Sky = Hex("#6FD3FF");
                    break;
                case AgeBand.C:
                    t.Radius = 22f;
                    t.Primary = Hex("#5B5BD6"); t.PrimaryText = Color.white;
                    t.Secondary = Hex("#E6E6FA"); t.SecondaryText = Hex("#2C2C6E");
                    t.Text = Hex("#1F2238"); t.SubtleText = Hex("#5D6380");
                    t.Sky = Hex("#7AB8F5");
                    break;
                default:
                    t.Radius = 38f;
                    t.Primary = Hex("#2F80ED"); t.PrimaryText = Color.white;
                    t.Secondary = Hex("#DCEBFF"); t.SecondaryText = Hex("#103A73");
                    t.Text = Hex("#14304F"); t.SubtleText = Hex("#4F6B8A");
                    t.Sky = Hex("#5CC7FA");
                    break;
            }
            return t;
        }

        public static Color Hex(string hex) => ColorUtility.TryParseHtmlString(hex, out var c) ? c : Color.magenta;
    }
}
