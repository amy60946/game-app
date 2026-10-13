using System.Collections.Generic;
using Pofi.Logic.Cosmetics;
using Pofi.Logic.Data;
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
        public static void Apply(Transform pet, PetSpeciesDef def, IEnumerable<ItemDef> items)
        {
            var old = pet.Find(RootName);
            if (old != null)
            {
                foreach (var r in old.GetComponentsInChildren<Renderer>())
                    foreach (var m in r.sharedMaterials) if (m != null) Object.Destroy(m);
                Object.Destroy(old.gameObject);
            }
            var root = new GameObject(RootName).transform;
            root.SetParent(pet, false);
            if (items == null) return;
            foreach (var item in items)
            {
                if (item == null) continue;
                var fit = CosmeticFit.Evaluate(def, item);
                if (!fit.Allowed) continue;
                Build(pet, root, item, fit.Variant ?? "normal");
            }
            foreach (var c in root.GetComponentsInChildren<Collider>()) Object.Destroy(c);
        }

        private static void Build(Transform pet, Transform root, ItemDef item, string variant)
        {
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
}
