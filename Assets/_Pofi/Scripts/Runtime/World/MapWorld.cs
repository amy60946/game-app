using System.Collections.Generic;
using Pofi.Logic.Island;
using UnityEngine;

namespace Pofi.World
{
    /// <summary>Yavaş dönen ve hafifçe süzülen nesne.</summary>
    public sealed class Spin : MonoBehaviour
    {
        private Vector3 _base;
        private void Start() => _base = transform.localPosition;
        private void Update()
        {
            transform.Rotate(0f, 90f * Time.deltaTime, 0f, Space.World);
            transform.localPosition = _base + Vector3.up * (Mathf.Sin(Time.time * 2.5f) * 0.12f);
        }
    }

    /// <summary>Kendi yerel dikey ekseninde sürekli döner (eşyanın dönen parçası: pervane, akvaryum balıkları).</summary>
    public sealed class SpinAxis : MonoBehaviour
    {
        public float Speed = 90f;
        private void Update() => transform.Rotate(0f, Speed * Time.deltaTime, 0f, Space.Self);
    }

    /// <summary>
    /// Gezilebilir 3B ada (M5, köy ölçeği): prosedürel arazi (Pofi.Logic.IslandTerrain) + Meshy yapıları ve süsleri
    /// + adada yürüyen pet. Ana sahneden uzakta (x = 200) kurulur. Zemin "ground" adlı MeshCollider taşır,
    /// bölgeler kendi adlarıyla BoxCollider taşır (dokunma).
    /// </summary>
    public sealed class MapWorld : MonoBehaviour
    {
        public static readonly Vector3 Origin = new Vector3(200f, 0f, 0f);

        public readonly Dictionary<string, Transform> Regions = new Dictionary<string, Transform>();
        /// <summary>Bölge etiketinin yapı tabanından yüksekliği.</summary>
        public readonly Dictionary<string, float> LabelHeights = new Dictionary<string, float>();
        /// <summary>Güneş Taşı bölgelerinin yer sisi (H1 sis kalkış sahnesi dağıtır).</summary>
        public readonly Dictionary<string, Transform> Fog = new Dictionary<string, Transform>();
        public IslandTerrain Terrain { get; private set; }
        public PetWalker Walker { get; private set; }
        /// <summary>Patika ve kumda solan ayak izleri (PetWalker adım temasında ekler).</summary>
        public Footprints Prints { get; private set; }
        /// <summary>Dokununca tepki veren süsler (O4): yerel (x, z) konumuyla; MapScreen dokunuş noktasına en yakını dürter.</summary>
        public readonly List<(Vector2 At, float Radius, Wobble W)> Reactive = new List<(Vector2, float, Wobble)>();
        public readonly List<(Vector2 At, CrabFlee C)> Crabs = new List<(Vector2, CrabFlee)>();

        private readonly List<Object> _owned = new List<Object>();

        /// <summary>Bölge → Meshy modeli (Resources/Env). Yoksa yer tutucu.</summary>
        private static readonly Dictionary<string, string> RegionAssets = new Dictionary<string, string>
        {
            { "region_home", "b_home" }, { "region_shop", "b_shop" }, { "region_task_board", "b_task_board" },
            { "region_swim_cove", "b_swim" }, { "region_surf_beach", "b_surf" }, { "region_game_hut", "b_game_hut" },
            { "region_ski_hill", "b_ski_hill" }, { "region_garden", "b_garden" }, { "region_pier", "b_pier" },
            { "region_cave", "b_cave" }, { "region_festival", "b_festival" }, { "region_mountain", "b_mountain" },
            { "region_lighthouse", "b_lighthouse" },
        };

        /// <summary>Pişmiş adada (v6) gerçek ölçülü bölge modelleri (art/code3d/v6/assets_v6_game.py).</summary>
        private static readonly Dictionary<string, string> V6Regions = new Dictionary<string, string>
        {
            { "region_cave", "b_cave_v6" }, { "region_ski_hill", "b_ski_v6" }, { "region_mountain", "b_summit_v6" },
        };

        public static MapWorld Create(IReadOnlyList<RegionView> views, IslandTerrain terrain)
        {
            var go = new GameObject("MapWorld");
            go.transform.position = Origin;
            var w = go.AddComponent<MapWorld>();
            w.Terrain = terrain;
            w.Build(views);
            return w;
        }

        /// <summary>Ada üzerindeki (yerel x, z) noktanın dünya konumu (zemin yüksekliğinde).</summary>
        public Vector3 World(float x, float z) => transform.TransformPoint(new Vector3(x, Terrain.Height(x, z), z));

        public Vector2 Local(Vector3 world)
        {
            var p = transform.InverseTransformPoint(world);
            return new Vector2(p.x, p.z);
        }

        private void Build(IReadOnlyList<RegionView> views)
        {
            BuildGround();
            BuildWater();
            foreach (var v in views) BuildRegion(v);
            BuildProps();
            BuildTrailRopes();
            if (Terrain.Baked != null)
            {
                BuildLake();
                // büyük ada (v6): bulut halkası ve kuşlar adayı çevreler; zirve 38 m, bulutlar üstünde
                Clouds.Spawn(transform, new Vector3(0f, 0f, 0f), 135f, 16, 46f, 70f, 16f, 5);
                Birds.Spawn(transform, new Vector3(0f, 0f, -10f), 105f, 4, 9);
            }
            else
            {
                Clouds.Spawn(transform, new Vector3(0f, 0f, Terrain.Def.Cz), 72f, 10, 18f, 30f, 9f, 5);   // ada çevresinde bulutlar
                Birds.Spawn(transform, new Vector3(0f, 0f, Terrain.Def.Cz), 54f, 3, 9);                   // denizin üstünde kuş sürüleri
            }
        }

        // ------------------------------------------------------------------ zemin

        // Zemin ağı ve dokusu pahalı: arazi başına bir kez üretilir, sahneler arası saklanır.
        private static IslandTerrain _cachedFor;
        private static Mesh _groundMesh;
        private static Texture2D _groundTex;

        // pişmiş v6 zemini: 8 × 8 parça (görüş dışı parçalar çizilmez), dokunma/kamera için 1 m'lik tek çarpışma ağı
        private static Mesh[] _bakedParts;
        private static Mesh _bakedCollider;
        private static IslandTerrain _bakedFor;

