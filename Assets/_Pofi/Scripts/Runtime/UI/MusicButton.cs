using Pofi.Core;
using Pofi.Logic.State;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.UI
{
    /// <summary>
    /// Her ekranın sağ üstünde (coin rozetinin solunda; pencerelerde çarpının solundaki coin rozetinin de solunda) müzik aç/kapa.
    /// Görünüş oyun içindekiyle aynı (24 Ekim 2026, kullanıcı): avatar menüsündeki gibi krem şeker düğme + 3B nota simgesi.
    /// Kapalıyken üstünde beyaz kenarlı çapraz kırmızı çizgi (<see cref="Candy.OffSlash"/>); çizgi oluşturulurken ve her
    /// durum değişiminde müziğin gerçek durumundan ayarlanır (ilk karede yanlış görünmez).
    /// </summary>
    public sealed class MusicButton : MonoBehaviour
    {
        private const float Size = 92f;

        private GameObject _slash;
        private Image _icon;
        private GameBootstrap _app;
        private GameState _appliedFor;   // tercihi uygulanan kayıt (başka çocuk / yeni oturum: yeniden uygulanır)
        private bool _chosenBeforeSignIn, _shownOff;
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
            // oyun içindeki (avatar menüsü) müzik düğmesiyle aynı yapı: krem yuvarlak gövde, gölgeli nota simgesi
            var b = Candy.Round(overlay, Candy.White, "ui_music", Size, new Vector2(1f, 1f), new Vector2(DefaultX, -66f), null);
            b.name = "MusicButton";
            var mb = b.gameObject.AddComponent<MusicButton>();
            mb._app = app;
            _instance = mb;
            var ic = b.transform.Find("Icon ui_music");
            mb._icon = ic != null ? ic.GetComponent<Image>() : null;
            mb._slash = Candy.OffSlash(b.transform, Size * 0.86f);
            b.onClick.AddListener(mb.Toggle);
            mb.Sync(true);   // ilk karede (Update'ten önce) doğru: müzik açıksa çizgi yok
            return mb;
        }

        private void Toggle()
        {
            var st = _app != null ? _app.State : null;
            var vol = Audio.Music.On ? 0f : Audio.Music.DefaultVolume;
            Audio.Music.SetVolume(vol);
            if (st != null) { st.Settings.MusicVolume = vol; _app.Save(); }
            else _chosenBeforeSignIn = true;   // giriş ekranında seçildi: oturum açılınca kayda yazılır (eski tercih ezmesin)
            Sync(true);
        }

        /// <summary>Çizgiyi (ve sönük simgeyi) müziğin gerçek durumuna getirir; yalnız değişince dokunur.</summary>
        private void Sync(bool force = false)
        {
            var off = !Audio.Music.On;
            if (!force && off == _shownOff) return;
            _shownOff = off;
            if (_slash != null) _slash.SetActive(off);
            if (_icon != null) _icon.color = off ? new Color(0.8f, 0.82f, 0.86f, 1f) : Color.white;
        }

        private void Update()
        {
            // oturum açılınca (ya da kayıt değişince) tercihi uygula; giriş ekranında yeni seçildiyse o seçim kayda yazılır
            var st = _app != null ? _app.State : null;
            if (st != null && st != _appliedFor)
            {
                _appliedFor = st;
                if (_chosenBeforeSignIn)
                {
                    _chosenBeforeSignIn = false;
                    st.Settings.MusicVolume = Audio.Music.On ? Audio.Music.DefaultVolume : 0f;
                    _app.Save();
                }
                else Audio.Music.SetVolume(st.Settings.MusicVolume > 0.001f ? Audio.Music.DefaultVolume : 0f);
            }
            else if (st == null) _appliedFor = null;
            Sync();   // başka yerden (avatar menüsü, ayarlar) değişse de çizgi hep doğru
        }
    }
}
