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
            if (w > 0.0001f) Fit(root, go.transform, b.size.y * footprint / w);
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
            return root;
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
            }
            foreach (var r in go.GetComponentsInChildren<Renderer>(true))
            {
                var mats = r.sharedMaterials;
                for (var i = 0; i < mats.Length; i++) mats[i] = mat;
                r.sharedMaterials = mats;
                if (r is SkinnedMeshRenderer smr) smr.updateWhenOffscreen = true;
            }
        }

        /// <summary>Modeli hedef yüksekliğe ölçekler, yatayda ortalar, tabanı y = 0'a koyar.</summary>
        private static void Fit(Transform root, Transform model, float height)
        {
            var b = Bounds(model);
            if (b.size.y <= 0.0001f) return;
            var s = height / b.size.y;
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
            Transform Bone(string n)
            {
                foreach (var t in model.GetComponentsInChildren<Transform>(true)) if (t.name == n) return t;
                return null;
            }
            void Socket(string name, Transform bone, Vector3 fallback)
            {
                var s = new GameObject(name).transform;
                s.SetParent(bone != null ? bone : root, false);
                if (bone == null) s.localPosition = fallback;
            }
            var b = Bounds(model);
            Socket("socket_head", Bone("head_end"), new Vector3(0f, b.max.y, 0f));
            Socket("socket_eyes", Bone("headfront"), new Vector3(0f, b.max.y * 0.7f, -0.3f));
            Socket("socket_body", Bone("Spine01"), new Vector3(0f, b.max.y * 0.3f, -0.2f));
            Socket("socket_back", Bone("Spine"), new Vector3(0f, b.max.y * 0.35f, 0.2f));
            Socket("socket_hand_L", Bone("LeftHand"), new Vector3(-0.3f, 0.4f, 0f));
            Socket("socket_hand_R", Bone("RightHand"), new Vector3(0.3f, 0.4f, 0f));
        }

        /// <summary>Animasyon oynat (varsa); yoksa false.</summary>
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