        private void BuildBakedGround()
        {
            var f = Terrain.Baked.Field;
            if (_bakedFor != Terrain || _bakedParts == null)
            {
                const int parts = 8;
                _bakedParts = new Mesh[parts * parts];
                for (var pj = 0; pj < parts; pj++)
                for (var pi = 0; pi < parts; pi++)
                {
                    int i0 = pi * (f.Nx - 1) / parts, i1 = (pi + 1) * (f.Nx - 1) / parts;
                    int j0 = pj * (f.Nz - 1) / parts, j1 = (pj + 1) * (f.Nz - 1) / parts;
                    _bakedParts[pj * parts + pi] = FieldMesh(f, i0, j0, i1, j1, 1, "IslandGround" + pi + "_" + pj);
                }
                _bakedCollider = FieldMesh(f, 0, 0, f.Nx - 1, f.Nz - 1, 2, "IslandGroundCollider");
                _bakedFor = Terrain;
            }
            var go = new GameObject("ground");
            go.transform.SetParent(transform, false);
            var gsh = Shader.Find("Pofi/Ground");
            var mat = gsh != null ? new Material(gsh) : PetModels.NewMaterial(Color.white, 0.12f);
            var tex = Resources.Load<Texture2D>("Env/ground_v6/ground_v6");
            if (tex != null) mat.SetTexture("_BaseMap", tex);
            mat.SetFloat("_RockStrata", 1f);   // dik yüzlerde tabaka bantları + dikey oluklar (taslaktaki kaya)
            var mask = Resources.Load<Texture2D>("Env/ground_v6/ground_v6_mask");   // r: kanyon kaldırımı (bake_game.py)
            if (mask != null) { mat.SetTexture("_MaskMap", mask); mat.SetFloat("_Cobble", 1f); }
            _owned.Add(mat);
            foreach (var m in _bakedParts)
            {
                var part = new GameObject("ground_part");
                part.transform.SetParent(go.transform, false);
                part.AddComponent<MeshFilter>().sharedMesh = m;
                var mr = part.AddComponent<MeshRenderer>();
                mr.sharedMaterial = mat;
                mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.On;   // yarlar platoya gölge düşürür (derinlik)
                mr.receiveShadows = true;
            }
            go.AddComponent<MeshCollider>().sharedMesh = _bakedCollider;
        }

        /// <summary>Izgara parçası ağı (i0..i1, j0..j1 hücre köşeleri, adım <paramref name="stride"/>); UV tüm adanın dokusuna göre.</summary>
        private static Mesh FieldMesh(BakedField f, int i0, int j0, int i1, int j1, int stride, string name)
        {
            var nx = (i1 - i0) / stride + 1; var nz = (j1 - j0) / stride + 1;
            var verts = new Vector3[nx * nz];
            var uvs = new Vector2[nx * nz];
            for (var j = 0; j < nz; j++)
            for (var i = 0; i < nx; i++)
            {
                var gi = Mathf.Min(i0 + i * stride, f.Nx - 1); var gj = Mathf.Min(j0 + j * stride, f.Nz - 1);
                var x = f.X0 + gi * f.Step; var z = f.Z0 + gj * f.Step;
                verts[j * nx + i] = new Vector3(x, f.Height(x, z), z);
                uvs[j * nx + i] = new Vector2(gi / (float)(f.Nx - 1), gj / (float)(f.Nz - 1));
            }
            var tris = new int[(nx - 1) * (nz - 1) * 6];
            var k = 0;
            for (var j = 0; j < nz - 1; j++)
            for (var i = 0; i < nx - 1; i++)
            {
                var a = j * nx + i;
                tris[k++] = a; tris[k++] = a + nx; tris[k++] = a + 1;
                tris[k++] = a + 1; tris[k++] = a + nx; tris[k++] = a + nx + 1;
            }
            var mesh = new Mesh { name = name };
            if (verts.Length > 65000) mesh.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
            mesh.vertices = verts; mesh.uv = uvs; mesh.triangles = tris;
            mesh.RecalculateNormals();   // parça kenarında normal dikişi küçük: komşu yükseklik aynı ızgaradan
            mesh.RecalculateBounds();
            return mesh;
        }

        /// <summary>Göl (v6): yüzey göl seviyesinde, aynı su gölgelendiricisi; sığlık göl derinliğinden.</summary>
        private void BuildLake()
        {
            var lake = Terrain.Baked.Layout.Lake;
            var sh = Shader.Find("Pofi/Water");
            if (lake == null || sh == null) return;
            var r = lake.R + 5f;
            const int size = 64;
            var px = new Color32[size * size];
            for (var j = 0; j < size; j++)
            for (var i = 0; i < size; i++)
            {
                var x = lake.X - r + (i + 0.5f) / size * 2f * r; var z = lake.Z - r + (j + 0.5f) / size * 2f * r;
                var d = Terrain.Height(x, z) - lake.Level;
                var shallow = d >= 0f ? 1f : Mathf.Clamp01(1f + d / 1.2f);
                var foam = d >= 0f ? 1f : Mathf.Pow(Mathf.Clamp01(1f + d / 0.3f), 2f) * 0.5f;
                px[j * size + i] = new Color32((byte)(shallow * 255), (byte)(foam * 255), 0, 255);
            }
            var tex = new Texture2D(size, size, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, filterMode = FilterMode.Bilinear };
            tex.SetPixels32(px); tex.Apply(false, true);
            _owned.Add(tex);
            var m = new Material(sh);
            m.SetTexture("_ShoreMap", tex);
            var o = transform.position;
            m.SetVector("_ShoreRect", new Vector4(o.x + lake.X - r, o.z + lake.Z - r, 2f * r, 2f * r));
            m.SetFloat("_WaveAmp", 0.025f);   // göl sakin
            _owned.Add(m);
            // taslaktaki gibi yuvarlak su yüzeyi (r + 5,5 m): kare düzlemin köşeleri göl çanağı dışındaki alçak dereye taşıp
            // çimenin üstünde düz kenarlı su gibi görünüyordu (geri bildirim 22 Ekim 2026)
            const int seg = 72;
            var rr = lake.R + 5.5f;
            var verts = new Vector3[seg + 1]; var tris = new int[seg * 3];
            for (var k = 0; k < seg; k++)
            {
                var a = k * Mathf.PI * 2f / seg;
                verts[k + 1] = new Vector3(Mathf.Cos(a) * rr, 0f, Mathf.Sin(a) * rr);
                tris[k * 3] = 0; tris[k * 3 + 1] = 1 + (k + 1) % seg; tris[k * 3 + 2] = 1 + k;
            }
            var disc = new Mesh { name = "LakeDisc", vertices = verts, triangles = tris };
            disc.RecalculateNormals(); disc.RecalculateBounds();
            _owned.Add(disc);
            var go = new GameObject("Lake");
            go.transform.SetParent(transform, false);
            go.transform.localPosition = new Vector3(lake.X, lake.Level, lake.Z);
            go.AddComponent<MeshFilter>().sharedMesh = disc;
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = m;
            mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        }

