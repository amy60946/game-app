using System.Collections.Generic;
using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// Gerçek (Meshy) varlıklar: Resources/Pets/&lt;id&gt;/&lt;id&gt;.fbx, Resources/Env/&lt;ad&gt;/&lt;ad&gt;.fbx.
    /// Varsa kullanılır, yoksa yer tutucuya dönülür. Malzeme çalışma anında URP Lit olarak kurulur
    /// (taban renk + normal haritası), boy hedef yüksekliğe ölçeklenir, ayaklar y = 0'a oturur.
    /// </summary>
    public static class RealAssets
    {
        private static Material _base;
        private static readonly Dictionary<string, Material> Materials = new Dictionary<string, Material>();

        /// <summary>Paylaşılan (önbellekteki) malzeme mi? Bunlar sahne temizlenirken yok edilmez.</summary>
        public static bool IsShared(Material m) => m != null && Materials.ContainsValue(m);

        public static bool HasPet(string petId) => Resources.Load<GameObject>($"Pets/{petId}/{petId}") != null;

        /// <summary>
        /// Büyüme evresine özel model (Okti, 20 Ekim 2026: çocuk / ergen / yetişkin ayrı Meshy modelleri): Pets/&lt;id&gt;_yavru|genc|yetiskin.
        /// Yoksa tek model (eski petler; evre yalnız ölçekle gösterilir).
        /// </summary>
        public static string StageModel(string petId, Logic.Progression.GrowthStage stage)
        {
            var id = petId + "_" + stage.ToString().ToLowerInvariant();
            return HasPet(id) ? id : petId;
        }

        /// <summary>Gerçek pet modeli + animasyonlar. Yoksa null.</summary>
        public static Transform Pet(string petId, Transform parent, float height)
        {
            var prefab = Resources.Load<GameObject>($"Pets/{petId}/{petId}");
            if (prefab == null) return null;
            var root = new GameObject(petId + "_real").transform;
            root.SetParent(parent, false);
            var go = Object.Instantiate(prefab, root, false);
            go.name = "model";
            go.transform.localRotation = Quaternion.Euler(0f, 180f, 0f) * go.transform.localRotation;   // Meshy/Blender önü +Z → kameraya (−Z) dön
            ApplyMaterial(go, $"Pets/{petId}/{petId}", 0.28f);
            Fit(root, go.transform, height);

            var anim = go.GetComponent<Animation>() ?? go.AddComponent<Animation>();
            foreach (var clip in Resources.LoadAll<AnimationClip>($"Pets/{petId}"))
            {
                clip.legacy = true;
                if (anim.GetClip(clip.name) == null) anim.AddClip(clip, clip.name);
            }
            // döngüsel klipler: içe aktarma ayarı Legacy durumuna her zaman geçmiyor (yürüme 2 adımda duruyordu) → çalışırken de döngü
            foreach (var loop in LoopClips)
                if (anim.GetClip(loop) != null) anim[loop].wrapMode = WrapMode.Loop;
            if (anim.GetClip("idle") != null)
            {
                anim.clip = anim.GetClip("idle");
                anim.Play("idle");
            }
            anim.cullingType = AnimationCullingType.AlwaysAnimate;
            AddSockets(root, go.transform);
            return root;
        }

        /// <summary>Gerçek çevre modeli (palmiye, ada parçası…). Yoksa null.</summary>
        public static Transform Env(string name, Transform parent, float height)
        {
            var prefab = Resources.Load<GameObject>($"Env/{name}/{name}");
            if (prefab == null) return null;
            var root = new GameObject(name).transform;
            root.SetParent(parent, false);
            var go = Object.Instantiate(prefab, root, false);
            ApplyMaterial(go, $"Env/{name}/{name}", 0.15f);
            Fit(root, go.transform, height);
            return root;
        }

        /// <summary>Çevre modeli, yatay en büyük boyutu <paramref name="footprint"/> olacak şekilde (harita karoları için).</summary>
        public static Transform EnvFootprint(string name, Transform parent, float footprint, float yaw = 0f) =>
            Footprint("Env", name, parent, footprint, yaw);

        /// <summary>
        /// v6 ada modeli (art/code3d/v6/assets_v6_game.py): gerçek ölçüde dışa aktarılmış; yalnız <paramref name="scale"/> ile büyütülür,
        /// taban = modelin orijini (taslaktaki yerleşimle birebir).
        /// </summary>
        public static Transform EnvScaled(string name, Transform parent, float scale, float yaw = 0f)
        {
            var prefab = Resources.Load<GameObject>($"Env/{name}/{name}");
            if (prefab == null) return null;
            var root = new GameObject(name).transform;
            root.SetParent(parent, false);
            var go = Object.Instantiate(prefab, root, false);
            // Blender→FBX (ileri −Z, yukarı Y) + Unity'nin X çevirmesi: Blender (x, y) → Unity (−x, −y). Taslak koordinatı (x, z) = Blender (x, y)
            // olduğundan model 180° döndürülür (mağara ağzı, tapınak önü, kayak bayrakları taslaktaki yöne bakar).
            go.transform.localRotation = Quaternion.Euler(0f, 180f + yaw, 0f) * go.transform.localRotation;
            // FBX birim ölçeği içe aktarmada farklı yorumlanabilir: gerçek boy tablosuna (Data/env_v6_sizes.json) göre düzelt
            var fix = 1f;
            if (V6Sizes().TryGetValue(name, out var real) && real > 0.0001f)
            {
                var b = Bounds(go.transform);
                var h = b.size.y / Mathf.Max(0.0001f, Mathf.Abs(root.lossyScale.y));
                if (h > 0.0001f) fix = real / h;
            }
            go.transform.localScale *= scale * fix;
            ApplyMaterial(go, $"Env/{name}/{name}", 0.15f);
            return root;
        }

        private static Dictionary<string, float> _v6Sizes;

        private static Dictionary<string, float> V6Sizes()
        {
            if (_v6Sizes != null) return _v6Sizes;
            _v6Sizes = new Dictionary<string, float>();
            var ta = Resources.Load<TextAsset>("Data/env_v6_sizes");
            if (ta == null) return _v6Sizes;
            _v6Sizes = Logic.Island.EnvSizes.Parse(ta.text);
            return _v6Sizes;
        }

        /// <summary>Ev eşyası modeli, taban genişliğine göre (Resources/Items).</summary>
        public static Transform ItemFootprint(string id, Transform parent, float footprint, float yaw = 0f) =>
            Footprint("Items", id, parent, footprint, yaw);

        private static Transform Footprint(string folder, string name, Transform parent, float footprint, float yaw)
        {
            var prefab = Resources.Load<GameObject>($"{folder}/{name}/{name}");
            if (prefab == null) return null;
            var root = new GameObject(name).transform;
            root.SetParent(parent, false);
            var go = Object.Instantiate(prefab, root, false);
            go.transform.localRotation = Quaternion.Euler(0f, yaw, 0f) * go.transform.localRotation;
            ApplyMaterial(go, $"{folder}/{name}/{name}", 0.15f);
            var b = Bounds(go.transform);
            var w = Mathf.Max(b.size.x, b.size.z);
            if (w <= 0.0001f) return root;
            if (folder == "Env")
            {
                // kodla yenilenen çevre modelleri (art/code3d, 15 Ekim 2026): zemin = modelin orijini (diorama tabanı yok;
                // iskele kazıkları suyun altına iner), yalnız ölçeklenir
                var s = footprint * Mathf.Abs(root.lossyScale.x) / w;
                go.transform.localScale *= s;
            }
            else Fit(root, go.transform, b.size.y * footprint / w);
            return root;
        }

        public static bool HasItem(string id) => Resources.Load<GameObject>($"Items/{id}/{id}") != null;

        /// <summary>Eşya modeli (Resources/Items/&lt;id&gt;), ölçeklenmemiş. Yoksa null.</summary>
        public static Transform Item(string id, Transform parent)
        {
            var prefab = Resources.Load<GameObject>($"Items/{id}/{id}");
            if (prefab == null) return null;
            var root = new GameObject(id).transform;
            root.SetParent(parent, false);
            var go = Object.Instantiate(prefab, root, false);
            ApplyMaterial(go, $"Items/{id}/{id}", 0.3f);
            var spin = Resources.Load<GameObject>($"Items/{id}/{id}_spin");   // dönen parça (pervane, balıklar): aynı koordinatta
            if (spin != null)
            {
                var sp = Object.Instantiate(spin, root, false);
                sp.name = SpinPart;
                ApplyMaterial(sp, $"Items/{id}/{id}_spin", 0.3f);
            }
            return root;
        }

        public const string SpinPart = "spin";

        /// <summary>
        /// Eşya yerine oturduktan sonra dönen parçayı kendi sınır merkezinden geçen dikey eksende (eşyanın yukarısı) döndürür.
        /// Parça yoksa bir şey yapmaz.
        /// </summary>
        public static void ArmSpin(Transform item, float degPerSec)
        {
            var sp = item.Find(SpinPart);
            if (sp == null) return;
            var any = false; Bounds b = default;
            foreach (var r in sp.GetComponentsInChildren<Renderer>())
            {
                if (!any) { b = r.bounds; any = true; } else b.Encapsulate(r.bounds);
            }
            if (!any) return;
            var pivot = new GameObject("spin_pivot").transform;
            pivot.SetParent(item, false);
            pivot.position = b.center;
            sp.SetParent(pivot, true);
            pivot.gameObject.AddComponent<SpinAxis>().Speed = degPerSec;
        }

        /// <summary>Paylaşılan malzemeyi bozmadan renk çarpanı (ör. kilitli bölge grisi).</summary>
        public static void Tint(Transform t, Color c)
        {
            var mpb = new MaterialPropertyBlock();
            mpb.SetColor("_BaseColor", c);
            foreach (var r in t.GetComponentsInChildren<Renderer>(true)) r.SetPropertyBlock(mpb);
        }

        /// <summary>Modelin dünya sınırları (etiket yüksekliği vb. için).</summary>
        public static Bounds WorldBounds(Transform t) => Bounds(t);

        private static void ApplyMaterial(GameObject go, string texBase, float smoothness)
        {
            if (!Materials.TryGetValue(texBase, out var mat))
            {
                if (_base == null) _base = Resources.Load<Material>("Materials/VinylPlaceholder");
                mat = new Material(_base) { name = texBase };
                var baseTex = Resources.Load<Texture2D>(texBase + "_basecolor");
                var normal = Resources.Load<Texture2D>(texBase + "_normal");
                mat.SetColor("_BaseColor", Color.white);
                if (baseTex != null) mat.SetTexture("_BaseMap", baseTex);
                if (normal != null)
                {
                    mat.SetTexture("_BumpMap", normal);
                    mat.EnableKeyword("_NORMALMAP");
                }
                mat.SetFloat("_Smoothness", smoothness);
                mat.SetFloat("_Metallic", 0f);
                Materials[texBase] = mat;
                // görsel stil çalışması: petler/eşyalar "vinyl" (daha parlak), çevre mat; dış çizgi petlerde biraz kalın
                var pet = texBase.StartsWith("Pets/");
                var info = new LookInfo { LitSmooth = smoothness, ToonSmooth = pet ? 0.6f : texBase.StartsWith("Items/") ? 0.45f : 0.12f, Outline = pet ? 1.6f : 1.3f };
                LookInfos[mat] = info;
                SetLook(mat, info, Look.Stylized);
            }
            foreach (var r in go.GetComponentsInChildren<Renderer>(true))
            {
                var mats = r.sharedMaterials;
                for (var i = 0; i < mats.Length; i++) mats[i] = mat;
                r.sharedMaterials = mats;
                if (r is SkinnedMeshRenderer smr) smr.updateWhenOffscreen = true;
            }
        }

        private struct LookInfo { public float LitSmooth, ToonSmooth, Outline; }
        private static readonly Dictionary<Material, LookInfo> LookInfos = new Dictionary<Material, LookInfo>();

        /// <summary>Önbellekteki tüm Meshy malzemelerini yeni stile (Pofi/Toon) ya da eski görünüme (URP Lit) geçirir.</summary>
        internal static void ApplyLook(bool stylized)
        {
            foreach (var kv in LookInfos) SetLook(kv.Key, kv.Value, stylized);
        }

        private static void SetLook(Material m, LookInfo info, bool stylized)
        {
            var sh = stylized ? Look.ToonShader : _base != null ? _base.shader : null;
            if (m == null || sh == null) return;
            if (m.shader != sh) m.shader = sh;
            m.SetFloat("_Smoothness", stylized ? info.ToonSmooth : info.LitSmooth);
            if (stylized) m.SetFloat("_OutlineWidth", info.Outline);
            if (stylized && m.name.StartsWith("Env/"))
            {
                // çevre: kenar ışığı az (soluk kaya "saydam" görünüyordu), taslaktan pişmiş normal tam güçte (22 Ekim 2026)
                m.SetFloat("_Rim", 0.3f);
                m.SetFloat("_BumpScale", 1f);
            }
            // dış çizgi kapalı (kullanıcı kararı 15 Ekim 2026: yeni tasarımda nesne/karakter çevresinde çizgi olmayacak)
            m.SetShaderPassEnabled("SRPDefaultUnlit", false);
            if (m.GetTexture("_BumpMap") != null) m.EnableKeyword("_NORMALMAP");
        }

        /// <summary>Modeli hedef yüksekliğe ölçekler, yatayda ortalar, tabanı y = 0'a koyar.</summary>
        private static void Fit(Transform root, Transform model, float height)
        {
            var b = Bounds(model);
            if (b.size.y <= 0.0001f) return;
            // height kökün yerel biriminde: üst nesne o an ölçekliyse (ör. büyüme animasyonu) dünya ölçüsüne çevir
            var s = height * Mathf.Abs(root.lossyScale.y) / b.size.y;
            model.localScale *= s;
            b = Bounds(model);
            var offset = root.position - new Vector3(b.center.x, b.min.y, b.center.z);
            model.position += offset;
        }

        private static Bounds Bounds(Transform t)
        {
            var rs = t.GetComponentsInChildren<Renderer>(true);
            if (rs.Length == 0) return new Bounds(t.position, Vector3.zero);
            var b = rs[0].bounds;
            for (var i = 1; i < rs.Length; i++) b.Encapsulate(rs[i].bounds);
            return b;
        }

        /// <summary>Kıyafet soketleri: iskelet kemiklerine bağlı boş nesneler (ad sözleşmesi PetModels ile aynı).</summary>
        private static void AddSockets(Transform root, Transform model)
        {
            // kemik adı: Meshy eski iskeleti ("Spine01", "LeftHand") ya da Mixamo adları ("mixamorig:Spine1", "mixamorig:LeftHand")
            Transform Bone(params string[] names)
            {
                var all = model.GetComponentsInChildren<Transform>(true);
                foreach (var n in names)
                    foreach (var t in all)
                        if (t.name == n || t.name.EndsWith(":" + n)) return t;
                return null;
            }
            void Socket(string name, Transform bone, Vector3 fallback)
            {
                var s = new GameObject(name).transform;
                s.SetParent(bone != null ? bone : root, false);
                if (bone == null) s.localPosition = fallback;
            }
            var b = Bounds(model);
            var headEnd = Bone("head_end", "HeadTop_End");
            var head = headEnd == null ? Bone("Head") : null;
            if (head != null)
            {
                // uç kemiği yok (Mixamo iskeleti): şapka soketi baş kemiğine bağlı, modelin tepesinde
                var s = new GameObject("socket_head").transform;
                s.SetParent(head, false);
                s.position = new Vector3(head.position.x, b.max.y, head.position.z);
            }
            else Socket("socket_head", headEnd, new Vector3(0f, b.max.y, 0f));
            Socket("socket_eyes", Bone("headfront"), new Vector3(0f, b.max.y * 0.7f, -0.3f));
            Socket("socket_body", Bone("Spine01", "Spine1"), new Vector3(0f, b.max.y * 0.3f, -0.2f));
            Socket("socket_back", Bone("Spine"), new Vector3(0f, b.max.y * 0.35f, 0.2f));
            Socket("socket_hand_L", Bone("LeftHand"), new Vector3(-0.3f, 0.4f, 0f));
            Socket("socket_hand_R", Bone("RightHand"), new Vector3(0.3f, 0.4f, 0f));
        }

        private static readonly string[] LoopClips = { "idle", "walk", "run", "sleep", "swim" };

        /// <summary>Animasyon oynat (varsa); yoksa false.</summary>
        /// <summary>Oynayan döngüsel klibin döngü içindeki konumu (0..1); oynamıyorsa -1 (adım sesleri için).</summary>
        public static float Phase(Transform pet, string clip)
        {
            if (pet == null) return -1f;
            var anim = pet.GetComponentInChildren<Animation>();
            if (anim == null || anim.GetClip(clip) == null || !anim.IsPlaying(clip)) return -1f;
            return Mathf.Repeat(anim[clip].normalizedTime, 1f);
        }

        public static bool Play(Transform pet, string clip, bool returnToIdle = true)
        {
            if (pet == null) return false;
            var anim = pet.GetComponentInChildren<Animation>();
            if (anim == null || anim.GetClip(clip) == null) return false;
            anim.CrossFade(clip, 0.15f);
            if (returnToIdle && anim.GetClip("idle") != null && clip != "idle") anim.CrossFadeQueued("idle", 0.2f);
            return true;
        }
    }
}
