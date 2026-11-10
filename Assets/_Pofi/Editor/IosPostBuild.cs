#if UNITY_IOS
using System.IO;
using UnityEditor;
using UnityEditor.Callbacks;
using UnityEditor.iOS.Xcode;

namespace Pofi.EditorTools
{
    /// <summary>
    /// iOS Xcode projesi son ayarları (TestFlight): şifreleme beyanı (yalnız standart HTTPS → muaf; "Missing Compliance" sorulmaz),
    /// görünen ad, tam ekran. Derleme sonrası Info.plist'e yazılır; Keychain için Security.framework bağlanır; gizlilik bildirimi (PrivacyInfo.xcprivacy).
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
            root.SetString("CFBundleDisplayName", "Moyo Pofi Adası");   // kullanıcı kararı 10 Kasım 2026 (productName aynı kaldı: WebGL kayıt yolu ona bağlı)
            root.SetBoolean("UIRequiresFullScreen", true);
            // QR okuma (PofiNative.mm PofiQrScan): kamera izni metni (yalnız giriş ekranında, görüntü kaydedilmez)
            root.SetString("NSCameraUsageDescription", "ParentApp'te gösterilen QR kodu okumak için kamerayı kullanırız. Görüntü kaydedilmez, gönderilmez.");
            plist.WriteToFile(plistPath);

            // Keychain (PofiNative.mm, oturum belirteci) için Security.framework
            var projPath = PBXProject.GetPBXProjectPath(path);
            var proj = new PBXProject();
            proj.ReadFromFile(projPath);
            proj.AddFrameworkToProject(proj.GetUnityFrameworkTargetGuid(), "Security.framework", false);
            AddPrivacyManifest(proj, path);
            proj.WriteToFile(projPath);
        }

        /// <summary>
        /// Uygulama gizlilik bildirimi (Apple, Mayıs 2024'ten beri zorunlu; canlıya alma 2.1). İzleme yok, reklam yok, üçüncü taraf yok.
        /// Toplanan (cihazdan çıkan) veri ortak hukuk/00-olgular "Çocuk (GameApp)": anonim oturum kimliği, oyun kaydı, ebeveyne mesaj,
        /// kullanım olayları + açılış süresi (akislar.md §9). Hepsi hesaba bağlı, amaç uygulama işlevi / analiz; izleme değil.
        /// Gerekçeli API: PlayerPrefs = NSUserDefaults (CA92.1, yalnız uygulamanın kendi verisi). Motorun kendi API'leri
        /// UnityFramework'ün bildirimindedir. App Store Connect "App Privacy" etiketi bununla aynı olmalı.
        /// </summary>
        private static void AddPrivacyManifest(PBXProject proj, string path)
        {
            const string file = "PrivacyInfo.xcprivacy";
            var doc = new PlistDocument();
            var root = doc.root;
            root.SetBoolean("NSPrivacyTracking", false);
            root.CreateArray("NSPrivacyTrackingDomains");

            var types = root.CreateArray("NSPrivacyCollectedDataTypes");
            void Collected(string type, params string[] purposes)
            {
                var d = types.AddDict();
                d.SetString("NSPrivacyCollectedDataType", type);
                d.SetBoolean("NSPrivacyCollectedDataTypeLinked", true);
                d.SetBoolean("NSPrivacyCollectedDataTypeTracking", false);
                var p = d.CreateArray("NSPrivacyCollectedDataTypePurposes");
                foreach (var x in purposes) p.AddString(x);
            }
            Collected("NSPrivacyCollectedDataTypeUserID", "NSPrivacyCollectedDataTypePurposeAppFunctionality");
            Collected("NSPrivacyCollectedDataTypeGameplayContent", "NSPrivacyCollectedDataTypePurposeAppFunctionality");
            Collected("NSPrivacyCollectedDataTypeOtherUserContent", "NSPrivacyCollectedDataTypePurposeAppFunctionality");
            Collected("NSPrivacyCollectedDataTypeProductInteraction", "NSPrivacyCollectedDataTypePurposeAnalytics");
            Collected("NSPrivacyCollectedDataTypePerformanceData", "NSPrivacyCollectedDataTypePurposeAnalytics");

            var apis = root.CreateArray("NSPrivacyAccessedAPITypes");
            var ud = apis.AddDict();
            ud.SetString("NSPrivacyAccessedAPIType", "NSPrivacyAccessedAPICategoryUserDefaults");
            ud.CreateArray("NSPrivacyAccessedAPITypeReasons").AddString("CA92.1");

            doc.WriteToFile(Path.Combine(path, file));
            if (!string.IsNullOrEmpty(proj.FindFileGuidByProjectPath(file))) return;
            var guid = proj.AddFile(file, file, PBXSourceTree.Source);
            var main = proj.GetUnityMainTargetGuid();
            proj.AddFileToBuildSection(main, proj.GetResourcesBuildPhaseByTarget(main), guid);
        }
    }
}
#endif
