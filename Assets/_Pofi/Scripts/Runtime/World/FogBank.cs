using System.Collections.Generic;
using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// Güneş Taşı bölgesinin yer sisi (kullanıcı GB18-5/6, 24 Ekim 2026: "sisler buluttan çok sise benzesin"; "koydaki sisin nerede
    /// olduğunu göremiyorum"). Eski sis yere konmuş opak bulut topaklarıydı. Bu sis tek ağ, tek çizim (Pofi/Fog):
    /// araziye yapışık dört kat örtü (yerden 0,25 / 0,7 / 1,3 / 2,1 m, kenarda söner), bölgeyi saran 20 kameraya dönük tül perde,
    /// içeride alçak sis öbekleri ve ortada uzaktan seçilen ince, yüksek bir sis sütunu (16 m'ye kadar; ağaçların üstünden görünür).
    /// 26 Ekim 2026 (kullanıcı: "sis detayını biraz daha yoğun yap"): katlar ve perdeler daha opak, içi boş kalmasın diye alçak öbekler.
    /// Taş yerleşince <see cref="SetLift"/> ile yükselip incelir ve söner (MapScreen.FogLift).
    /// </summary>
    public sealed class FogBank : MonoBehaviour
    {
        private static Material _mat;
        private MeshRenderer _mr;
        private MaterialPropertyBlock _mpb;
        private Vector3 _pos0;

        /// <param name="height">Arazi yüksekliği (yerel x, z → y); denizde 0'ın altı.</param>
        public static FogBank Spawn(Transform parent, Vector3 center, float radius, int seed, System.Func<float, float, float> height)
        {
            if (_mat == null)
            {
                var sh = Shader.Find("Pofi/Fog");
                if (sh == null) return null;
                _mat = new Material(sh) { name = "PofiFog" };
            }
            var rnd = new System.Random(seed);
            var verts = new List<Vector3>(); var cols = new List<Color>(); var uv = new List<Vector2>(); var size = new List<Vector2>();
            var tris = new List<int>();

            // örtü: kutup ızgarası, her köşe yerel araziye (deniz 0) yapışık
            const int Rings = 7, Segs = 28;
            var blanket = radius * 1.35f;
            var layers = new[] { (0.25f, 0.78f, new Color(0.92f, 0.94f, 1f)), (0.7f, 0.62f, new Color(0.95f, 0.97f, 1f)),
                                 (1.3f, 0.46f, new Color(0.98f, 0.99f, 1f)), (2.1f, 0.3f, Color.white) };
            foreach (var (lift, alpha, tint) in layers)
            {
                var b = verts.Count;
                verts.Add(new Vector3(center.x, Ground(height, center.x, center.z) + lift, center.z));
                cols.Add(new Color(tint.r, tint.g, tint.b, alpha)); uv.Add(Vector2.zero); size.Add(Vector2.zero);
                for (var r = 1; r <= Rings; r++)
                {
                    var k = r / (float)Rings;
                    for (var s = 0; s < Segs; s++)
                    {
                        var a = (s + (r % 2) * 0.5f) / Segs * Mathf.PI * 2f;
                        var wob = 1f + Mathf.Sin(a * 3f + seed) * 0.12f + Mathf.Sin(a * 5f + seed * 0.3f) * 0.06f;   // kenar yuvarlak değil
                        var x = center.x + Mathf.Cos(a) * blanket * k * wob;
                        var z = center.z + Mathf.Sin(a) * blanket * k * wob;
                        verts.Add(new Vector3(x, Ground(height, x, z) + lift * Mathf.Lerp(1f, 0.6f, k), z));
                        cols.Add(new Color(tint.r, tint.g, tint.b, alpha));
                        uv.Add(new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * k);
                        size.Add(Vector2.zero);
                    }
                }
                for (var s = 0; s < Segs; s++) { tris.Add(b); tris.Add(b + 1 + (s + 1) % Segs); tris.Add(b + 1 + s); }
                for (var r = 1; r < Rings; r++)
                {
                    int i0 = b + 1 + (r - 1) * Segs, i1 = b + 1 + r * Segs;
                    for (var s = 0; s < Segs; s++)
                    {
                        int a0 = i0 + s, a1 = i0 + (s + 1) % Segs, c0 = i1 + s, c1 = i1 + (s + 1) % Segs;
                        tris.Add(a0); tris.Add(a1); tris.Add(c0);
                        tris.Add(a1); tris.Add(c1); tris.Add(c0);
                    }
                }
            }

            // perdeler: bölgeyi saran tül; sütun: ortada ince, yüksek tutamlar (uzaktan yer belli olsun)
            void Veil(float x, float z, float w, float h, float alpha, Color tint)
            {
                var b = verts.Count;
                var y = Ground(height, x, z) - 0.2f;
                for (var c = 0; c < 4; c++)
                {
                    verts.Add(new Vector3(x, y, z));
                    cols.Add(new Color(tint.r, tint.g, tint.b, alpha));
                    uv.Add(new Vector2(c == 1 || c == 2 ? 1f : 0f, c >= 2 ? 1f : 0f));
                    size.Add(new Vector2(w, h));
                }
                tris.Add(b); tris.Add(b + 2); tris.Add(b + 1);
                tris.Add(b); tris.Add(b + 3); tris.Add(b + 2);
            }
            const int VeilN = 20;
            for (var i = 0; i < VeilN; i++)
            {
                var a = (i + (float)rnd.NextDouble() * 0.6f) / VeilN * Mathf.PI * 2f;
                var d = radius * (0.35f + (float)rnd.NextDouble() * 0.65f);
                Veil(center.x + Mathf.Cos(a) * d, center.z + Mathf.Sin(a) * d,
                    radius * (0.55f + (float)rnd.NextDouble() * 0.45f), 3.6f + (float)rnd.NextDouble() * 3.4f, 0.64f, new Color(0.95f, 0.97f, 1f));
            }
            // içeride alçak, kalın öbekler: perdelerin arası boş görünmesin, sis "dolu" dursun
            for (var i = 0; i < 10; i++)
            {
                var a = (float)rnd.NextDouble() * Mathf.PI * 2f;
                var d = radius * (float)rnd.NextDouble() * 0.6f;
                Veil(center.x + Mathf.Cos(a) * d, center.z + Mathf.Sin(a) * d,
                    radius * (0.3f + (float)rnd.NextDouble() * 0.25f), 1.6f + (float)rnd.NextDouble() * 1.2f, 0.7f, new Color(0.93f, 0.95f, 1f));
            }
            for (var i = 0; i < 4; i++)
            {
                var a = i * 1.6f + (float)rnd.NextDouble();
                Veil(center.x + Mathf.Cos(a) * radius * 0.2f, center.z + Mathf.Sin(a) * radius * 0.2f,
                    radius * (0.7f + i * 0.12f), 13f + i * 2.5f, 0.5f, Color.white);   // uzaktan seçilsin (kullanıcı GB18-5)
            }

            var mesh = new Mesh { name = "FogBank" };
            mesh.SetVertices(verts); mesh.SetColors(cols); mesh.SetUVs(0, uv); mesh.SetUVs(1, size); mesh.SetTriangles(tris, 0);
            mesh.RecalculateBounds();
            var bnd = mesh.bounds; bnd.Expand(new Vector3(radius * 1.2f, 18f, radius * 1.2f));   // perdeler gölgelendiricide büyür
            mesh.bounds = bnd;

            var go = new GameObject("FogBank");
            go.transform.SetParent(parent, false);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var bank = go.AddComponent<FogBank>();
            bank._mr = go.AddComponent<MeshRenderer>();
            bank._mr.sharedMaterial = _mat;
            bank._mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            bank._mr.receiveShadows = false;
            bank._mpb = new MaterialPropertyBlock();
            bank._pos0 = go.transform.localPosition;
            return bank;
        }

        private static float Ground(System.Func<float, float, float> height, float x, float z) => Mathf.Max(0.05f, height(x, z));

        /// <summary>Dağılma (0 sis tam, 1 yok): yükselir, incelir, söner.</summary>
        public void SetLift(float e)
        {
            if (_mr == null) return;
            _mpb.SetFloat("_Fade", Mathf.Clamp01(e));
            _mr.SetPropertyBlock(_mpb);
            transform.localPosition = _pos0 + Vector3.up * e * 3f;
        }
    }
}