        private void BuildGround()
        {
            if (Terrain.Baked != null) { BuildBakedGround(); return; }
            if (_cachedFor != Terrain || _groundMesh == null || _groundTex == null)
            {
                _groundMesh = GroundMesh();
                _groundTex = PaintGround();
                _cachedFor = Terrain;
            }
            var go = new GameObject("ground");
            go.transform.SetParent(transform, false);
            go.AddComponent<MeshFilter>().sharedMesh = _groundMesh;
            var mr = go.AddComponent<MeshRenderer>();
            var gsh = Shader.Find("Pofi/Ground");
            var mat = gsh != null ? new Material(gsh) : PetModels.NewMaterial(Color.white, 0.12f);
            mat.SetTexture("_BaseMap", _groundTex);
            mr.sharedMaterial = mat;
            mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            mr.receiveShadows = true;
            _owned.Add(mat);
            go.AddComponent<MeshCollider>().sharedMesh = _groundMesh;
        }

        private Mesh GroundMesh()
        {
            const float step = 0.5f;
            var t = Terrain;
            var nx = Mathf.CeilToInt((t.MaxX - t.MinX) / step) + 1;
            var nz = Mathf.CeilToInt((t.MaxZ - t.MinZ) / step) + 1;
            var verts = new Vector3[nx * nz];
            var uvs = new Vector2[nx * nz];
            for (var j = 0; j < nz; j++)
            for (var i = 0; i < nx; i++)
            {
                var x = t.MinX + i * step; var z = t.MinZ + j * step;
                verts[j * nx + i] = new Vector3(x, t.Height(x, z), z);
                uvs[j * nx + i] = new Vector2(i / (float)(nx - 1), j / (float)(nz - 1));
            }
            var tris = new int[(nx - 1) * (nz - 1) * 6];
            var k = 0;
            for (var j = 0; j < nz - 1; j++)
            for (var i = 0; i < nx - 1; i++)
            {
                var a = j * nx + i;
                tris[k++] = a; tris[k++] = a + nx; tris[k++] = a + 1;
                tris[k++] = a + 1; tris[k++] = a + nx; tris[k++] = a + nx + 1;
            }
            var mesh = new Mesh { name = "IslandGround" };
            if (verts.Length > 65000) mesh.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
            mesh.vertices = verts; mesh.uv = uvs; mesh.triangles = tris;
            mesh.RecalculateNormals();
            mesh.RecalculateBounds();
            return mesh;
        }

        /// <summary>Yüzey türlerinden zemin dokusu (kum, çimen, patika, kaya, kar) + hafif renk dalgası.</summary>
        private Texture2D PaintGround()
        {
            var t = Terrain;
            const int w = 384;
            var h = Mathf.RoundToInt(w * (t.MaxZ - t.MinZ) / (t.MaxX - t.MinX));
            var px = new Color32[w * h];
            // çimen tonları sakin (kullanıcı, 19 Ekim 2026: "çok yeşil ve parlak olmasın"): zeytin ve kuru ot dalgası, çimsiz açıklıklar toprak
            Color sand = Theme(0.97f, 0.87f, 0.63f), grass = Theme(0.45f, 0.63f, 0.31f), grass2 = Theme(0.34f, 0.52f, 0.25f), dry = Theme(0.58f, 0.6f, 0.36f),
                bare = Theme(0.56f, 0.5f, 0.35f),
                path = Theme(0.83f, 0.66f, 0.45f), rock = Theme(0.62f, 0.57f, 0.52f), snow = Theme(0.97f, 0.98f, 1f), wet = Theme(0.55f, 0.78f, 0.82f);
            var rng = new System.Random(5);
            for (var j = 0; j < h; j++)
            for (var i = 0; i < w; i++)
            {
                var x = t.MinX + (i + 0.5f) / w * (t.MaxX - t.MinX);
                var z = t.MinZ + (j + 0.5f) / h * (t.MaxZ - t.MinZ);
                var mix = t.MixAt(x, z);
                var c = Color.Lerp(grass2, grass, Mathf.PerlinNoise(x * 0.12f + 31f, z * 0.12f + 7f));
                c = Color.Lerp(c, dry, Mathf.Clamp01(Mathf.PerlinNoise(x * 0.05f + 3f, z * 0.05f + 91f) * 1.6f - 0.75f));   // yer yer kuru ot
                c = Color.Lerp(c, bare, Mathf.Clamp01((0.3f - GrassField.Noise(x * 0.42f, z * 0.42f)) / 0.08f) * 0.8f);  // çim telinin olmadığı açıklıklar
                c = Color.Lerp(c, sand, mix.Sand);
                c = Color.Lerp(c, rock, mix.Rock);
                c = Color.Lerp(c, snow, mix.Snow);
                c = Color.Lerp(c, path, mix.Path);
                c = Color.Lerp(c, wet, mix.Water);
                var v = 0.96f + (float)rng.NextDouble() * 0.05f;
                var sandW = Mathf.Clamp01(mix.Sand * (1f - mix.Path) * (1f - mix.Water));   // alfa: kum (çizgi ve ıslaklık gölgelendiricide)
                px[j * w + i] = new Color(c.r * v, c.g * v, c.b * v, sandW);
            }
            var tex = new Texture2D(w, h, TextureFormat.RGBA32, true) { wrapMode = TextureWrapMode.Clamp, filterMode = FilterMode.Bilinear, anisoLevel = 4 };
            tex.SetPixels32(px);
            tex.Apply(true, true);
            return tex;
        }

        private static Color Theme(float r, float g, float b) => new Color(r, g, b);

        private static Texture2D _shoreTex;
        private static Mesh _waterMesh;
        private static bool _waterBig;

        /// <summary>Deniz: dalgalı ağ (Pofi/Water), kıyı haritasıyla sığ turkuaz ve köpük; uzakta düz ufuk düzlemi.</summary>
        private void BuildWater()
        {
            var t = Terrain;
            var sh = Shader.Find("Pofi/Water");
            Material m;
            if (sh != null)
            {
                if (_cachedFor != Terrain || _shoreTex == null) _shoreTex = ShoreMap();
                m = new Material(sh);
                m.SetTexture("_ShoreMap", _shoreTex);
                var o = transform.position;   // gölgelendirici dünya koordinatıyla okur (ada x = 200'de kurulu)
                m.SetVector("_ShoreRect", new Vector4(o.x + t.MinX, o.z + t.MinZ, t.MaxX - t.MinX, t.MaxZ - t.MinZ));
            }
            else m = PetModels.NewMaterial(new Color(0.22f, 0.7f, 0.95f), 0.88f);
            _owned.Add(m);

            var big = t.Baked != null;
            if (_waterMesh == null || _waterBig != big) { _waterMesh = WaterGrid(big ? 150 : 140, big ? 1.6f * 1.6f : 1.6f); _waterBig = big; }
            var go = new GameObject("Water");
            go.transform.SetParent(transform, false);
            go.transform.localPosition = new Vector3((t.MinX + t.MaxX) * 0.5f, -0.02f, (t.MinZ + t.MaxZ) * 0.5f);
            go.AddComponent<MeshFilter>().sharedMesh = _waterMesh;
            var r = go.AddComponent<MeshRenderer>();
            r.sharedMaterial = m;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;

            // ufka kadar düz deniz (dalga ağı bitince boşluk görünmesin)
            var far = GameObject.CreatePrimitive(PrimitiveType.Plane);
            far.name = "FarWater";
            far.transform.SetParent(transform, false);
            far.transform.localPosition = new Vector3(0f, -0.06f, t.Baked != null ? 0f : t.Def.Cz);
            far.transform.localScale = new Vector3(80f, 1f, 80f);
            var fr = far.GetComponent<Renderer>();
            fr.sharedMaterial = m;
            fr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            Destroy(far.GetComponent<Collider>());
        }

