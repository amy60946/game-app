using System;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace Pofi.EditorTools
{
    /// <summary>
    /// Komut satırı / CI derlemeleri. GameCI `buildMethod: Pofi.EditorTools.BuildScript.Build` ile çağırır;
    /// hedef platform `-buildTarget`, çıktı yolu `-customBuildPath` argümanından okunur.
    /// </summary>
    public static class BuildScript
    {
        public static void Build()
        {
            var args = Environment.GetCommandLineArgs();
            string Arg(string name, string fallback)
            {
                var i = Array.IndexOf(args, name);
                return i >= 0 && i + 1 < args.Length ? args[i + 1] : fallback;
            }

            var target = EditorUserBuildSettings.activeBuildTarget;
            var path = Arg("-customBuildPath", "Build/" + target);

            ProjectSetup.Run();

            if (target == BuildTarget.iOS)
            {
                // Bundle ID: -iosBundleId (CI secret IOS_BUNDLE_ID; yoksa varsayılan), derleme no: CI çalışma numarası
                var bundle = Arg("-iosBundleId", "");
                if (!string.IsNullOrWhiteSpace(bundle)) PlayerSettings.SetApplicationIdentifier(UnityEditor.Build.NamedBuildTarget.iOS, bundle.Trim());
                var buildNo = System.IO.File.Exists("Assets/_Pofi/Resources/build_number.txt") ? System.IO.File.ReadAllText("Assets/_Pofi/Resources/build_number.txt").Trim() : "1";
                PlayerSettings.iOS.buildNumber = int.TryParse(buildNo, out _) ? buildNo : "1";
                Debug.Log($"[Pofi] iOS: {PlayerSettings.GetApplicationIdentifier(UnityEditor.Build.NamedBuildTarget.iOS)} {PlayerSettings.bundleVersion} ({PlayerSettings.iOS.buildNumber})");
            }

            if (target == BuildTarget.WebGL)
            {
                // 26 Ekim 2026 (derleme 147, önizleme iPhone'da çöktü): WebGL varsayılanı DXT; iPhone tarayıcısı DXT okuyamaz, Unity her
                // dokuyu açılışta sıkıştırmasız RGBA'ya çevirir (~200 MB doku → 1 GB üstü bellek). ASTC iPhone'da sıkışık kalır;
                // masaüstü tarayıcıda (bulut ekran görüntüleri) Unity yine açar, yalnız yavaşlar.
                EditorUserBuildSettings.webGLBuildSubtarget = WebGLTextureSubtarget.ASTC;
                Debug.Log("[Pofi] WebGL doku biçimi: " + EditorUserBuildSettings.webGLBuildSubtarget);
            }

            if (target == BuildTarget.Android)
            {
                // M0: imzasız/debug APK yeterli (kullanıcı şimdilik yalnızca iPhone kullanıyor).
                EditorUserBuildSettings.buildAppBundle = false;
                if (!path.EndsWith(".apk")) path += "/pofi-adasi.apk";
            }

            var options = new BuildPlayerOptions
            {
                scenes = EditorBuildSettings.scenes.Where(s => s.enabled).Select(s => s.path).ToArray(),
                locationPathName = path,
                target = target,
                options = BuildOptions.None,
            };
            Debug.Log($"[Pofi] Derleniyor: {target} → {path}");
            var report = BuildPipeline.BuildPlayer(options);
            var s = report.summary;
            Debug.Log($"[Pofi] Sonuç: {s.result}, boyut {s.totalSize / (1024f * 1024f):0.0} MB, süre {s.totalTime}");
            if (s.result != BuildResult.Succeeded) EditorApplication.Exit(1);
        }
    }
}
