using System;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace Pofi.UI
{
    /// <summary>
    /// Sürükle-bırak eşya (ör. yiyecek, sabun): basılı tutup sürükleyince simgenin kopyası parmağı izler; bırakınca
    /// <see cref="Dropped"/> ekran konumuyla çağrılır (hedef üstündeyse true döndürür). Dokunup bırakmak <see cref="Tapped"/> çağırır.
    /// </summary>
    public sealed class DragItem : MonoBehaviour, IBeginDragHandler, IDragHandler, IEndDragHandler, IPointerClickHandler
    {
        public string IconId;
        public RectTransform Layer;                 // kopyanın çizileceği katman (ekran kökü)
        public Func<Vector2, bool> Dropped;
        /// <summary>Sürüklerken her konumda (ör. bahçede tohumu tarlaların üstünden geçirince ekim, D2).</summary>
        public Action<Vector2> Dragging;
        public Action Tapped;
        private RectTransform _ghost;
        private bool _dragging;

        public void OnBeginDrag(PointerEventData e)
        {
            _dragging = true;
            _ghost = Ui.IconImage(Layer, IconId, Vector2.zero, 150f);
            if (_ghost != null) _ghost.gameObject.AddComponent<Shadow>().effectDistance = new Vector2(0f, -10f);
            Move(e.position);
            transform.localScale = Vector3.one * 0.85f;
        }

        public void OnDrag(PointerEventData e) { Move(e.position); Dragging?.Invoke(e.position); }

        private void Move(Vector2 screen)
        {
            if (_ghost == null) return;
            var k = Layer.rect.width / Mathf.Max(1f, Screen.width);
            _ghost.anchoredPosition = screen * k + new Vector2(0f, 60f);   // parmağın biraz üstünde (görünsün)
        }

        public void OnEndDrag(PointerEventData e)
        {
            _dragging = false;
            transform.localScale = Vector3.one;
            if (_ghost != null) Destroy(_ghost.gameObject);
            Dropped?.Invoke(e.position);
        }

        public void OnPointerClick(PointerEventData e)
        {
            if (!_dragging && !e.dragging) Tapped?.Invoke();
        }
    }

    /// <summary>Yukarı süzülüp kaybolan yazı (ör. "+5 ★").</summary>
    public sealed class FloatUp : MonoBehaviour
    {
        private float _t;
        private Vector2 _start;
        private Graphic[] _g;
        private void Start() { _start = ((RectTransform)transform).anchoredPosition; _g = GetComponentsInChildren<Graphic>(); }
        private void Update()
        {
            _t += Time.unscaledDeltaTime / 1.6f;
            ((RectTransform)transform).anchoredPosition = _start + new Vector2(0f, 90f * _t);
            foreach (var g in _g) { var c = g.color; c.a = 1f - Mathf.Clamp01((_t - 0.5f) * 2f); g.color = c; }
            if (_t >= 1f) Destroy(gameObject);
        }
    }
}