        private static Mesh WaterGrid(int n, float step)
        {
            var verts = new Vector3[(n + 1) * (n + 1)];
            var half = n * step * 0.5f;
            for (var j = 0; j <= n; j++)
            for (var i = 0; i <= n; i++) verts[j * (n + 1) + i] = new Vector3(i * step - half, 0f, j * step - half);
            var tris = new int[n * n * 6];
            var k = 0;
            for (var j = 0; j < n; j++)
            for (var i = 0; i < n; i++)
            {
                var a = j * (n + 1) + i;
                tris[k++] = a; tris[k++] = a + n + 1; tris[k++] = a + 1;
                tris[k++] = a + 1; tris[k++] = a + n + 1; tris[k++] = a + n + 2;
            }
            var mesh = new Mesh { name = "WaterGrid", indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 };
            mesh.vertices = verts; mesh.triangles = tris;
            mesh.RecalculateNormals();
            mesh.bounds = new Bounds(Vector3.zero, new Vector3(n * step, 4f, n * step));
            return mesh;
        }

        /// <summary>Kıyı haritası: r = sığlık (kıyıya yakın 1), g = köpük şeridi (kıyı çizgisinde 1).</summary>
        private Texture2D ShoreMap()
        {
            var size = Terrain.Baked != null ? 400 : 192;   // büyük ada: kıyı köpüğü aynı incelikte
            var t = Terrain;
            var hs = new float[size * size];
            for (var j = 0; j < size; j++)
            for (var i = 0; i < size; i++)
                hs[j * size + i] = t.Height(t.MinX + (i + 0.5f) / size * (t.MaxX - t.MinX), t.MinZ + (j + 0.5f) / size * (t.MaxZ - t.MinZ));
            // v6 pişmiş arazide deniz tabanı her yerde −0,6 m'de kesik: yükseklikten sığlık bütün denizi "orta sığ" yapıyordu
            // (açık deniz turkuaz + taban çizgileri kuşbakışında zikzak). Sığlık burada kıyıya uzaklıktan: ~22 m'de derin mavi (taslakta adacığa kadar açık turkuaz).
            float[] dist = t.Baked != null ? CoastDistance(hs, size, (t.MaxX - t.MinX) / size) : null;
            if (dist != null) for (var pass = 0; pass < 3; pass++) dist = Blur(dist, size);   // pah dönüşümü köşeli (sekizgen) sığ kenarı verir
            var px = new Color32[size * size];
            for (var k = 0; k < hs.Length; k++)
            {
                var h = hs[k];
                var shallow = h >= 0f ? 1f : dist != null ? Mathf.Pow(Mathf.Clamp01(1f - dist[k] / 22f), 1.3f) : Mathf.Clamp01(1f + h / 1.4f);
                var foam = h >= 0f ? 1f : Mathf.Pow(Mathf.Clamp01(1f + h / 0.45f), 2f);
                px[k] = new Color32((byte)(shallow * 255), (byte)(foam * 255), 0, 255);
            }
            var tex = new Texture2D(size, size, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, filterMode = FilterMode.Bilinear };
            tex.SetPixels32(px);
            tex.Apply(false, true);
            return tex;
        }

        private static float[] Blur(float[] a, int n)
        {
            var b = new float[a.Length];
            for (var j = 0; j < n; j++)
            for (var i = 0; i < n; i++)
            {
                float sum = 0f; var c = 0;
                for (var dj = -2; dj <= 2; dj++)
                for (var di = -2; di <= 2; di++)
                {
                    int x = i + di, y = j + dj;
                    if (x < 0 || y < 0 || x >= n || y >= n) continue;
                    sum += a[y * n + x]; c++;
                }
                b[j * n + i] = sum / c;
            }
            return b;
        }

        /// <summary>Kara hücrelerine yaklaşık uzaklık (metre; iki geçişli 3-4 pah dönüşümü).</summary>
        private static float[] CoastDistance(float[] hs, int n, float cell)
        {
            var d = new float[n * n];
            const float big = 1e6f, a = 1f, b = 1.4142f;
            for (var k = 0; k < d.Length; k++) d[k] = hs[k] >= 0f ? 0f : big;
            for (var j = 0; j < n; j++)
            for (var i = 0; i < n; i++)
            {
                var k = j * n + i; var v = d[k];
                if (i > 0) v = Mathf.Min(v, d[k - 1] + a);
                if (j > 0) { v = Mathf.Min(v, d[k - n] + a); if (i > 0) v = Mathf.Min(v, d[k - n - 1] + b); if (i < n - 1) v = Mathf.Min(v, d[k - n + 1] + b); }
                d[k] = v;
            }
            for (var j = n - 1; j >= 0; j--)
            for (var i = n - 1; i >= 0; i--)
            {
                var k = j * n + i; var v = d[k];
                if (i < n - 1) v = Mathf.Min(v, d[k + 1] + a);
                if (j < n - 1) { v = Mathf.Min(v, d[k + n] + a); if (i < n - 1) v = Mathf.Min(v, d[k + n + 1] + b); if (i > 0) v = Mathf.Min(v, d[k + n - 1] + b); }
                d[k] = v;
            }
            for (var k = 0; k < d.Length; k++) d[k] *= cell;
            return d;
        }

        // ------------------------------------------------------------------ bölgeler

        /// <summary>Görsel karşılaştırma çekimleri (PofiDebug "showall"): kilitli bölgeler gri boya ve sis olmadan, açık hâliyle kurulur.</summary>
        public static bool DebugShowAll;

