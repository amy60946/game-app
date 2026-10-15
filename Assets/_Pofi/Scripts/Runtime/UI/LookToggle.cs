using Pofi.World;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.UI
{
    /// <summary>Görsel stil çalışması: alt ortada "Stil: Yeni / Eski" düğmesi (her ekranda). Onaydan sonra kaldırılacak.</summary>
    public sealed class LookToggle : MonoBehaviour
    {
        private Transform _overlay;
        private Button _button;

        public static void Create(Transform overlay)
        {
            if (!Look.StudyToggle) return;
            var go = new GameObject("LookToggle", typeof(RectTransform));
            go.transform.SetParent(overlay, false);
            var rt = (RectTransform)go.transform;
            rt.anchorMin = Vector2.zero; rt.anchorMax = Vector2.one; rt.offsetMin = rt.offsetMax = Vector2.zero;
            var t = go.AddComponent<LookToggle>();
            t._overlay = rt;
            t.Build();
        }

        private void Build()
        {
            if (_button != null) Destroy(_button.gameObject);
            var on = Look.Stylized;
            _button = Candy.Pill(_overlay, on ? Candy.Gold : Candy.Blue, on ? "Stil: Yeni" : "Stil: Eski",
                new Vector2(0.5f, 0f), new Vector2(250f, 72f), new Vector2(0f, 128f), () => { Look.Set(!Look.Stylized); Build(); }, null, 32);
        }
    }
}
