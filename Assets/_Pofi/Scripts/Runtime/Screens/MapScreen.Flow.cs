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
        // Kıskaç'a teslimden sonra "adayı biraz dolaş" (akış haritası yorumu, 25 Ekim 2026: araya 15–20 sn es; Mavi kadrajın içinden uçarak gelir)
        private const float MeetRange = 3.6f, MaviDelay = 16f;
        private bool _kiskacWalks;
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
            UpdateCompanions(g);
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
                case "gift":   // GB19: Mavi'nin hediye taşı (sahne bittikten sonra)
                    UpdateGift();
                    break;
                case "mavi":
                    if (_maviArriveT < 0f && _maviLandT < 0f) { _maviArriveT = MaviDelay; Debug.Log("[PofiDebug] flow: Mavi " + MaviDelay + " sn sonra gelecek"); }
                    break;
                case "gather":
                    if (Gathering.CanBuild(App.State.Gather)) App.RecordActivity("hut_ready");
                    break;
            }
        }

        /// <summary>
        /// Yol arkadaşları (akış haritası yorumları, 25 Ekim 2026): Mavi kendi bölümünde (hediye, sis, malzeme, kulübe) Okti'nin başının
        /// yanında kanat çırparak süzülür; panoya giderken Kıskaç Okti'nin yanında yürür (uzaktaysa yanına gelir).
        /// </summary>
        private void UpdateCompanions(GuideStep g)
        {
            var id = g?.Id;
            if (_mavi != null && _maviArriveT < 0f && _maviLandT < 0f && _maviNewsT <= 0f
                && (id == "gift" || id == "clear" || id == "gather" || id == "hut" || (id == "mavi" && App.State.Counters.Total("mavi_arrived") > 0)))
                _mavi.Hover(1.2f, PetTop, App.Stage.Camera);
            var walk = id == "board" && _kiskac != null && !_cine;
            if (walk && !_kiskacWalks)
            {
                var p = _world.Walker.Position;
                var k = _kiskac.transform.localPosition;
                if (Vector2.Distance(p, new Vector2(k.x, k.z)) > 14f)
                {
                    // uzaktaysa yanına gelir (kısa ışıltıyla), sonra birlikte yürürler
                    var side = p + new Vector2(_world.Walker.transform.right.x, _world.Walker.transform.right.z).normalized * 1.6f;
                    _kiskac.Teleport(new Vector3(side.x, _terrain.Height(side.x, side.y), side.y));
                    var glow = GainFx.Glow(_world.transform, new Color(1f, 0.6f, 0.4f), 0.7f, false);
                    glow.position = _kiskac.transform.position + Vector3.up * 0.6f;
                    Destroy(glow.gameObject, 0.6f);
                    Audio.Sfx.Play(Audio.SfxKind.Pop);
                }
                _kiskac.Follow(_world.Walker.transform);
                _kiskacWalks = true;
            }
            else if (!walk && _kiskacWalks && !StoryPlayer.Playing)
            {
                _kiskac.Follow(null);   // pano sahnesinden sonra dükkânına döner
                _kiskacWalks = false;
            }
        }

        /// <summary>Okti'nin boyu (Mavi başının yanında süzülsün).</summary>
        private float PetTop => _world.Walker != null ? Mathf.Max(0.8f, (PetHeadWorld.y - _world.Walker.transform.position.y) * 0.62f) : 1.4f;

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
                // kadrajın içinden gelsin: Okti'nin önünde, gökyüzünde belirir ve süzülerek iner (posta kutusu çoğu zaman görünmüyordu)
                var cam = App.Stage.Camera.transform;
                var fwd = cam.forward; fwd.y = 0f; fwd = fwd.sqrMagnitude > 0.01f ? fwd.normalized : Vector3.forward;
                var sky = _world.Walker.transform.position + fwd * 11f + cam.right * 3f + Vector3.up * 7f;
                _mavi.Appear(_world.transform.InverseTransformPoint(sky));
                _maviNewsT = 2.6f;   // Okti'nin yanına uç (UpdateMaviGuide)
                _maviLandT = 2.9f;
                Audio.Sfx.Play(Audio.SfxKind.Chime);
            }
            if (_maviLandT > 0f && (_maviLandT -= dt) <= 0f)
            {
                _maviLandT = -1f;
                Debug.Log("[PofiDebug] flow: Mavi kondu");
                _mavi.React();
                _mavi.Hover(18f, PetTop, App.Stage.Camera);   // sahne boyunca Okti'nin başının yanında kanat çırpar
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
