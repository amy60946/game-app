using Pofi.Core;
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
