using System;
using System.Collections.Generic;
using Newtonsoft.Json;

namespace Pofi.Logic.Island
{
    /// <summary>
    /// Pişmiş ada ızgarası (v6, 22 Ekim 2026; art/code3d/v6/bake_game.py → Resources/Data/island_v6.bytes).
    /// Onaylı taslağın yükseklik haritası 0,5 m adımla; yüzey katmanları 0..1 (kum, patika, kar, kaya, göl).
    /// Biçim: "PV6" + sürüm bayt, nx, nz (int32), x0, z0, step (float32), yükseklik int16 cm (nx·nz), katmanlar × uint8 (nx·nz). Küçük sonlu.
    /// Sürüm 1: 5 katman; sürüm 2 (22 Ekim 2026): + mavi çan çiçeği ve turuncu çiçek yoğunluğu (oyunda 3B çiçek öbekleri).
    /// </summary>
    public sealed class BakedField
    {
        public readonly int Nx, Nz;
        public readonly float X0, Z0, Step;
        private readonly float[] _h;
        private readonly byte[][] _layers;
        public const float SeaFloor = -7f;

        public enum Layer { Sand = 0, Path = 1, Snow = 2, Rock = 3, Lake = 4, Bluebell = 5, Orange = 6 }

        public float X1 => X0 + (Nx - 1) * Step;
        public float Z1 => Z0 + (Nz - 1) * Step;

        public BakedField(int nx, int nz, float x0, float z0, float step, float[] heights, byte[][] layers)
        {
            Nx = nx; Nz = nz; X0 = x0; Z0 = z0; Step = step; _h = heights; _layers = layers;
        }

        public static BakedField Parse(byte[] data)
        {
            if (data == null || data.Length < 24 || data[0] != (byte)'P' || data[1] != (byte)'V' || data[2] != (byte)'6')
                throw new FormatException("island_v6.bytes biçimi tanınmadı");
            var nx = BitConverter.ToInt32(data, 4); var nz = BitConverter.ToInt32(data, 8);
            var x0 = BitConverter.ToSingle(data, 12); var z0 = BitConverter.ToSingle(data, 16); var step = BitConverter.ToSingle(data, 20);
            var n = nx * nz;
            var count = data[3] >= 2 ? 7 : 5;
            if (nx < 2 || nz < 2 || data.Length < 24 + n * 2 + n * count) throw new FormatException("island_v6.bytes eksik");
            var h = new float[n];
            for (var i = 0; i < n; i++) h[i] = BitConverter.ToInt16(data, 24 + i * 2) / 100f;
            var layers = new byte[count][];
            var off = 24 + n * 2;
            for (var k = 0; k < count; k++) { layers[k] = new byte[n]; Buffer.BlockCopy(data, off + k * n, layers[k], 0, n); }
            return new BakedField(nx, nz, x0, z0, step, h, layers);
        }

        private bool Cell(float x, float z, out int i, out int j, out float tx, out float tz)
        {
            var fi = (x - X0) / Step; var fj = (z - Z0) / Step;
            i = (int)Math.Floor(fi); j = (int)Math.Floor(fj);
            tx = fi - i; tz = fj - j;
            if (i < 0 || j < 0 || i >= Nx - 1 || j >= Nz - 1) return false;
            return true;
        }

        public float Height(float x, float z)
        {
            if (!Cell(x, z, out var i, out var j, out var tx, out var tz)) return SeaFloor;
            var a = j * Nx + i;
            return (_h[a] * (1 - tx) + _h[a + 1] * tx) * (1 - tz) + (_h[a + Nx] * (1 - tx) + _h[a + Nx + 1] * tx) * tz;
        }

        public float Get(Layer layer, float x, float z)
        {
            if ((int)layer >= _layers.Length || !Cell(x, z, out var i, out var j, out var tx, out var tz)) return 0f;
            var l = _layers[(int)layer]; var a = j * Nx + i;
            return ((l[a] * (1 - tx) + l[a + 1] * tx) * (1 - tz) + (l[a + Nx] * (1 - tx) + l[a + Nx + 1] * tx) * tz) / 255f;
        }
    }

    /// <summary>Pişmiş süs (island_v6.json "props"): tür, konum, taban yüksekliği, dönüş (°), ölçek ya da taban genişliği (fp).</summary>
    public sealed class BakedProp
    {
        [JsonProperty("a")] public string Asset;
        [JsonProperty("x")] public float X;
        [JsonProperty("z")] public float Z;
        [JsonProperty("y")] public float Y;
        [JsonProperty("r")] public float Yaw;
        [JsonProperty("s")] public float S = 1f;
        [JsonProperty("fp")] public int Fp;          // 1: S = taban genişliği (eski modeller), 0: S = ölçek (v6 modelleri gerçek ölçüde)
    }

    /// <summary>island_v6.json: meydan, patikalar (çoklu çizgi), göl, açık ada, karlı patika, süsler.</summary>
    public sealed class BakedLayout
    {
        public sealed class LakeDef
        {
            [JsonProperty("x")] public float X;
            [JsonProperty("z")] public float Z;
            [JsonProperty("r")] public float R;
            [JsonProperty("level")] public float Level;
        }

        [JsonProperty("plaza")] public float[] Plaza = { 0f, 0f };
        [JsonProperty("paths")] public List<List<float[]>> Paths = new List<List<float[]>>();
        [JsonProperty("lake")] public LakeDef Lake;
        [JsonProperty("props")] public List<BakedProp> Props = new List<BakedProp>();
        [JsonProperty("spots")] public Dictionary<string, float[]> Spots = new Dictionary<string, float[]>();

        public static BakedLayout Parse(string json) => JsonConvert.DeserializeObject<BakedLayout>(json) ?? new BakedLayout();
    }

    /// <summary>Pişmiş ada: ızgara + yerleşim.</summary>
    public sealed class BakedIsland
    {
        public BakedField Field;
        public BakedLayout Layout;

        public static BakedIsland Load(byte[] field, string layoutJson) =>
            new BakedIsland { Field = BakedField.Parse(field), Layout = BakedLayout.Parse(layoutJson) };
    }

    /// <summary>v6 modellerinin gerçek boyu (Data/env_v6_sizes.json; art/code3d/v6/measure_sizes.py). Sayı olmayan alanlar atlanır.</summary>
    public static class EnvSizes
    {
        public static Dictionary<string, float> Parse(string json)
        {
            var d = new Dictionary<string, float>();
            if (string.IsNullOrWhiteSpace(json)) return d;
            try
            {
                var o = Newtonsoft.Json.Linq.JObject.Parse(json);
                foreach (var kv in o)
                    if (kv.Value.Type == Newtonsoft.Json.Linq.JTokenType.Float || kv.Value.Type == Newtonsoft.Json.Linq.JTokenType.Integer)
                        d[kv.Key] = (float)kv.Value;
            }
            catch (JsonException) { }
            return d;
        }
    }
}
