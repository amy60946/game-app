using Pofi.Logic.Core;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.Core
{
    /// <summary>
    /// Açılış sahnesindeki tek bileşen. M0'da boru hattını kanıtlayan basit bir ekran kurar:
    /// gökyüzü degrade arka plan, başlık, sürüm ve 360° dönen yer tutucu Pofi.
    /// Sahne ve arayüz koddan kurulur; böylece proje Unity Editor açılmadan CI'da üretilebilir.
    /// </summary>
    public sealed class GameBootstrap : MonoBehaviour
    {
        public static EventBus Events { get; private set; }

        private Transform _pet;

        private void Awake()
        {
            Application.targetFrameRate = 60;
            Events = new EventBus();
            BuildWorld();
            BuildUi();
        }

        private void Update()
        {
            if (_pet != null) _pet.Rotate(0f, 40f * Time.deltaTime, 0f, Space.World);
        }

        private void BuildWorld()
        {
            var camGo = new GameObject("Main Camera");
            camGo.tag = "MainCamera";
            var cam = camGo.AddComponent<Camera>();
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.36f, 0.78f, 0.98f);
            cam.fieldOfView = 30f;
            camGo.transform.SetPositionAndRotation(new Vector3(0f, 0.75f, -4.2f), Quaternion.Euler(6f, 0f, 0f));

            var sun = new GameObject("Sun").AddComponent<Light>();
            sun.type = LightType.Directional;
            sun.color = new Color(1f, 0.95f, 0.86f);
            sun.intensity = 1.3f;
            sun.shadows = LightShadows.Soft;
            sun.transform.rotation = Quaternion.Euler(40f, -30f, 0f);
            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(0.62f, 0.78f, 1f);
            RenderSettings.ambientEquatorColor = new Color(1f, 0.85f, 0.7f);
            RenderSettings.ambientGroundColor = new Color(0.95f, 0.8f, 0.55f);

            var lit = Resources.Load<Material>("Materials/VinylPlaceholder");
            Material Mat(Color c, float smooth = 0.75f)
            {
                var m = new Material(lit);
                m.SetColor("_BaseColor", c);
                m.SetFloat("_Smoothness", smooth);
                return m;
            }

            // Kum adacığı
            var island = Prim(PrimitiveType.Cylinder, "Island", null, new Vector3(0f, -0.05f, 0f), new Vector3(2.6f, 0.05f, 2.6f), Mat(new Color(1f, 0.86f, 0.6f), 0.2f));
            Destroy(island.GetComponent<Collider>());

            // Yer tutucu Pofi (gerçek model gelince prefab değişir; soket isimleri şimdiden doğru)
            _pet = new GameObject("pet_01_placeholder").transform;
            var orange = Mat(new Color(1f, 0.53f, 0.18f));
            var cream = Mat(new Color(1f, 0.93f, 0.8f));
            var dark = Mat(new Color(0.08f, 0.08f, 0.12f), 0.95f);
            Prim(PrimitiveType.Sphere, "body", _pet, new Vector3(0f, 0.38f, 0f), new Vector3(0.62f, 0.6f, 0.55f), orange);
            Prim(PrimitiveType.Sphere, "belly", _pet, new Vector3(0f, 0.36f, -0.2f), new Vector3(0.4f, 0.42f, 0.2f), cream);
            Prim(PrimitiveType.Sphere, "head", _pet, new Vector3(0f, 1.0f, 0f), new Vector3(0.95f, 0.85f, 0.85f), orange);
            Prim(PrimitiveType.Capsule, "ear_L", _pet, new Vector3(-0.2f, 1.55f, 0.05f), new Vector3(0.18f, 0.35f, 0.12f), orange).transform.localRotation = Quaternion.Euler(0f, 0f, 12f);
            Prim(PrimitiveType.Capsule, "ear_R", _pet, new Vector3(0.2f, 1.55f, 0.05f), new Vector3(0.18f, 0.35f, 0.12f), orange).transform.localRotation = Quaternion.Euler(0f, 0f, -12f);
            Prim(PrimitiveType.Sphere, "eye_L", _pet, new Vector3(-0.17f, 1.05f, -0.38f), new Vector3(0.14f, 0.18f, 0.08f), dark);
            Prim(PrimitiveType.Sphere, "eye_R", _pet, new Vector3(0.17f, 1.05f, -0.38f), new Vector3(0.14f, 0.18f, 0.08f), dark);
            Prim(PrimitiveType.Sphere, "tail", _pet, new Vector3(0f, 0.3f, 0.33f), new Vector3(0.3f, 0.3f, 0.3f), cream);
            Prim(PrimitiveType.Capsule, "foot_L", _pet, new Vector3(-0.15f, 0.06f, -0.05f), new Vector3(0.18f, 0.08f, 0.22f), orange);
            Prim(PrimitiveType.Capsule, "foot_R", _pet, new Vector3(0.15f, 0.06f, -0.05f), new Vector3(0.18f, 0.08f, 0.22f), orange);
            foreach (var s in new[] { "socket_head", "socket_eyes", "socket_body", "socket_back", "socket_hand_L", "socket_hand_R" })
                new GameObject(s).transform.SetParent(_pet, false);
            foreach (var c in _pet.GetComponentsInChildren<Collider>()) Destroy(c);
            _pet.rotation = Quaternion.Euler(0f, 180f, 0f);
        }

        private static GameObject Prim(PrimitiveType type, string name, Transform parent, Vector3 pos, Vector3 scale, Material mat)
        {
            var go = GameObject.CreatePrimitive(type);
            go.name = name;
            if (parent != null) go.transform.SetParent(parent, false);
            go.transform.localPosition = pos;
            go.transform.localScale = scale;
            go.GetComponent<Renderer>().sharedMaterial = mat;
            return go;
        }

        private static void BuildUi()
        {
            var canvasGo = new GameObject("Canvas");
            var canvas = canvasGo.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            var scaler = canvasGo.AddComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1080f, 1920f);
            scaler.matchWidthOrHeight = 0.5f;

            var font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            Label(canvas.transform, font, "Pofi Adası", 110, FontStyle.Bold, new Color(1f, 1f, 1f), new Vector2(0.5f, 0.86f));
            Label(canvas.transform, font, "Çok yakında burada bir ada seni bekliyor", 40, FontStyle.Normal, new Color(1f, 1f, 1f, 0.92f), new Vector2(0.5f, 0.8f));
            var build = Resources.Load<TextAsset>("build_number");
            Label(canvas.transform, font, GameVersion.Display(build != null ? build.text.Trim() : null), 30, FontStyle.Normal, new Color(0.1f, 0.2f, 0.35f, 0.8f), new Vector2(0.5f, 0.06f));
        }

        private static void Label(Transform parent, Font font, string text, int size, FontStyle style, Color color, Vector2 anchor)
        {
            var go = new GameObject(text);
            go.transform.SetParent(parent, false);
            var t = go.AddComponent<Text>();
            t.font = font;
            t.text = text;
            t.fontSize = size;
            t.fontStyle = style;
            t.color = color;
            t.alignment = TextAnchor.MiddleCenter;
            t.horizontalOverflow = HorizontalWrapMode.Overflow;
            var shadow = go.AddComponent<Shadow>();
            shadow.effectColor = new Color(0.05f, 0.2f, 0.45f, 0.35f);
            shadow.effectDistance = new Vector2(0f, -4f);
            var rt = t.rectTransform;
            rt.anchorMin = rt.anchorMax = anchor;
            rt.sizeDelta = new Vector2(1000f, size * 1.6f);
        }
    }
}
