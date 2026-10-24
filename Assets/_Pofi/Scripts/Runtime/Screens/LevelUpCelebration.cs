using System.Collections.Generic;
using System.Linq;
using Pofi.Core;
using Pofi.Logic.App;
using Pofi.Logic.Data;
using Pofi.Logic.Progression;
using Pofi.UI;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.Screens
{
    /// <summary>
    /// L1 penceresiz seviye atlama (23 Ekim 2026, kullanıcı onayı): ekran hafifçe kısılır (0,12 sn), yıldız ortada aşırı sıçrar
    /// (0,25 sn), 0,9 sn sonra "Seviye N!" kurdelesi ve tek ödül (seviye hediyesi eşya, <see cref="LevelGifts"/>), 1 sn sonra
    /// "Harika!". Basınca eşya Evim düğmesine uçar (1,1 sn) ve "… Evim'e gitti" notu çıkar. Ödül coin ya da Güneş Taşı olmaz;
    /// açılan yer ödül değil, adada okla gösterilir. Işınlar yarı saydam, beyaz yalnız yazıda (ekran parlamaz).
    /// </summary>
    public sealed class LevelUpCelebration : MonoBehaviour
    {
        private GameBootstrap _app;
        private LevelUp _up;
        private List<ItemDef> _gifts;
        private RectTransform _root, _star, _rays, _ribbon, _reward, _go;
        private Image _veil;
        private float _t;
        private bool _shownText, _shownGo, _closing;

        public static void Show(GameBootstrap app, LevelUp up)
        {
            World.HitStop.Do();   // A4: büyük an
            Audio.Sfx.Play(Audio.SfxKind.Success);
            var gifts = LevelGifts.Claim(app.State, app.Data, up);   // bir kez; kutlama yarıda kalsa da eşya kayıtlı
            app.Save();
            var root = Ui.Fill(app.Overlay.transform, "LevelUp");
            var c = root.gameObject.AddComponent<LevelUpCelebration>();
            c._app = app; c._up = up; c._gifts = gifts; c._root = root;
            c.Build();
        }

        private void Build()
        {
            _veil = _root.gameObject.AddComponent<Image>(); _veil.color = new Color(0.02f, 0.06f, 0.12f, 0f);   // dokunmayı tutar
            _rays = Ui.Rect(_root, "Rays", new Vector2(0.5f, 0.56f), new Vector2(980f, 980f));
            var ri = _rays.gameObject.AddComponent<RawImage>(); ri.texture = RaysTex(); ri.color = new Color(1f, 0.82f, 0.35f, 0f); ri.raycastTarget = false;
            _star = Ui.Rect(_root, "Star", new Vector2(0.5f, 0.56f), new Vector2(320f, 320f));
            var big = Skin.Plain("star_big") ?? Ui.Icon("ui_star");
            var si = _star.gameObject.AddComponent<Image>(); si.sprite = big; si.preserveAspect = true; si.raycastTarget = false;
            Candy.Caption(_star, _up.To.ToString(), 128, new Vector2(0.5f, 0.45f), new Vector2(320f, 200f), Vector2.zero, new Color(0.47f, 0.25f, 0f, 1f));
            _star.localScale = Vector3.zero;
        }

        private void Update()
        {
            var dt = Time.unscaledDeltaTime;
            _t += dt;
            if (!_closing) _veil.color = new Color(0.02f, 0.06f, 0.12f, Mathf.Min(0.42f, _t / 0.12f * 0.42f));
            var ri = _rays.GetComponent<RawImage>();
            _rays.localRotation = Quaternion.Euler(0f, 0f, -_t * 14f);
            if (!_closing) ri.color = new Color(1f, 0.82f, 0.35f, Mathf.Clamp01((_t - 0.1f) / 0.4f) * 0.32f);
            // yıldız: 0 → 1,25 (0,25 sn) → 1 (0,15 sn)
            var st = _t - 0.12f;
            var s = st <= 0f ? 0f : st < 0.25f ? Mathf.SmoothStep(0f, 1.25f, st / 0.25f) : st < 0.4f ? Mathf.Lerp(1.25f, 1f, (st - 0.25f) / 0.15f) : 1f + Mathf.Sin((st - 0.4f) * 3f) * 0.025f;
            _star.localScale = Vector3.one * s;
            if (!_shownText && _t > 1.15f) ShowText();
            if (!_shownGo && _t > 2.15f) ShowGo();
        }

        private void ShowText()
        {
            _shownText = true;
            var loc = _app.Loc;
            _ribbon = (RectTransform)Candy.Ribbon(_root, loc.Get("levelup.title", _up.To), new Vector2(0.5f, 0.56f), new Vector2(0f, -205f), 130f, 56).transform.parent;
            _ribbon.gameObject.AddComponent<PopIn>();
            var gift = _gifts.FirstOrDefault();
            if (gift != null)
            {
                // tek ödül: krem yuvarlak kart içinde eşya + "+1"
                _reward = Ui.Rect(_root, "Reward", new Vector2(0.5f, 0.56f), new Vector2(170f, 170f), new Vector2(330f, 0f));
                var bg = _reward.gameObject.AddComponent<Image>();
                if (Skin.Card != null) { Skin.Apply(bg, Skin.Card, 170f); bg.color = Color.white; }
                else { bg.sprite = Ui.Rounded; bg.type = Image.Type.Sliced; bg.color = new Color(1f, 0.96f, 0.86f); }
                bg.raycastTarget = false;
                Ui.IconImage(_reward, gift.Id, new Vector2(0.5f, 0.56f), 120f);
                Candy.Caption(_reward, "+1", 44, new Vector2(0.82f, 0.18f), new Vector2(100f, 60f));
                _reward.gameObject.AddComponent<PopIn>();
            }
            // açılan yerler ve büyüme tek satır (yer ödül değil: adada oklar oraya akar)
            var news = _up.Unlocked.Where(id => !id.StartsWith("growth_") && loc.Has("unlock." + id)).Select(id => loc.Get("unlock." + id)).Take(3).ToList();
            var line = _up.NewStage != null ? loc.Get("levelup.grew", _app.State.PetName) : news.Count > 0 ? loc.Get("levelup.new", string.Join(" · ", news)) : null;
            if (line != null) Candy.Caption(_root, line, 40, new Vector2(0.5f, 0.56f), new Vector2(1400f, 64f), new Vector2(0f, -300f));
            var sp = RectTransformUtility.WorldToScreenPoint(null, _star.position);
            StarSparkles.Around(_root, new Vector2(sp.x / Mathf.Max(1f, Screen.width), sp.y / Mathf.Max(1f, Screen.height)), new Vector2(0.16f, 0.22f), 10, _up.To, 0f);   // kutlamayla birlikte kalkar
        }

        private void ShowGo()
        {
            _shownGo = true;
            var b = Candy.Pill(_root, Candy.Green, _app.Loc.Get("levelup.ok"), new Vector2(0.5f, 0f), new Vector2(420f, 130f), new Vector2(0f, 120f), Close, null, 54);
            _go = (RectTransform)b.transform;
            _go.gameObject.AddComponent<PopIn>();
        }

        private void Close()
        {
            if (_closing) return;
            _closing = true;
            Progress.MarkCelebrated(_app.State, _up);
            _app.Save();
            var gift = _gifts.FirstOrDefault();
            if (gift != null && _reward != null)
            {
                // eşya Evim düğmesine uçar (adada); başka ekranda düğme yoksa yerinde parlayıp söner
                var map = FindAnyObjectByType<MapScreen>();
                if (map != null) RewardFlight.Register("home_gift", map.HomeTarget());
                var from = RectTransformUtility.WorldToScreenPoint(null, _reward.position);
                RewardFlight.Fly(_app.Overlay.transform, "home_gift", gift.Id, 1, from);
                Toast.Post(_app.Overlay.transform, _app.Theme, _app.Loc.Get(_gifts.Count > 1 ? "levelup.home_n" : "levelup.home", gift.Name, _gifts.Count));
            }
            Destroy(gameObject);
            if (_up.NewStage != null)
            {
                // büyüme (Sv 5 ergen, Sv 10 yetişkin): adadaysa dönüşüm sahnesi + konfeti + bilgi; başka sayfada sayfa yenilenir, kart gelir
                var stage = _up.NewStage.Value;
                var island = _app.Page == AppPage.Map ? FindAnyObjectByType<MapScreen>() : null;
                if (island == null || !island.PlayGrowUp(stage, null))
                {
                    if (_app.Page == AppPage.Home || _app.Page == AppPage.Map) _app.Route();   // büyüyen peti yeniden çiz
                    if (_app.Stage != null) _app.Stage.Hop();
                    GrowUpCard.Show(_app, stage, null);
                }
            }
        }

        private static Texture2D _rayTex;

        /// <summary>Yarı saydam ışın demeti: 14 yumuşak kenarlı dilim, merkezden dışa söner.</summary>
        private static Texture2D RaysTex()
        {
            if (_rayTex != null) return _rayTex;
            const int n = 256;
            _rayTex = new Texture2D(n, n, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, name = "level_rays" };
            var px = new Color32[n * n];
            for (var y = 0; y < n; y++)
                for (var x = 0; x < n; x++)
                {
                    var u = (x + 0.5f) / n * 2f - 1f; var v = (y + 0.5f) / n * 2f - 1f;
                    var r = Mathf.Sqrt(u * u + v * v);
                    var a = Mathf.Atan2(v, u) / (Mathf.PI * 2f) * 14f;
                    var wedge = Mathf.Clamp01(1f - Mathf.Abs(Mathf.Repeat(a, 1f) - 0.5f) * 4f);
                    var fade = Mathf.Clamp01(1f - r) * Mathf.Clamp01((r - 0.12f) * 6f);
                    px[y * n + x] = new Color(1f, 1f, 1f, wedge * fade);
                }
            _rayTex.SetPixels32(px); _rayTex.Apply();
            return _rayTex;
        }
    }
}
