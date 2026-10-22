using UnityEngine;
using UnityEngine.UI;

namespace Pofi.UI
{
    /// <summary>Coin kazanma kutlaması: ortada büyük "+N coin", ekrana dağılan altın paralar. Dokunmayı engellemez.</summary>
    public sealed class CoinBurst : MonoBehaviour
    {
        private RectTransform[] _coins;
        private Vector2[] _vel;
        private Text _label;
        private float _t;
        private const float Duration = 2.2f;

        /// <summary>
        /// <paramref name="coins"/> &gt; 0: dağılan paralar yerine kazanılan coin ortadan sayaca uçar (O1, RewardFlight);
        /// yalnız yazı kalır. 0: eski kutlama (dağılan paralar).
        /// </summary>
        public static void Play(Transform overlay, Theme th, string text, int coins = 0)
        {
            Audio.Sfx.Play(Audio.SfxKind.Coin);
            var root = Ui.Fill(overlay, "CoinBurst");
            var cb = root.gameObject.AddComponent<CoinBurst>();
            var group = root.gameObject.AddComponent<CanvasGroup>();
            group.blocksRaycasts = false;
            group.interactable = false;
            if (coins > 0) RewardFlight.Fly(overlay, "coin", "ui_coin", coins, new Vector2(Screen.width * 0.5f, Screen.height * 0.5f));
            cb._coins = new RectTransform[Theme.ReduceMotion || coins > 0 ? 0 : 18];
            cb._vel = new Vector2[cb._coins.Length];
            for (var i = 0; i < cb._coins.Length; i++)
            {
                var c = Ui.Rect(root, "Coin", new Vector2(0.5f, 0.55f), new Vector2(70f, 70f));
                Ui.Panel(c, Theme.Hex("#FFD23F"), 35f).raycastTarget = false;
                var inner = Ui.Rect(c, "In", new Vector2(0.5f, 0.5f), new Vector2(40f, 40f));
                Ui.Panel(inner, Theme.Hex("#F5A300"), 20f).raycastTarget = false;
                var a = Random.Range(0f, Mathf.PI * 2f);
                var sp = Random.Range(700f, 1300f);
                cb._vel[i] = new Vector2(Mathf.Cos(a) * sp, Mathf.Abs(Mathf.Sin(a)) * sp + 400f);
                cb._coins[i] = c;
            }
            cb._label = Ui.Label(root, text, th.Font(110), Theme.Hex("#FFD23F"), new Vector2(0.5f, 0.6f), new Vector2(1000f, 160f), FontStyle.Bold);
            var o = cb._label.gameObject.AddComponent<Outline>();
            o.effectColor = new Color(0.45f, 0.25f, 0f, 0.9f);
            o.effectDistance = new Vector2(5f, -5f);
        }

        private void Update()
        {
            var dt = Time.unscaledDeltaTime;
            _t += dt;
            for (var i = 0; i < _coins.Length; i++)
            {
                _vel[i].y -= 2600f * dt;
                _coins[i].anchoredPosition += _vel[i] * dt;
                _coins[i].localRotation = Quaternion.Euler(0f, 0f, _t * 360f * (i % 2 == 0 ? 1f : -1f));
            }
            var pop = _t < 0.25f ? Mathf.SmoothStep(0.3f, 1.15f, _t / 0.25f) : Mathf.Lerp(1.15f, 1f, (_t - 0.25f) * 4f);
            _label.transform.localScale = Vector3.one * pop;
            var fade = Mathf.Clamp01((Duration - _t) / 0.5f);
            GetComponent<CanvasGroup>().alpha = fade;
            if (_t > Duration) Destroy(gameObject);
        }
    }
}
