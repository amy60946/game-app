using System;
using System.Collections.Generic;
using System.Linq;

namespace Pofi.Logic.Audio
{
    [Serializable]
    public struct WordTiming { public int StartMs; public int EndMs; }

    [Serializable]
    public struct VisemeKey { public int AtMs; public string Shape; } // kapalı, A, E, O, U, MBP, FV

    /// <summary>Ses satırı verisi (VoiceLineSO karşılığı). Ses dosyası yoksa zamanlar tahmin edilir (sessiz mod).</summary>
    [Serializable]
    public sealed class VoiceLine
    {
        public string Id;
        public string Text;
        public string AudioClip;              // null: henüz ses yok
        public List<WordTiming> Words = new List<WordTiming>();
        public List<VisemeKey> Visemes = new List<VisemeKey>();

        public string[] Tokens => Text.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);
    }

    /// <summary>
    /// Karaoke vurgusu (FR-VOICE-1) ve ağız şekli (FR-VOICE-4). Ses varken zamanlamaları kullanır;
    /// yoksa okuma hızına göre kelime süresi tahmin eder (yaş bandı A daha yavaş).
    /// </summary>
    public static class SubtitleSync
    {
        public static List<WordTiming> EstimateTimings(string text, float charsPerSecond)
        {
            var list = new List<WordTiming>();
            var t = 0;
            foreach (var w in text.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries))
            {
                var dur = (int)Math.Max(220, (w.Length + 1) / charsPerSecond * 1000);
                list.Add(new WordTiming { StartMs = t, EndMs = t + dur });
                t += dur;
            }
            return list;
        }

        public static List<WordTiming> TimingsFor(VoiceLine line, float charsPerSecond) =>
            line.Words != null && line.Words.Count == line.Tokens.Length ? line.Words : EstimateTimings(line.Text, charsPerSecond);

        /// <summary>Şu an vurgulanacak kelimenin sırası; başlamadıysa −1, bittiyse son kelime.</summary>
        public static int ActiveWord(IReadOnlyList<WordTiming> words, int timeMs)
        {
            if (words.Count == 0 || timeMs < words[0].StartMs) return -1;
            for (var i = 0; i < words.Count; i++) if (timeMs < words[i].EndMs) return i;
            return words.Count - 1;
        }

        public static int DurationMs(IReadOnlyList<WordTiming> words) => words.Count == 0 ? 0 : words[words.Count - 1].EndMs;

        /// <summary>Ağız şekli: anahtarlar arasında son geçerli şekil; satır bitince "kapalı".</summary>
        public static string VisemeAt(IReadOnlyList<VisemeKey> keys, int timeMs, int durationMs)
        {
            if (keys.Count == 0 || timeMs >= durationMs) return "kapalı";
            var current = "kapalı";
            foreach (var k in keys) { if (k.AtMs > timeMs) break; current = k.Shape; }
            return current;
        }

        /// <summary>
        /// Ses yokken kaba viseme tahmini: her kelimenin ilk ünlüsünden şekil (a/ı→A, e/i→E, o/ö→O, u/ü→U, m/b/p→MBP).
        /// Stüdyo kaydı gelince araçla üretilen gerçek zamanlamalar bunun yerini alır.
        /// </summary>
        public static List<VisemeKey> EstimateVisemes(string text, IReadOnlyList<WordTiming> words)
        {
            var tokens = text.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);
            var keys = new List<VisemeKey>();
            for (var i = 0; i < Math.Min(tokens.Length, words.Count); i++)
            {
                var w = tokens[i].ToLowerInvariant();
                var first = w.FirstOrDefault(c => "aeıioöuümbpfv".IndexOf(c) >= 0);
                string shape;
                switch (first)
                {
                    case 'a': case 'ı': shape = "A"; break;
                    case 'e': case 'i': shape = "E"; break;
                    case 'o': case 'ö': shape = "O"; break;
                    case 'u': case 'ü': shape = "U"; break;
                    case 'm': case 'b': case 'p': shape = "MBP"; break;
                    case 'f': case 'v': shape = "FV"; break;
                    default: shape = "E"; break;
                }
                keys.Add(new VisemeKey { AtMs = words[i].StartMs, Shape = shape });
                keys.Add(new VisemeKey { AtMs = words[i].EndMs - 60, Shape = "kapalı" });
            }
            return keys;
        }
    }
}
