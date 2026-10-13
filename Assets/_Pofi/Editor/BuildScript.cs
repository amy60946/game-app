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
