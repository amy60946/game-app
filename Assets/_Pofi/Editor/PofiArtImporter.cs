using System.IO;
using UnityEditor;
using UnityEngine;

namespace Pofi.EditorTools
{
    /// <summary>
    /// Meshy'den gelen sanat varlıklarının içe aktarma ayarları (Resources/Pets, Resources/Env).
    /// - Modeller: malzeme içe aktarılmaz (çalışma anında URP Lit kurulur), ölçek dosyadan.
    /// - Petler: Legacy animasyon; "pet_01@idle.fbx" dosyasındaki klip "idle" adını alır, döngüsel klipler loop.
    /// - Dokular: *_normal → normal haritası; en fazla 1024 px, mobil sıkıştırma.
    /// </summary>
    public sealed class PofiArtImporter : AssetPostprocessor
    {
        // Ayar değişince artırılır: CI'daki önbellekli Library varlıkları yeni ayarlarla yeniden içe aktarır.
        public override uint GetVersion() => 15;   // 15: uzay kıyafetleri 1024   // 14: koşu oyunu Env/rs_* dokuları 1024, Ay arazisi/krater 2048   // 13: eşyalar okunabilir (gövde giysisi vücuda deri olarak bağlanır)   // 12: evre petleri okunabilir (eşya yerleşimi gerçek ağı ölçer)   // 11: evre klasörleri (Okti) kırpılmaz   // 9: idle 2–98, 10: Resources/UI (v3 arayüz parçaları)

        private static readonly string[] Loops = { "idle", "walk", "run", "sleep", "swim" };

        // idle: Meshy klibi 18–80. kareler arasında gövdeyi ±45° sağa sola çeviriyor (dolap/evde pet arkasını dönüyordu, 15 Ekim 2026);
        // yalnız baştaki sakin kısım döngülenir, nefes alma Stage/PetLife tarafından verilir.
        /// <summary>Klip başına gerçek hareket aralığı (kare, 24 fps; art/meshy/anim_ranges.json ölçümü, 12 petin hepsinde aynı).</summary>
        private static readonly System.Collections.Generic.Dictionary<string, Vector2> ClipFrames = new System.Collections.Generic.Dictionary<string, Vector2>
        {
            // idle: ölçülen hareket 2–98. kare (4 sn, döngü hatası 0.01). Önceki 2–14 kesimi yarım saniyelik, başa uymayan bir
            // döngüydü: pet seçme ekranında "takılıp sıçrıyor" gibi görünüyordu (kullanıcı geri bildirimi, 19 Ekim 2026).
            { "walk", new Vector2(2f, 27f) }, { "run", new Vector2(2f, 17f) }, { "idle", new Vector2(2f, 98f) },
            { "sleep", new Vector2(2f, 139f) }, { "wave", new Vector2(2f, 130f) },
        };

        private bool IsStagePet
        {
            get
            {
                var dir = Path.GetFileName(Path.GetDirectoryName(assetPath) ?? "");
                return dir.EndsWith("_yavru") || dir.EndsWith("_genc") || dir.EndsWith("_yetiskin");
            }
        }

        private bool IsPet => assetPath.Replace('\\', '/').Contains("/Resources/Pets/");
        private bool IsArt => IsPet || assetPath.Replace('\\', '/').Contains("/Resources/Env/") || assetPath.Replace('\\', '/').Contains("/Resources/Items/");

        private void OnPreprocessModel()
        {
            if (!IsArt) return;
            var m = (ModelImporter)assetImporter;
            m.materialImportMode = ModelImporterMaterialImportMode.None;
            m.useFileScale = true;
            m.importCameras = false;
            m.importLights = false;
            // evre petleri: CosmeticModels deri ağını pişirip gerçek boyu/yüzü ölçer; eşyalar: gövde giysisi vücuttan kemik ağırlığı alır (SkinToBody)
            // Gezegen Koşusu Ay arazisi/krateri okunabilir: oyunda çarpıştırıcı olur, ayrıntı katmanı (MoonField) taşları zemine oturtur
            var moonGround = assetPath.Replace('\\', '/').Contains("/Resources/Env/rs_ground") || assetPath.Replace('\\', '/').Contains("/Resources/Env/rs_crater");
            m.isReadable = IsStagePet || assetPath.Replace('\\', '/').Contains("/Resources/Items/") || moonGround;
            // çevre modellerinde normal haritası var: yüksek sıkıştırma UV/teğetleri kaydırıp pişmiş dikişleri belli ediyordu
            m.meshCompression = assetPath.Replace('\\', '/').Contains("/Resources/Env/") ? ModelImporterMeshCompression.Low : ModelImporterMeshCompression.High;
            var isAnim = Path.GetFileNameWithoutExtension(assetPath).Contains("@");
            // uzay takımlarının evre derileri (Items/<id>/skin_<evre>.fbx): vücudun kemik ağırlıklarıyla gelir; temel giysi gibi Legacy
            // iskelet (deri ağı ve kemikler korunsun, animasyon yok)
            if (!IsPet && assetPath.Replace('\\', '/').Contains("/Resources/Items/") && Path.GetFileName(assetPath).StartsWith("skin_"))
            {
                m.animationType = ModelImporterAnimationType.Legacy;
                m.importAnimation = false;
                m.preserveHierarchy = true;
                return;
            }
            if (IsPet)
            {
                m.animationType = ModelImporterAnimationType.Legacy;
                m.importAnimation = isAnim;
                // Model ve animasyon dosyalarında kök düğüm aynı kalsın: aksi halde Unity boş kökü modelde siler ama
                // animasyonlu kökü korur → kemik yolları uyuşmaz, hiçbir animasyon oynamaz (14 Ekim 2026 önizlemesi).
                m.preserveHierarchy = true;
                m.generateAnimations = ModelImporterGenerateAnimations.GenerateAnimations;
            }
            else
            {
                m.animationType = ModelImporterAnimationType.None;
                m.importAnimation = false;
            }
        }

