using Pofi.Core;
using Pofi.Logic.App;
using Pofi.UI;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.Screens
{
    /// <summary>Tüm ekranların tabanı: arayüz bu nesnenin altına kurulur, ekran değişince birlikte silinir.</summary>
    public abstract class ScreenBase : MonoBehaviour
    {
        protected GameBootstrap App;
        protected Theme Th => App.Theme;
        protected RectTransform Root => (RectTransform)transform;

        public void Init(GameBootstrap app)
        {
            App = app;
            Build();
        }

        protected abstract void Build();

        protected string T(string key, params object[] args) => App.Loc.Get(key, args);

        protected Text Footer() =>
            Ui.Label(Root, App.BuildLabel, Th.Font(26), new Color(1f, 1f, 1f, 0.85f), new Vector2(0.5f, 0.018f), new Vector2(1000f, 40f));

        /// <summary>Yatay düzen ölçüleri (tuval yüksekliği her zaman 1080; genişlik ≥ 1920).</summary>
        public const float NavHeight = 120f, HeaderHeight = 120f;

        /// <summary>Tuvalin güncel genişliği (yatay telefonda ~1920–2340).</summary>
        protected float Width => Root.rect.width > 1f ? Root.rect.width : 1920f;

        /// <summary>Ekran genişliğinde, alttan <paramref name="bottom"/> yukarıda, <paramref name="height"/> yüksekliğinde şerit.</summary>
        protected RectTransform Strip(string name, float bottom, float height)
        {
            var rt = Ui.Rect(Root, name, Vector2.zero, Vector2.zero);
            rt.anchorMin = new Vector2(0f, 0f); rt.anchorMax = new Vector2(1f, 0f);
            rt.pivot = new Vector2(0.5f, 0f);
            rt.sizeDelta = new Vector2(0f, height);
            rt.anchoredPosition = new Vector2(0f, bottom);
            return rt;
        }

        /// <summary>Başlık ve alt menü arasında kalan içerik alanı (kenarlardan <paramref name="side"/> boşluk).</summary>
        protected RectTransform ContentArea(string name, float side = 40f, float top = HeaderHeight, float bottom = NavHeight)
        {
            var rt = Ui.Area(Root, name, Vector2.zero, Vector2.one);
            rt.offsetMin = new Vector2(side, bottom + 10f);
            rt.offsetMax = new Vector2(-side, -(top + 10f));
            return rt;
        }

        /// <summary>Ortada sabit genişlikte, başlık ile alt menü arasını dolduran sütun (listeler için).</summary>
        protected RectTransform CenterColumn(string name, float width, float top = HeaderHeight, float bottom = NavHeight, bool backdrop = false)
        {
            var rt = Ui.Rect(Root, name, Vector2.zero, Vector2.zero);
            rt.anchorMin = new Vector2(0.5f, 0f); rt.anchorMax = new Vector2(0.5f, 1f);
            rt.pivot = new Vector2(0.5f, 0.5f);
            rt.offsetMin = new Vector2(-width / 2f, bottom + 10f);
            rt.offsetMax = new Vector2(width / 2f, -(top + 10f));
            if (backdrop) Ui.Panel(rt, new Color(0.05f, 0.2f, 0.42f, 0.38f), Th.Radius).raycastTarget = false;   // sahne üstünde okunurluk
            return rt;
        }

        /// <summary>Sağ alt köşeye (alt menünün üstüne) yerleştirilmiş düğme.</summary>
        protected Button CornerButton(string text, System.Action onClick, float width = 420f)
        {
            var b = Ui.Button(Root, Th, text, new Vector2(1f, 0f), new Vector2(width, 90f), onClick, false, default, 34, false);
            var rt = (RectTransform)b.transform;
            rt.pivot = new Vector2(1f, 0f);
            rt.anchoredPosition = new Vector2(-36f, NavHeight + 20f);
            return b;
        }

        /// <summary>
        /// Alt menü kaldırıldı (14 Ekim 2026): ada ana merkez. Her ekranın sol altında geri düğmesi: evin alt sayfaları
        /// (defter, ayarlar, süsle) Evim'e, diğerleri adaya döner. Adanın kendisinde düğme yok.
        /// </summary>
        protected void NavBar(AppPage current)
        {
            if (App.Page == AppPage.Map) return;
            var home = App.Page == AppPage.Settings || App.Page == AppPage.Album || App.Page == AppPage.Decorate;
            var target = home ? AppPage.Home : AppPage.Map;
            Candy.Pill(Root, Candy.Blue, T(home ? "hud.home" : "hud.back"), new Vector2(0f, 0f), new Vector2(250f, 100f), new Vector2(160f, 66f),
                () => App.Open(target), home ? "home_bed" : "decor_palm", 42);
        }

        private void TaskBadge(Transform button)
        {
            var badge = Ui.Rect(button, "Badge", new Vector2(0.92f, 0.92f), new Vector2(56f, 56f));
            Ui.Panel(badge, Th.Danger, 28f).raycastTarget = false;
            var text = Ui.Label(badge, "", Th.Font(30), Color.white, new Vector2(0.5f, 0.5f), new Vector2(56f, 56f), FontStyle.Bold);
            var live = badge.gameObject.AddComponent<TaskBadgeView>();
            live.Init(App, text);
        }

        /// <summary>Üst başlık şeridi + sağda coin rozeti. Coin metnini döndürür.</summary>
        protected Text Header(string title)
        {
            // Şerit yok: başlık sahne üstünde kenarlı yazı, coin sağ üstte rozet (14 Ekim 2026 arayüz kararı)
            var t = Candy.Caption(Root, title, 64, new Vector2(0f, 1f), new Vector2(900f, 110f), new Vector2(480f, -62f));
            t.alignment = TextAnchor.MiddleLeft;
            var coins = Candy.Badge(Root, "ui_coin", App.State.Wallet.Available.ToString(), new Vector2(1f, 1f), new Vector2(1f, 1f), new Vector2(-30f, -20f), 84f, 250f);
            coins.gameObject.AddComponent<CoinLive>().Init(App, coins);   // coin sayısı her zaman görünür ve güncel (festival vb. ekranlarda boş kalıyordu)
            return coins;
        }

        protected Text CoinPill(Transform parent, Vector2 anchor)
        {
            var coin = Ui.Rect(parent, "Coins", anchor, new Vector2(230f, 84f));
            Ui.Panel(coin, Theme.Hex("#FFD23F"), 42f).raycastTarget = false;
            var dot = Ui.Rect(coin, "Icon", new Vector2(0.2f, 0.5f), new Vector2(54f, 54f));
            if (Ui.IconImage(coin, "ui_coin", new Vector2(0.2f, 0.5f), 70f) != null) Object.Destroy(dot.gameObject);
            else Ui.Panel(dot, Theme.Hex("#F5A300"), 27f).raycastTarget = false;
            return Ui.Label(coin, App.State.Wallet.Available.ToString(), Th.Font(46), Theme.Hex("#5A3B00"), new Vector2(0.62f, 0.5f), new Vector2(150f, 80f), FontStyle.Bold);
        }

        /// <summary>Ekranı karartan ortalanmış kutu (onay, ebeveyn kapısı, panel). Kökü döndürür; kutuya .GetChild(0) ile erişilir.</summary>
        protected RectTransform Modal(float height, out RectTransform box)
        {
            var root = Ui.Fill(Root, "Modal");
            root.gameObject.AddComponent<Image>().color = new Color(0f, 0.08f, 0.2f, 0.5f);
            box = Ui.Rect(root, "Box", new Vector2(0.5f, 0.5f), new Vector2(960f, Mathf.Min(height, 980f)));
            Candy.Shell(box, new Color(1f, 0.99f, 0.96f)).raycastTarget = true;   // kabarık beyaz kutu
            box.GetComponent<Image>().raycastTarget = true;
            return root;
        }

        /// <summary>
        /// Oyun içi görevler (sağ üst "Görev"; kullanıcı kararı 14 Ekim 2026): seviyeye göre açılan günlük görevler, her biri yıldız (XP) verir.
        /// Ebeveynin gerçek hayat görevleri ayrı: adadaki "Ev Görevleri" panosunda.
        /// </summary>
        protected void QuestPanel()
        {
            Logic.App.Activity.EnsureQuests(App.State, App.Data, App.Levels, App.LocalNow);
            var root = Modal(760f, out var box);
            Ui.Label(box, T("home.daily"), Th.Font(60), Th.Text, new Vector2(0.5f, 0.88f), new Vector2(880f, 90f), FontStyle.Bold);
            var i = 0;
            foreach (var id in App.State.DailyQuests.Ids)
            {
                var q = System.Linq.Enumerable.FirstOrDefault(App.Data.DailyQuests, x => x.Id == id);
                if (q == null) continue;
                var y = 0.7f - i * 0.17f;
                var done = App.State.DailyQuests.Claimed.Contains(id);
                var prog = Logic.Meta.DailyQuests.Progress(q, App.State.Counters);
                Ui.Label(box, q.Text, Th.Font(40), done ? Theme.Hex("#2E9E4F") : Th.Text, new Vector2(0.4f, y), new Vector2(640f, 70f), FontStyle.Bold, TextAnchor.MiddleLeft);
                // ödül: yıldız simgesi + XP (coin değil: oyun içi görevler yıldız verir)
                Ui.IconImage(box, "ui_star", new Vector2(0.77f, y), 54f);
                Ui.Label(box, T("xp.star", Logic.App.Activity.QuestXp(App.State, App.Levels, q)), Th.Font(36), Th.Text, new Vector2(0.83f, y), new Vector2(110f, 60f), FontStyle.Bold);
                Ui.Label(box, done ? T("home.daily_done") : prog + "/" + q.Target, Th.Font(34), Th.SubtleText, new Vector2(0.93f, y), new Vector2(120f, 60f), FontStyle.Bold);
                var bar = Ui.Bar(box, new Vector2(0.5f, y - 0.055f), new Vector2(860f, 16f), new Color(0f, 0f, 0f, 0.08f), Th.Primary, 8f);
                Ui.SetBar(bar, (float)prog / q.Target);
                i++;
            }
            // günlük sandık (S2): üç görev bitince bir kez açılır; şans oranları her zaman görünür
            var dq = App.State.DailyQuests;
            var ready = Logic.Meta.DailyChest.Ready(dq);
            Ui.IconImage(box, "ui_gift", new Vector2(0.1f, 0.22f), 84f);
            Ui.Label(box, T(dq.ChestOpened ? "chest.opened" : ready ? "chest.open_hint" : "chest.locked"), Th.Font(34), Th.Text,
                new Vector2(0.43f, 0.245f), new Vector2(560f, 56f), FontStyle.Bold, TextAnchor.MiddleLeft);
            Ui.Label(box, T("chest.odds"), Th.Font(26), Th.SubtleText, new Vector2(0.43f, 0.19f), new Vector2(560f, 44f), FontStyle.Normal, TextAnchor.MiddleLeft);
            if (ready)
            {
                var b = Ui.Button(box, Th, T("chest.open"), new Vector2(0.86f, 0.22f), new Vector2(220f, 96f), () =>
                {
                    Destroy(root.gameObject);
                    var level = App.Levels.LevelFor(App.State.Xp.TotalXp);
                    var prize = Logic.Meta.DailyChest.Open(App.State.DailyQuests, App.Data, App.State.Inventory, level, App.State.ChildId ?? "");
                    App.Save();
                    var item = prize != null ? App.Data.Item(prize.ItemId) : null;
                    PlayChest(item != null ? Ui.Icon(item.Id) : null, () =>
                    {
                        Audio.Sfx.Play(Audio.SfxKind.Success);
                        if (item != null) Toast.Post(App.Overlay.transform, Th, T(prize.Quantity > 1 ? "chest.got_n" : "chest.got", item.Name, prize.Quantity));
                    });
                }, true, default, 40);
                Hover.On(b.GetComponent<RectTransform>(), 6f, 0.08f);
            }
            Ui.Button(box, Th, T("common.ok"), new Vector2(0.5f, 0.07f), new Vector2(360f, 100f), () => Destroy(root.gameObject), false, default, 44);
        }

        /// <summary>Sandık açılış gösterisi; adada 3B (MapScreen), başka ekranda hemen biter.</summary>
        protected virtual void PlayChest(Sprite prize, System.Action done)
        {
            StarSparkles.Around(App.Overlay.transform, new Vector2(0.5f, 0.55f), new Vector2(0.2f, 0.22f), 12, 77);
            done?.Invoke();
        }

        /// <summary>Bugün henüz tamamlanmamış oyun içi görev sayısı (Görev rozeti).</summary>
        protected int OpenQuests()
        {
            Logic.App.Activity.EnsureQuests(App.State, App.Data, App.Levels, App.LocalNow);
            return System.Linq.Enumerable.Count(App.State.DailyQuests.Ids, id => !App.State.DailyQuests.Claimed.Contains(id));
        }

        /// <summary>Ebeveyn sorusu (FR-SET-1): doğru cevapta <paramref name="onPass"/> çalışır.</summary>
        private static readonly Logic.Safety.GateLock _gateLock = new Logic.Safety.GateLock();

        protected void ParentGate(System.Action onPass, System.Action<string> onFail = null)
        {
            var wait = _gateLock.Remaining(System.DateTime.UtcNow);
            if (wait > System.TimeSpan.Zero) { onFail?.Invoke(T("gate.wait", (int)System.Math.Ceiling(wait.TotalSeconds))); return; }
            App.Stage.AllowDrag = false;
            var ch = Logic.Safety.ParentGate.Create(App.Session.AgeBand, new System.Random());
            var root = Modal(860f, out var box);
            void Close() { Destroy(root.gameObject); App.Stage.AllowDrag = true; }
            Ui.Label(box, T("gate.title"), Th.Font(56), Th.Text, new Vector2(0.5f, 0.9f), new Vector2(880f, 80f), FontStyle.Bold);
            Ui.Label(box, T("gate.hint"), Th.Font(34), Th.SubtleText, new Vector2(0.5f, 0.82f), new Vector2(880f, 60f));
            Ui.Label(box, ch.Prompt, Th.Font(48), Th.Text, new Vector2(0.5f, 0.69f), new Vector2(880f, 140f), FontStyle.Bold);
            for (var i = 0; i < ch.Options.Count; i++)
            {
                var v = ch.Options[i];
                var anchor = new Vector2(i % 2 == 0 ? 0.28f : 0.72f, i < 2 ? 0.47f : 0.29f);
                Ui.Button(box, Th, v.ToString(), anchor, new Vector2(360f, 130f), () =>
                {
                    Close();
                    if (v == ch.Answer) { _gateLock.Pass(); onPass(); }
                    else { _gateLock.Fail(System.DateTime.UtcNow); onFail?.Invoke(T("gate.wrong")); }
                }, false, default, 56, false);
            }
            Ui.Button(box, Th, "X", new Vector2(0.5f, 0.09f), new Vector2(160f, 100f), Close, false, default, 48);
        }

        /// <summary>
        /// Kamerayı, petin ekranda istenen yerde durması için konumlar: yatay merkez <paramref name="x01"/>,
        /// ayaklar <paramref name="feet01"/>, kafa üstü <paramref name="top01"/> (0–1 ekran oranları). Ekran en-boy oranına uyar.
        /// </summary>
        protected void PetCamera(float x01, float feet01, float top01, float height = World.PetModels.RealHeight)
        {
            var cam = App.Stage.Camera;
            const float fov = 34f;
            var tanV = Mathf.Tan(fov * 0.5f * Mathf.Deg2Rad);
            var aspect = Mathf.Max(1.2f, (float)Screen.width / Mathf.Max(1, Screen.height));
            var tFeet = (feet01 - 0.5f) * 2f * tanV;
            var tTop = (top01 - 0.5f) * 2f * tanV;
            var d = height / Mathf.Max(0.05f, tTop - tFeet);
            var cy = -tFeet * d;
            var cx = -(x01 - 0.5f) * 2f * tanV * aspect * d;
            App.Stage.SetCamera(new Vector3(cx, cy, -d), 0f, fov);
            if (cam != null) cam.fieldOfView = fov;
        }

        /// <summary>Konuşma balonu (petin üstünde); kısa süre sonra kaybolur.</summary>
        protected SpeechBubble Bubble(Vector2 anchor) => SpeechBubble.Create(Root, Th, anchor);
    }

    /// <summary>Görevler sekmesindeki sayaç: yapılmayı bekleyen görev sayısı; senkron sonrası kendini günceller.</summary>
    public sealed class TaskBadgeView : MonoBehaviour
    {
        private GameBootstrap _app;
        private Text _text;
        private float _t;

        public void Init(GameBootstrap app, Text text) { _app = app; _text = text; Refresh(); }

        private void Update()
        {
            _t += Time.unscaledDeltaTime;
            if (_t > 0.5f) { _t = 0f; Refresh(); }
        }

        private void Refresh()
        {
            if (_app == null || _app.State == null) return;
            var open = 0;
            foreach (var t in _app.State.Tasks.Tasks)
                if (t.Status == Logic.Tasks.ChildTaskStatus.Assigned && !t.IsMissed(_app.LocalNow)) open++;
            _text.text = open.ToString();
            var img = GetComponent<Image>();
            if (img != null) img.enabled = open > 0;
            _text.enabled = open > 0;
        }
    }

    /// <summary>Pet konuşma baloncuğu: turuncu şeker panel, alt kuyruk, oyun yazı tarzı; genişlik yazıya göre.</summary>
    /// <summary>Coin rozeti metnini güncel tutar (alışveriş, onay, senkron sonrası).</summary>
    public sealed class CoinLive : MonoBehaviour
    {
        private GameBootstrap _app;
        private Text _text;
        private int _shown = -1;
        public void Init(GameBootstrap app, Text text) { _app = app; _text = text; }
        private void Update()
        {
            if (_app == null || _app.State == null) return;
            var n = _app.State.Wallet.Available;
            if (n != _shown) { _shown = n; _text.text = n.ToString(); }
        }
    }

    public sealed class SpeechBubble : MonoBehaviour
    {
        private CandyBanner _banner;
        private CanvasGroup _group;
        private float _left;

        public static SpeechBubble Create(Transform parent, Theme th, Vector2 anchor)
        {
            var banner = Candy.Banner(parent, Candy.Orange, null, anchor, Vector2.zero, 980f, 40, true);
            var b = banner.gameObject.AddComponent<SpeechBubble>();
            b._banner = banner;
            b._group = banner.gameObject.AddComponent<CanvasGroup>();
            b._group.alpha = 0f;
            b._group.blocksRaycasts = false;
            Hover.On(banner, 4f, 0.015f);   // bilgilendirici baloncuk canlı (S5)
            return b;
        }

        public void Say(string text, float seconds = 3.5f)
        {
            if (string.IsNullOrEmpty(text)) return;
            _banner.SetText(text);
            _left = seconds;
            transform.localScale = Vector3.one * 0.85f;
        }

        private void Update()
        {
            _left -= Time.deltaTime;
            var target = _left > 0f ? 1f : 0f;
            _group.alpha = Mathf.MoveTowards(_group.alpha, target, Time.deltaTime * 5f);
            var s = Mathf.Lerp(transform.localScale.x, 1f, 1f - Mathf.Exp(-12f * Time.deltaTime));
            transform.localScale = new Vector3(s, s, 1f);
        }
    }
}
