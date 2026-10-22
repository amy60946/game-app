using UnityEngine;

namespace Pofi.UI
{
    /// <summary>
    /// Öğretici/bilgilendirici baloncukların ortak canlılığı (XP takibi S5, 22 Ekim 2026): yavaşça yukarı-aşağı süzülür
    /// (±Amp, 1,6 sn) ve hafifçe nefes alır (%95–105). Konumu ya da ölçeği her karede başka bir kod yazıyorsa (ör. dünyadaki
    /// nesnenin üstünü izleyen baloncuk) onun değerinin üstüne eklenir. <see cref="Calm"/>: çocuk öğrendikten sonra hareket
    /// küçülür (sürekli zıplayan baloncuk yorar). Zaman ölçeğinden bağımsızdır.
    /// </summary>
    public sealed class Hover : MonoBehaviour
    {
        public const float Period = 1.6f;
        public float Amp = 8f;            // piksel (tuval)
        public float Breath = 0.05f;      // ölçek payı
        private float _phase, _calm = 1f, _calmTarget = 1f;
        private Vector2 _basePos, _appliedPos;
        private Vector3 _baseScale, _appliedScale;
        private bool _init;

        public static Hover On(Component c, float amp = 8f, float breath = 0.05f)
        {
            var h = c.GetComponent<Hover>();
            if (h == null) h = c.gameObject.AddComponent<Hover>();
            h.Amp = amp; h.Breath = breath;
            return h;
        }

        /// <summary>true: hareket %35'e iner (öğrenildi); false: tam canlı.</summary>
        public Hover Calm(bool calm) { _calmTarget = calm ? 0.35f : 1f; return this; }

        private void Awake() { _phase = Random.value * Period; }

        private void LateUpdate()
        {
            var rt = transform as RectTransform;
            if (rt == null) return;
            // başka kod bu kare konum/ölçek yazdıysa onu taban al; yazmadıysa tabanı koru
            if (!_init || rt.anchoredPosition != _appliedPos) _basePos = rt.anchoredPosition;
            if (!_init || transform.localScale != _appliedScale) _baseScale = transform.localScale;
            _init = true;

            _calm = Mathf.MoveTowards(_calm, _calmTarget, Time.unscaledDeltaTime);
            var a = (Time.unscaledTime + _phase) / Period * Mathf.PI * 2f;
            var bob = Mathf.Sin(a) * Amp * _calm;
            var s = 1f + Mathf.Sin(a * 0.5f + 0.7f) * Breath * _calm;   // nefes süzülmenin yarı hızında: iki hareket üst üste binip titremez

            rt.anchoredPosition = _basePos + new Vector2(0f, bob);
            transform.localScale = new Vector3(_baseScale.x * s, _baseScale.y * s, _baseScale.z);
            _appliedPos = rt.anchoredPosition;
            _appliedScale = transform.localScale;
        }

        private void OnDisable()
        {
            // devre dışı kalırken tabana dön (yeniden açılınca kaymış başlamasın)
            if (!_init) return;
            var rt = transform as RectTransform;
            if (rt != null && rt.anchoredPosition == _appliedPos) rt.anchoredPosition = _basePos;
            if (transform.localScale == _appliedScale) transform.localScale = _baseScale;
            _init = false;
        }
    }
}
