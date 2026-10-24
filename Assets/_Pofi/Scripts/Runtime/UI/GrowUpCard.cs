using System;
using System.Collections.Generic;
using Pofi.Core;
using Pofi.Logic.Progression;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.UI
{
    /// <summary>
    /// Büyüme kutlaması (kullanıcı, 24 Ekim 2026: "o level atlayınca karakter dans etsin, konfetiler patlasın, belki bilgi ver"):
    /// her oyuncu çocuk Okti ile başlar; Sv 5'te ergen, Sv 10'da yetişkin olur (levels.json growth). Bu kart, sahnedeki
    /// dönüşümden sonra gelir: konfeti yağar, kırmızı kurdele "Okti büyüdü!", altında bu evrenin yenilikleri, tek yeşil düğme.
    /// Adada dönüşüm sahnesi MapScreen.GrowUp'ta (dönen eski Okti → ışık → dans eden yeni Okti).
    /// </summary>
    public sealed class GrowUpCard : MonoBehaviour
    {
        private Action _done;
        private float _t;
        private RectTransform _go;

        public static GrowUpCard Show(GameBootstrap app, GrowthStage stage, Action done)
        {
            var root = Ui.Fill(app.Overlay.transform, "GrowUp");
            var c = root.gameObject.AddComponent<GrowUpCard>();
            c._done = done;
            var veil = root.gameObject.AddComponent<Image>(); veil.color = new Color(0.02f, 0.06f, 0.12f, 0.18f);   // dokunmayı tutar
            Confetti.Burst(root, 90, 4.5f);
            var loc = app.Loc;
            var title = GoldKit.Ribbon(root, loc.Get("grow.title", app.State.PetName), GoldKit.Tone.Red, 120f, 62, new Vector2(0.5f, 1f), new Vector2(0f, -150f));
            title.transform.parent.gameObject.AddComponent<PopIn>();
            // bilgi kartı: krem, altın kenar; evrenin adı + yeni hareketler + kıyafet notu
            var card = Ui.Rect(root, "Info", new Vector2(0.5f, 0f), new Vector2(980f, 190f), new Vector2(0f, 310f));
            var inner = GoldKit.RimCapsule(card, Theme.Hex("#FFF7E0"), Theme.Hex("#F4DEA8"), 7f);
            var key = stage == GrowthStage.Yetiskin ? "grow.yetiskin" : "grow.genc";
            var t1 = Ui.Label(inner, loc.Get(key, app.State.PetName), 40, Theme.Hex("#6B3F0E"), new Vector2(0.5f, 0.66f), new Vector2(900f, 64f), FontStyle.Bold);
            t1.raycastTarget = false;
            var t2 = Ui.Label(inner, loc.Get(key + "_moves") + "  ·  " + loc.Get("grow.clothes"), 30, Theme.Hex("#8A5A22"), new Vector2(0.5f, 0.3f), new Vector2(900f, 50f), FontStyle.Bold);
            t2.raycastTarget = false;
            card.gameObject.AddComponent<PopIn>();
            c._go = (RectTransform)Candy.Pill(root, Candy.Green, loc.Get("levelup.ok"), new Vector2(0.5f, 0f), new Vector2(420f, 130f), new Vector2(0f, 120f), c.Close, null, 54).transform;
            c._go.gameObject.SetActive(false);
            Audio.Sfx.Play(Audio.SfxKind.Success);
            Audio.Haptics.Medium();
            return c;
        }

        private void Update()
        {
            _t += Time.unscaledDeltaTime;
            if (_go != null && !_go.gameObject.activeSelf && _t > 1.4f) { _go.gameObject.SetActive(true); _go.gameObject.AddComponent<PopIn>(); }
        }

        private void Close()
        {
            Destroy(gameObject);
            var d = _done; _done = null;
            d?.Invoke();
        }
    }

    /// <summary>Konfeti (ParticleSystem yok): renkli küçük şeritler yukarıdan dönerek, sallanarak düşer; süre bitince söner.</summary>
    public sealed class Confetti : MonoBehaviour
    {
        private sealed class Bit { public RectTransform Rt; public Vector2 V; public float Spin, Flip, Phase, Sway; }
        private readonly List<Bit> _bits = new List<Bit>();
        private float _t, _life;
        private static readonly string[] Cols = { "#FF5D73", "#FFC93C", "#3FA9F5", "#7ED957", "#B57BFF", "#FF8A3D", "#FFFFFF" };

        public static void Burst(Transform parent, int count, float life)
        {
            if (Theme.ReduceMotion) count = Mathf.Min(count, 20);
            var root = Ui.Fill(parent, "Confetti");
            var c = root.gameObject.AddComponent<Confetti>();
            c._life = life;
            var cg = root.gameObject.AddComponent<CanvasGroup>(); cg.blocksRaycasts = false; cg.interactable = false;
            var w = ((RectTransform)parent).rect.width; if (w < 10f) w = 1920f;
            for (var i = 0; i < count; i++)
            {
                var rt = Ui.Rect(root, "Bit", new Vector2(0f, 1f), new Vector2(UnityEngine.Random.Range(14f, 24f), UnityEngine.Random.Range(26f, 40f)));
                var img = rt.gameObject.AddComponent<Image>(); img.color = Theme.Hex(Cols[i % Cols.Length]); img.raycastTarget = false;
                if (i % 3 == 0) { img.sprite = Ui.Rounded; img.type = Image.Type.Sliced; rt.sizeDelta = Vector2.one * 22f; }   // yuvarlak pul
                rt.anchoredPosition = new Vector2(UnityEngine.Random.Range(0f, w), UnityEngine.Random.Range(20f, 520f));
                c._bits.Add(new Bit
                {
                    Rt = rt, V = new Vector2(UnityEngine.Random.Range(-60f, 60f), -UnityEngine.Random.Range(260f, 520f)),
                    Spin = UnityEngine.Random.Range(-360f, 360f), Flip = UnityEngine.Random.Range(4f, 9f), Phase = UnityEngine.Random.value * 6f,
                    Sway = UnityEngine.Random.Range(30f, 90f),
                });
            }
        }

        private void Update()
        {
            var dt = Time.unscaledDeltaTime;
            _t += dt;
            var fade = Mathf.Clamp01((_life - _t) / 0.8f);
            foreach (var b in _bits)
            {
                var p = b.Rt.anchoredPosition + b.V * dt;
                p.x += Mathf.Sin(_t * 2.4f + b.Phase) * b.Sway * dt;
                b.Rt.anchoredPosition = p;
                b.Rt.localRotation = Quaternion.Euler(0f, 0f, b.Spin * _t);
                b.Rt.localScale = new Vector3(Mathf.Cos(_t * b.Flip + b.Phase), 1f, 1f);   // kâğıt gibi dönerek
                var img = b.Rt.GetComponent<Image>(); var c = img.color; c.a = fade; img.color = c;
            }
            if (_t > _life) Destroy(gameObject);
        }
    }
}