        private void BuildRegion(RegionView v)
        {
            var r = v.Region;
            var shown = v.Unlocked || DebugShowAll;
            var root = new GameObject(r.Id).transform;
            root.SetParent(transform, false);
            var baseY = r.Water ? 0f : Terrain.PadHeight(r);
            root.localPosition = new Vector3(r.X, baseY, r.Z);

            if (r.Id == "region_coconut_grove")
            {
                var sizes = new[] { 2.8f, 2.3f, 2.0f };
                var offs = new[] { new Vector2(-1.4f, 0.8f), new Vector2(1.6f, -0.9f), new Vector2(0.3f, 2.1f) };
                for (var i = 0; i < 3; i++)
                {
                    var p = RealAssets.EnvFootprint("palm", root, sizes[i], i * 120f);
                    if (p == null) break;
                    p.localPosition = new Vector3(offs[i].x, -0.1f, offs[i].y);
                }
            }
            else if (r.Id == "region_swim_cove" && Terrain.Baked != null)
            {
                // v6: koy havuzu süs olarak gelir (p_pool); dokunma kutusu için görünmez taban
                new GameObject("pool_pad").transform.SetParent(root, false);
            }
            else if (Terrain.Baked != null && V6Regions.TryGetValue(r.Id, out var v6) && RealAssets.EnvScaled(v6, root, 1f, r.Yaw) != null)
            {
                // v6 (geri bildirim 13, 22 Ekim 2026): taslaktaki mağara (kaya kemeri + tünel), kayak kapısı/bayraklar/kardan adam,
                // zirve taş kulesi; eski minyatür tepe modelleri pişmiş arazinin gerçek dağıyla çakışıyordu
            }
            else if (RegionAssets.TryGetValue(r.Id, out var asset))
            {
                var m = RealAssets.EnvFootprint(asset, root, r.Size, 180f + r.Yaw);   // ham önü +z → güneye dön, sonra bölge açısı
            }
            if (root.childCount == 0) Placeholder(root, r, shown);
            var poolPad = root.Find("pool_pad");
            if (!shown) RealAssets.Tint(root, new Color(0.62f, 0.64f, 0.72f));
            SeasonLook.Mark(root, false);   // kışın çatı karlanır
            // Güneş Taşı ile açılan kilitli bölge: yere yakın, yapıyı saran yoğun sis (kullanıcı, 19 Ekim 2026: gökyüzündeki
            // bulutlar sis gibi okunmuyordu; sis bölgenin üstünde, kamera hizasında olmalı). Taş yerleşince bölge yeniden kurulur, sis kalkar.
            if (!shown && v.Spot != null)
                Fog[r.Id] = Clouds.Spawn(transform, new Vector3(r.X, Terrain.Height(r.X, r.Z) + 0.4f, r.Z), r.Size * 0.42f, 7, 0f, r.Size * 0.25f, r.Size * 0.32f,
                    r.Id.GetHashCode(), 0f, 360f, true);

            var b = poolPad != null ? new Bounds(root.position + Vector3.up * 0.6f, new Vector3(r.Size * 1.2f, 1.2f, r.Size * 1.2f)) : RealAssets.WorldBounds(root);
            if (poolPad != null) Destroy(poolPad.gameObject);
            var col = root.gameObject.AddComponent<BoxCollider>();
            col.center = root.InverseTransformPoint(b.center);
            col.size = new Vector3(Mathf.Max(1f, b.size.x), Mathf.Max(1f, b.size.y), Mathf.Max(1f, b.size.z));
            Regions[r.Id] = root;
            LabelHeights[r.Id] = Mathf.Max(1.5f, b.max.y - root.position.y + 0.3f);
        }

        private void Placeholder(Transform root, RegionDef r, bool unlocked)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.transform.SetParent(root, false);
            go.transform.localScale = new Vector3(r.Size * 0.6f, r.Size * 0.5f, r.Size * 0.6f);
            go.transform.localPosition = new Vector3(0f, r.Size * 0.25f, 0f);
            var m = PetModels.NewMaterial(unlocked && ColorUtility.TryParseHtmlString(r.Color, out var c) ? c : Color.gray, 0.3f);
            _owned.Add(m);
            go.GetComponent<Renderer>().sharedMaterial = m;
            Destroy(go.GetComponent<Collider>());
        }

        private void BuildProps()
        {
            var parent = new GameObject("Props").transform;
            parent.SetParent(transform, false);
            var culler = Terrain.Baked != null ? gameObject.AddComponent<PropCuller>() : null;
            var clear = Terrain.Baked != null ? gameObject.AddComponent<CameraClear>() : null;
            clear?.Init(this);
            foreach (var p in Terrain.Props())
            {
                var cell = culler != null ? culler.Cell(parent, p.X, p.Z) : parent;
                var t = p.Scaled ? RealAssets.EnvScaled(p.Asset, cell, p.Size, p.Yaw) : RealAssets.EnvFootprint(p.Asset, cell, p.Size, p.Yaw);
                if (t == null) continue;
                t.localPosition = new Vector3(p.X, float.IsNaN(p.Y) ? Terrain.Height(p.X, p.Z) : p.Y, p.Z) - cell.localPosition;
                if (clear != null && (p.Asset.StartsWith("t_") || p.Asset == "palm" || (p.Asset.StartsWith("r_boulder") && p.Size > 1.6f))) clear.Add(t);
                SeasonLook.Mark(t, p.Asset.StartsWith("t_round") || p.Asset == "t_birch" || p.Asset == "t_bush");
                if (p.Asset.StartsWith("t_") || p.Asset == "palm")
                    Reactive.Add((new Vector2(p.X, p.Z), Mathf.Max(1.2f, p.Size * 0.45f), Wobble.Add(t, p.Asset == "t_bush" ? Wobble.Kind.Shake : Wobble.Kind.Sway)));
                else if (p.Asset == "p_starfish") Reactive.Add((new Vector2(p.X, p.Z), 1.0f, Wobble.Add(t, Wobble.Kind.Flip)));
                if (p.Asset == "p_crab") { var cf = t.gameObject.AddComponent<CrabFlee>(); cf.Init(this); Crabs.Add((new Vector2(p.X, p.Z), cf)); }
                else if (p.Asset == "p_campfire") Campfire.Light(t, p.Size);
                else if (p.Asset == "p_starfish" || p.Asset == "p_snow_lump") { foreach (var r in t.GetComponentsInChildren<Renderer>()) r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; }
            }
        }

