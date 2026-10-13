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

        public const float NavHeight = 190f;

        /// <summary>Alt menü: Ev, Görevler, Dükkan, Dolap. Seçili sekme vurgulu. Ekranın altına yapışır.</summary>
        protected void NavBar(AppPage current)
        {
            var bar = Ui.Rect(Root, "Nav", new Vector2(0.5f, 0f), new Vector2(1080f, NavHeight));
            bar.pivot = new Vector2(0.5f, 0f);
            bar.anchoredPosition = Vector2.zero;
            bar.gameObject.AddComponent<Image>().color = new Color(1f, 1f, 1f, 0.97f);
            var pages = new[] { AppPage.Home, AppPage.Map, AppPage.Tasks, AppPage.Shop, AppPage.Wardrobe };
            var keys = new[] { "nav.home", "nav.map", "nav.tasks", "nav.shop", "nav.wardrobe" };
            for (var i = 0; i < pages.Length; i++)
            {
                var page = pages[i];
                var on = page == current;
                var b = Ui.Button(bar, Th, T(keys[i]), new Vector2(0.1f + i * 0.2f, 0.55f), new Vector2(196f, 120f),
                    () => { if (App.Page != page) App.Open(page); }, on, default, 34, false);
                if (page == AppPage.Tasks) TaskBadge(b.transform);
            }
        }

        private void TaskBadge(Transform button)
        {
            var open = 0;
            foreach (var t in App.State.Tasks.Tasks)
                if (t.Status == Logic.Tasks.ChildTaskStatus.Assigned && !t.IsMissed(App.LocalNow)) open++;
            if (open == 0) return;
            var badge = Ui.Rect(button, "Badge", new Vector2(0.92f, 0.92f), new Vector2(56f, 56f));
            Ui.Panel(badge, Th.Danger, 28f).raycastTarget = false;
            Ui.Label(badge, open.ToString(), Th.Font(30), Color.white, new Vector2(0.5f, 0.5f), new Vector2(56f, 56f), FontStyle.Bold);
        }

        /// <summary>Üst başlık şeridi + sağda coin rozeti. Coin metnini döndürür.</summary>
        protected Text Header(string title)
        {
            var top = Ui.Rect(Root, "Header", new Vector2(0.5f, 1f), new Vector2(1080f, 170f));
            top.pivot = new Vector2(0.5f, 1f);
            top.anchoredPosition = Vector2.zero;
            Ui.Label(top, title, Th.Font(72), Color.white, new Vector2(0.36f, 0.45f), new Vector2(700f, 120f), FontStyle.Bold, TextAnchor.MiddleLeft)
                .gameObject.AddComponent<Shadow>().effectDistance = new Vector2(0f, -5f);
            return CoinPill(top, new Vector2(0.84f, 0.45f));
        }

        protected Text CoinPill(Transform parent, Vector2 anchor)
        {
            var coin = Ui.Rect(parent, "Coins", anchor, new Vector2(230f, 84f));
            Ui.Panel(coin, Theme.Hex("#FFD23F"), 42f).raycastTarget = false;
            var dot = Ui.Rect(coin, "Icon", new Vector2(0.2f, 0.5f), new Vector2(54f, 54f));
            Ui.Panel(dot, Theme.Hex("#F5A300"), 27f).raycastTarget = false;
            return Ui.Label(coin, App.State.Wallet.Available.ToString(), Th.Font(46), Theme.Hex("#5A3B00"), new Vector2(0.62f, 0.5f), new Vector2(150f, 80f), FontStyle.Bold);
        }

        /// <summary>Ekranı karartan ortalanmış kutu (onay, ebeveyn kapısı, panel). Kökü döndürür; kutuya .GetChild(0) ile erişilir.</summary>
        protected RectTransform Modal(float height, out RectTransform box)
        {
            var root = Ui.Fill(Root, "Modal");
            root.gameObject.AddComponent<Image>().color = new Color(0f, 0.08f, 0.2f, 0.5f);
            box = Ui.Rect(root, "Box", new Vector2(0.5f, 0.5f), new Vector2(960f, height));
            Ui.Panel(box, Color.white, Th.Radius);
            return root;
        }

        /// <summary>Ebeveyn sorusu (FR-SET-1): doğru cevapta <paramref name="onPass"/> çalışır.</summary>
        protected void ParentGate(System.Action onPass, System.Action<string> onFail = null)
        {
            App.Stage.AllowDrag = false;
            var ch = Logic.Safety.ParentGate.Create(App.Session.AgeBand, new System.Random());
            var root = Modal(900f, out var box);
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
                    if (v == ch.Answer) onPass();
                    else onFail?.Invoke(T("gate.wrong"));
                }, false, default, 56, false);
            }
            Ui.Button(box, Th, "X", new Vector2(0.5f, 0.09f), new Vector2(160f, 100f), Close, false, default, 48);
        }

        /// <summary>Konuşma balonu (petin üstünde); kısa süre sonra kaybolur.</summary>
        protected SpeechBubble Bubble(Vector2 anchor) => SpeechBubble.Create(Root, Th, anchor);
    }

    public sealed class SpeechBubble : MonoBehaviour
    {
        private Text _text;
        private CanvasGroup _group;
        private float _left;

        public static SpeechBubble Create(Transform parent, Theme th, Vector2 anchor)
        {
            var rt = Ui.Rect(parent, "Bubble", anchor, new Vector2(820f, 150f));
            Ui.Panel(rt, Color.white, th.Radius).raycastTarget = false;
            var tail = Ui.Rect(rt, "Tail", new Vector2(0.5f, 0f), new Vector2(44f, 44f), new Vector2(0f, -6f));
            Ui.Panel(tail, Color.white, 8f).raycastTarget = false;
            tail.localRotation = Quaternion.Euler(0f, 0f, 45f);
            tail.SetAsFirstSibling();
            var b = rt.gameObject.AddComponent<SpeechBubble>();
            b._group = rt.gameObject.AddComponent<CanvasGroup>();
            b._group.alpha = 0f;
            b._group.blocksRaycasts = false;
            b._text = Ui.Label(rt, "", th.Font(42), th.Text, new Vector2(0.5f, 0.5f), new Vector2(760f, 130f), FontStyle.Bold);
            return b;
        }

        public void Say(string text, float seconds = 3.5f)
        {
            if (string.IsNullOrEmpty(text)) return;
            _text.text = text;
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
