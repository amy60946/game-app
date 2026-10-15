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
        public override uint GetVersion() => 5;

        private static readonly string[] Loops = { "idle", "walk", "run", "sleep", "swim" };

        /// <summary>Klip başına gerçek hareket aralığı (kare, 24 fps; art/meshy/anim_ranges.json ölçümü, 12 petin hepsinde aynı).</summary>
        private static readonly System.Collections.Generic.Dictionary<string, Vector2> ClipFrames = new System.Collections.Generic.Dictionary<string, Vector2>
        {
            { "walk", new Vector2(2f, 27f) }, { "run", new Vector2(2f, 17f) }, { "idle", new Vector2(2f, 98f) },
            { "sleep", new Vector2(2f, 139f) }, { "wave", new Vector2(2f, 130f) },
        };

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
            m.isReadable = false;
            m.meshCompression = ModelImporterMeshCompression.High;
            var isAnim = Path.GetFileNameWithoutExtension(assetPath).Contains("@");
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
                if (ClipFrames.TryGetValue(clipName, out var fr))
                {
                    clips[i].firstFrame = Mathf.Max(clips[i].firstFrame, fr.x);
                    clips[i].lastFrame = Mathf.Min(clips[i].lastFrame, fr.y);
                }
            }
            m.clipAnimations = clips;
        }

        private void OnPreprocessTexture()
        {
            if (assetPath.Replace('\\', '/').Contains("/Resources/Games/") || assetPath.Replace('\\', '/').Contains("/Resources/Art/"))
            {
                // kodla üretilmiş 3B arayüz görselleri (art/scripts/ui_games.py, keyart.py): şeffaf, mipmapsiz
                var gi = (TextureImporter)assetImporter;
                gi.alphaIsTransparency = true;
                gi.mipmapEnabled = false;
                gi.maxTextureSize = assetPath.Contains("/Resources/Art/") ? 2048 : 512;
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
            var normal = Path.GetFileNameWithoutExtension(assetPath).EndsWith("_normal");
            // Telefon/WebGL boyutu (14 Ekim 2026: veri 88 MB'tı): pet rengi 1024, diğer her şey 512.
            // Crunch kapalı: CI kapsayıcısında crnlib iş parçacığı (sem_wait) Unity'yi çökertti (derleme 46).
            t.maxTextureSize = IsPet && !normal ? 1024 : 512;
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
