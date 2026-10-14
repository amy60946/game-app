using System.Collections.Generic;
using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// Petin çevresinde çim telleri (GPU instancing, Pofi/Grass). Telefonu yormamak için yalnız ~14 m yarıçapta ve
    /// çimen yüzeyinde çizilir; pet 3 m yürüyünce alan yeniden kurulur. Uzakta zemin dokusu yeterli.
    /// </summary>
    public sealed class GrassField : MonoBehaviour
    {
        private const float Radius = 14f, Cell = 0.7f, Rebuild = 3f;
        private MapWorld _world;
        private Mesh _mesh;
        private Material _mat;
        private readonly List<Matrix4x4[]> _batches = new List<Matrix4x4[]>();
        private Vector2 _center = new Vector2(float.MaxValue, 0f);
        private RenderParams _rp;

        public void Init(MapWorld world)
        {
            _world = world;
            var sh = Shader.Find("Pofi/Grass");
            if (sh == null) { enabled = false; return; }
            _mat = new Material(sh) { enableInstancing = true };
            _mesh = Clump();
            _rp = new RenderParams(_mat) { shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off, receiveShadows = true };
        }

        /// <summary>Bir öbek: 7 incelen tel, rastgele yön ve boy (0,18–0,32 m).</summary>
        private static Mesh Clump()
        {
            var rnd = new System.Random(11);
            var v = new List<Vector3>(); var uv = new List<Vector2>(); var t = new List<int>();
            for (var b = 0; b < 7; b++)
            {
                var a = (float)rnd.NextDouble() * Mathf.PI * 2f;
                var r = (float)rnd.NextDouble() * 0.22f;
                var root = new Vector3(Mathf.Cos(a) * r, 0f, Mathf.Sin(a) * r);
                var face = (float)rnd.NextDouble() * Mathf.PI;
                var side = new Vector3(Mathf.Cos(face), 0f, Mathf.Sin(face)) * 0.022f;
                var h = 0.18f + (float)rnd.NextDouble() * 0.14f;
                var lean = new Vector3((float)rnd.NextDouble() - 0.5f, 0f, (float)rnd.NextDouble() - 0.5f) * 0.08f;
                var i0 = v.Count;
                v.Add(root - side); v.Add(root + side); v.Add(root + lean + Vector3.up * h);
                uv.Add(new Vector2(0f, 0f)); uv.Add(new Vector2(1f, 0f)); uv.Add(new Vector2(0.5f, 1f));
                t.Add(i0); t.Add(i0 + 1); t.Add(i0 + 2);
            }
            var m = new Mesh { name = "GrassClump" };
            m.SetVertices(v); m.SetUVs(0, uv); m.SetTriangles(t, 0);
            m.RecalculateNormals();
            m.bounds = new Bounds(Vector3.up * 0.2f, Vector3.one * 1f);
            return m;
        }

        private void Update()
        {
            if (_world == null || _world.Walker == null || _mesh == null) return;
            var p = _world.Walker.Position;
            if (Vector2.Distance(p, _center) > Rebuild) Build(p);
            for (var i = 0; i < _batches.Count; i++)
                Graphics.RenderMeshInstanced(_rp, _mesh, 0, _batches[i]);
        }

        private void Build(Vector2 c)
        {
            _center = c;
            _batches.Clear();
            var t = _world.Terrain;
            var list = new List<Matrix4x4>();
            var steps = Mathf.CeilToInt(Radius / Cell);
            for (var j = -steps; j <= steps; j++)
            for (var i = -steps; i <= steps; i++)
            {
                // ızgaraya sabit tohumlu sapma: aynı yerde hep aynı öbek (yeniden kurulunca titremez)
                var gx = Mathf.Floor(c.x / Cell) + i; var gz = Mathf.Floor(c.y / Cell) + j;
                var hsh = Hash(gx, gz);
                var x = (gx + 0.5f + (hsh - 0.5f) * 0.8f) * Cell;
                var z = (gz + 0.5f + (Hash(gz, gx) - 0.5f) * 0.8f) * Cell;
                var dx = x - c.x; var dz = z - c.y;
                if (dx * dx + dz * dz > Radius * Radius) continue;
                var mix = t.MixAt(x, z);
                var grass = 1f - Mathf.Max(Mathf.Max(mix.Sand, mix.Path), Mathf.Max(mix.Rock, Mathf.Max(mix.Snow, mix.Water)));
                if (grass < 0.6f) continue;
                if (t.BuildingAt(x, z) != null) continue;
                var pos = _world.transform.TransformPoint(new Vector3(x, t.Height(x, z) - 0.02f, z));
                var s = 0.8f + hsh * 0.6f;
                list.Add(Matrix4x4.TRS(pos, Quaternion.Euler(0f, hsh * 360f, 0f), new Vector3(s, s * (0.8f + Hash(gx + 7, gz) * 0.5f), s)));
            }
            for (var k = 0; k < list.Count; k += 1000)
                _batches.Add(list.GetRange(k, Mathf.Min(1000, list.Count - k)).ToArray());
        }

        private static float Hash(float x, float z)
        {
            unchecked
            {
                var h = (uint)((int)x * 73856093 ^ (int)z * 19349663);
                h = (h ^ (h >> 13)) * 1274126177u;
                return (h & 0xFFFF) / 65535f;
            }
        }

        private void OnDestroy()
        {
            if (_mat != null) Destroy(_mat);
            if (_mesh != null) Destroy(_mesh);
        }
    }
}