        private void OnPreprocessAnimation()
        {
            if (!IsPet) return;
            var file = Path.GetFileNameWithoutExtension(assetPath);
            var at = file.IndexOf('@');
            if (at < 0) return;
            var clipName = file.Substring(at + 1);
            var m = (ModelImporter)assetImporter;
            var clips = m.defaultClipAnimations;
            var loop = System.Array.IndexOf(Loops, clipName) >= 0;
            for (var i = 0; i < clips.Length; i++)
            {
                clips[i].name = clipName;
                clips[i].loopTime = loop;
                clips[i].wrapMode = loop ? WrapMode.Loop : WrapMode.Once;
                // Meshy klipleri 10 sn uzunluğunda ama hareket yalnız baştaki kısımda (yürüme 2–27. kare); geri kalanı donuk.
                // Kırpılmazsa döngü 10 sn sürer: pet iki adım atıp kayıyormuş gibi görünüyordu. Ölçüm: art/scripts/anim_ranges.py
                // Meshy web sitesinin "All Animations" klipleri (Okti, evre klasörleri) zaten tam döngü: kırpılmaz
                if (!IsStagePet && ClipFrames.TryGetValue(clipName, out var fr))
                {
                    clips[i].firstFrame = Mathf.Max(clips[i].firstFrame, fr.x);
                    clips[i].lastFrame = Mathf.Min(clips[i].lastFrame, fr.y);
                }
            }
            m.clipAnimations = clips;
        }

