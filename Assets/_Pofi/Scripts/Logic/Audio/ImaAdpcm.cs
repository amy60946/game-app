using System;

namespace Pofi.Logic.Audio
{
    /// <summary>
    /// Sesli okuma kayıtlarının biçimi (Resources/Voice/v_*.bytes): "IMA1" + örnek hızı + örnek sayısı (int32, küçük uçlu) +
    /// 4 bitlik IMA ADPCM kodları (her baytta önce alt yarım). Ham PCM'in dörtte biri; çözmek için tarayıcının ses çözücüsü
    /// gerekmez (WebGL'de sıkıştırılmış ses iPhone'da çalmıyordu, müzik de ham PCM). Kodlayıcı art/voice/build_voice.py ile aynı.
    /// </summary>
    public static class ImaAdpcm
    {
        private static readonly int[] Step =
        {
            7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66, 73, 80, 88, 97, 107, 118,
            130, 143, 157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449, 494, 544, 598, 658, 724, 796, 876, 963, 1060,
            1166, 1282, 1411, 1552, 1707, 1878, 2066, 2272, 2499, 2749, 3024, 3327, 3660, 4026, 4428, 4871, 5358, 5894, 6484,
            7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899, 15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767,
        };
        private static readonly int[] IndexStep = { -1, -1, -1, -1, 2, 4, 6, 8, -1, -1, -1, -1, 2, 4, 6, 8 };
        private const int Header = 12;

        /// <summary>Başlık geçerli mi; örnek hızı ve sayısı.</summary>
        public static bool TryHeader(byte[] data, out int rate, out int count)
        {
            rate = count = 0;
            if (data == null || data.Length < Header || data[0] != 'I' || data[1] != 'M' || data[2] != 'A' || data[3] != '1') return false;
            rate = BitConverter.ToInt32(data, 4);
            count = BitConverter.ToInt32(data, 8);
            return rate > 0 && count >= 0 && data.Length >= Header + (count + 1) / 2;
        }

        /// <summary>−1…1 aralığında örnekler; başlık bozuksa null.</summary>
        public static float[] Decode(byte[] data, out int rate)
        {
            if (!TryHeader(data, out rate, out var count)) return null;
            var output = new float[count];
            int pred = 0, idx = 0;
            for (var i = 0; i < count; i++)
            {
                var b = data[Header + (i >> 1)];
                var code = (i & 1) == 0 ? b & 15 : b >> 4;
                var step = Step[idx];
                var diff = step >> 3;
                if ((code & 4) != 0) diff += step;
                if ((code & 2) != 0) diff += step >> 1;
                if ((code & 1) != 0) diff += step >> 2;
                pred = (code & 8) != 0 ? pred - diff : pred + diff;
                if (pred > 32767) pred = 32767; else if (pred < -32768) pred = -32768;
                idx += IndexStep[code];
                if (idx < 0) idx = 0; else if (idx > 88) idx = 88;
                output[i] = pred / 32768f;
            }
            return output;
        }

        /// <summary>Kodlayıcı (testler ve araçlar için; oyun yalnız çözer).</summary>
        public static byte[] Encode(short[] samples, int rate)
        {
            var body = new byte[(samples.Length + 1) / 2];
            int pred = 0, idx = 0;
            for (var i = 0; i < samples.Length; i++)
            {
                var step = Step[idx];
                var diff = samples[i] - pred;
                var code = 0;
                if (diff < 0) { code = 8; diff = -diff; }
                var delta = step >> 3;
                if (diff >= step) { code |= 4; diff -= step; delta += step; }
                step >>= 1;
                if (diff >= step) { code |= 2; diff -= step; delta += step; }
                step >>= 1;
                if (diff >= step) { code |= 1; delta += step; }
                pred = (code & 8) != 0 ? pred - delta : pred + delta;
                if (pred > 32767) pred = 32767; else if (pred < -32768) pred = -32768;
                idx += IndexStep[code];
                if (idx < 0) idx = 0; else if (idx > 88) idx = 88;
                body[i >> 1] |= (byte)((i & 1) == 0 ? code : code << 4);
            }
            var data = new byte[Header + body.Length];
            data[0] = (byte)'I'; data[1] = (byte)'M'; data[2] = (byte)'A'; data[3] = (byte)'1';
            BitConverter.GetBytes(rate).CopyTo(data, 4);
            BitConverter.GetBytes(samples.Length).CopyTo(data, 8);
            body.CopyTo(data, Header);
            return data;
        }
    }
}
