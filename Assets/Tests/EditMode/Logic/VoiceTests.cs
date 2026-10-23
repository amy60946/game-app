using System;
using System.IO;
using System.Linq;
using NUnit.Framework;
using Pofi.Logic.Audio;

namespace Pofi.Tests
{
    /// <summary>Sesli okuma: anahtar ve ses biçimi art/voice/build_voice.py ile birebir aynı olmalı (değerler oradan).</summary>
    public class VoiceTests
    {
        [Test]
        public void KeyMatchesBuildScript()
        {
            Assert.AreEqual("54f798c96e2782e3", VoiceKey.Of("Merhaba Okti! Dükkânım hep açık."));
            Assert.AreEqual("3becc9ffe7491d34", VoiceKey.Of("Işık Adası ğüşiöç"));
        }

        [Test]
        public void KeyIgnoresTagsAndSpacing()
        {
            Assert.AreEqual("0b17bb4ebbf178c5", VoiceKey.Of("Merhaba Okti!"));
            Assert.AreEqual(VoiceKey.Of("Merhaba Okti!"), VoiceKey.Of("  <b>Merhaba</b>   Okti!\n"));
            Assert.AreNotEqual(VoiceKey.Of("Merhaba Okti!"), VoiceKey.Of("Merhaba Pofi!"));   // pet adı değişince kayıt çalmaz
        }

        [Test]
        public void DecodesBuildScriptOutput()
        {
            // build_voice.adpcm(…) çıktısı ve Python çözücüsünün ilk 64 örneği
            var data = Convert.FromBase64String("SU1BMSJWAABAAAAAcHd3d0eJiQggMjQjArjcvLyqiRAiE5DNvsyrq4kgQiM=");
            int[] expected =
            {
                0, 11, 41, 104, 240, 533, 1164, 2521, 5431, 9173, 7664, 7207, 5961, 5583, 5240, 5552, 5836, 7127, 8300, 9792, 11538,
                13180, 14672, 15642, 16523, 16683, 16538, 15611, 14528, 12926, 11006, 9199, 7087, 5099, 3808, 2635, 1996, 1802, 1978,
                2458, 3186, 3848, 4689, 5017, 5116, 4845, 3941, 2858, 964, -843, -2955, -5511, -7915, -9476, -11464, -12755, -13458,
                -13671, -13477, -12596, -11795, -10484, -9251, -8450,
            };
            var pcm = ImaAdpcm.Decode(data, out var rate);
            Assert.AreEqual(22050, rate);
            Assert.AreEqual(expected.Length, pcm.Length);
            for (var i = 0; i < expected.Length; i++) Assert.AreEqual(expected[i], (int)Math.Round(pcm[i] * 32768f), "örnek " + i);
        }

        [Test]
        public void EncoderMatchesBuildScript()
        {
            var sig = Enumerable.Range(0, 64).Select(i => (short)(int)(12000 * Math.Sin(i * 0.07) + 5000 * Math.Sin(i * 0.31))).ToArray();
            Assert.AreEqual("SU1BMSJWAABAAAAAcHd3d0eJiQggMjQjArjcvLyqiRAiE5DNvsyrq4kgQiM=", Convert.ToBase64String(ImaAdpcm.Encode(sig, 22050)));
        }

        [Test]
        public void SpeechLikeSignalSurvivesRoundTrip()
        {
            // 1 sn, yumuşak başlayan konuşma benzeri karışım: sinyal/gürültü 25 dB'den iyi
            var n = 22050;
            var sig = new short[n];
            for (var i = 0; i < n; i++)
            {
                var t = i / 22050.0;
                var env = Math.Min(1.0, t / 0.05);
                sig[i] = (short)(env * (9000 * Math.Sin(2 * Math.PI * 180 * t) + 4000 * Math.Sin(2 * Math.PI * 720 * t) + 1500 * Math.Sin(2 * Math.PI * 2400 * t)));
            }
            var back = ImaAdpcm.Decode(ImaAdpcm.Encode(sig, 22050), out _);
            double s = 0, e = 0;
            for (var i = 0; i < n; i++) { s += (double)sig[i] * sig[i]; var d = sig[i] - back[i] * 32768.0; e += d * d; }
            Assert.Greater(10 * Math.Log10(s / e), 25.0);
        }

        [Test]
        public void RejectsBrokenData()
        {
            Assert.IsNull(ImaAdpcm.Decode(null, out _));
            Assert.IsNull(ImaAdpcm.Decode(new byte[] { 1, 2, 3 }, out _));
            Assert.IsNull(ImaAdpcm.Decode(new byte[] { (byte)'I', (byte)'M', (byte)'A', (byte)'1', 0x22, 0x56, 0, 0, 100, 0, 0, 0 }, out _));   // gövde eksik
        }

        [Test]
        public void IndexedVoiceFilesExistAndDecode()
        {
            // Resources/Voice/index.txt'teki her anahtarın dosyası var ve çözülüyor (kayıtlar üretildiyse)
            var dir = Path.Combine(TestContext.CurrentContext.TestDirectory, "..", "..", "..", "..", "Assets", "_Pofi", "Resources", "Voice");
            var index = Path.Combine(dir, "index.txt");
            if (!File.Exists(index)) Assert.Ignore("ses kayıtları henüz üretilmedi");
            var keys = File.ReadAllLines(index).Where(l => l.Length > 0).Select(l => l.Split('\t')).ToList();
            Assert.Greater(keys.Count, 0);
            foreach (var k in keys)
            {
                Assert.AreEqual(VoiceKey.Of(k[2]), k[0], "anahtar metinle eşleşmeli: " + k[2]);
                var pcm = ImaAdpcm.Decode(File.ReadAllBytes(Path.Combine(dir, "v_" + k[0] + ".bytes")), out var rate);
                Assert.IsNotNull(pcm, k[2]);
                Assert.AreEqual(22050, rate);
                Assert.Greater(pcm.Length, rate / 4, k[2]);
            }
        }
    }
}
