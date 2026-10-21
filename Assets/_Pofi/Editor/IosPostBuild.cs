#if UNITY_IOS
using System.IO;
using UnityEditor;
using UnityEditor.Callbacks;
using UnityEditor.iOS.Xcode;

namespace Pofi.EditorTools
{
    /// <summary>
    /// iOS Xcode projesi son ayarları (TestFlight): şifreleme beyanı (yalnız standart HTTPS → muaf; "Missing Compliance" sorulmaz),
    /// görünen ad, tam ekran. Derleme sonrası Info.plist'e yazılır; Keychain için Security.framework bağlanır.
    /// </summary>
    public static class IosPostBuild
    {
        [PostProcessBuild(100)]
        public static void OnPostBuild(BuildTarget target, string path)
        {
            if (target != BuildTarget.iOS) return;
            var plistPath = Path.Combine(path, "Info.plist");
            var plist = new PlistDocument();
            plist.ReadFromFile(plistPath);
            var root = plist.root;
            root.SetBoolean("ITSAppUsesNonExemptEncryption", false);
            root.SetString("CFBundleDisplayName", "Pofi Adası");
            root.SetBoolean("UIRequiresFullScreen", true);
            plist.WriteToFile(plistPath);

            // Keychain (PofiNative.mm, oturum belirteci) için Security.framework
            var projPath = PBXProject.GetPBXProjectPath(path);
            var proj = new PBXProject();
            proj.ReadFromFile(projPath);
            proj.AddFrameworkToProject(proj.GetUnityFrameworkTargetGuid(), "Security.framework", false);
            proj.WriteToFile(projPath);
        }
    }
}
#endif
