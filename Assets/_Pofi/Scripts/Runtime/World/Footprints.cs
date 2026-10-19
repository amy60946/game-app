using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// Pet yürüdükçe patika ve kumda ayak izi bırakır (kullanıcı isteği): her adım temasında bir iz (sol/sağ),
    /// en çok <see cref="Max"/> iz; eskiler <see cref="Life"/> saniyede solup kaybolur, yenileri oluşur. Çimde iz bırakılmaz.
    /// İzler tek ağda (Pofi/Print), doku kodla çizilir (yuvarlak pati: taban + 3 parmak).
    /// </summary>
    public sealed class Footprints : MonoBehaviour
    {
        private const int Max = 12;
        private const float Life = 5f, Size = 0.24f, Side = 0.12f;   // pet ~1,75 m (PetModels.RealHeight)
        private readonly Vector3[] _pos = new Vector3[Max];
        private readonly float[] _yaw = new float[Max], _born = new float[Max];
        private int _next;
        private MapWorld _world;
        private Mesh _mesh;
        private Material _mat;
        private Texture2D _tex;
        private readonly Vector3[] _v = new Vector3[Max * 4];
        private readonly Color[] _c = new Color[Max * 4];

        public void Init(MapWorld world)
        {
            _world = world;
            var sh = Shader.Find("Pofi/Print");
            if (sh == null) { enabled = false; return; }
            _tex = PawTexture();
            _mat = new Material(sh) { mainTexture = _tex };
            _mesh = new Mesh { name = "Footprints" };
            _mesh.MarkDynamic();
            var uv = new Vector2[Max * 4]; var tri = new int[Max * 6];
            for (var i = 0; i < Max; i++)
            {
                uv[i * 4] = new Vector2(0f, 0f); uv[i * 4 + 1] = new Vector2(0f, 1f); uv[i * 4 + 2] = new Vector2(1f, 1f); uv[i * 4 + 3] = new Vector2(1f, 0f);
                tri[i * 6] = i * 4; tri[i * 6 + 1] = i * 4 + 1; tri[i * 6 + 2] = i * 4 + 2;
                tri[i * 6 + 3] = i * 4; tri[i * 6 + 4] = i * 4 + 2; tri[i * 6 + 5] = i * 4 + 3;
                _born[i] = -100f;
            }
            _mesh.vertices = _v; _mesh.uv = uv; _mesh.colors = _c; _mesh.triangles = tri;
            _mesh.bounds = new Bounds(Vector3.zero, Vector3.one * 2000f);
            var go = new GameObject("FootprintMesh");
            go.transform.SetParent(transform, false);
            go.AddComponent<MeshFilter>().sharedMesh = _mesh;
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = _mat;
            mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            mr.receiveShadows = false;
        }

        /// <summary>Adım teması (PetWalker): ada yerel konumu ve bakış açısı; <paramref name="left"/> hangi ayak.</summary>
        public void Step(float x, float z, float yaw, bool left)
        {
            if (_mesh == null) return;
            var mix = _world.Terrain.MixAt(x, z);
            if (Mathf.Max(mix.Path, mix.Sand) < 0.45f || mix.Water > 0.2f) return;   // yalnız toprak patika ve kumda
            var r = yaw * Mathf.Deg2Rad;
            var right = new Vector2(Mathf.Cos(r), -Mathf.Sin(r));   // bakış (sin, cos) yönünün sağı
            var off = right * (left ? -Side : Side);
            _pos[_next] = new Vector3(x + off.x, 0f, z + off.y);
            _yaw[_next] = yaw;
            _born[_next] = Time.time;
            _next = (_next + 1) % Max;
        }

        private void LateUpdate()
        {
            if (_mesh == null) return;
            var t = _world.Terrain;
            var toLocal = transform.worldToLocalMatrix * _world.transform.localToWorldMatrix;
            for (var i = 0; i < Max; i++)
            {
                var age = Time.time - _born[i];
                var a = age < 0f || age > Life ? 0f : Mathf.Clamp01(age / 0.15f) * (1f - Mathf.Clamp01((age - Life * 0.5f) / (Life * 0.5f)));
                var p = _pos[i];
                var r = _yaw[i] * Mathf.Deg2Rad;
                var fwd = new Vector3(Mathf.Sin(r), 0f, Mathf.Cos(r)) * (Size * 0.5f);
                var side = new Vector3(fwd.z, 0f, -fwd.x);
                Corner(i * 4, p - fwd - side, t, toLocal);
                Corner(i * 4 + 1, p + fwd - side, t, toLocal);
                Corner(i * 4 + 2, p + fwd + side, t, toLocal);
                Corner(i * 4 + 3, p - fwd + side, t, toLocal);
                var col = new Color(0.32f, 0.22f, 0.14f, 0.42f * a);
                for (var k = 0; k < 4; k++) _c[i * 4 + k] = col;
            }
            _mesh.vertices = _v;
            _mesh.colors = _c;
        }

        private void Corner(int idx, Vector3 p, Logic.Island.IslandTerrain t, Matrix4x4 toLocal) =>
            _v[idx] = toLocal.MultiplyPoint3x4(new Vector3(p.x, t.Height(p.x, p.z) + 0.012f, p.z));

        /// <summary>Pati izi: oval taban + önde 3 parmak; kenarlar yumuşak (alfa kanalı).</summary>
        private static Texture2D PawTexture()
        {
            const int n = 48;
            var tex = new Texture2D(n, n, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, name = "paw" };
            var px = new Color[n * n];
            for (var y = 0; y < n; y++)
            for (var x = 0; x < n; x++)
            {
                float u = (x + 0.5f) / n, v = (y + 0.5f) / n;   // v: arkadan (0) öne (1)
                var a = Blob(u, v, 0.5f, 0.34f, 0.22f, 0.18f);
                a = Mathf.Max(a, Blob(u, v, 0.28f, 0.68f, 0.09f, 0.1f));
                a = Mathf.Max(a, Blob(u, v, 0.5f, 0.76f, 0.09f, 0.1f));
                a = Mathf.Max(a, Blob(u, v, 0.72f, 0.68f, 0.09f, 0.1f));
                px[y * n + x] = new Color(1f, 1f, 1f, a);
            }
            tex.SetPixels(px);
            tex.Apply();
            return tex;
        }

        private static float Blob(float u, float v, float cx, float cy, float rx, float ry)
        {
            var dx = (u - cx) / rx; var dy = (v - cy) / ry;
            var d = Mathf.Sqrt(dx * dx + dy * dy);
            return Mathf.Clamp01((1f - d) / 0.3f);
        }

        private void OnDestroy()
        {
            if (_mat != null) Destroy(_mat);
            if (_tex != null) Destroy(_tex);
            if (_mesh != null) Destroy(_mesh);
        }
    }
}
