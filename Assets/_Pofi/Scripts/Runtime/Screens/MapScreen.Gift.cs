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

        /// <summary>
        /// Rehberin "gift" adımı (kullanıcı, 26 Ekim 2026: "hediye taşı panodaki hoş geldin göreviyle ver"): Mavi'nin sahnesinden sonra
        /// Okti panoya gider; panonun kapısına varınca Kıskaç'ın pano sahnesi oynar, sonra el "Gir"i gösterir. Taş Görevler
        /// penceresindeki hoş geldin kartında "Yaptım" ile kazanılır (TasksScreen.WelcomeDone).
        /// </summary>
        private void UpdateGift()
        {
            if (_storyBusy || StoryPlayer.Playing || _cine) return;
            if (!App.State.Story.Seen.Contains("ch2_open")) return;   // önce Mavi kendini tanıtır ("panoya sana bir görev bıraktım")
            var door = DoorOf("region_task_board");
            if (!door.HasValue || App.State.Counters.Total(Guide.BoardCounter) > 0) return;
            if (Vector2.Distance(_world.Walker.Position, door.Value) > 5f) return;
            _world.Walker.Steer(Vector2.zero);
            App.RecordActivity(Guide.BoardCounter);   // Kıskaç'ın pano sahnesi (story.json ch1_board)
            TriggerStory();
        }

    }
}
