using System;
using System.IO;
using Pofi.Core;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.SceneManagement;

namespace Pofi.EditorTools
{
    /// <summary>
    /// "Kod olarak proje": Unity Editor'u kimse elle açmadığı için proje ayarları, URP varlıkları
    /// ve açılış sahnesi her derlemede bu betikle (idempotent) kurulur.
    /// Menüden de çalıştırılabilir: Pofi > Projeyi kur.
    /// </summary>
    public static class ProjectSetup
    {
        public const string BundleId = "com.fidan.pofi";
        private const string Root = "Assets/_Pofi";
        private const string SettingsDir = Root + "/Settings";
        private const string ResourcesDir = Root + "/Resources";
        public const string BootScene = Root + "/Scenes/Boot.unity";

        [MenuItem("Pofi/Projeyi kur")]
        public static void Run()
        {
            EnsureFolder(SettingsDir);
            EnsureFolder(ResourcesDir + "/Materials");
            EnsureFolder(Root + "/Scenes");

            ConfigurePlayer();
            ConfigureUrp();
            EnsurePlaceholderMaterial();
            WriteBuildNumber();
            EnsureBootScene();

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log("[Pofi] Proje kurulumu tamam.");
        }

        private static void ConfigurePlayer()
        {
            PlayerSettings.companyName = "Fidan";
            PlayerSettings.productName = "Pofi Adası";
            PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android, BundleId);
            PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.iOS, BundleId);
            // Yatay oyun (14 Ekim 2026 kararı): iki yatay yöne döner, dikeye dönmez
            PlayerSettings.defaultInterfaceOrientation = UIOrientation.AutoRotation;
            PlayerSettings.allowedAutorotateToLandscapeLeft = true;
            PlayerSettings.allowedAutorotateToLandscapeRight = true;
            PlayerSettings.allowedAutorotateToPortrait = false;
            PlayerSettings.allowedAutorotateToPortraitUpsideDown = false;
            PlayerSettings.colorSpace = ColorSpace.Linear;
            PlayerSettings.WebGL.compressionFormat = WebGLCompressionFormat.Gzip;
            // Sıkıştırmalı dosyalar, sunucu özel başlık göndermese de açılsın (statik barındırma).
            PlayerSettings.WebGL.decompressionFallback = true;
            PlayerSettings.WebGL.dataCaching = true;
            PlayerSettings.Android.minSdkVersion = AndroidSdkVersions.AndroidApiLevel26;
            PlayerSettings.iOS.targetOSVersionString = "15.0";
            // iOS / TestFlight (15 Ekim 2026): tam ekran, durum çubuğu gizli, sürüm; imza Xcode'da otomatik (CI: tools/ci/ios-testflight.sh)
            PlayerSettings.bundleVersion = AppVersion;
            PlayerSettings.iOS.requiresFullScreen = true;
            PlayerSettings.statusBarHidden = true;
            PlayerSettings.iOS.appleEnableAutomaticSigning = true;
            PlayerSettings.SetScriptingBackend(NamedBuildTarget.iOS, ScriptingImplementation.IL2CPP);
            PlayerSettings.SetArchitecture(NamedBuildTarget.iOS, 1);   // ARM64
            // uygulama simgesi (art/scripts/app_icon.py): tüm boyutlar bu 1024 px görselden üretilir
            AssetDatabase.ImportAsset(Root + "/Art/AppIcon.png");
            var icon = AssetDatabase.LoadAssetAtPath<Texture2D>(Root + "/Art/AppIcon.png");
            if (icon != null) PlayerSettings.SetIcons(NamedBuildTarget.Unknown, new[] { icon }, IconKind.Any);
            else Debug.LogWarning("ProjectSetup: AppIcon.png bulunamadı");
        }

        /// <summary>Mağaza sürümü (CFBundleShortVersionString); derleme numarası CI çalışma numarasıdır.</summary>
        public const string AppVersion = "0.9.0";

        private static void ConfigureUrp()
        {
            var rendererPath = SettingsDir + "/PofiRenderer.asset";
            var assetPath = SettingsDir + "/PofiURP.asset";
            var renderer = AssetDatabase.LoadAssetAtPath<UniversalRendererData>(rendererPath);
            if (renderer == null)
            {
                renderer = ScriptableObject.CreateInstance<UniversalRendererData>();
                AssetDatabase.CreateAsset(renderer, rendererPath);
            }
            var urp = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(assetPath);
            if (urp == null)
            {
                urp = UniversalRenderPipelineAsset.Create(renderer);
                AssetDatabase.CreateAsset(urp, assetPath);
            }
            urp.supportsHDR = false;          // mobil: daha ucuz
            urp.msaaSampleCount = 4;           // yuvarlak "oyuncak" kenarları yumuşak
            // gölgeler (görsel stil 15 Ekim 2026): yumuşak kenarlı ve net; harita kamerasında uzaktaki yapılar da gölge düşürsün
            urp.shadowDistance = 28f;
            urp.shadowCascadeCount = 2;
            urp.cascade2Split = 0.3f;
            urp.mainLightShadowmapResolution = 2048;
            var so = new SerializedObject(urp);
            var soft = so.FindProperty("m_SoftShadowsSupported");     // ayarlayıcı internal; varsayılanı kapalı (gölgeler sertti)
            if (soft != null) soft.boolValue = true;
            else Debug.LogWarning("ProjectSetup: m_SoftShadowsSupported bulunamadı");
            var softQ = so.FindProperty("m_SoftShadowQuality");          // orta kalite (ayarlayıcı herkese açık değil)
            if (softQ != null) softQ.intValue = (int)SoftShadowQuality.Medium;
            so.ApplyModifiedPropertiesWithoutUndo();
            EditorUtility.SetDirty(urp);
            // renk ayarı (Volume) için son işlem kaynakları: CreateInstance ile kurulan çizicide boş kalabiliyor
            if (renderer.postProcessData == null)
            {
                renderer.postProcessData = AssetDatabase.LoadAssetAtPath<PostProcessData>("Packages/com.unity.render-pipelines.universal/Runtime/Data/PostProcessData.asset");
                if (renderer.postProcessData == null) Debug.LogWarning("ProjectSetup: PostProcessData bulunamadı");
                EditorUtility.SetDirty(renderer);
            }

            GraphicsSettings.defaultRenderPipeline = urp;
            var current = QualitySettings.GetQualityLevel();
            for (var i = 0; i < QualitySettings.names.Length; i++)
            {
                QualitySettings.SetQualityLevel(i, false);
                QualitySettings.renderPipeline = urp;
            }
            QualitySettings.SetQualityLevel(current, false);
        }

        private static void EnsurePlaceholderMaterial()
        {
            var path = ResourcesDir + "/Materials/VinylPlaceholder.mat";
            if (AssetDatabase.LoadAssetAtPath<Material>(path) != null) return;
            var shader = Shader.Find("Universal Render Pipeline/Lit");
            if (shader == null) throw new Exception("URP Lit shader bulunamadı");
            var mat = new Material(shader);
            mat.SetFloat("_Smoothness", 0.75f);
            AssetDatabase.CreateAsset(mat, path);
        }

        private static void WriteBuildNumber()
        {
            // GameCI kapsayıcısına GITHUB_RUN_NUMBER geçmez; CI dosyayı derlemeden önce yazar, burada korunur.
            var file = ResourcesDir + "/build_number.txt";
            var build = Environment.GetEnvironmentVariable("GITHUB_RUN_NUMBER");
            if (string.IsNullOrEmpty(build) && File.Exists(file)) build = File.ReadAllText(file).Trim();
            if (string.IsNullOrEmpty(build)) build = "yerel";
            File.WriteAllText(file, build);
            AssetDatabase.ImportAsset(file);
        }

        private static void EnsureBootScene()
        {
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            new GameObject("Bootstrap").AddComponent<GameBootstrap>();
            EditorSceneManager.SaveScene(scene, BootScene);
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(BootScene, true) };
        }

        private static void EnsureFolder(string path)
        {
            if (AssetDatabase.IsValidFolder(path)) return;
            var parent = Path.GetDirectoryName(path)!.Replace('\\', '/');
            EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent, Path.GetFileName(path));
        }
    }
}
