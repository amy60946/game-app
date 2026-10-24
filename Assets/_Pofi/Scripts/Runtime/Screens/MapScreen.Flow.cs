using System.Linq;
using Pofi.Logic.App;
using Pofi.Logic.Island;
using Pofi.UI;
using Pofi.World;
using UnityEngine;

namespace Pofi.Screens
{
    /// <summary>
    /// Sıralı ilk oyun akışı (kullanıcı GB17-9/11, 24 Ekim 2026): besle, yıka, giydir → Kıskaç'ın yanına git (2 hindistan cevizi
    /// ister) → cevizleri kumsaldan ya da bahçeden topla → Kıskaç'a teslim et → bir süre sonra Mavi uçarak gelir, kulübesini
    /// anlatır → malzeme topla → kulübeyi yap. Adımlar Logic/App/Guide'da; burası adadaki tetikleri (yakınlık, sahne, Mavi'nin gelişi)
    /// bağlar. Hikâye sahneleri olay sayaçlarıyla (story.json: kiskac_met, coconut_delivered, mavi_arrived) oynar.
    /// </summary>
    public sealed partial class MapScreen
    {
        private const float MeetRange = 3.6f, MaviDelay = 8f;
        private float _flowT, _maviArriveT = -1f, _maviLandT = -1f;
        private bool _storyBusy, _deliverOpened;

        /// <summary>Oturum ortasında olay sayacı değişince sırası gelen hikâye sahnesini oynat.</summary>
        private void TriggerStory()
        {
            if (_storyBusy || !isActiveAndEnabled) return;
            StartCoroutine(StoryCheck());
        }

        private Vector2 KiskacPos => _kiskac != null ? new Vector2(_kiskac.transform.localPosition.x, _kiskac.transform.localPosition.z) : Vector2.zero;

        /// <summary>Saniyede birkaç kez: rehber adımına göre adadaki tetikler.</summary>
        private void UpdateFlow(float dt)
        {
            if (_world.Walker == null || _overview || _cine || StoryPlayer.Playing) return;
            UpdateMaviArrival(dt);
            if ((_flowT -= dt) > 0f) return;
            _flowT = 0.25f;
            var g = Guide.Current(App.State, App.Level);
            if (g == null) return;
            var p = _world.Walker.Position;
            var nearKiskac = _kiskac != null && Vector2.Distance(p, KiskacPos) < MeetRange;
            switch (g.Id)
            {
                case "kiskac":
                    if (nearKiskac) MeetKiskac();
                    break;
                case "coconut":
                    EnsureCoconutRequest();
                    CheckCoconuts();   // dükkândan ya da oyundan gelmiş olabilir
                    break;
                case "deliver":
                    EnsureCoconutRequest();
                    if (!nearKiskac) { if (_kiskac == null || Vector2.Distance(p, KiskacPos) > 5f) _deliverOpened = false; break; }
                    if (_deliverOpened) break;
                    _deliverOpened = true;
                    _world.Walker.Face(KiskacPos.x, KiskacPos.y);
                    _kiskac.React();
                    RequestCard(Guide.CoconutRequest);
                    break;
                case "mavi":
                    if (_maviArriveT < 0f && _maviLandT < 0f) { _maviArriveT = MaviDelay; Debug.Log("[PofiDebug] flow: Mavi " + MaviDelay + " sn sonra gelecek"); }
                    break;
                case "gather":
                    if (Gathering.CanBuild(App.State.Gather)) App.RecordActivity("hut_ready");
                    break;
            }
        }

        /// <summary>Kıskaç'la tanışma: isteği açılır, sahne oynar ("2 hindistan cevizi getirir misin?").</summary>
        private void MeetKiskac()
        {
            _world.Walker.Steer(Vector2.zero);
            _world.Walker.Face(KiskacPos.x, KiskacPos.y);
            _kiskac.React();
            EnsureCoconutRequest();
            App.RecordActivity("kiskac_met");
            TriggerStory();
        }

        /// <summary>Kıskaç'ın ceviz isteği açık değilse açar ve kapı baloncuğunu kurar.</summary>
        private void EnsureCoconutRequest()
        {
            if (!Logic.Story.ResidentRequests.Open(App.State.Story, App.Data.Story.Requests, Guide.CoconutRequest, Day)) return;
            App.Save();
            RebuildRequests();
        }

        private void RebuildRequests()
        {
            foreach (var (_, b, _) in _reqBubbles) if (b != null) Destroy(b.gameObject);
            _reqBubbles.Clear();
            _reqAnchor.Clear();
            BuildRequests();
        }

        /// <summary>İstek teslim edildi (RequestCard): Kıskaç'ın cevizleri akışı ilerletir, teşekkür sahnesi oynar.</summary>
        private void OnRequestDone(string id)
        {
            if (id != Guide.CoconutRequest) return;
            App.RecordActivity("coconut_delivered");
            TriggerStory();
        }

        /// <summary>
        /// Mavi'nin gelişi: teşekkür sahnesinden birkaç saniye sonra posta kutusundan Okti'ye uçar, yanına konar; konunca
        /// "mavi_arrived" sayılır ve 2. bölümün açılış sahnesi (kulübesi uçmuş) oynar.
        /// </summary>
        private void UpdateMaviArrival(float dt)
        {
            if (_maviArriveT > 0f && (_maviArriveT -= dt) <= 0f)
            {
                _maviArriveT = -1f;
                if (_mavi == null) CreateMavi();
                Debug.Log("[PofiDebug] flow: Mavi uçuyor (model " + (_mavi != null) + ")");
                if (_mavi == null) { App.RecordActivity("mavi_arrived"); TriggerStory(); return; }
                _maviNewsT = 2.6f;   // Okti'nin yanına uç (UpdateMaviGuide)
                _maviLandT = 2.9f;
                Audio.Sfx.Play(Audio.SfxKind.Chime);
            }
            if (_maviLandT > 0f && (_maviLandT -= dt) <= 0f)
            {
                _maviLandT = -1f;
                Debug.Log("[PofiDebug] flow: Mavi kondu");
                _mavi.React();
                _mavi.Linger(16f);   // sahne boyunca Okti'nin yanında kalsın
                App.RecordActivity("mavi_arrived");
                TriggerStory();
            }
        }

        /// <summary>Ayıklama (PofiDebug flow): akışın anlık durumu.</summary>
        public string DebugFlow() =>
            $"adım={Guide.Current(App.State, App.Level)?.Id ?? "-"} gel={_maviArriveT:0.0} kon={_maviLandT:0.0} uç={_maviNewsT:0.0} mavi={_mavi != null} " +
            $"hikâye={StoryPlayer.Playing} sinema={_cine} harita={_overview} meşgul={_storyBusy} pet={_world?.Walker != null} zaman={Time.timeScale:0.00} dt={Time.deltaTime:0.000}";

        /// <summary>Eski oyuncu (rehber kapalı, Sv2+): Mavi'nin açılış sahnesi seviyeyle gelirdi; artık olayla geldiği için sayılır.</summary>
        private void CatchUpMavi()
        {
            if (Guide.Active(App.State, App.Level) || App.Level < 2 || App.State.Counters.Total("mavi_arrived") > 0) return;
            App.RecordActivity("mavi_arrived");
        }
    }
}
