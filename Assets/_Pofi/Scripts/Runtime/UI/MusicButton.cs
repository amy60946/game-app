using Pofi.Core;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.UI
{
    /// <summary>Her ekranın sağ üstünde (coin rozetinin solunda; pencerelerde çarpının solundaki coin rozetinin de solunda) müzik aç/kapa: ♪; kapalıyken üstü çizili.</summary>
    public sealed class MusicButton : MonoBehaviour
    {
        private GameObject _slash;
        private GameBootstrap _app;
        private static MusicButton _instance;

        /// <summary>Varsayılan yer (adada: Ayarlar ile Harita arasında) ve pencerelerde coin rozetinin solu.</summary>
        public const float DefaultX = -386f, BesideClose = -466f;

        /// <summary>Düğmeyi sağ üstte yatayda taşır (ekran değişince <see cref="GameBootstrap.Route"/> varsayılana döndürür).</summary>
        public static void Place(float x)
        {
            if (_instance == null) return;
            var rt = (RectTransform)_instance.transform;
            rt.anchoredPosition = new Vector2(x, rt.anchoredPosition.y);
        }

        /// <summary>
        /// G sade gösterge (23 Ekim 2026, kullanıcı onayı): adada müzik avatar menüsünde; ada ekranı düğmeyi gizler,
        /// <see cref="GameBootstrap.Route"/> her ekran değişiminde geri açar. Gizliyken de kayıttaki tercih uygulanır.
        /// </summary>
        public static void SetVisible(bool on)
        {
            if (_instance == null) return;
            var g = _instance.GetComponent<CanvasGroup>();
            if (g == null) g = _instance.gameObject.AddComponent<CanvasGroup>();
            g.alpha = on ? 1f : 0f; g.interactable = on; g.blocksRaycasts = on;
        }

        /// <summary>Avatar menüsünden müzik aç/kapa.</summary>
        public static void ToggleMusic() { if (_instance != null) _instance.Toggle(); else Audio.Music.SetVolume(Audio.Music.On ? 0f : Audio.Music.DefaultVolume); }

        public static MusicButton Create(Transform overlay, GameBootstrap app)
        {
            var b = Candy.Round(overlay, Candy.Blue, null, 92f, new Vector2(1f, 1f), new Vector2(-386f, -66f), null);
            var mb = b.gameObject.AddComponent<MusicButton>();
            mb._app = app;
            _instance = mb;
            Ui.IconImage(b.transform, "ui_music", new Vector2(0.5f, 0.5f), 64f);   // ♪ yazı tipinde yoktu: düğme boş mavi küre görünüyordu
            var slash = Ui.Rect(b.transform, "Off", new Vector2(0.5f, 0.5f), new Vector2(84f, 12f));
            slash.localRotation = Quaternion.Euler(0f, 0f, 45f);
            var si = slash.gameObject.AddComponent<Image>(); si.sprite = Ui.Rounded; si.type = Image.Type.Sliced; si.color = Candy.Pink; si.raycastTarget = false;
            mb._slash = slash.gameObject;
            b.onClick.AddListener(mb.Toggle);
            mb.Sync();
            return mb;
        }

        private void Toggle()
        {
            var st = _app.State;
            var on = !Audio.Music.On;
            var vol = on ? Audio.Music.DefaultVolume : 0f;
            Audio.Music.SetVolume(vol);
            if (st != null) { st.Settings.MusicVolume = vol; _app.Save(); }
            Sync();
        }

        private void Sync() => _slash.SetActive(!Audio.Music.On);

        private void Update()
        {
            // oturum açılınca kayıttaki tercihi uygula (bir kez)
            if (_app != null && _app.State != null && !_applied)
            {
                _applied = true;
                Audio.Music.SetVolume(_app.State.Settings.MusicVolume > 0.001f ? Audio.Music.DefaultVolume : 0f);
                Sync();
            }
        }

        private bool _applied;
    }
}
