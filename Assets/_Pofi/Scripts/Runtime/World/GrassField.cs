using System.Collections.Generic;
using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// Petin çevresinde çim telleri (Pofi/Grass). Telefonu yormamak için yalnız ~13 m yarıçapta ve çimen yüzeyinde çizilir;
    /// pet 3 m yürüyünce alan yeniden kurulur. Uzakta zemin dokusu yeterli.
    /// Öbekler tek bir birleşik ağda çizilir: GPU instancing derlemede ayıklanıyordu (kodla kurulan malzeme instancing
    /// kullanmadığı için Unity varyantı siliyor → çim hiç görünmüyordu).
    /// </summary>
    public sealed class GrassField : MonoBehaviour
    {
        private const float Radius = 13f, Cell = 0.5f, Rebuild = 3f;
        private MapWorld _world;
        private Mesh _mesh;
        private Material _mat;
        private Mesh _field;
        private Transform _holder;
        private Vector2 _center = new Vector2(float.MaxValue, 0f);

        public void Init(MapWorld world)
        {
            _world = world;
            var sh = Shader.Find("Pofi/Grass");
            if (sh == null) { enabled = false; return; }
            _mat = new Material(sh);
            _mesh = Clump();
            _field = new Mesh { name = "GrassField", indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 };
            _field.MarkDynamic();
            var holder = new GameObject("GrassMesh");
            holder.transform.SetParent(transform, false);
            _holder = holder.transform;
            holder.AddComponent<MeshFilter>().sharedMesh = _field;
            var mr = holder.AddComponent<MeshRenderer>();
            mr.sharedMaterial = _mat;
            mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            mr.receiveShadows = true;
        }

        /// <summary>Bir öbek: 7 incelen tel, rastgele yön ve boy (0,24–0,42 m).</summary>
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
                var side = new Vector3(Mathf.Cos(face), 0f, Mathf.Sin(face)) * 0.03f;
                var h = 0.24f + (float)rnd.NextDouble() * 0.18f;
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
        }

        private void Build(Vector2 c)
        {
            _center = c;
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
            // öbekleri tek ağda birleştir (dünya → bu nesnenin yerel uzayı)
            var src = _mesh.vertices; var suv = _mesh.uv; var stri = _mesh.triangles;
            var verts = new List<Vector3>(list.Count * src.Length); var uvs = new List<Vector2>(list.Count * src.Length);
            var tris = new List<int>(list.Count * stri.Length);
            var toLocal = _holder.worldToLocalMatrix;
            foreach (var m in list)
            {
                var mm = toLocal * m;
                var b = verts.Count;
                for (var i = 0; i < src.Length; i++) { verts.Add(mm.MultiplyPoint3x4(src[i])); uvs.Add(suv[i]); }
                for (var i = 0; i < stri.Length; i++) tris.Add(b + stri[i]);
            }
            _field.Clear();
            _field.SetVertices(verts); _field.SetUVs(0, uvs); _field.SetTriangles(tris, 0);
            _field.RecalculateNormals();
            _field.RecalculateBounds();
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
            if (_field != null) Destroy(_field);
        }
    }
}
