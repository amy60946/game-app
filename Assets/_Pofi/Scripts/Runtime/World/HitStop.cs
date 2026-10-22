using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// Büyük anda kısa duraklama (A4, 23 Ekim 2026): oyun 0,1 sn durur, kamera hafifçe yaklaşır (görüş açısı birkaç derece daralıp
    /// yumuşakça geri döner). Sarsıntı yok: büyük sarsıntı mide bulandırır. Hareket azaltma açıksa yalnız yakınlaşma da olmaz.
    /// </summary>
    public sealed class HitStop : MonoBehaviour
    {
        private static HitStop _me;
        private float _stop, _punch;
        /// <summary>Kameranın görüş açısından düşülecek derece (MapScreen okur).</summary>
        public static float Zoom => _me != null ? _me._punch * 5f : 0f;

        public static void Do(float seconds = 0.1f)
        {
            if (UI.Theme.ReduceMotion) return;
            if (_me == null) { var go = new GameObject("HitStop"); DontDestroyOnLoad(go); _me = go.AddComponent<HitStop>(); }
            _me._stop = Mathf.Max(_me._stop, seconds);
            _me._punch = 1f;
            Time.timeScale = 0f;
        }

        private void Update()
        {
            if (_stop > 0f && (_stop -= Time.unscaledDeltaTime) <= 0f) { _stop = 0f; Time.timeScale = 1f; }
            if (_punch > 0f) _punch = Mathf.Max(0f, _punch - Time.unscaledDeltaTime / 0.7f);
        }

        private void OnDisable() { if (_stop > 0f) Time.timeScale = 1f; }
    }
}
