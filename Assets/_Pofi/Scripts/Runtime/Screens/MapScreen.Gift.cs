using Pofi.Logic.App;
using Pofi.Logic.Island;
using Pofi.UI;
using Pofi.World;
using UnityEngine;

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
            var cam = App.Stage.Camera;
            Vector2 from = _mavi != null ? (Vector2)cam.WorldToScreenPoint(_mavi.transform.position + Vector3.up * 0.9f) : PetScreen();
            if (_mavi != null) _mavi.React();
            var glow = GainFx.Glow(_world.transform, GainFx.StoneColor, 0.8f, false);
            glow.position = (_mavi != null ? _mavi.transform.position : _world.Walker.transform.position) + Vector3.up * 1.0f;
            Audio.Sfx.Play(Audio.SfxKind.Chime);
            yield return new WaitForSeconds(0.5f);
            RewardFlight.Fly(App.Overlay.transform, "sunstone", "ui_sunstone", 1, from, 120f, Audio.SfxKind.Success, true);   // aksiyon çıktısı: taş sayaca uçar
            for (var t = 0f; t < 0.6f; t += Time.deltaTime) { if (glow != null) glow.localScale *= 0.96f; yield return null; }
            if (glow != null) Destroy(glow.gameObject);
            yield return new WaitForSeconds(1.0f);
            GiftCard();
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