        /// <summary>Karlı patika direkleri arasında hafif sarkık halat (taslaktaki gibi; tek birleşik ağ, gölge yok).</summary>
        private void BuildTrailRopes()
        {
            var lay = Terrain.Baked?.Layout;
            if (lay == null || lay.SnowPath == null || lay.SnowPath.Count < 2) return;
            var verts = new List<Vector3>(); var tris = new List<int>();
            const int seg = 6, ring = 4; const float r = 0.017f;
            foreach (var side in lay.RopeSides())
            for (var i = 0; i + 1 < side.Count; i++)
            {
                var a = side[i]; var b = side[i + 1];
                if (a == null || b == null) continue;
                var pa = new Vector3(a[0], Terrain.Height(a[0], a[1]) + 0.95f, a[1]);
                var pb = new Vector3(b[0], Terrain.Height(b[0], b[1]) + 0.95f, b[1]);
                if ((pb - pa).magnitude > 6f) continue;
                var dir = (pb - pa).normalized;
                var side1 = Vector3.Cross(dir, Vector3.up).normalized; var up1 = Vector3.Cross(side1, dir);
                var b0 = verts.Count;
                for (var k = 0; k <= seg; k++)
                {
                    var t = k / (float)seg;
                    var c = Vector3.Lerp(pa, pb, t) + Vector3.down * 0.15f * 4f * t * (1f - t);   // sarkma
                    for (var q = 0; q < ring; q++)
                    {
                        var ang = q * Mathf.PI * 2f / ring;
                        verts.Add(c + (side1 * Mathf.Cos(ang) + up1 * Mathf.Sin(ang)) * r);
                    }
                }
                for (var k = 0; k < seg; k++)
                for (var q = 0; q < ring; q++)
                {
                    int i0 = b0 + k * ring + q, i1 = b0 + k * ring + (q + 1) % ring;
                    tris.Add(i0); tris.Add(i0 + ring); tris.Add(i1);
                    tris.Add(i1); tris.Add(i0 + ring); tris.Add(i1 + ring);
                }
            }
            if (verts.Count == 0) return;
            var mesh = new Mesh { name = "TrailRopes" };
            mesh.SetVertices(verts); mesh.SetTriangles(tris, 0); mesh.RecalculateNormals(); mesh.RecalculateBounds();
            _owned.Add(mesh);
            var go = new GameObject("TrailRopes");
            go.transform.SetParent(transform, false);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var mr = go.AddComponent<MeshRenderer>();
            var m = PetModels.NewMaterial(new Color(0.79f, 0.65f, 0.42f), 0.1f);
            _owned.Add(m);
            mr.sharedMaterial = m;
            mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        }

        // ------------------------------------------------------------------ pet ve parıltılar

        /// <summary>Peti adaya koyar (kapı ya da verilen noktada).</summary>
        public PetWalker PlacePet(Logic.Data.PetSpeciesDef def, Logic.Progression.GrowthStage stage, IEnumerable<Logic.Data.ItemDef> items, float x, float z)
        {
            var scale = PetModels.StageScale(stage);
            var holder = new GameObject("MapPet").transform;
            holder.SetParent(transform, false);
            var pet = PetModels.Build(def, holder, stage);
            CosmeticModels.Apply(pet, def, items, stage);
            holder.localScale = Vector3.one * scale;
            var col = holder.gameObject.AddComponent<CapsuleCollider>();   // pete dokununca giydirme
            col.center = new Vector3(0f, 0.9f, 0f); col.height = 1.8f; col.radius = 0.6f;
            holder.gameObject.name = "pet";
            Walker = holder.gameObject.AddComponent<PetWalker>();
            Walker.Init(this, pet, x, z);
            gameObject.AddComponent<GrassField>().Init(this);
            Prints = gameObject.AddComponent<Footprints>();
            Prints.Init(this);
            return Walker;
        }

        /// <summary>
        /// Günlük keşif parıltısı (S/M5, 22 Ekim 2026): havada süzülen, yavaş dönen kristal; altında ışık halkası, içinden ışık
        /// hüzmesi. Yeni tür (koleksiyonda yok) altın, bulunmuş tür gümüş. Pet yaklaşınca parlar. Dokunma için "sparkle_N" collider.
        /// </summary>
        public Transform AddSparkle(int index, float x, float z, bool fresh = true)
        {
            var root = new GameObject("sparkle_" + index).transform;
            root.SetParent(transform, false);
            var ground = Terrain.Height(x, z);
            root.localPosition = new Vector3(x, ground + 1.1f, z);
            var color = fresh ? new Color(1f, 0.82f, 0.22f) : new Color(0.82f, 0.88f, 0.98f);
            var mat = PetModels.NewMaterial(color, 0.95f);
            mat.SetFloat("_Rim", 2.4f);
            _owned.Add(mat);
            var crystal = new GameObject("Crystal").transform;
            crystal.SetParent(root, false);
            crystal.gameObject.AddComponent<MeshFilter>().sharedMesh = GainFx.GemMesh;
            var mr = crystal.gameObject.AddComponent<MeshRenderer>();
            mr.sharedMaterial = mat; mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            crystal.localScale = Vector3.one * 2.1f;
            var halo = GainFx.Glow(root, color, 0.9f, false); halo.localScale = Vector3.one * 1.9f;
            var beam = GainFx.Glow(root, color, 0.45f, false); beam.localScale = new Vector3(0.7f, 4.2f, 1f); beam.localPosition = Vector3.up * 0.6f;
            var ring = GainFx.Glow(root, color, 0.8f, true); ring.localPosition = Vector3.down * 1.05f; ring.localRotation = Quaternion.Euler(90f, 0f, 0f); ring.localScale = Vector3.one * 2.2f;
            var col = root.gameObject.AddComponent<SphereCollider>();
            col.radius = 1.0f;
            root.gameObject.AddComponent<SparkleFloat>().Init(crystal, halo, ring);
            return root;
        }

