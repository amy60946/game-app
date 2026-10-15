using Pofi.Core;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.UI
{
    /// <summary>Her ekranın sağ üstünde (coin rozetinin solunda) müzik aç/kapa: ♪; kapalıyken üstü çizili.</summary>
    public sealed class MusicButton : MonoBehaviour
    {
        private GameObject _slash;
        private GameBootstrap _app;

        public static MusicButton Create(Transform overlay, GameBootstrap app)
        {
            var b = Candy.Round(overlay, Candy.Blue, null, 92f, new Vector2(1f, 1f), new Vector2(-386f, -66f), null);
            var mb = b.gameObject.AddComponent<MusicButton>();
            mb._app = app;
            Candy.Caption(b.transform, "♪", 60, new Vector2(0.5f, 0.52f), new Vector2(92f, 92f));
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
