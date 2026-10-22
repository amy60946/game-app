using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.UI
{
    /// <summary>
    /// Ödül uçuşu (O1, 23 Ekim 2026): kazanılan coin, Güneş Taşı ya da malzeme kazanıldığı yerden dışa saçılır (0,35 sn), kısa durur,
    /// sonra tek tek yay çizerek kendi sayacına uçar (0,07 sn arayla). Sayaç her gelişte bir dilim artar ve zıplar.
    /// Uçuşta olan miktar <see cref="Pending"/> ile sayaçtan düşülür (HUD her kare durumu yazsa da sayma görünür). Dokunmayı engellemez.
    /// </summary>
    public sealed class RewardFlight : MonoBehaviour
    {
        private static readonly Dictionary<string, int> PendingBy = new Dictionary<string, int>();
        private static readonly Dictionary<string, RectTransform> Targets = new Dictionary<string, RectTransform>();

        private sealed class Piece { public RectTransform Rt; public Vector2 From, Burst, To; public float Delay; public int Share; public bool Done; }
        private readonly List<Piece> _pieces = new List<Piece>();
        private string _kind;
        private RectTransform _target;
        private float _t;
        private const float BurstT = 0.35f, Hold = 0.2f, FlyT = 0.55f, Gap = 0.07f;

        /// <summary>Sayaç kaydı: aynı türde en son kurulan ve görünen hedef kullanılır.</summary>
        public static void Register(string kind, RectTransform target) { if (target != null) Targets[kind] = target; }

        /// <summary>Henüz sayaca ulaşmamış miktar (sayaç gösterirken düşülür).</summary>
        public static int Pending(string kind) => PendingBy.TryGetValue(kind, out var n) ? n : 0;

        /// <summary>
        /// <paramref name="from"/>: ekran pikseli. Hedef yoksa ya da görünmüyorsa parçalar yerinde parlayıp söner (sayaç hemen günceldir).
        /// </summary>
        public static void Fly(Transform overlay, string kind, string icon, int amount, Vector2 from)
        {
            if (overlay == null || amount <= 0) return;
            Targets.TryGetValue(kind, out var target);
            if (target != null && !target.gameObject.activeInHierarchy) target = null;
            var root = Ui.Fill(overlay, "RewardFlight");
            var group = root.gameObject.AddComponent<CanvasGroup>(); group.blocksRaycasts = false; group.interactable = false;
            var f = root.gameObject.AddComponent<RewardFlight>();
            f._kind = kind; f._target = target;
            var canvas = overlay.GetComponentInParent<Canvas>();
            var cam = canvas != null && canvas.renderMode != RenderMode.ScreenSpaceOverlay ? canvas.worldCamera : null;
            RectTransformUtility.ScreenPointToLocalPointInRectangle(root, from, cam, out var local);
            var to = local;
            if (target != null)
            {
                var sp = RectTransformUtility.WorldToScreenPoint(cam, target.position);
                RectTransformUtility.ScreenPointToLocalPointInRectangle(root, sp, cam, out to);
            }
            var n = Mathf.Clamp(amount, 1, Theme.ReduceMotion ? 1 : 10);
            var sprite = Ui.Icon(icon);
            for (var i = 0; i < n; i++)
            {
                var rt = Ui.Rect(root, "Piece", new Vector2(0.5f, 0.5f), new Vector2(86f, 86f));
                var img = rt.gameObject.AddComponent<Image>(); img.raycastTarget = false; img.preserveAspect = true;
                if (sprite != null) img.sprite = sprite; else { img.sprite = Ui.Rounded; img.color = Theme.Hex("#FFD23F"); }
                var a = (i / (float)n) * Mathf.PI * 2f + Random.Range(-0.3f, 0.3f);
                var r = n == 1 ? 0f : Random.Range(90f, 170f);
                var share = amount / n + (i < amount % n ? 1 : 0);
                f._pieces.Add(new Piece { Rt = rt, From = local, Burst = local + new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * r, To = to, Delay = i * Gap, Share = share });
                rt.anchoredPosition = local; rt.localScale = Vector3.zero;
            }
            if (target != null) PendingBy[kind] = Pending(kind) + amount;
            Audio.Sfx.Play(Audio.SfxKind.Coin);
        }

        private void Update()
        {
            _t += Time.unscaledDeltaTime;
            var all = true;
            foreach (var p in _pieces)
            {
                if (p.Done) continue;
                all = false;
                if (_t < BurstT)
                {
                    var k = 1f - Mathf.Pow(1f - _t / BurstT, 3f);
                    p.Rt.anchoredPosition = Vector2.LerpUnclamped(p.From, p.Burst, k);
                    p.Rt.localScale = Vector3.one * Mathf.Lerp(0.2f, 1.15f, k);
                    continue;
                }
                var ft = (_t - BurstT - Hold - p.Delay) / FlyT;
                if (ft <= 0f) { p.Rt.localScale = Vector3.one * (1.1f + Mathf.Sin(_t * 12f) * 0.04f); continue; }
                if (_target == null)
                {
                    // hedef yok: yerinde parlayıp söner
                    p.Rt.localScale = Vector3.one * Mathf.Lerp(1.1f, 0f, ft);
                    if (ft >= 1f) { p.Done = true; p.Rt.gameObject.SetActive(false); }
                    continue;
                }
                var e = ft * ft;   // ivmelenerek
                var mid = (p.Burst + p.To) * 0.5f + new Vector2(0f, 220f);
                var q = Vector2.Lerp(Vector2.Lerp(p.Burst, mid, e), Vector2.Lerp(mid, p.To, e), e);
                p.Rt.anchoredPosition = q;
                p.Rt.localScale = Vector3.one * Mathf.Lerp(1.1f, 0.7f, e);
                if (ft >= 1f)
                {
                    p.Done = true; p.Rt.gameObject.SetActive(false);
                    PendingBy[_kind] = Mathf.Max(0, Pending(_kind) - p.Share);
                    Bump.Play(_target, 0.18f);
                    Audio.Haptics.Light();
                }
            }
            if (all) Finish();
        }

        private void Finish()
        {
            if (_target != null)
            {
                var left = 0;
                foreach (var p in _pieces) if (!p.Done) left += p.Share;
                PendingBy[_kind] = Mathf.Max(0, Pending(_kind) - left);
            }
            Destroy(gameObject);
        }

        private void OnDestroy()
        {
            // ekran değişip yarıda kalırsa sayaç takılı kalmasın
            if (_target == null) return;
            var left = 0;
            foreach (var p in _pieces) if (!p.Done) { left += p.Share; p.Done = true; }
            if (left > 0) PendingBy[_kind] = Mathf.Max(0, Pending(_kind) - left);
        }
    }
}
