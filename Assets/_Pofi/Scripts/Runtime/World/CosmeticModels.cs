using System.Collections.Generic;
using Pofi.Logic.Cosmetics;
using Pofi.Logic.Data;
using Pofi.Logic.Progression;
using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// Giyilebilir eşyaların yer tutucu modelleri. Petin soketlerine (socket_head, socket_eyes, socket_body,
    /// socket_back, socket_hand_L/R) takılır; uyum varyantı (ör. "raised", "mane_fit", "on_shell") konumu ayarlar.
    /// Gerçek eşya modelleri gelince aynı soket/varyant sözleşmesiyle değiştirilecek.
    /// </summary>
    public static class CosmeticModels
    {
        public const string RootName = "cosmetics";
        private static string _petId;
        private static GrowthStage _stage = GrowthStage.Genc;

        private static readonly Dictionary<string, string> Colors = new Dictionary<string, string>
        {
            ["glasses_round"] = "#3B2A20", ["glasses_sun"] = "#1B1B24", ["glasses_star"] = "#FFC400",
            ["shirt_stripes"] = "#3D7BFF", ["shirt_hawaii"] = "#FF5A7A", ["apron_sailor"] = "#F4F8FF", ["hoodie_soft"] = "#9B7BFF",
            ["vest_explorer"] = "#8A6A3A", ["raincoat"] = "#FFD23F",
            ["hat_cap"] = "#E8453C", ["hat_straw"] = "#F2D27A", ["hat_beanie"] = "#2FB59A", ["hat_crown"] = "#FFC400", ["headphones"] = "#30304A",
            ["scarf_knit"] = "#E8453C", ["backpack_small"] = "#2F80ED", ["cape_hero"] = "#D6336C", ["badge_patch"] = "#FFC400",
            ["sash_belt"] = "#7A3B00", ["glove_mitten"] = "#FF8A2A", ["hand_flag"] = "#2FB59A",
            ["set_captain"] = "#1F3A93", ["set_captain_hat"] = "#F4F8FF", ["set_star_cape"] = "#5B5BD6",
        };

        public static Color ColorOf(string itemId) =>
            Colors.TryGetValue(itemId, out var h) && ColorUtility.TryParseHtmlString(h, out var c) ? c : new Color(0.9f, 0.5f, 0.2f);

        /// <summary>Petteki tüm eşyaları kaldırıp verilenleri takar. Uymayan eşya atlanır.</summary>
        public static void Apply(Transform pet, PetSpeciesDef def, IEnumerable<ItemDef> items, GrowthStage stage = GrowthStage.Genc)
        {
            var old = pet.Find(RootName);
            if (old != null)
            {
                foreach (var r in old.GetComponentsInChildren<Renderer>())
                    foreach (var m in r.sharedMaterials) if (m != null && !RealAssets.IsShared(m)) Object.Destroy(m);
                Object.Destroy(old.gameObject);
            }
            foreach (var tag in pet.GetComponentsInChildren<RealCosmetic>(true)) Object.Destroy(tag.gameObject);   // kemiklere takılı gerçek eşyalar
            var root = new GameObject(RootName).transform;
            root.SetParent(pet, false);
            if (items == null) items = System.Array.Empty<ItemDef>();   // eşyasız da temel giysi giyilir
            _petId = def?.Id; _stage = stage;
            // yerleşim dinlenme duruşunda (kurallar bu duruşta ölçüldü); bitince o anki animasyon duruşu geri gelir
            var rest = pet.GetComponentInChildren<RestPose>();
            var hold = rest != null ? rest.Hold() : default;
            try
            {
                Capture(pet, root);
                var list = new List<ItemDef>();
                foreach (var item in items) if (item != null) list.Add(item);
                BuildBase(pet, root, list);
                foreach (var item in list)
                {
                    if (item == null) continue;
                    var fit = CosmeticFit.Evaluate(def, item);
                    if (!fit.Allowed) continue;
                    Build(pet, root, item, fit.Variant ?? "normal");
                }
            }
            finally { hold.Dispose(); }
            foreach (var c in root.GetComponentsInChildren<Collider>()) Object.Destroy(c);
        }

        // ---- temel giysi (kullanıcı, 23 Ekim 2026: "karakter kıyafetsiz kalmasın"): Okti hep sarı tişört + mercan şortla görünür.
        // Başka bir üst (giysi kategorisinde gövde eşyası) tişörtün yerine geçer, çıkarınca tişört geri gelir; altı da kaplayan
        // kostümler şortun yerine geçer. Envanterde değil, dolapta çıkarılamaz; her evrede o evrenin bedenine göre oturur.
        private static readonly ItemDef BaseTop = new ItemDef { Id = "base_top", Name = "Temel tişört", Category = ItemCategory.Clothes, Slot = "body", Cut = "full" };
        private static readonly ItemDef BaseBottom = new ItemDef { Id = "base_bottom", Name = "Temel şort", Category = ItemCategory.Clothes, Slot = "hips" };
        /// <summary>Altı da kaplayan eşyalar (çim etek, hamburger, tavuk kostümü): şort giyilmez.</summary>
        private static readonly HashSet<string> CoversBottom = new HashSet<string> { "outfit_hula", "outfit_burger", "outfit_chicken" };

        private static void BuildBase(Transform pet, Transform root, List<ItemDef> items)
        {
            if (_petId != "pet_13") return;
            var top = true; var bottom = true;
            foreach (var i in items)
            {
                if (i.Slot == Slot.Body && i.Category == ItemCategory.Clothes) top = false;
                if (CoversBottom.Contains(i.Id)) bottom = false;
            }
            // önce vücuttan kesilmiş, vücutla esneyen giysi (24 Ekim 2026); evrede yoksa eski katı model
            if (top && !BuildSkinWear(pet, "base_top")) BuildReal(pet, root, BaseTop, "normal", _petId);
            if (bottom && !BuildSkinWear(pet, "base_bottom")) BuildReal(pet, root, BaseBottom, "normal", _petId);
        }

        // ---- vücuttan kesilmiş temel giysi (kullanıcı, 24 Ekim 2026: "ilk kıyafetler karakterin vücuduna optimal oturmuyor").
        // art/meshy/scripts/base_wear.py her evre için Pets/<evre>/<evre>_wear.fbx yazar: tişört ve şort vücut ağının o bölgesinden
        // kesilip biraz dışarı itilmiş, kalınlık verilmiş kabuklardır; ağırlıkları vücuttan gelir. Burada vücudun kemiklerine
        // bağlanır (kemik sırası vücudunkine çevrilir, bağlanma duruşu vücudunki) → yürürken, dans ederken kumaş vücutla esner.
        private static readonly Dictionary<string, Mesh> WearMeshes = new Dictionary<string, Mesh>();

        private static bool BuildSkinWear(Transform pet, string part)
        {
            var model = RealAssets.StageModel(_petId, _stage);
            SkinnedMeshRenderer body = null;
            foreach (var r in pet.GetComponentsInChildren<SkinnedMeshRenderer>())
                if (r.GetComponentInParent<RealCosmetic>() == null && r.sharedMesh != null && (body == null || r.sharedMesh.vertexCount > body.sharedMesh.vertexCount)) body = r;
            if (body == null || body.bones == null || body.bones.Length == 0) return false;
            var key = model + "/" + part;
            if (!WearMeshes.TryGetValue(key, out var mesh))
            {
                mesh = WearMesh(model, part, body);
                WearMeshes[key] = mesh;
            }
            if (mesh == null) return false;
            var go = new GameObject(part);
            go.AddComponent<RealCosmetic>();
            var t = go.transform;
            t.SetParent(body.transform.parent, false);
            t.localPosition = body.transform.localPosition; t.localRotation = body.transform.localRotation; t.localScale = body.transform.localScale;
            go.layer = body.gameObject.layer;
            var smr = go.AddComponent<SkinnedMeshRenderer>();
            smr.sharedMesh = mesh;
            smr.bones = body.bones;
            smr.rootBone = body.rootBone;
            smr.updateWhenOffscreen = true;
            smr.shadowCastingMode = body.shadowCastingMode;
            smr.sharedMaterial = RealAssets.SharedMaterial("Items/" + part + "/shell", 0.15f);
            return true;
        }

        // ---- gövde giysisi deri olur (kıyafet × hareket denemesi, kullanıcı 24 Ekim 2026: "kıyafetlerin oturmasını farklı
        // hareketlerde de dene"). Tek gövde kemiğine sert bağlı tişört, kapüşonlu, yağmurluk, kostüm; kollar kalkınca, kalça dönünce
        // vücuda giriyordu (genç evre el sallamada boyun %9'u, koşuda tavuk kostümü %16). Dinlenme duruşunda yerleşmiş eşyanın her
        // köşesi en yakın 4 vücut köşesinin kemik ağırlıklarını uzaklığa göre harmanlayıp alır; vücudun kemikleriyle bükülür
        // (temel giysi BuildSkinWear ile aynı kemik sırası ve bağlanma duruşu). Ölçü ve önce/sonra: art/meshy/scripts/anim_fit_test.py.
        // Yalnız vücuda yakın giysiler: kabarık kostümlerde (tavuk, hamburger, çim etek, simit) vücuttan uzak kabuk bacak ve kalça
        // ağırlıkları arasında gerilip yırtılmış gibi görünüyordu (Blender önce/sonra paftası) → onlar kemiğe sert bağlı kalır.
        private static readonly HashSet<string> SkinItems = new HashSet<string>
            { "shirt_stripes", "shirt_hawaii", "apron_sailor", "hoodie_soft", "vest_explorer", "raincoat", "set_captain", "scarf_knit", "sash_belt" };
        private static readonly Dictionary<string, Mesh[]> SkinMeshes = new Dictionary<string, Mesh[]>();

        private static SkinnedMeshRenderer BodyOf(Transform pet)
        {
            SkinnedMeshRenderer body = null;
            foreach (var r in pet.GetComponentsInChildren<SkinnedMeshRenderer>())
                if (r.GetComponentInParent<RealCosmetic>() == null && r.sharedMesh != null && (body == null || r.sharedMesh.vertexCount > body.sharedMesh.vertexCount)) body = r;
            return body != null && body.bones != null && body.bones.Length > 0 && body.sharedMesh.isReadable && body.sharedMesh.bindposes.Length == body.bones.Length ? body : null;
        }

        /// <summary>Yerleşmiş eşyayı (dinlenme duruşunda) vücuda deri olarak bağlar; eşya kökü silinir. Olmazsa false (eşya dokunulmaz).</summary>
        private static bool SkinToBody(Transform pet, Transform t, string key)
        {
            var body = BodyOf(pet);
            if (body == null) return false;
            var filters = t.GetComponentsInChildren<MeshFilter>();
            if (filters.Length == 0) return false;
            foreach (var f in filters) if (f.sharedMesh == null || !f.sharedMesh.isReadable || f.GetComponent<MeshRenderer>() == null) return false;
            key = key + "/" + body.sharedMesh.GetInstanceID();
            if (!SkinMeshes.TryGetValue(key, out var meshes))
            {
                var grid = BodyGrid.For(body);
                if (grid == null) return false;
                var toBody = body.transform.worldToLocalMatrix;
                meshes = new Mesh[filters.Length];
                for (var i = 0; i < filters.Length; i++) meshes[i] = SkinMesh(filters[i], toBody * filters[i].transform.localToWorldMatrix, grid, body.sharedMesh.bindposes);
                SkinMeshes[key] = meshes;
            }
            for (var i = 0; i < filters.Length; i++)
            {
                var mr = filters[i].GetComponent<MeshRenderer>();
                var go = new GameObject(filters[i].name + "_skin");
                go.AddComponent<RealCosmetic>();
                go.layer = body.gameObject.layer;
                var tr = go.transform;
                tr.SetParent(body.transform.parent, false);
                tr.localPosition = body.transform.localPosition; tr.localRotation = body.transform.localRotation; tr.localScale = body.transform.localScale;
                var smr = go.AddComponent<SkinnedMeshRenderer>();
                smr.sharedMesh = meshes[i];
                smr.bones = body.bones;
                smr.rootBone = body.rootBone;
                smr.updateWhenOffscreen = true;
                smr.shadowCastingMode = mr.shadowCastingMode;
                smr.sharedMaterials = mr.sharedMaterials;
            }
            t.gameObject.SetActive(false);
            Object.Destroy(t.gameObject);
            return true;
        }

        private static Mesh SkinMesh(MeshFilter f, Matrix4x4 toBody, BodyGrid grid, Matrix4x4[] bindposes)
        {
            var src = f.sharedMesh;
            var v = src.vertices; var n = src.normals; var tg = src.tangents;
            var bw = new BoneWeight[v.Length];
            for (var i = 0; i < v.Length; i++)
            {
                v[i] = toBody.MultiplyPoint3x4(v[i]);
                if (i < n.Length) n[i] = toBody.MultiplyVector(n[i]).normalized;
                if (i < tg.Length) { var d = toBody.MultiplyVector(new Vector3(tg[i].x, tg[i].y, tg[i].z)).normalized; tg[i] = new Vector4(d.x, d.y, d.z, tg[i].w); }
                bw[i] = grid.Weights(v[i], grid.Sleeve(v[i]));
            }
            var m = new Mesh { name = src.name + "_skin", indexFormat = src.indexFormat };
            m.vertices = v;
            if (n.Length == v.Length) m.normals = n;
            if (tg.Length == v.Length) m.tangents = tg;
            m.uv = src.uv;
            m.subMeshCount = src.subMeshCount;
            for (var s = 0; s < src.subMeshCount; s++) m.SetTriangles(src.GetTriangles(s), s);
            m.boneWeights = bw;
            m.bindposes = bindposes;
            m.RecalculateBounds();
            return m;
        }

        /// <summary>
        /// Vücut ağı köşeleri için kaba ızgara: bir noktaya en yakın 4 köşenin kemik ağırlıkları (uzaklığın karesiyle ters orantılı).
        /// Kol/yen bölgesi (koltuk altı hizasının üstü ve omuzdan dışarı) dışındaki giysi köşeleri yalnız gövde köşelerinden alır:
        /// dinlenme duruşunda gövdenin yanında sarkan kol yeleğin yanını çekiyor, zıplarken etek gibi açıyordu. Bacak payı kalçaya
        /// geçer (üst giysi bacakla gerilmez). Aynı kural Blender denemesinde: art/meshy/scripts/anim_fit_test.py skin_to_body.
        /// </summary>
        private sealed class BodyGrid
        {
            private static readonly Dictionary<int, BodyGrid> Cache = new Dictionary<int, BodyGrid>();
            private static readonly HashSet<string> Torso = new HashSet<string> { "Hips", "Spine", "Spine1", "Spine2", "Neck", "Head", "LeftShoulder", "RightShoulder" };
            private readonly Vector3[] _v; private readonly BoneWeight[] _w;
            private readonly Cells _all, _torso;
            private readonly Vector3 _mid, _side, _up; private readonly float _half, _pit, _h;
            private readonly int[] _best = new int[4]; private readonly float[] _bestD = new float[4];
            private readonly Dictionary<int, float> _acc = new Dictionary<int, float>();

            public static BodyGrid For(SkinnedMeshRenderer body)
            {
                var mesh = body.sharedMesh;
                var id = mesh.GetInstanceID();
                if (Cache.TryGetValue(id, out var g)) return g;
                var w = mesh.boneWeights;
                if (w == null || w.Length != mesh.vertexCount) return null;
                Transform la = null, ra = null; var hips = -1;
                var leg = new bool[body.bones.Length]; var torso = new bool[body.bones.Length];
                for (var i = 0; i < body.bones.Length; i++)
                {
                    var b = body.bones[i];
                    if (b == null) continue;
                    var n = b.name.Substring(b.name.LastIndexOf(':') + 1);
                    if (n == "Hips") hips = i;
                    if (n == "LeftArm") la = b; else if (n == "RightArm") ra = b;
                    leg[i] = n.Contains("UpLeg") || n.Contains("Leg") || n.Contains("Foot") || n.Contains("Toe");
                    torso[i] = Torso.Contains(n);
                }
                if (la == null || ra == null || hips < 0) return null;
                g = new BodyGrid(body, mesh.vertices, w, leg, torso, hips, la, ra);
                Cache[id] = g;
                return g;
            }

            private BodyGrid(SkinnedMeshRenderer body, Vector3[] v, BoneWeight[] w, bool[] leg, bool[] torso, int hips, Transform la, Transform ra)
            {
                _v = v; _w = new BoneWeight[w.Length];
                var cell = Mathf.Max(1e-4f, body.sharedMesh.bounds.size.magnitude / 48f);
                _all = new Cells(cell); _torso = new Cells(cell);
                for (var i = 0; i < w.Length; i++)
                {
                    var b = w[i];
                    // bacak → kalça
                    if (leg[b.boneIndex0]) b.boneIndex0 = hips;
                    if (leg[b.boneIndex1]) b.boneIndex1 = hips;
                    if (leg[b.boneIndex2]) b.boneIndex2 = hips;
                    if (leg[b.boneIndex3]) b.boneIndex3 = hips;
                    _w[i] = b;
                    _all.Add(v[i], i);
                    var dom = b.boneIndex0; var dw = b.weight0;   // en ağır kemik (aynı kemik birden çok yuvada olabilir)
                    if (b.weight1 > dw) { dom = b.boneIndex1; dw = b.weight1; }
                    if (b.weight2 > dw) { dom = b.boneIndex2; dw = b.weight2; }
                    if (b.weight3 > dw) dom = b.boneIndex3;
                    if (torso[dom]) _torso.Add(v[i], i);
                }
                // dinlenme duruşunda (RestPose.Hold) omuz eklemleri vücut ağı uzayında
                var t = body.transform;
                var l = t.InverseTransformPoint(la.position); var r = t.InverseTransformPoint(ra.position);
                _up = t.InverseTransformDirection(Vector3.up).normalized;
                _mid = (l + r) * 0.5f; _side = (r - l).normalized; _half = (r - l).magnitude * 0.5f;
                _pit = Mathf.Min(Vector3.Dot(l, _up), Vector3.Dot(r, _up));
                _h = Mathf.Abs(Vector3.Dot(body.sharedMesh.bounds.size, _up));
            }

            /// <summary>Kol/yen bölgesi mi (koltuk altı hizasının biraz altına kadar ve omuzdan dışarı)?</summary>
            public bool Sleeve(Vector3 p) => Mathf.Abs(Vector3.Dot(p - _mid, _side)) > _half * 0.85f && Vector3.Dot(p, _up) > _pit - 0.025f * _h;

            public BoneWeight Weights(Vector3 p, bool sleeve)
            {
                var cells = sleeve ? _all : _torso;
                for (var i = 0; i < 4; i++) { _best[i] = -1; _bestD[i] = float.MaxValue; }
                cells.Nearest(p, _v, _best, _bestD);
                _acc.Clear();
                for (var k = 0; k < 4; k++)
                {
                    if (_best[k] < 0) continue;
                    var iw = 1f / (_bestD[k] + 1e-8f);
                    var b = _w[_best[k]];
                    Add(b.boneIndex0, b.weight0 * iw); Add(b.boneIndex1, b.weight1 * iw); Add(b.boneIndex2, b.weight2 * iw); Add(b.boneIndex3, b.weight3 * iw);
                }
                var res = new BoneWeight();
                float sum = 0f;
                for (var slot = 0; slot < 4 && _acc.Count > 0; slot++)
                {
                    var bi = -1; var bv = 0f;
                    foreach (var kv in _acc) if (kv.Value > bv) { bi = kv.Key; bv = kv.Value; }
                    if (bi < 0) break;
                    _acc.Remove(bi);
                    switch (slot)
                    {
                        case 0: res.boneIndex0 = bi; res.weight0 = bv; break;
                        case 1: res.boneIndex1 = bi; res.weight1 = bv; break;
                        case 2: res.boneIndex2 = bi; res.weight2 = bv; break;
                        default: res.boneIndex3 = bi; res.weight3 = bv; break;
                    }
                    sum += bv;
                }
                if (sum <= 0f) { res.boneIndex0 = 0; res.weight0 = 1f; return res; }
                res.weight0 /= sum; res.weight1 /= sum; res.weight2 /= sum; res.weight3 /= sum;
                return res;
            }

            private void Add(int bone, float w)
            {
                if (w <= 0f) return;
                _acc.TryGetValue(bone, out var a);
                _acc[bone] = a + w;
            }

            /// <summary>Köşe alt kümesinin hücre ızgarası; en yakın 4 köşeyi kabuk kabuk arar.</summary>
            private sealed class Cells
            {
                private readonly Dictionary<long, List<int>> _cells = new Dictionary<long, List<int>>();
                private readonly float _cell;
                public Cells(float cell) { _cell = cell; }
                private int C(float x) => Mathf.FloorToInt(x / _cell);
                private static long Key(int x, int y, int z) => ((long)(x & 0x1FFFFF) << 42) | ((long)(y & 0x1FFFFF) << 21) | (long)(z & 0x1FFFFF);

                public void Add(Vector3 p, int i)
                {
                    var k = Key(C(p.x), C(p.y), C(p.z));
                    if (!_cells.TryGetValue(k, out var l)) _cells[k] = l = new List<int>();
                    l.Add(i);
                }

                public void Nearest(Vector3 p, Vector3[] v, int[] best, float[] bestD)
                {
                    int cx = C(p.x), cy = C(p.y), cz = C(p.z);
                    for (var r = 1; r <= 16; r++)
                    {
                        for (var x = cx - r; x <= cx + r; x++)
                        for (var y = cy - r; y <= cy + r; y++)
                        for (var z = cz - r; z <= cz + r; z++)
                        {
                            if (r > 1 && Mathf.Abs(x - cx) < r && Mathf.Abs(y - cy) < r && Mathf.Abs(z - cz) < r) continue;   // içteki kabuklar bakıldı
                            if (!_cells.TryGetValue(Key(x, y, z), out var l)) continue;
                            foreach (var i in l)
                            {
                                var d = (v[i] - p).sqrMagnitude;
                                if (d >= bestD[3]) continue;
                                var k = 3;
                                while (k > 0 && bestD[k - 1] > d) { bestD[k] = bestD[k - 1]; best[k] = best[k - 1]; k--; }
                                bestD[k] = d; best[k] = i;
                            }
                        }
                        if (best[3] >= 0 && bestD[3] <= (r * _cell) * (r * _cell)) break;   // dördüncü en yakın bu kabuğun içinde
                    }
                }
            }
        }

        /// <summary>Giysi ağının kemik dizinleri vücudun kemik sırasına çevrilmiş kopyası; olmazsa null.</summary>
        private static Mesh WearMesh(string model, string part, SkinnedMeshRenderer body)
        {
            var prefab = Resources.Load<GameObject>("Pets/" + model + "/" + model + "_wear");
            if (prefab == null) return null;
            SkinnedMeshRenderer src = null;
            foreach (var r in prefab.GetComponentsInChildren<SkinnedMeshRenderer>(true)) if (r.name == part) src = r;
            if (src == null || src.sharedMesh == null || !src.sharedMesh.isReadable || body.sharedMesh.bindposes.Length != body.bones.Length) return null;
            var index = new Dictionary<string, int>();
            for (var i = 0; i < body.bones.Length; i++) if (body.bones[i] != null) index[body.bones[i].name] = i;
            var map = new int[src.bones.Length];
            for (var i = 0; i < map.Length; i++)
                if (src.bones[i] == null || !index.TryGetValue(src.bones[i].name, out map[i])) return null;
            var mesh = Object.Instantiate(src.sharedMesh);
            mesh.name = model + "_" + part;
            var w = mesh.boneWeights;
            for (var i = 0; i < w.Length; i++)
            {
                var b = w[i];
                b.boneIndex0 = map[b.boneIndex0]; b.boneIndex1 = map[b.boneIndex1]; b.boneIndex2 = map[b.boneIndex2]; b.boneIndex3 = map[b.boneIndex3];
                w[i] = b;
            }
            mesh.boneWeights = w;
            mesh.bindposes = body.sharedMesh.bindposes;
            return mesh;
        }

        /// <summary>Gerçek eşya yerleşim kuralı: kemik, boy (pet boyuna oran), yukarı/ileri/yan kayma, alttan mı oturur.</summary>
        private struct Rule
        {
            public string Bone; public float Size, Up, Fwd, Side; public bool Bottom;
            public Rule(string bone, float size, float up = 0f, float fwd = 0f, float side = 0f, bool bottom = false)
            { Bone = bone; Size = size; Up = up; Fwd = fwd; Side = side; Bottom = bottom; }
        }

        // art/meshy önizlemesiyle (Blender, 3 farklı pet) ayarlandı; Meshy iskelet kemik adları
        private static readonly Dictionary<string, Rule> Rules = new Dictionary<string, Rule>
        {
            ["head"] = new Rule("head_end", 0.55f, up: -0.07f, bottom: true),
            ["eyes"] = new Rule("headfront", 0.32f, fwd: -0.03f),   // yükseklik: EyeLine (pet başına)
            ["body"] = new Rule("Spine02", 0.44f, up: 0.02f),
            ["back"] = new Rule("Spine01", 0.30f, up: -0.08f, fwd: -0.12f),
            ["hand"] = new Rule("RightHand", 0.16f, side: 0.04f),
        };

        /// <summary>
        /// Okti (pet_13, Mixamo iskeleti, uç kemik yok): 3 evre × 24 eşya Blender'da oyundaki yerleşimle denendi
        /// (art/meshy/scripts/fit_test_okti.py + okti_fit_rules.json, 22 Ekim 2026). Baş eşyası gövde ağının tepesine oturur,
        /// gözlük göz hizasında yüzün hemen önüne, gövde eşyası Spine2'de pet giysisinin üstüne.
        /// </summary>
        private static readonly Dictionary<string, Rule> OktiRules = new Dictionary<string, Rule>
        {
            ["head"] = new Rule("Head", 0.62f, up: -0.14f, bottom: true),
            ["eyes"] = new Rule("Head", 0.40f, fwd: 0.015f),
            ["body"] = new Rule("Spine2", 0.72f, up: -0.02f),
            ["back"] = new Rule("Spine1", 0.36f, up: -0.04f, fwd: -0.2f),
            ["hand"] = new Rule("RightHand", 0.2f, side: 0.03f),
            ["hips"] = new Rule("Hips", 0.46f, up: -0.07f),   // temel şort
        };
        /// <summary>Kıyafetsiz ergen ve yetişkin Okti (23 Ekim 2026, kullanıcı yüklemesi; baştaki bant silindi): başları ve gövdeleri
        /// çocuğa göre boya oranla küçük → evre başına tüm yuvalar (fit_test_okti.py + okti_fit_rules.json "genc:&lt;yuva&gt;").</summary>
        private static readonly Dictionary<string, Rule> OktiGenc = new Dictionary<string, Rule>
        {
            ["head"] = new Rule("Head", 0.465f, up: -0.14f, bottom: true), ["eyes"] = new Rule("Head", 0.29f, fwd: 0.015f),
            ["body"] = new Rule("Spine1", 0.53f, up: -0.03f), ["back"] = new Rule("Spine1", 0.25f, up: -0.04f, fwd: -0.11f),
            ["hand"] = new Rule("RightHand", 0.17f, side: 0.03f), ["hips"] = new Rule("Hips", 0.33f, up: -0.05f),
        };
        private static readonly Dictionary<string, Rule> OktiAdult = new Dictionary<string, Rule>
        {
            ["head"] = new Rule("Head", 0.42f, up: -0.14f, bottom: true), ["eyes"] = new Rule("Head", 0.256f, fwd: 0.015f),
            ["body"] = new Rule("Spine1", 0.50f, up: -0.03f), ["back"] = new Rule("Spine1", 0.24f, up: -0.04f, fwd: -0.11f),
            ["hand"] = new Rule("RightHand", 0.17f, side: 0.03f), ["hips"] = new Rule("Hips", 0.31f, up: -0.04f),
        };
        /// <summary>Kıyafetsiz çocuk Okti (23 Ekim 2026): gövde başın etek kısmının altında kalıyordu → gövde eşyaları Spine1'de,
        /// görünen gövdeyi saracak boyda (fit_test_okti.py + okti_fit_rules.json "yavru:body").</summary>
        private static readonly Dictionary<string, Rule> OktiChild = new Dictionary<string, Rule>
        {
            ["body"] = new Rule("Spine1", 0.62f, up: -0.03f),
        };
        /// <summary>Evre başına göz hizası (petin boyuna oran, tabandan) ve göz hizasında yüzün önü (Head kemiğinden ileri, boya oran).</summary>
        private static readonly Dictionary<GrowthStage, Vector2> OktiEyes = new Dictionary<GrowthStage, Vector2>
        {
            // kıyafetsiz modeller (23 Ekim 2026): göz noktaları dokudan, yüzün önü göz hizasında ağdan (fit_test_okti.py report face_front_at_eye)
            [GrowthStage.Yavru] = new Vector2(0.817f, 0.253f), [GrowthStage.Genc] = new Vector2(0.862f, 0.173f), [GrowthStage.Yetiskin] = new Vector2(0.889f, 0.163f),
        };
        /// <summary>Eşya başına boy çarpanı, yukarı ve ileri kayma (Okti'de; çift el eşyasında ileri = kol boyunca uca doğru).</summary>
        private static readonly Dictionary<string, Vector3> OktiItem = new Dictionary<string, Vector3>
        {
            ["vest_explorer"] = new Vector3(0.82f, 0f), ["headphones"] = new Vector3(1f, -0.3f), ["scarf_knit"] = new Vector3(0.62f, -0.02f),
            ["sash_belt"] = new Vector3(0.85f, 0f), ["hat_beanie"] = new Vector3(0.92f, -0.03f), ["cape_hero"] = new Vector3(1.15f, 0f),
            ["set_star_cape"] = new Vector3(1.15f, 0f), ["glove_mitten"] = new Vector3(1.3f, 0f), ["hand_flag"] = new Vector3(1.6f, 0f),
            // komik eşyalar (23 Ekim 2026, F1–F17): çocuk Okti'de fit_test_okti.py ile ayarlandı
            ["hat_shark"] = new Vector3(1.35f, -0.03f), ["hat_banana"] = new Vector3(1.05f, -0.02f), ["outfit_burger"] = new Vector3(1.08f, 0f),
            ["outfit_chicken"] = new Vector3(1.3f, -0.07f), ["float_flamingo"] = new Vector3(1.12f, -0.02f), ["backpack_rocket"] = new Vector3(1.6f, 0.08f),
            ["hat_propeller"] = new Vector3(0.95f, -0.02f), ["hat_cake"] = new Vector3(0.95f, -0.02f), ["hat_watermelon"] = new Vector3(0.95f, -0.03f),
            ["hat_crown_tilt"] = new Vector3(1.05f, -0.09f), ["hat_bucket"] = new Vector3(0.95f, -0.03f), ["hat_fishbowl"] = new Vector3(0.81f, 0.09f),
            // gözlükte ileri = yüzün önüne (fit_test_okti.py'de göz için işaret ters: −fwd)
            ["glasses_heart"] = new Vector3(0.98f, 0f, 0.0125f), ["glasses_nose"] = new Vector3(0.77f, 0f, 0.089f), ["glasses_snorkel"] = new Vector3(1.05f, 0f, 0.097f),
            ["mask_hero"] = new Vector3(1.06f, 0f, 0.005f), ["socks_arm"] = new Vector3(1.163f, 0f, 0.016f), ["pompom"] = new Vector3(1.3f, 0f, 0.12f),
            ["outfit_hula"] = new Vector3(0.925f, -0.034f, -0.05f), ["base_top"] = new Vector3(1f, 0.04f),
        };
        /// <summary>Evreye özel eşya ayarı ("genc:&lt;id&gt;"; varsa <see cref="OktiItem"/> yerine): köpekbalığı kapüşonu ve bere ergen/yetişkinde gözü örtmesin.</summary>
        private static readonly Dictionary<string, Vector3> OktiItemStage = new Dictionary<string, Vector3>
        {
            ["genc:hat_shark"] = new Vector3(1.35f, 0.04f), ["yetiskin:hat_shark"] = new Vector3(1.35f, 0.04f),
            ["genc:hat_beanie"] = new Vector3(0.92f, 0f), ["yetiskin:hat_beanie"] = new Vector3(0.92f, 0f),
            ["genc:base_top"] = new Vector3(1.06f, 0.04f),
        };
        /// <summary>Dosyada ters dönük eşyalar: sırt çantasının cebi önde, askıları arkada modellenmiş → petin sırtında askılar gövdeye dönsün.</summary>
        private static readonly HashSet<string> Reversed = new HashSet<string> { "backpack_small" };
        /// <summary>Dönen parçası olan eşyalar (Items/&lt;id&gt;/&lt;id&gt;_spin): derece/sn.</summary>
        private static readonly Dictionary<string, float> SpinSpeed = new Dictionary<string, float> { ["hat_propeller"] = 620f, ["hat_fishbowl"] = 40f };

        private static string StageKey(GrowthStage s) => s == GrowthStage.Yavru ? "yavru" : s == GrowthStage.Yetiskin ? "yetiskin" : "genc";

        /// <summary>Gözlerin yüksekliği: Head kemiğinden head_end'e oranla (Blender'da 12 pet ölçüldü).</summary>
        private static readonly Dictionary<string, float> EyeLine = new Dictionary<string, float>
        {
            ["pet_01"] = 0.38f, ["pet_02"] = 0.6f, ["pet_03"] = 0.55f, ["pet_04"] = 0.5f, ["pet_05"] = 0.45f, ["pet_06"] = 0.5f,
            ["pet_07"] = 0.5f, ["pet_08"] = 0.3f, ["pet_09"] = 0.55f, ["pet_10"] = 0.47f, ["pet_11"] = 0.45f, ["pet_12"] = 0.5f,
        };

        private static Transform FindDeep(Transform t, string name)
        {
            if (t.name == name || t.name.EndsWith(":" + name)) return t;   // Mixamo iskeleti: "mixamorig:Head"

            for (var i = 0; i < t.childCount; i++)
            {
                var r = FindDeep(t.GetChild(i), name);
                if (r != null) return r;
            }
            return null;
        }

        /// <summary>Gerçek pet + gerçek eşya: kemiğe takılır (animasyonla birlikte hareket eder). Olmazsa false.</summary>
        private static bool BuildReal(Transform pet, Transform root, ItemDef item, string variant, string petId)
        {
            var okti = petId == "pet_13";
            if (item.Slot == null || !(okti ? OktiRules : Rules).TryGetValue(item.Slot, out var rule)) return false;
            if (okti && _stage == GrowthStage.Yetiskin && OktiAdult.TryGetValue(item.Slot, out var adult)) rule = adult;
            if (okti && _stage == GrowthStage.Genc && OktiGenc.TryGetValue(item.Slot, out var teen)) rule = teen;
            if (okti && _stage == GrowthStage.Yavru && OktiChild.TryGetValue(item.Slot, out var child)) rule = child;
            if (okti && (OktiItemStage.TryGetValue(StageKey(_stage) + ":" + item.Id, out var io) || OktiItem.TryGetValue(item.Id, out io)))
            { rule.Size *= io.x; rule.Up += io.y; rule.Fwd += io.z; }
            var bone = FindDeep(pet, rule.Bone);
            if (bone == null || !RealAssets.HasItem(item.Id)) return false;

            // petin dünyadaki boyu ve yönü (eşyalar hariç): önce gerçek ağdan (Capture), olmazsa çizici sınırlarından
            Bounds pb = _geoBounds; var any = _geoOk;
            if (!any)
                foreach (var r in pet.GetComponentsInChildren<Renderer>())
                {
                    if (r.transform.IsChildOf(root) || r.GetComponentInParent<RealCosmetic>() != null) continue;   // eşyalar ölçüye girmesin
                    if (!any) { pb = r.bounds; any = true; } else pb.Encapsulate(r.bounds);
                }
            if (!any) return false;
            var h = pb.size.y;
            var front = pet.TransformDirection(Vector3.back);   // gerçek pet kameraya (−z) dönük kurulu
            front.y = 0f; front = front.sqrMagnitude > 0.001f ? front.normalized : Vector3.back;
            var right = Vector3.Cross(Vector3.up, front);
            if (item.Pair) return BuildPair(pet, root, item, rule, h, front);

            var t = RealAssets.Item(item.Id, root);
            var face = Quaternion.LookRotation(Reversed.Contains(item.Id) ? -front : front, Vector3.up);   // eşyanın önü (+z) petin önüne
            // ölçüler eşyanın kendi ekseninde: pet yana dönükken (dolap, ada) dünya kutusu şişiyor, gözlük yüze gömülüyor,
            // şapka küçülüyordu (23 Ekim 2026); Blender oturma denemesi dönüksüz ölçer
            t.rotation = Quaternion.identity;
            var ib = RealAssets.WorldBounds(t);
            var w = Mathf.Max(ib.size.x, ib.size.z);
            if (w < 0.0001f) return false;
            t.localScale *= rule.Size * h / w;
            ib = RealAssets.WorldBounds(t);
            var off = ib.center - t.position;
            var up = rule.Up + (variant == "raised" ? 0.05f : 0f);
            var target = bone.position + Vector3.up * (up * h) + front * (rule.Fwd * h) + right * (rule.Side * h);
            var headBone = FindDeep(pet, "Head");
            var headEnd = FindDeep(pet, "head_end");
            if (!okti && item.Slot == "eyes" && headBone != null && headEnd != null)
            {
                var hh = Vector3.Distance(headEnd.position, headBone.position);
                target.y = headBone.position.y + (EyeLine.TryGetValue(petId ?? "", out var k) ? k : 0.48f) * hh;
            }
            if (okti)
            {
                if (item.Slot == "head") target.y = pb.max.y + rule.Up * h;                                // uç kemik yok: ağın tepesi
                if (item.Slot == "eyes" && OktiEyes.TryGetValue(_stage, out var ey))
                {
                    var eyeY = pb.min.y + ey.x * h;
                    target = bone.position + front * FaceFront(bone.position, front, right, eyeY, h, ey.y * h); target.y = eyeY;   // yüzün önü, göz hizası
                    target += front * (rule.Fwd * h - ib.extents.z);                                          // camlar yüzün önünde
                }
            }
            t.rotation = face;
            var c = face * off;                                       // dönüş yalnız dikey eksende: düşey kayma aynı
            var y = rule.Bottom ? target.y - (off.y - ib.extents.y) : target.y - off.y;
            t.position = new Vector3(target.x - c.x, y, target.z - c.z);
            if (okti && SkinItems.Contains(item.Id))
            {
                Note(item.Id, t, pb);
                if (SkinToBody(pet, t, StageKey(_stage) + "/" + item.Id)) return true;   // olmazsa eskisi gibi kemiğe sert bağlanır
            }
            // head_end bir uç kemik: animasyonlarda ölçeği bozulabiliyor → kafa eşyaları asıl Head kemiğine takılır
            t.SetParent(rule.Bone == "head_end" && headBone != null ? headBone : bone, true);
            t.gameObject.AddComponent<RealCosmetic>();
            if (SpinSpeed.TryGetValue(item.Id, out var spin)) RealAssets.ArmSpin(t, spin);
            Note(item.Id, t, pb);
            return true;
        }

        // ---- petin gerçek boyu: kemiklerden (oturma denemesi art/meshy/scripts/fit_test_okti.py ağı ölçer; oyunda çizici sınırı
        // deri ağında %14'e kadar büyük çıkıyordu, ağ pişirme de ölçekte şaşıyordu → 23 Ekim 2026 gözlük/maske yüzün içinde kaldı)
        private static readonly List<Vector3> Verts = new List<Vector3>();
        private static Bounds _geoBounds; private static bool _geoOk;
        private static readonly System.Text.StringBuilder Report = new System.Text.StringBuilder();
        /// <summary>Evre başına Head ve Hips kemiklerinin yüksekliği (ağ boyuna oran, tabandan; Blender'da dinlenme pozunda ölçüldü).</summary>
        private static readonly Dictionary<GrowthStage, Vector2> OktiBones = new Dictionary<GrowthStage, Vector2>
        {
            [GrowthStage.Yavru] = new Vector2(0.5184f, 0.3049f), [GrowthStage.Genc] = new Vector2(0.6888f, 0.4284f), [GrowthStage.Yetiskin] = new Vector2(0.7227f, 0.4764f),
        };

        private static void Capture(Transform pet, Transform root)
        {
            Verts.Clear(); _geoOk = false; Report.Length = 0;
            Bounds rb = default; var rany = false;
            foreach (var r in pet.GetComponentsInChildren<Renderer>())
            {
                if (r.transform.IsChildOf(root) || r.GetComponentInParent<RealCosmetic>() != null) continue;
                if (!rany) { rb = r.bounds; rany = true; } else rb.Encapsulate(r.bounds);
            }
            var head = FindDeep(pet, "Head"); var hips = FindDeep(pet, "Hips");
            if (_petId != "pet_13" || head == null || hips == null || !OktiBones.TryGetValue(_stage, out var fr)) { Report.Append("kemik=yok "); return; }
            var h = (head.position.y - hips.position.y) / (fr.x - fr.y);
            if (h <= 1e-4f || (rany && (h < rb.size.y * 0.5f || h > rb.size.y * 1.5f))) { Report.Append($"kemik boyu şüpheli {h:0.###} "); return; }
            var minY = hips.position.y - fr.y * h;
            var c = rany ? rb.center : head.position;
            _geoBounds = new Bounds(new Vector3(c.x, minY + h / 2f, c.z), new Vector3(rany ? rb.size.x : h, h, rany ? rb.size.z : h));
            _geoOk = true;
            Report.Append($"kemik boyu={h:0.###} çizici={(rany ? rb.size.y : 0f):0.###} ");
        }

        /// <summary>Göz hizasında, ortadaki şeritte yüzün en ön noktası: kemikten ileri uzaklık. Ölçü yoksa yedek.</summary>
        private static float FaceFront(Vector3 origin, Vector3 front, Vector3 right, float eyeY, float h, float fallback)
        {
            if (Verts.Count == 0) return fallback;
            var best = float.MinValue;
            foreach (var v in Verts)
            {
                if (Mathf.Abs(v.y - eyeY) > 0.03f * h) continue;
                var rel = v - origin;
                if (Mathf.Abs(Vector3.Dot(rel, right)) > 0.12f * h) continue;
                var d = Vector3.Dot(rel, front);
                if (d > best) best = d;
            }
            if (best == float.MinValue) return fallback;
            Report.Append($"yüz={best / h:0.###}h(yedek {fallback / h:0.###}h) ");
            return best;
        }

        private static void Note(string id, Transform t, Bounds pb)
        {
            var b = RealAssets.WorldBounds(t);
            var h = Mathf.Max(1e-5f, pb.size.y);
            Report.Append($"| {id} alt={(b.min.y - pb.min.y) / h:0.##} üst={(b.max.y - pb.min.y) / h:0.##} gen={b.size.x / h:0.##} ");
        }

        /// <summary>Son giydirmenin ölçüleri (ayıklama komutu "cos").</summary>
        public static string Describe() => Report.ToString();

        /// <summary>
        /// Çift eşya (pair: kol çorabı, ponpon): tek model iki ele birden. Modelin altı önkol → el yönüne (kol ucuna), önü petin önüne;
        /// boy döndürmeden önceki genişlikten, Fwd = kol boyunca uca doğru kayma (art/meshy/scripts/fit_test_okti.py place_pair ile aynı).
        /// </summary>
        private static bool BuildPair(Transform pet, Transform root, ItemDef item, Rule rule, float h, Vector3 front)
        {
            var any = false;
            var face = Quaternion.LookRotation(front, Vector3.up);
            foreach (var side in new[] { "Right", "Left" })
            {
                var hand = FindDeep(pet, side + "Hand");
                var fore = FindDeep(pet, side + "ForeArm");
                if (hand == null || fore == null) continue;
                var d = hand.position - fore.position;
                if (d.sqrMagnitude < 1e-8f) continue;
                d.Normalize();
                var t = RealAssets.Item(item.Id, root);
                if (t == null) return any;
                t.rotation = Quaternion.identity;                     // boy eşyanın kendi ekseninde (pet dönükken kutu şişmesin)
                var ib = RealAssets.WorldBounds(t);
                var w = Mathf.Max(ib.size.x, ib.size.z);
                if (w < 0.0001f) { Object.Destroy(t.gameObject); continue; }
                t.localScale *= rule.Size * h / w;
                t.rotation = Quaternion.FromToRotation(Vector3.down, d) * face;
                ib = RealAssets.WorldBounds(t);
                t.position += hand.position + d * (rule.Fwd * h) - ib.center;
                t.SetParent(hand, true);
                t.gameObject.AddComponent<RealCosmetic>();
                Note(item.Id + "_" + side, t, new Bounds(hand.position, Vector3.one * h));
                any = true;
            }
            return any;
        }

        private static void Build(Transform pet, Transform root, ItemDef item, string variant)
        {
            if (BuildReal(pet, root, item, variant, _petId)) return;
            var col = ColorOf(item.Id);
            var m = PetModels.NewMaterial(col, 0.55f);
            switch (item.Slot)
            {
                case "head": Head(At(pet, root, "socket_head", item.Id), item.Id, variant, m); break;
                case "eyes": Eyes(At(pet, root, "socket_eyes", item.Id), item.Id, variant, m); break;
                case "body": Body(At(pet, root, null, item.Id), item, m); break;
                case "back": Back(At(pet, root, "socket_back", item.Id), item.Id, variant, m); break;
                case "hand": Hand(pet, root, item.Id, m); break;
            }
        }

        /// <summary>Soketin konumunda (soket yoksa kökte) eşya için boş nesne.</summary>
        private static Transform At(Transform pet, Transform root, string socket, string id)
        {
            var t = new GameObject(id).transform;
            t.SetParent(root, false);
            var s = socket != null ? pet.Find(socket) : null;
            if (s != null) t.localPosition = s.localPosition;
            return t;
        }

        private static void Head(Transform t, string id, string variant, Material m)
        {
            if (variant == "raised") t.localPosition += Vector3.up * 0.1f;
            if (variant == "mane_fit") t.localScale = Vector3.one * 1.15f;
            switch (id)
            {
                case "hat_straw":
                    P(PrimitiveType.Cylinder, t, new Vector3(0f, -0.06f, 0f), new Vector3(0.95f, 0.015f, 0.95f), m);
                    P(PrimitiveType.Cylinder, t, new Vector3(0f, 0.02f, 0f), new Vector3(0.5f, 0.09f, 0.5f), m);
                    break;
                case "hat_beanie":
                    P(PrimitiveType.Sphere, t, new Vector3(0f, -0.04f, 0f), new Vector3(0.62f, 0.38f, 0.62f), m);
                    P(PrimitiveType.Sphere, t, new Vector3(0f, 0.17f, 0f), Vector3.one * 0.14f, PetModels.NewMaterial(Color.white, 0.2f));
                    break;
                case "hat_crown":
                    for (var i = 0; i < 6; i++)
                    {
                        var a = i / 6f * Mathf.PI * 2f;
                        P(PrimitiveType.Cube, t, new Vector3(Mathf.Cos(a) * 0.18f, 0.02f, Mathf.Sin(a) * 0.18f), new Vector3(0.09f, 0.16f, 0.09f), m, new Vector3(0f, -a * Mathf.Rad2Deg, 45f));
                    }
                    P(PrimitiveType.Cylinder, t, new Vector3(0f, -0.05f, 0f), new Vector3(0.42f, 0.03f, 0.42f), m);
                    break;
                case "headphones":
                    t.localPosition += Vector3.down * 0.3f;
                    P(PrimitiveType.Sphere, t, new Vector3(-0.47f, 0f, 0f), new Vector3(0.12f, 0.2f, 0.2f), m);
                    P(PrimitiveType.Sphere, t, new Vector3(0.47f, 0f, 0f), new Vector3(0.12f, 0.2f, 0.2f), m);
                    P(PrimitiveType.Capsule, t, new Vector3(0f, 0.36f, 0f), new Vector3(0.06f, 0.46f, 0.06f), m, new Vector3(0f, 0f, 90f));
                    break;
                case "set_captain_hat":
                    P(PrimitiveType.Cylinder, t, new Vector3(0f, 0.02f, 0f), new Vector3(0.52f, 0.1f, 0.52f), m);
                    P(PrimitiveType.Cylinder, t, new Vector3(0f, -0.08f, -0.12f), new Vector3(0.4f, 0.012f, 0.3f), PetModels.NewMaterial(new Color(0.1f, 0.1f, 0.2f)));
                    break;
                default: // kasket
                    P(PrimitiveType.Sphere, t, new Vector3(0f, -0.04f, 0f), new Vector3(0.6f, 0.32f, 0.6f), m);
                    P(PrimitiveType.Cylinder, t, new Vector3(0f, -0.1f, -0.3f), new Vector3(0.36f, 0.012f, 0.3f), m);
                    break;
            }
        }

        private static void Eyes(Transform t, string id, string variant, Material m)
        {
            var lens = id == "glasses_sun" ? PetModels.NewMaterial(new Color(0.1f, 0.1f, 0.15f), 0.95f)
                : id == "glasses_star" ? PetModels.NewMaterial(new Color(1f, 0.9f, 0.4f), 0.6f) : null;
            t.localPosition += new Vector3(0f, -0.02f, -0.04f);
            foreach (var s in new[] { -1f, 1f })
            {
                if (id == "glasses_star")
                {
                    P(PrimitiveType.Cube, t, new Vector3(0.17f * s, 0f, 0f), new Vector3(0.17f, 0.17f, 0.03f), m, new Vector3(0f, 0f, 45f));
                    P(PrimitiveType.Cube, t, new Vector3(0.17f * s, 0f, -0.005f), new Vector3(0.17f, 0.17f, 0.03f), lens);
                }
                else
                {
                    P(PrimitiveType.Cylinder, t, new Vector3(0.17f * s, 0f, 0f), new Vector3(0.2f, 0.015f, 0.2f), m, new Vector3(90f, 0f, 0f));
                    if (lens != null) P(PrimitiveType.Cylinder, t, new Vector3(0.17f * s, 0f, -0.01f), new Vector3(0.17f, 0.01f, 0.17f), lens, new Vector3(90f, 0f, 0f));
                }
            }
            if (variant != "clip") P(PrimitiveType.Capsule, t, Vector3.zero, new Vector3(0.025f, 0.06f, 0.025f), m, new Vector3(0f, 0f, 90f));
        }

        private static void Body(Transform t, ItemDef item, Material m)
        {
            var id = item.Id;
            if (id == "scarf_knit")
            {
                P(PrimitiveType.Capsule, t, new Vector3(0f, 0.66f, -0.02f), new Vector3(0.22f, 0.36f, 0.22f), m, new Vector3(0f, 0f, 90f));
                P(PrimitiveType.Capsule, t, new Vector3(0.12f, 0.52f, -0.24f), new Vector3(0.1f, 0.14f, 0.05f), m);
                return;
            }
            if (id == "sash_belt")
            {
                P(PrimitiveType.Capsule, t, new Vector3(0f, 0.4f, -0.12f), new Vector3(0.1f, 0.36f, 0.5f), m, new Vector3(0f, 0f, 40f));
                return;
            }
            if (item.Cut == "apron" || id == "apron_sailor")
            {
                P(PrimitiveType.Sphere, t, new Vector3(0f, 0.36f, -0.22f), new Vector3(0.48f, 0.5f, 0.16f), m);
                return;
            }
            P(PrimitiveType.Sphere, t, new Vector3(0f, 0.43f, 0f), new Vector3(0.67f, 0.5f, 0.61f), m);
            if (id == "shirt_stripes")
                for (var i = 0; i < 2; i++)
                    P(PrimitiveType.Sphere, t, new Vector3(0f, 0.36f + i * 0.13f, 0f), new Vector3(0.68f, 0.05f, 0.62f), PetModels.NewMaterial(Color.white, 0.4f));
            if (id == "hoodie_soft" || id == "raincoat")
                P(PrimitiveType.Sphere, t, new Vector3(0f, 0.75f, 0.24f), new Vector3(0.5f, 0.3f, 0.26f), m);
        }

        private static void Back(Transform t, string id, string variant, Material m)
        {
            if (variant == "on_shell") t.localPosition += new Vector3(0f, 0.38f, -0.1f);
            switch (id)
            {
                case "cape_hero":
                case "set_star_cape":
                    P(PrimitiveType.Cube, t, new Vector3(0f, -0.05f, 0.04f), new Vector3(0.5f, 0.5f, 0.03f), m, new Vector3(-12f, 0f, 0f));
                    break;
                case "badge_patch":
                    P(PrimitiveType.Cylinder, t, new Vector3(0f, 0f, 0.0f), new Vector3(0.16f, 0.01f, 0.16f), m, new Vector3(90f, 0f, 0f));
                    break;
                default:
                    P(PrimitiveType.Cube, t, new Vector3(0f, 0f, 0.08f), new Vector3(0.34f, 0.36f, 0.18f), m);
                    P(PrimitiveType.Cube, t, new Vector3(0f, -0.08f, 0.18f), new Vector3(0.26f, 0.14f, 0.05f), m);
                    break;
            }
        }

        private static void Hand(Transform pet, Transform root, string id, Material m)
        {
            if (id == "glove_mitten")
            {
                foreach (var s in new[] { "socket_hand_L", "socket_hand_R" })
                    P(PrimitiveType.Sphere, At(pet, root, s, id), Vector3.zero, Vector3.one * 0.15f, m);
                return;
            }
            var t = At(pet, root, "socket_hand_R", id);
            P(PrimitiveType.Cylinder, t, new Vector3(0f, 0.2f, 0f), new Vector3(0.03f, 0.25f, 0.03f), PetModels.NewMaterial(new Color(0.55f, 0.38f, 0.2f)));
            P(PrimitiveType.Cube, t, new Vector3(0.13f, 0.36f, 0f), new Vector3(0.24f, 0.15f, 0.015f), m);
        }

        private static GameObject P(PrimitiveType type, Transform parent, Vector3 pos, Vector3 scale, Material m, Vector3 euler = default)
        {
            var go = GameObject.CreatePrimitive(type);
            go.transform.SetParent(parent, false);
            go.transform.localPosition = pos;
            go.transform.localRotation = Quaternion.Euler(euler);
            go.transform.localScale = scale;
            go.GetComponent<Renderer>().sharedMaterial = m;
            return go;
        }
    }

    /// <summary>Kemiğe takılmış gerçek eşya işareti (yeniden giydirirken bulunup kaldırılır).</summary>
    public sealed class RealCosmetic : MonoBehaviour { }
}
