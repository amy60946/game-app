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
        protected RectTransform CenterColumn(string name, float width, float top = HeaderHeight, float bottom = NavHeight)
        {
            var rt = Ui.Rect(Root, name, Vector2.zero, Vector2.zero);
            rt.anchorMin = new Vector2(0.5f, 0f); rt.anchorMax = new Vector2(0.5f, 1f);
            rt.pivot = new Vector2(0.5f, 0.5f);
            rt.offsetMin = new Vector2(-width / 2f, bottom + 10f);
            rt.offsetMax = new Vector2(width / 2f, -(top + 10f));
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

        /// <summary>Alt menü: Ev, Ada, Görevler, Dükkan, Dolap. Seçili sekme vurgulu. Ekranın altına yapışır, ortalı.</summary>
        protected void NavBar(AppPage current)
        {
            var bar = Strip("Nav", 0f, NavHeight);
            bar.gameObject.AddComponent<Image>().color = new Color(1f, 1f, 1f, 0.97f);
            var pages = new[] { AppPage.Home, AppPage.Map, AppPage.Tasks, AppPage.Shop, AppPage.Wardrobe };
            var keys = new[] { "nav.home", "nav.map", "nav.tasks", "nav.shop", "nav.wardrobe" };
            for (var i = 0; i < pages.Length; i++)
            {
                var page = pages[i];
                var on = page == current;
                var b = Ui.Button(bar, Th, T(keys[i]), new Vector2(0.5f, 0.5f), new Vector2(240f, 92f),
                    () => { if (App.Page != page) App.Open(page); }, on, new Vector2((i - 2) * 270f, 0f), 34, false);
                if (page == AppPage.Tasks) TaskBadge(b.transform);
            }
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
            var top = Ui.Rect(Root, "Header", Vector2.zero, Vector2.zero);
            top.anchorMin = new Vector2(0f, 1f); top.anchorMax = new Vector2(1f, 1f);
            top.pivot = new Vector2(0.5f, 1f);
            top.sizeDelta = new Vector2(0f, HeaderHeight);
            top.anchoredPosition = Vector2.zero;
            var t = Ui.Label(top, title, Th.Font(64), Color.white, new Vector2(0f, 0.5f), new Vector2(900f, 110f), FontStyle.Bold, TextAnchor.MiddleLeft);
            t.rectTransform.pivot = new Vector2(0f, 0.5f);
            t.rectTransform.anchoredPosition = new Vector2(48f, 0f);
            t.gameObject.AddComponent<Shadow>().effectDistance = new Vector2(0f, -5f);
            var pill = CoinPill(top, new Vector2(1f, 0.5f));
            ((RectTransform)pill.transform.parent).anchoredPosition = new Vector2(-170f, 0f);
            return pill;
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
            Ui.Panel(box, Color.white, Th.Radius);
            return root;
        }

        /// <summary>Ebeveyn sorusu (FR-SET-1): doğru cevapta <paramref name="onPass"/> çalışır.</summary>
        protected void ParentGate(System.Action onPass, System.Action<string> onFail = null)
        {
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
                    if (v == ch.Answer) onPass();
                    else onFail?.Invoke(T("gate.wrong"));
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
