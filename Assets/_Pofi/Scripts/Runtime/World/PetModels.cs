using Pofi.Logic.Data;
using Pofi.Logic.Progression;
using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// 12 yer tutucu pet: renkli primitiflerden, konsept blockout'larının (art/scripts/pets.py) ayırt edici
    /// özellikleriyle. Gerçek modeller gelince aynı soket adlarını taşıyan prefab'larla değiştirilecek.
    /// Yön: yüz −Z (kameraya bakar), ayaklar y = 0. Ölçü "Genç" evre; evre ölçeği kökte uygulanır.
    /// </summary>
    public static class PetModels
    {
        private static Material _base;

        public static readonly string[] Sockets = { "socket_head", "socket_eyes", "socket_body", "socket_back", "socket_hand_L", "socket_hand_R" };

        public static float StageScale(GrowthStage s) => s == GrowthStage.Yavru ? 0.8f : s == GrowthStage.Yetiskin ? 1.17f : 1f;

        /// <summary>Gerçek modelin hedef boyu (kulak/anten dahil), yer tutucuyla aynı çerçeve.</summary>
        public const float RealHeight = 1.75f;

        public static Transform Build(PetSpeciesDef def, Transform parent)
        {
            var real = RealAssets.Pet(def.Id, parent, RealHeight);
            if (real != null) return real;

            var root = new GameObject(def.Id + "_placeholder").transform;
            root.SetParent(parent, false);
            var b = new Builder(root, Hex(def.MainColor), Hex(def.AccentColor));
            switch (def.Id)
            {
                case "pet_01": Pofi(b); break;
                case "pet_02": Mavi(b); break;
                case "pet_03": Kurbi(b); break;
                case "pet_04": Mimi(b); break;
                case "pet_05": Piti(b); break;
                case "pet_06": Boncuk(b); break;
                case "pet_07": Tosbi(b); break;
                case "pet_08": Piko(b); break;
                case "pet_09": Fifi(b); break;
                case "pet_10": Arlo(b); break;
                case "pet_11": Lolo(b); break;
                case "pet_12": Benli(b); break;
                default: Standard(b, 1f); break;
            }
            foreach (var s in Sockets) new GameObject(s).transform.SetParent(root, false);
            Place(root, "socket_head", new Vector3(0f, b.HeadY + b.HeadR, 0f));
            Place(root, "socket_eyes", new Vector3(0f, b.HeadY + 0.05f, -b.HeadR * 0.95f));
            Place(root, "socket_body", new Vector3(0f, 0.4f, -0.3f));
            Place(root, "socket_back", new Vector3(0f, 0.45f, 0.3f));
            Place(root, "socket_hand_L", new Vector3(-0.36f, 0.36f, -0.08f));
            Place(root, "socket_hand_R", new Vector3(0.36f, 0.36f, -0.08f));
            foreach (var c in root.GetComponentsInChildren<Collider>()) Object.Destroy(c);
            return root;
        }

        private static void Place(Transform root, string socket, Vector3 pos) => root.Find(socket).localPosition = pos;

        // ---- ortak gövde ----
        private static void Standard(Builder b, float headScale, bool belly = true)
        {
            b.S("body", new Vector3(0f, 0.4f, 0f), new Vector3(0.62f, 0.6f, 0.56f), b.Main);
            if (belly) b.S("belly", new Vector3(0f, 0.38f, -0.2f), new Vector3(0.42f, 0.44f, 0.22f), b.Accent);
            b.HeadY = 1.0f; b.HeadR = 0.45f * headScale;
            b.S("head", new Vector3(0f, b.HeadY, 0f), new Vector3(0.95f, 0.85f, 0.85f) * headScale, b.Main);
            Face(b, 1.03f, 0.37f * headScale);
            b.C("arm_L", new Vector3(-0.32f, 0.42f, -0.02f), new Vector3(0.16f, 0.16f, 0.16f), b.Main, new Vector3(0f, 0f, -35f));
            b.C("arm_R", new Vector3(0.32f, 0.42f, -0.02f), new Vector3(0.16f, 0.16f, 0.16f), b.Main, new Vector3(0f, 0f, 35f));
            Feet(b, b.Main);
        }

        private static void Face(Builder b, float y, float depth)
        {
            b.S("eye_L", new Vector3(-0.17f, y, -depth), new Vector3(0.14f, 0.18f, 0.08f), b.Dark);
            b.S("eye_R", new Vector3(0.17f, y, -depth), new Vector3(0.14f, 0.18f, 0.08f), b.Dark);
            b.S("glint_L", new Vector3(-0.15f, y + 0.04f, -depth - 0.035f), new Vector3(0.045f, 0.05f, 0.02f), b.White);
            b.S("glint_R", new Vector3(0.19f, y + 0.04f, -depth - 0.035f), new Vector3(0.045f, 0.05f, 0.02f), b.White);
            b.S("blush_L", new Vector3(-0.27f, y - 0.1f, -depth + 0.04f), new Vector3(0.12f, 0.06f, 0.04f), b.Blush);
            b.S("blush_R", new Vector3(0.27f, y - 0.1f, -depth + 0.04f), new Vector3(0.12f, 0.06f, 0.04f), b.Blush);
        }

        private static void Feet(Builder b, Material m)
        {
            b.C("foot_L", new Vector3(-0.15f, 0.07f, -0.05f), new Vector3(0.2f, 0.09f, 0.24f), m, new Vector3(90f, 0f, 0f));
            b.C("foot_R", new Vector3(0.15f, 0.07f, -0.05f), new Vector3(0.2f, 0.09f, 0.24f), m, new Vector3(90f, 0f, 0f));
        }

        // ---- türler ----
        private static void Pofi(Builder b)
        {
            Standard(b, 1f);
            var inner = b.M(Hex("#FFB38A"));
            foreach (var s in new[] { -1f, 1f })
            {
                b.C("ear_" + (s < 0 ? "L" : "R"), new Vector3(0.2f * s, 1.58f, 0.04f), new Vector3(0.2f, 0.36f, 0.12f), b.Main, new Vector3(0f, 0f, -12f * s));
                b.C("ear_in_" + (s < 0 ? "L" : "R"), new Vector3(0.205f * s, 1.58f, -0.015f), new Vector3(0.11f, 0.28f, 0.05f), inner, new Vector3(0f, 0f, -12f * s));
            }
            b.S("tail", new Vector3(0f, 0.36f, 0.36f), new Vector3(0.34f, 0.34f, 0.36f), b.Main);
            b.S("tail_tip", new Vector3(0f, 0.46f, 0.52f), new Vector3(0.2f, 0.2f, 0.2f), b.Accent);
        }

        private static void Mavi(Builder b)
        {
            var orange = b.M(Hex("#FF9A2E"));
            b.S("body", new Vector3(0f, 0.62f, 0f), new Vector3(0.95f, 1.2f, 0.85f), b.Main);
            b.S("mask", new Vector3(0f, 0.72f, -0.18f), new Vector3(0.74f, 0.95f, 0.55f), b.Accent);
            b.HeadY = 0.86f; b.HeadR = 0.4f;
            Face(b, 0.9f, 0.43f);
            b.S("beak", new Vector3(0f, 0.76f, -0.47f), new Vector3(0.18f, 0.1f, 0.16f), orange);
            b.C("flipper_L", new Vector3(-0.5f, 0.6f, 0f), new Vector3(0.14f, 0.34f, 0.24f), b.Main, new Vector3(0f, 0f, -25f));
            b.C("flipper_R", new Vector3(0.5f, 0.6f, 0f), new Vector3(0.14f, 0.34f, 0.24f), b.Main, new Vector3(0f, 0f, 25f));
            Feet(b, orange);
        }

        private static void Kurbi(Builder b)
        {
            Standard(b, 1f);
            var plate = b.M(Hex("#FFD23F"));
            b.S("snout", new Vector3(0f, 0.92f, -0.4f), new Vector3(0.44f, 0.3f, 0.3f), b.Main);
            for (var i = 0; i < 4; i++)
            {
                var a = Mathf.Lerp(-30f, 80f, i / 3f) * Mathf.Deg2Rad;
                var p = new Vector3(0f, 1.0f + Mathf.Sin(a) * 0.48f, Mathf.Cos(a) * 0.48f);
                if (i == 3) p = new Vector3(0f, 0.58f, 0.32f);
                b.Cube("plate_" + i, p, new Vector3(0.05f, 0.18f, 0.18f), plate, new Vector3(45f, 0f, 0f));
            }
            for (var i = 0; i < 4; i++)
                b.S("tail_" + i, new Vector3(0f, 0.3f + i * 0.05f, 0.35f + i * 0.17f), Vector3.one * (0.3f - i * 0.05f), b.Main);
        }

        private static void Mimi(Builder b)
        {
            Standard(b, 1f);
            foreach (var s in new[] { -1f, 1f })
            {
                b.Cube("ear_" + (s < 0 ? "L" : "R"), new Vector3(0.27f * s, 1.36f, 0.02f), new Vector3(0.22f, 0.22f, 0.07f), b.Main, new Vector3(0f, 0f, 45f + 8f * s));
                for (var k = 0; k < 2; k++)
                    b.C("whisker_" + s + k, new Vector3(0.36f * s, 0.92f - k * 0.05f, -0.32f), new Vector3(0.012f, 0.13f, 0.012f), b.White, new Vector3(0f, 0f, 80f + k * 15f));
            }
            for (var i = 0; i < 4; i++)
                b.C("tail_" + i, new Vector3(0.04f * i, 0.36f + i * 0.13f, 0.36f + i * 0.02f), new Vector3(0.08f, 0.09f, 0.08f), b.Main, new Vector3(-10f, 0f, -10f * i));
        }

        private static void Piti(Builder b)
        {
            var orange = b.M(Hex("#FF8A1F"));
            b.S("body", new Vector3(0f, 0.62f, 0f), new Vector3(1.15f, 1.12f, 1.05f), b.Main);
            b.HeadY = 0.72f; b.HeadR = 0.56f;
            Face(b, 0.78f, 0.5f);
            b.S("beak", new Vector3(0f, 0.64f, -0.55f), new Vector3(0.16f, 0.1f, 0.14f), orange);
            for (var i = -1; i <= 1; i++)
                b.C("tuft_" + i, new Vector3(0.07f * i, 1.27f, 0f), new Vector3(0.09f, 0.14f, 0.09f), orange, new Vector3(0f, 0f, -22f * i));
            b.S("wing_L", new Vector3(-0.56f, 0.6f, 0f), new Vector3(0.12f, 0.3f, 0.26f), b.Main);
            b.S("wing_R", new Vector3(0.56f, 0.6f, 0f), new Vector3(0.12f, 0.3f, 0.26f), b.Main);
            Feet(b, orange);
        }

        private static void Boncuk(Builder b)
        {
            Standard(b, 1f);
            b.S("belly", new Vector3(0f, 0.38f, -0.24f), new Vector3(0.5f, 0.48f, 0.24f), b.Accent);
            b.S("muzzle", new Vector3(0f, 0.9f, -0.38f), new Vector3(0.3f, 0.2f, 0.16f), b.Accent);
            b.S("nose", new Vector3(0f, 0.95f, -0.46f), new Vector3(0.09f, 0.06f, 0.05f), b.Dark);
            foreach (var s in new[] { -1f, 1f })
            {
                b.S("ear_" + s, new Vector3(0.33f * s, 1.43f, 0.04f), new Vector3(0.36f, 0.36f, 0.14f), b.Main);
                b.S("ear_in_" + s, new Vector3(0.33f * s, 1.43f, -0.02f), new Vector3(0.2f, 0.2f, 0.06f), b.Accent);
            }
        }

        private static void Tosbi(Builder b)
        {
            Standard(b, 0.95f, belly: false);
            var shell = b.M(Hex("#0B5E66"));
            var spot = b.M(Hex("#7FE3D3"));
            b.S("shell", new Vector3(0f, 0.5f, 0.14f), new Vector3(0.95f, 0.78f, 0.82f), shell);
            b.S("shell_rim", new Vector3(0f, 0.36f, 0.12f), new Vector3(1.0f, 0.18f, 0.86f), spot);
            for (var i = 0; i < 5; i++)
            {
                var a = (i / 5f) * Mathf.PI * 2f;
                b.S("spot_" + i, new Vector3(Mathf.Cos(a) * 0.3f, 0.72f, 0.2f + Mathf.Sin(a) * 0.25f), new Vector3(0.18f, 0.1f, 0.18f), spot);
            }
            b.S("spot_top", new Vector3(0f, 0.88f, 0.18f), new Vector3(0.2f, 0.1f, 0.2f), spot);
        }

        private static void Piko(Builder b)
        {
            Standard(b, 1f);
            var spike = b.M(Hex("#5E3A22"));
            b.S("face", new Vector3(0f, 0.96f, -0.24f), new Vector3(0.74f, 0.66f, 0.42f), b.Accent);
            Face(b, 1.0f, 0.44f);
            b.S("nose", new Vector3(0f, 0.9f, -0.47f), new Vector3(0.09f, 0.07f, 0.06f), b.Dark);
            for (var r = 0; r < 3; r++)
            for (var i = 0; i < 7; i++)
            {
                var yaw = Mathf.Lerp(-70f, 70f, i / 6f);
                var pitch = 20f + r * 32f;
                var dir = Quaternion.Euler(-pitch, yaw, 0f) * Vector3.forward;
                var pos = new Vector3(0f, 0.95f, 0.02f) + dir * 0.43f;
                var rot = Quaternion.LookRotation(dir) * Quaternion.Euler(90f, 0f, 0f);
                b.C("spike_" + r + "_" + i, pos, new Vector3(0.1f, 0.13f, 0.1f), spike, rot.eulerAngles);
            }
        }

        private static void Fifi(Builder b)
        {
            Standard(b, 1f);
            var inner = b.M(Hex("#FFD84A"));
            foreach (var s in new[] { -1f, 1f })
            {
                b.S("ear_" + s, new Vector3(0.55f * s, 1.02f, 0.06f), new Vector3(0.12f, 0.62f, 0.5f), b.Main);
                b.S("ear_in_" + s, new Vector3(0.53f * s, 1.02f, 0.02f), new Vector3(0.06f, 0.46f, 0.36f), inner);
            }
            for (var i = 0; i < 4; i++)
                b.S("trunk_" + i, new Vector3(0f, 0.88f - i * 0.08f, -0.42f - i * 0.05f + (i == 3 ? 0.04f : 0f)), Vector3.one * (0.17f - i * 0.02f), b.Main);
        }

        private static void Arlo(Builder b)
        {
            var mane = b.M(Hex("#E8501A"));
            for (var i = 0; i < 14; i++)
            {
                var a = i / 14f * Mathf.PI * 2f;
                b.S("mane_" + i, new Vector3(Mathf.Cos(a) * 0.45f, 1.0f + Mathf.Sin(a) * 0.42f, 0.08f), Vector3.one * 0.3f, mane);
            }
            Standard(b, 1f);
            b.S("muzzle", new Vector3(0f, 0.9f, -0.38f), new Vector3(0.3f, 0.2f, 0.16f), b.Accent);
            b.S("nose", new Vector3(0f, 0.96f, -0.46f), new Vector3(0.09f, 0.06f, 0.05f), b.Dark);
            b.C("tail", new Vector3(0f, 0.36f, 0.45f), new Vector3(0.06f, 0.2f, 0.06f), b.Main, new Vector3(60f, 0f, 0f));
            b.S("tail_tuft", new Vector3(0f, 0.48f, 0.62f), Vector3.one * 0.16f, mane);
        }

        private static void Lolo(Builder b)
        {
            b.S("body", new Vector3(0f, 0.4f, 0f), new Vector3(0.62f, 0.6f, 0.56f), b.Main);
            b.C("neck", new Vector3(0f, 0.78f, 0f), new Vector3(0.3f, 0.3f, 0.3f), b.Main);
            b.HeadY = 1.2f; b.HeadR = 0.4f;
            b.S("head", new Vector3(0f, b.HeadY, 0f), new Vector3(0.8f, 0.72f, 0.76f), b.Main);
            Face(b, 1.22f, 0.33f);
            var ear = b.M(Hex("#FF9B54"));
            b.C("ear_L", new Vector3(-0.2f, 1.66f, 0f), new Vector3(0.12f, 0.24f, 0.1f), ear, new Vector3(0f, 0f, 12f));
            b.C("ear_R", new Vector3(0.2f, 1.66f, 0f), new Vector3(0.12f, 0.24f, 0.1f), ear, new Vector3(0f, 0f, -12f));
            for (var i = 0; i < 5; i++)
                b.S("wool_" + i, new Vector3((i - 2) * 0.08f, 1.55f + (i % 2) * 0.04f, 0f), Vector3.one * 0.17f, b.White);
            string[] tassels = { "#FF5A7A", "#FFC83D", "#3DC9FF" };
            for (var i = 0; i < 3; i++)
                b.S("tassel_" + i, new Vector3((i - 1) * 0.12f, 0.88f, -0.16f), Vector3.one * 0.1f, b.M(Hex(tassels[i])));
            b.C("arm_L", new Vector3(-0.32f, 0.42f, -0.02f), new Vector3(0.16f, 0.16f, 0.16f), b.Main, new Vector3(0f, 0f, -35f));
            b.C("arm_R", new Vector3(0.32f, 0.42f, -0.02f), new Vector3(0.16f, 0.16f, 0.16f), b.Main, new Vector3(0f, 0f, 35f));
            Feet(b, b.Main);
        }

        private static void Benli(Builder b)
        {
            Standard(b, 1f, belly: false);
            b.S("face", new Vector3(0f, 0.97f, -0.22f), new Vector3(0.78f, 0.68f, 0.45f), b.Accent);
            Face(b, 1.0f, 0.44f);
            foreach (var s in new[] { -1f, 1f })
            {
                b.S("elytron_" + s, new Vector3(0.17f * s, 0.5f, 0.2f), new Vector3(0.42f, 0.66f, 0.5f), b.Main);
                b.S("dot_a" + s, new Vector3(0.26f * s, 0.62f, 0.4f), Vector3.one * 0.12f, b.Dark);
                b.S("dot_b" + s, new Vector3(0.2f * s, 0.36f, 0.42f), Vector3.one * 0.1f, b.Dark);
                b.C("antenna_" + s, new Vector3(0.16f * s, 1.52f, 0f), new Vector3(0.025f, 0.12f, 0.025f), b.Dark, new Vector3(0f, 0f, -20f * s));
                b.S("antenna_tip_" + s, new Vector3(0.22f * s, 1.65f, 0f), Vector3.one * 0.08f, b.Dark);
            }
        }

        // ---- yardımcılar ----
        private static Color Hex(string h) => ColorUtility.TryParseHtmlString(h, out var c) ? c : Color.magenta;

        public static Material NewMaterial(Color c, float smooth = 0.72f)
        {
            if (_base == null) _base = Resources.Load<Material>("Materials/VinylPlaceholder");
            var m = new Material(_base);
            m.SetColor("_BaseColor", c);
            m.SetFloat("_Smoothness", smooth);
            return m;
        }

        private sealed class Builder
        {
            public readonly Transform Root;
            public readonly Material Main, Accent, Dark, White, Blush;
            public float HeadY = 1f, HeadR = 0.45f;

            public Builder(Transform root, Color main, Color accent)
            {
                Root = root;
                Main = NewMaterial(main);
                Accent = NewMaterial(accent);
                Dark = NewMaterial(new Color(0.08f, 0.08f, 0.12f), 0.95f);
                White = NewMaterial(Color.white, 0.9f);
                Blush = NewMaterial(new Color(1f, 0.55f, 0.6f), 0.4f);
            }

            public Material M(Color c) => NewMaterial(c);

            public GameObject S(string n, Vector3 p, Vector3 s, Material m) => Prim(PrimitiveType.Sphere, n, p, s, m, Vector3.zero);
            public GameObject C(string n, Vector3 p, Vector3 s, Material m, Vector3 euler = default) => Prim(PrimitiveType.Capsule, n, p, s, m, euler);
            public GameObject Cube(string n, Vector3 p, Vector3 s, Material m, Vector3 euler) => Prim(PrimitiveType.Cube, n, p, s, m, euler);

            private GameObject Prim(PrimitiveType t, string n, Vector3 p, Vector3 s, Material m, Vector3 euler)
            {
                var go = GameObject.CreatePrimitive(t);
                go.name = n;
                go.transform.SetParent(Root, false);
                go.transform.localPosition = p;
                go.transform.localRotation = Quaternion.Euler(euler);
                go.transform.localScale = s;
                go.GetComponent<Renderer>().sharedMaterial = m;
                return go;
            }
        }
    }
}
