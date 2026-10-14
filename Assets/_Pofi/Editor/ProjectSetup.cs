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
        }

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
            urp.shadowDistance = 12f;
            EditorUtility.SetDirty(urp);

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