        private void OnPreprocessTexture()
        {
            if (assetPath.Replace('\\', '/').Contains("/Resources/Games/") || assetPath.Replace('\\', '/').Contains("/Resources/Art/") || assetPath.Replace('\\', '/').Contains("/Resources/UI/"))
            {
                // kodla üretilmiş 3B arayüz görselleri (art/scripts/ui_games.py, keyart.py): şeffaf, mipmapsiz
                var gi = (TextureImporter)assetImporter;
                gi.alphaIsTransparency = true;
                gi.mipmapEnabled = false;
                // tam ekran sahne arka planları (Art/, Games/*_bg — ör. Ceviz Yakala kumsalı, art/scripts/coconut_scene.py) 2048
                var fullScreen = assetPath.Contains("/Resources/Art/") || Path.GetFileNameWithoutExtension(assetPath).EndsWith("_bg");
                gi.maxTextureSize = fullScreen ? 2048 : 512;
                gi.npotScale = TextureImporterNPOTScale.None;
                gi.sRGBTexture = true;
                gi.textureCompression = TextureImporterCompression.Compressed;
                return;
            }
            if (assetPath.Replace('\\', '/').Contains("/Resources/Icons/"))
            {
                var ti = (TextureImporter)assetImporter;
                ti.alphaIsTransparency = true;
                ti.mipmapEnabled = false;
                ti.maxTextureSize = 256;
                ti.sRGBTexture = true;
                ti.textureCompression = TextureImporterCompression.Compressed;
                return;
            }
            if (!IsArt) return;
            var t = (TextureImporter)assetImporter;
            if (Path.GetFileName(assetPath).StartsWith("g_"))
            {
                // kodla üretilmiş modellerin palet dokusu (art/code3d/kit.py export_palette_fbx): her renk 8 px'lik kare,
                // UV kare ortasında → mipmap/sıkıştırma renkleri karıştırmasın
                t.mipmapEnabled = false;
                t.textureCompression = TextureImporterCompression.Uncompressed;
                t.filterMode = FilterMode.Point;
                t.sRGBTexture = true;
                t.maxTextureSize = 256;
                return;
            }
            if (Path.GetFileName(assetPath).StartsWith("ground_"))
            {
                // v6 ada zemini (art/code3d/v6/bake_game.py): 200 m'ye 2048 px (10 cm/px); alfa = kum ağırlığı (gölgelendirici)
                var isMask = Path.GetFileNameWithoutExtension(assetPath).EndsWith("_mask");   // kaldırım maskesi: doğrusal, 1024
                t.maxTextureSize = isMask ? 1024 : 2048;
                t.mipmapEnabled = true;
                t.sRGBTexture = !isMask;
                t.alphaSource = TextureImporterAlphaSource.FromInput;
                t.alphaIsTransparency = false;
                t.wrapMode = TextureWrapMode.Clamp;
                t.anisoLevel = 4;
                t.textureCompression = TextureImporterCompression.Compressed;
                t.crunchedCompression = false;
                return;
            }
            if (Path.GetFileName(assetPath).StartsWith("floor_"))
            {
                // Evim zemini (art/scripts/home_floor.py, 24 Ekim 2026): 7,4 m'ye 2048 px (kum, kabuk, hasır boyalı); kamera zemine
                // yatık bakar → anizotropik süzme. Yeni dosya: ilk içe aktarmada bu ayar uygulanır (sürüm artırılmadı).
                t.maxTextureSize = 2048;
                t.mipmapEnabled = true;
                t.sRGBTexture = true;
                t.wrapMode = TextureWrapMode.Clamp;
                t.anisoLevel = 4;
                t.textureCompression = TextureImporterCompression.Compressed;
                t.crunchedCompression = false;
                return;
            }
            var normal = Path.GetFileNameWithoutExtension(assetPath).EndsWith("_normal");
            // Telefon/WebGL boyutu (14 Ekim 2026: veri 88 MB'tı): pet rengi 1024, diğer her şey 512.
            // Crunch kapalı: CI kapsayıcısında crnlib iş parçacığı (sem_wait) Unity'yi çökertti (derleme 46).
            // kodla yenilenen yapılar (b_*, adacık; art/code3d/export_game.py): pişirilmiş ayrıntı 1024'te korunur
            var file = Path.GetFileName(assetPath);
            var building = assetPath.Replace('\\', '/').Contains("/Resources/Env/") && (file.StartsWith("b_") || file.StartsWith("island_chunk"));
            // v6 ağaçları (art/code3d/v6/proxy_bake.py): taç yaprak dokusu taslaktan pişirilir, 1024'te korunur
            var tree = assetPath.Replace('\\', '/').Contains("/Resources/Env/t_") && !normal;
            // 3B adalılar (Kıskaç, Mavi, Pus, Tosbi, Pıtır, Hışır; GB18: "detaylı 3D olsun"): yüz ve kabuk ayrıntısı 1024'te korunur
            var resident = (assetPath.Replace('\\', '/').Contains("/Resources/Env/res_") || assetPath.Replace('\\', '/').Contains("/Resources/Env/palm/")) && !normal;   // + ayrıntılı palmiye (palm_v2)
            // tapınak avlusu (30 × 22 m, tek doku; art/code3d/v6/temple_game.py): eskitme/fener ayrıntısı 1024'te siliniyordu (24 Ekim 2026)
            var hero = file.StartsWith("b_temple") && !normal;
            // Gezegen Koşusu (25 Ekim 2026; art/code3d/runner): yol, korkuluk, kapı, Ay üssü 1024; Ay arazisi ve krater köprüsü
            // (40–80 m'ye tek doku, kamera hemen üstünde) 2048 — kullanıcı: "hız, derinlik ve ayrıntı en iyi şekilde geçsin"
            var runnerPath = assetPath.Replace('\\', '/').Contains("/Resources/Env/rs_");
            var runnerGround = runnerPath && (file.StartsWith("rs_ground") || file.StartsWith("rs_crater")) && !normal;
            // uzay kıyafetleri (26 Ekim 2026; art/code3d/space_wear): kask, takım dikişleri, rozetler 512'de siliniyordu; kask camı saydam (RGBA)
            var space = System.Text.RegularExpressions.Regex.IsMatch(assetPath.Replace('\\', '/'),
                "/Resources/Items/(outfit_(astro|pilot|star)|hat_(astro_helmet|pilot_goggles|star_antenna)|back_(astro_pack|pilot_jetpack|star_cape))/");
            t.maxTextureSize = hero || runnerGround ? 2048 : (IsPet && !normal) || building || tree || resident || runnerPath || space ? 1024 : 512;
            t.mipmapEnabled = true;
            t.textureCompression = TextureImporterCompression.Compressed;
            t.crunchedCompression = false;
            if (normal)
                t.textureType = TextureImporterType.NormalMap;
            else
                t.sRGBTexture = true;
        }
    }
}
