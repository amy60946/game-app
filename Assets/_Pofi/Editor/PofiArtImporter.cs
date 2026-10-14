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
        private static readonly string[] Loops = { "idle", "walk", "run", "sleep", "swim" };

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
            m.meshCompression = ModelImporterMeshCompression.Medium;
            var isAnim = Path.GetFileNameWithoutExtension(assetPath).Contains("@");
            if (IsPet)
            {
                m.animationType = ModelImporterAnimationType.Legacy;
                m.importAnimation = isAnim;
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
            }
            m.clipAnimations = clips;
        }

        private void OnPreprocessTexture()
        {
            if (!IsArt) return;
            var t = (TextureImporter)assetImporter;
            t.maxTextureSize = 1024;
            t.mipmapEnabled = true;
            t.textureCompression = TextureImporterCompression.Compressed;
            if (Path.GetFileNameWithoutExtension(assetPath).EndsWith("_normal"))
                t.textureType = TextureImporterType.NormalMap;
            else
                t.sRGBTexture = true;
        }
    }
}