        private void OnDestroy()
        {
            foreach (var o in _owned) if (o != null) Destroy(o);
        }
    }

    /// <summary>
    /// Adada yürüyen pet: ara noktalar boyunca yürür (uzaksa koşar), zemine oturur, yönünü çevirir; varınca
    /// "idle"a döner ve <see cref="Arrived"/> çağrılır.
    /// </summary>
    public sealed class PetWalker : MonoBehaviour
    {
        public const float WalkSpeed = 2.6f, RunSpeed = 5.2f;
        public System.Action Arrived;
        public bool Moving => _route.Count > 0;
        public bool Steering => _steering;
        /// <summary>Petin baktığı yön (derece; 0 = +z).</summary>
        public float Heading => _yaw;
        public Vector2 Position => new Vector2(_x, _z);

        private MapWorld _world;
        private Transform _pet;
        private readonly List<Vector2> _route = new List<Vector2>();
        private float _x, _z, _yaw, _speed, _jump;
        private Vector2 _direct;
        private bool _steering;
        private string _clip;

        /// <summary>Ek engeller (kütük, taş, kulübe): joystickle yürürken içinden geçilmez.</summary>
        public System.Func<float, float, bool> Blocked;
        private float _swing;

        private bool Free(float x, float z) => _world.Terrain.Walkable(x, z) && (Blocked == null || !Blocked(x, z));

        /// <summary>Hedefe dön (aksiyondan önce).</summary>
        public void Face(float x, float z)
        {
            _route.Clear(); Arrived = null; _direct = Vector2.zero;
            _yaw = Mathf.Atan2(x - _x, z - _z) * Mathf.Rad2Deg;
            Play("idle");
            Apply();
        }

        /// <summary>Aksiyon hareketi (balta/kazma vuruşu): kısa ileri-geri eğilme.</summary>
        public void Swing() { _swing = 1f; }

        /// <summary>Joystick: dünya düzleminde yön (uzunluk 0..1). Sıfır verilince durur.</summary>
        public void Steer(Vector2 dir)
        {
            if (dir.sqrMagnitude > 0.0004f) { _route.Clear(); Arrived = null; }
            _direct = Vector2.ClampMagnitude(dir, 1f);
        }

        /// <summary>Zıpla: sevinç animasyonu + küçük sıçrama (yürürken de olur).</summary>
        public void Jump()
        {
            if (_jump > 0f) return;
            Cheer();
            Audio.Sfx.Play(Audio.SfxKind.Tap);
        }

        /// <summary>Zafer hareketi (kazanınca): sevinç klibi (kollar havada) + sıçrama; ses kazanımın kendisinden gelir.</summary>
        public void Cheer()
        {
            if (_jump > 0f) return;
            _jump = 1f;
            if (RealAssets.Play(_pet, "happy")) _clip = null;
        }

        // A1 Okti'nin tepki dili (23 Ekim 2026): dokununca sıradaki tepki (Logic.Story.OktiReactions), art arda aynısı gelmez
        private float _hold, _wiggle, _clap;
        private Vector3 _baseScale = Vector3.one;   // evre boyu (PlacePet tutucunun ölçeğini verir)

        /// <summary>Dokunuş tepkisi: jump, wave, tickle, clap, ink_heart. Yürürken de olur, yürüyüşü durdurmaz.</summary>
        public void React(string kind)
        {
            if (_jump > 0f || _hold > 0f) return;
            switch (kind)
            {
                case Logic.Story.OktiReactions.Wave:
                    if (!PlayFor("wave", 1.6f)) Cheer();
                    Audio.Sfx.Play(Audio.SfxKind.Chime);
                    break;
                case Logic.Story.OktiReactions.Tickle:
                    _wiggle = 1f; PlayFor("happy", 0.9f);
                    Audio.Sfx.Play(Audio.SfxKind.Pop);
                    break;
                case Logic.Story.OktiReactions.Clap:
                    _clap = 1f; PlayFor("happy", 1.0f);
                    Audio.Sfx.Play(Audio.SfxKind.Tap);
                    break;
                case Logic.Story.OktiReactions.InkHeart:
                    PlayFor("happy", 1.0f);
                    InkHeart.Spawn(transform, 1.9f * _baseScale.y);
                    Audio.Sfx.Play(Audio.SfxKind.Sparkle);
                    break;
                default:
                    Jump();
                    break;
            }
            Audio.Haptics.Light();
        }

        private bool PlayFor(string clip, float seconds)
        {
            if (!RealAssets.Play(_pet, clip, false)) return false;
            _clip = clip; _hold = seconds;
            return true;
        }

        public void Init(MapWorld world, Transform pet, float x, float z)
        {
            _world = world; _pet = pet; _baseScale = transform.localScale;
            Teleport(x, z, 180f);
        }

        public void Teleport(float x, float z, float yaw)
        {
            _route.Clear();
            _x = x; _z = z; _yaw = yaw;
            Apply();
            Play("idle");
        }

        /// <summary>Hedefe yol bulur ve yürür. Yol yoksa false.</summary>
        public bool WalkTo(float x, float z, System.Action arrived = null)
        {
            var path = _world.Terrain.FindPath(_x, _z, x, z);
            _route.Clear();
            Arrived = arrived;
            if (path.Count == 0) return false;
            foreach (var p in path) _route.Add(new Vector2(p.x, p.z));
            var total = 0f; var from = Position;
            foreach (var p in _route) { total += Vector2.Distance(from, p); from = p; }
            _speed = total > 14f ? RunSpeed : WalkSpeed;
            Play(_speed > WalkSpeed ? "run" : "walk", "walk");
            return true;
        }

        public void Stop()
        {
            _route.Clear();
            Arrived = null;
            Play("idle");
        }

        private void Update()
        {
            if (_jump > 0f) { _jump = Mathf.Max(0f, _jump - Time.deltaTime / 0.75f); Apply(); }
            if (_swing > 0f) { _swing = Mathf.Max(0f, _swing - Time.deltaTime / 0.35f); Apply(); }
            if (_wiggle > 0f) { _wiggle = Mathf.Max(0f, _wiggle - Time.deltaTime / 0.8f); Apply(); }
            if (_clap > 0f) { _clap = Mathf.Max(0f, _clap - Time.deltaTime / 0.9f); Apply(); }
            if (_hold > 0f && (_hold -= Time.deltaTime) <= 0f)
            {
                _hold = 0f;
                if (_direct.sqrMagnitude <= 0.0004f && _route.Count == 0) { _clip = null; Play("idle"); }
                else _clip = null;   // yürüyorsa bir sonraki karede yürüme klibi yeniden seçilir
            }
            if (_direct.sqrMagnitude > 0.0004f)
            {
                _steering = true;
                var sp = Mathf.Lerp(WalkSpeed * 0.6f, RunSpeed, _direct.magnitude);
                var nx = _x + _direct.x * sp * Time.deltaTime; var nz = _z + _direct.y * sp * Time.deltaTime;
                var moved = true;
                if (Free(nx, nz)) { _x = nx; _z = nz; }
                else if (Free(nx, _z)) _x = nx;          // engelde kayarak ilerle
                else if (Free(_x, nz)) _z = nz;
                else moved = false;
                var want = Mathf.Atan2(_direct.x, _direct.y) * Mathf.Rad2Deg;
                _yaw = Mathf.MoveTowardsAngle(_yaw, want, 480f * Time.deltaTime);   // doğal dönüş (ani savrulma yok)
                // kıyıya/duvara dayanınca yerinde koşmasın: durur
                if (moved) Play(_direct.magnitude > 0.7f ? "run" : "walk", "walk"); else Play("idle");
                Apply();
                Footsteps();
                return;
            }
            if (_steering) { _steering = false; if (_route.Count == 0) Play("idle"); }
            if (_route.Count == 0) return;
            var target = _route[0];
            var pos = Position;
            var to = target - pos;
            var step = _speed * Time.deltaTime;
            if (to.magnitude <= step)
            {
                _x = target.x; _z = target.y;
                _route.RemoveAt(0);
                if (_route.Count == 0)
                {
                    Apply();
                    Play("idle");
                    var a = Arrived; Arrived = null;
                    a?.Invoke();
                    return;
                }
            }
            else
            {
                var dir = to.normalized;
                _x += dir.x * step; _z += dir.y * step;
                var want = Mathf.Atan2(dir.x, dir.y) * Mathf.Rad2Deg;
                _yaw = Mathf.MoveTowardsAngle(_yaw, want, 540f * Time.deltaTime);
            }
            Apply();
            Footsteps();
        }

        // ------------------------------------------------------------------ adım sesleri
        // Meshy yürüme/koşu kliplerinde ayağın yere değdiği anlar (döngü içinde 0..1; art/scripts ölçümü, ayak kemiği en alçakta):
        // yürüme 2–27. kare: sol 0.22, sağ 0.72 · koşu 2–17. kare: sol 0.40, sağ 0.90. Ses klibin kendi zamanına bağlı: hız değişse de senkron.
        private static readonly float[] WalkContacts = { 0.22f, 0.72f }, RunContacts = { 0.40f, 0.90f };
        // Okti evreleri (Meshy web "All Animations", prepare_stages.py ölçümü): model başına sol/sağ temas
        private static readonly Dictionary<string, float[][]> ModelContacts = new Dictionary<string, float[][]>
        {
            { "pet_13_yavru", new[] { new[] { 0.29f, 0.83f }, new[] { 0.40f, 0.93f } } },   // kıyafetsiz çocuk (23 Ekim 2026)
            { "pet_13_genc", new[] { new[] { 0.40f, 0.92f }, new[] { 0.38f, 0.88f } } },
            { "pet_13_yetiskin", new[] { new[] { 0.20f, 0.64f }, new[] { 0.01f, 0.44f } } },
        };

        private float[] Contacts(string clip)
        {
            var model = _pet != null ? _pet.name.Replace("_real", "") : "";
            if (ModelContacts.TryGetValue(model, out var c)) return clip == "run" ? c[1] : c[0];
            return clip == "run" ? RunContacts : WalkContacts;
        }

        private float _lastPhase = -1f;
        private string _phaseClip;

        private void Footsteps()
        {
            var clip = _clip == "run" || _clip == "walk" ? _clip : null;
            var ph = clip == null || _jump > 0f ? -1f : RealAssets.Phase(_pet, clip);
            if (ph < 0f && clip == "run") { clip = "walk"; ph = RealAssets.Phase(_pet, clip); }   // koşu klibi yoksa yürüme oynar
            if (ph < 0f || clip != _phaseClip) { _lastPhase = ph; _phaseClip = clip; return; }
            var contacts = Contacts(clip);
            foreach (var c in contacts)
                if (Crossed(_lastPhase, ph, c)) { Audio.Sfx.Step(clip == "run"); _world.Prints?.Step(_x, _z, _yaw, c == contacts[0]); break; }
            _lastPhase = ph;
        }

        private static bool Crossed(float from, float to, float t) => from <= to ? from < t && to >= t : from < t || to >= t;

        private void Apply()
        {
            var hop = _jump > 0f ? Mathf.Sin((1f - _jump) * Mathf.PI) * 0.9f : 0f;
            transform.localPosition = new Vector3(_x, _world.Terrain.Height(_x, _z) + hop, _z);
            // gerçek pet modeli kameraya dönük (180°) kurulu; yürüme yönüne bakması için ön = +z kabul edilir
            var lean = _swing > 0f ? Mathf.Sin((1f - _swing) * Mathf.PI * 2f) * 12f : 0f;
            // gıdıklanma: sağa sola hızlı kıvrılma; alkış: üç kısa ezilip uzama (vantuzlar birbirine değer gibi)
            var roll = _wiggle > 0f ? Mathf.Sin((1f - _wiggle) * Mathf.PI * 9f) * 9f * _wiggle : 0f;
            transform.localRotation = Quaternion.Euler(0f, _yaw + 180f, 0f) * Quaternion.Euler(lean, 0f, roll);
            var sq = _clap > 0f ? Mathf.Abs(Mathf.Sin((1f - _clap) * Mathf.PI * 3f)) * 0.12f * _clap : 0f;
            transform.localScale = Vector3.Scale(_baseScale, new Vector3(1f + sq * 0.6f, 1f - sq, 1f + sq * 0.6f));
        }

        private void Play(string clip, string fallback = null)
        {
            if (_clip == clip) return;
            if (RealAssets.Play(_pet, clip, false) || (fallback != null && RealAssets.Play(_pet, fallback, false))) _clip = clip;
        }
    }

    /// <summary>Parıltının canlılığı: süzülür, döner, hâle nefes alır, halka yavaşça döner; pet yaklaşınca parlar.</summary>
    public sealed class SparkleFloat : MonoBehaviour
    {
        private Transform _crystal, _halo, _ring;
        private Vector3 _base, _haloS, _ringS;
        private float _phase, _near, _open = -1f;

        public void Init(Transform crystal, Transform halo, Transform ring)
        {
            _crystal = crystal; _halo = halo; _ring = ring;
            _base = transform.localPosition; _haloS = halo.localScale; _ringS = ring.localScale;
            _phase = Random.value * 6f;
        }

        /// <summary>0..1: pet ne kadar yakın (parlaklık).</summary>
        public float Near { set { _near = Mathf.Clamp01(value); } }

        /// <summary>Açılma: kristal hızla döner, büyür ve söner; sonra nesne silinir.</summary>
        public void Open() { if (_open < 0f) { _open = 0f; var c = GetComponent<Collider>(); if (c != null) c.enabled = false; } }

        private void Update()
        {
            var t = Time.time + _phase;
            if (_open >= 0f)
            {
                _open += Time.deltaTime / 0.45f;
                var k = Mathf.Clamp01(_open);
                _crystal.Rotate(0f, 1400f * Time.deltaTime, 0f, Space.Self);
                _crystal.localScale = Vector3.one * 2.1f * (1f + k * 0.8f) * (1f - k * k);
                _halo.localScale = _haloS * (1f + k * 2.2f) * (1f - k);
                _ring.localScale = _ringS * (1f + k * 1.6f) * (1f - k);
                if (k >= 1f) Destroy(gameObject);
                return;
            }
            transform.localPosition = _base + Vector3.up * Mathf.Sin(t * 1.9f) * 0.15f;
            _crystal.Rotate(0f, (55f + _near * 120f) * Time.deltaTime, 0f, Space.Self);
            var breath = 1f + Mathf.Sin(t * 2.6f) * 0.08f + _near * 0.35f;
            _halo.localScale = _haloS * breath;
            _ring.localScale = _ringS * (1f + Mathf.Sin(t * 1.3f) * 0.06f + _near * 0.2f);
            _ring.localPosition = Vector3.down * (1.05f + Mathf.Sin(t * 1.9f) * 0.15f);   // halka zeminde kalır (kök süzülse de)
            _ring.Rotate(0f, 0f, 20f * Time.deltaTime, Space.Self);
        }
    }
}
