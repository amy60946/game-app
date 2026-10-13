using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.UI
{
    /// <summary>Üstten kayan kısa bildirim ("Yeni rozet: …", "+15 XP"). Sırayla gösterilir, dokunmayı engellemez.</summary>
    public sealed class Toast : MonoBehaviour
    {
        private static Toast _instance;
        private readonly Queue<string> _queue = new Queue<string>();
        private RectTransform _box;
        private Text _text;
        private float _t = -1f;
        private const float Show = 2.4f;

        public static void Post(Transform overlay, Theme th, string text)
        {
            if (_instance == null)
            {
                var root = Ui.Fill(overlay, "Toast");
                var g = root.gameObject.AddComponent<CanvasGroup>();
                g.blocksRaycasts = false;
                _instance = root.gameObject.AddComponent<Toast>();
                _instance._box = Ui.Rect(root, "Box", new Vector2(0.5f, 1f), new Vector2(940f, 120f));
                _instance._box.pivot = new Vector2(0.5f, 1f);
                Ui.Panel(_instance._box, new Color(0.13f, 0.16f, 0.3f, 0.92f), 60f).raycastTarget = false;
                _instance._text = Ui.Label(_instance._box, "", th.Font(40), Color.white, new Vector2(0.5f, 0.5f), new Vector2(900f, 110f), FontStyle.Bold);
                _instance._box.anchoredPosition = new Vector2(0f, 200f);
            }
            _instance._queue.Enqueue(text);
        }

        private void Update()
        {
            if (_t < 0f)
            {
                if (_queue.Count == 0) return;
                _text.text = _queue.Dequeue();
                _t = 0f;
            }
            _t += Time.unscaledDeltaTime;
            var inOut = Mathf.Min(Mathf.Clamp01(_t / 0.25f), Mathf.Clamp01((Show - _t) / 0.25f));
            _box.anchoredPosition = new Vector2(0f, Mathf.Lerp(200f, -40f, Mathf.SmoothStep(0f, 1f, inOut)));
            if (_t > Show) _t = -1f;
        }
    }
}
