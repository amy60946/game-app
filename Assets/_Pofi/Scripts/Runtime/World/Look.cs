using System;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace Pofi.World
{
    /// <summary>
    /// Görsel stil (15 Ekim 2026 çalışması, docs: CLAUDE.md "Görsel stil kararı"):
    /// yeni stil = Pofi/Toon malzemeleri (yumuşak iki ton, vinyl parlaması, ince dış çizgi) + hafif renk ayarı.
    /// Eski stil = URP Lit + ayarsız görüntü. Çalışma süresince ekrandaki "Stil" düğmesiyle karşılaştırılır; seçim cihazda kalır.
    /// </summary>
    public static class Look
    {
        private const string PrefKey = "pofi.look.stylized";

        /// <summary>Karşılaştırma düğmesi görünsün mü (yalnız stil çalışması süresince).</summary>
        public const bool StudyToggle = true;

        public static bool Stylized { get; private set; } = true;
        public static event Action Changed;

        private static Shader _toon;
        public static Shader ToonShader => _toon != null ? _toon : _toon = Shader.Find("Pofi/Toon");

        private static Volume _volume;

        /// <summary>Kamera kurulunca bir kez: renk ayarı katmanı + kayıtlı tercih.</summary>
        public static void Init(Camera cam)
        {
            try { Stylized = PlayerPrefs.GetInt(PrefKey, 1) == 1; } catch { Stylized = true; }
            if (cam != null)
            {
                var data = cam.GetUniversalAdditionalCameraData();
                if (data != null) data.renderPostProcessing = true;
            }
            var go = new GameObject("LookVolume");
            UnityEngine.Object.DontDestroyOnLoad(go);
            _volume = go.AddComponent<Volume>();
            _volume.isGlobal = true;
            _volume.priority = 1f;
            var profile = ScriptableObject.CreateInstance<VolumeProfile>();
            // canlı ama dengeli: hafif kontrast + doygunluk, çok az sıcak ton; parlama (bloom) yok — kullanıcı uyarısı
            var color = profile.Add<ColorAdjustments>();
            color.contrast.Override(10f);
            color.saturation.Override(12f);
            color.colorFilter.Override(new Color(1f, 0.985f, 0.96f));
            // kenarlarda çok hafif kararma: göz ortadaki pete gider
            var vig = profile.Add<Vignette>();
            vig.intensity.Override(0.16f);
            vig.smoothness.Override(0.5f);
            vig.color.Override(new Color(0.12f, 0.1f, 0.22f));
            _volume.sharedProfile = profile;
            Apply();
        }

        public static void Set(bool stylized)
        {
            if (Stylized == stylized) return;
            Stylized = stylized;
            try { PlayerPrefs.SetInt(PrefKey, stylized ? 1 : 0); PlayerPrefs.Save(); } catch { }
            Apply();
            Changed?.Invoke();
        }

        private static void Apply()
        {
            if (_volume != null) _volume.enabled = Stylized;
            RealAssets.ApplyLook(Stylized);
        }
    }
}
