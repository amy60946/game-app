using Pofi.Logic.App;
using Pofi.Logic.Island;
using Pofi.UI;
using Pofi.World;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.Screens
{
    /// <summary>
    /// Hediye Güneş Taşı ve kulübe yerindeki sis (kullanıcı GB19, 24 Ekim 2026: "kulübe yerine de sis koy; ilk oyunda bir aksiyon
    /// çıktısı olarak bir Güneş Taşı ver, onunla sisi dağıtsın; hediye olduğunu ve sonrakilerin gerçek görevlerle kazanılacağını
    /// söyle"). Akış: Mavi'nin açılış sahnesi biter → taş Mavi'den sayaca uçar → 3 satırlık bilgi kartı (hediye · sisi dağıtır ·
    /// sonrakiler gerçek görevden) → rehber "clear": oklar ve taş rozeti kulübe yerine götürür → "Taşı koy" → sis kalkar → malzeme.
    /// Hediye taş yalnız adada geçerlidir (Logic/Island/SunStones.Gift; sunucuya gitmez, gerçek ödüle harcanmaz).
    /// </summary>
    public sealed partial class MapScreen
    {
        private const float SiteFogRadius = 6f, SiteFogReach = 6.5f;
        private bool _giftBusy;

        /// <summary>Kulübe yeri sisli mi (hediye taş henüz konmadı)?</summary>
        private bool SiteFogged
        {
            get
            {
                var book = App.Data.SunBook;
                return book.Find(SunStoneBook.HutSpot) != null && !book.IsRepaired(App.State.SunStones, SunStoneBook.HutSpot);
            }
        }

        /// <summary>Onarım noktasının adadaki merkezi (kulübe sisi: kulübe yeri; diğerleri bölge).</summary>
        private Vector2? SpotPos(SunSpotDef spot)
        {
            if (spot == null) return null;
            if (spot.Id == SunStoneBook.HutSpot) return new Vector2(_sitePos.x, _sitePos.z);
            var r = App.Map.Find(spot.Region);
            return r != null ? new Vector2(r.X, r.Z) : (Vector2?)null;
        }

        /// <summary>Yürünecek yer (kulübe sisi: kulübe yeri; diğerleri bölgenin kapısı).</summary>
        private Vector2? SpotDoor(SunSpotDef spot) =>
            spot == null ? null : spot.Id == SunStoneBook.HutSpot ? new Vector2(_sitePos.x, _sitePos.z) : DoorOf(spot.Region);

        private string SpotName(SunSpotDef spot) => spot == null ? "" : App.Map.Find(spot.Region)?.Name ?? spot.Name;

        /// <summary>BuildGather içinden: kulübe yeri sisliyse şantiye gizlenir, üstüne yer sisi (FogBank) konur.</summary>
        private void BuildSiteFog()
        {
            var hut = App.Data.SunBook.Find(SunStoneBook.HutSpot);
            if (hut == null || !SiteFogged) return;
            if (_site != null) _site.gameObject.SetActive(false);
            var fog = FogBank.Spawn(_world.transform, new Vector3(_sitePos.x, 0f, _sitePos.z), SiteFogRadius, 4711, _terrain.Height);
            if (fog != null) _world.Fog[hut.Region] = fog.transform;
        }

        /// <summary>Eylem düğmesi: sisli kulübe yerinin yanında "Taşı koy".</summary>
        private bool SiteFogAction(Vector2 p, out System.Action act)
        {
            act = null;
            var hut = App.Data.SunBook.Find(SunStoneBook.HutSpot);
            if (hut == null || !SiteFogged || Vector2.Distance(p, new Vector2(_sitePos.x, _sitePos.z)) > SiteFogReach) return false;
            act = () => PlaceStone(hut);
            return true;
        }

        /// <summary>Rehberin "gift" adımı (UpdateFlow): Mavi'nin sahnesi bitince taş uçar, sonra bilgi kartı.</summary>
        private void UpdateGift()
        {
            if (_giftBusy || _storyBusy || StoryPlayer.Playing || _cine) return;
            if (!App.State.Story.Seen.Contains("ch2_open")) return;   // önce Mavi kendini tanıtır (sahnede "al, bu taş sana hediye")
            _giftBusy = true;
            StartCoroutine(GiftStone());
        }

        private System.Collections.IEnumerator GiftStone()
        {
            var st = App.State.SunStones;
            if (SunStoneBook.GiveGift(st)) App.Save();
            if (_world.Walker != null) _world.Walker.Steer(Vector2.zero);
            if (_mavi != null) _mavi.React();
            var glow = GainFx.Glow(_world.transform, GainFx.StoneColor, 0.8f, false);
            glow.position = (_mavi != null ? _mavi.transform.position : _world.Walker.transform.position) + Vector3.up * 1.0f;
            Audio.Sfx.Play(Audio.SfxKind.Chime);
            yield return new WaitForSeconds(0.4f);
            if (glow != null) Destroy(glow.gameObject);
            // kazanma anı (akış haritası yorumu, 25 Ekim 2026: "yalnız sayı 0'dan 1 oluyor; taşın ne olduğunu gösteren bir animasyon,
            // bitince görsel sayaçtaki taşa süzülsün"): ekran kısılır, dönen altın ışınların önünde taş büyüyerek belirir, adı ve
            // işi yazar; sonra küçülerek sayaca uçar
            yield return StoneReveal();
            yield return new WaitForSeconds(0.9f);
            GiftCard();
        }

        /// <summary>Güneş Taşı kazanma gösterisi (≈2,6 sn): ışınlar + taş + kurdele, sonra taş sayaca uçar (RewardFlight).</summary>
        private System.Collections.IEnumerator StoneReveal()
        {
            var root = Ui.Fill(App.Overlay.transform, "StoneReveal");
            var veil = root.gameObject.AddComponent<Image>(); veil.color = new Color(0.02f, 0.06f, 0.14f, 0f); veil.raycastTarget = true;
            var rays = Ui.Rect(root, "Rays", new Vector2(0.5f, 0.55f), new Vector2(900f, 900f));
            var ri = rays.gameObject.AddComponent<RawImage>(); ri.texture = LevelUpCelebration.RaysTex(); ri.raycastTarget = false; ri.color = new Color(1f, 0.8f, 0.3f, 0f);
            var halo = Ui.Rect(root, "Halo", new Vector2(0.5f, 0.55f), new Vector2(420f, 420f));
            var hi = halo.gameObject.AddComponent<Image>(); hi.sprite = Ui.Rounded; hi.type = Image.Type.Sliced; hi.pixelsPerUnitMultiplier = 0.25f;
            hi.color = new Color(1f, 0.9f, 0.55f, 0f); hi.raycastTarget = false;
            var stone = Ui.Rect(root, "Stone", new Vector2(0.5f, 0.55f), new Vector2(300f, 300f));
            var si = stone.gameObject.AddComponent<Image>(); si.sprite = Ui.Icon("ui_sunstone"); si.preserveAspect = true; si.raycastTarget = false;
            stone.localScale = Vector3.zero;
            Audio.Sfx.Play(Audio.SfxKind.Success);
            Audio.Haptics.Medium();
            Text title = null, sub = null;
            for (var t = 0f; t < 2.0f; t += Time.unscaledDeltaTime)
            {
                veil.color = new Color(0.02f, 0.06f, 0.14f, Mathf.Min(0.45f, t * 1.6f));
                ri.color = new Color(1f, 0.8f, 0.3f, Mathf.Clamp01(t / 0.4f) * 0.42f);
                rays.localRotation = Quaternion.Euler(0f, 0f, -t * 22f);
                // 0 → 1,3 (0,3 sn) → 1, sonra hafif nefes ve dönme
                var s = t < 0.3f ? Mathf.SmoothStep(0f, 1.3f, t / 0.3f) : t < 0.48f ? Mathf.Lerp(1.3f, 1f, (t - 0.3f) / 0.18f) : 1f + Mathf.Sin((t - 0.48f) * 4f) * 0.04f;
                stone.localScale = Vector3.one * s;
                stone.localRotation = Quaternion.Euler(0f, 0f, Mathf.Sin(t * 2.4f) * 6f);
                var hp = Mathf.Repeat(t / 0.9f, 1f);
                halo.localScale = Vector3.one * Mathf.Lerp(0.6f, 1.5f, hp);
                hi.color = new Color(1f, 0.9f, 0.55f, (1f - hp) * 0.45f);
                if (title == null && t > 0.45f)
                {
                    title = Candy.Ribbon(root, T("gift.reveal"), new Vector2(0.5f, 0.55f), new Vector2(0f, -215f), 120f, 54);
                    title.transform.parent.gameObject.AddComponent<PopIn>();
                    var sp = RectTransformUtility.WorldToScreenPoint(null, stone.position);
                    StarSparkles.Around(root, new Vector2(sp.x / Mathf.Max(1f, Screen.width), sp.y / Mathf.Max(1f, Screen.height)), new Vector2(0.14f, 0.2f), 12, 77, 1.6f);
                    Audio.Sfx.Play(Audio.SfxKind.Chime);
                }
                if (sub == null && t > 0.8f)
                {
                    sub = Candy.Caption(root, T("gift.reveal_sub"), 40, new Vector2(0.5f, 0.55f), new Vector2(1300f, 64f), new Vector2(0f, -310f));
                    Audio.Voice.Say(T("gift.reveal") + " " + T("gift.reveal_sub"));
                }
                yield return null;
            }
            // taş sayaca süzülür: büyük görsel küçülürken aynı yerden uçan taş çıkar
            var from = RectTransformUtility.WorldToScreenPoint(null, stone.position);
            RewardFlight.Fly(App.Overlay.transform, "sunstone", "ui_sunstone", 1, from, 150f, Audio.SfxKind.Success, true);
            for (var t = 0f; t < 1f; t += Time.unscaledDeltaTime / 0.35f)
            {
                stone.localScale = Vector3.one * Mathf.Lerp(1f, 0f, t);
                var a = 1f - t;
                veil.color = new Color(0.02f, 0.06f, 0.14f, 0.45f * a);
                ri.color = new Color(1f, 0.8f, 0.3f, 0.42f * a);
                if (title != null) title.transform.parent.localScale = Vector3.one * a;
                if (sub != null) sub.color = new Color(sub.color.r, sub.color.g, sub.color.b, a);
                yield return null;
            }
            Destroy(root.gameObject);
        }

        /// <summary>Bilgi kartı (E dili; ödül tanıtımıyla aynı düzen): hediye · sisi dağıtır · sonrakiler gerçek görevden.</summary>
        private void GiftCard()
        {
            var root = Modal(640f, out var box, false);
            ModalTitle(box, T("gift.title"));
            var rows = new[] { ("ui_gift", "gift.l1"), ("ui_sunstone", "gift.l2"), ("ui_board", "gift.l3") };
            for (var i = 0; i < rows.Length; i++)
            {
                var y = 0.72f - i * 0.19f;
                Ui.Label(box, (i + 1).ToString(), Th.Font(56), Theme.Hex("#C26A08"), new Vector2(0.1f, y), new Vector2(80f, 90f), FontStyle.Bold);
                Ui.IconImage(box, rows[i].Item1, new Vector2(0.21f, y), 96f);
                Ui.Label(box, T(rows[i].Item2), Th.Font(38), Th.Text, new Vector2(0.62f, y), new Vector2(700f, 110f), FontStyle.Bold, TextAnchor.MiddleLeft);
            }
            var say = T("gift.l1") + " " + T("gift.l2") + " " + T("gift.l3");
            Audio.Voice.Say(say);
            Ui.Button(box, Th, T("gift.ok"), new Vector2(0.5f, 0.1f), new Vector2(420f, 120f), () =>
            {
                Audio.Voice.StopIf(say);
                Destroy(root.gameObject);
                _giftBusy = false;
                App.RecordActivity("gift_stone");   // rehber: sıradaki adım kulübe yerindeki sis
                _pinGo = true;                       // oklar hemen yolu göstersin
            });
        }
    }
}
