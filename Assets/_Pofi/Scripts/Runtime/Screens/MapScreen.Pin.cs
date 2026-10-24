using Pofi.Logic.App;
using Pofi.Logic.Island;
using Pofi.UI;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.Screens
{
    /// <summary>
    /// Haritada hedef imi (kullanıcı GB18-8, 24 Ekim 2026: "nereye gitmesi gerektiğini harita üzerinde de gösterelim; ilk başlayana
    /// anlatalım, sonra oraya bakması gerektiğini bilir"). Kuşbakışında sıradaki işin yerinde zıplayan sarı im + "Buraya git" kurdelesi,
    /// yerde genişleyen halka; içinde işin simgesi. Hedef: rehber adımının yeri; rehber bittiyse yerleştirilecek Güneş Taşı'nın yeri,
    /// yoksa bekleyen Ev Görevleri varken pano. İme dokununca harita kapanır, yerde altın oklar hemen yolu gösterir.
    /// İlk kez: uzak hedefte duran çocuğa el Harita düğmesini gösterir (<see cref="Onboarding.MapFar"/>), harita açılınca el ime dokunur
    /// (<see cref="Onboarding.MapPin"/>).
    /// </summary>
    public sealed partial class MapScreen
    {
        private const float PinFar = 35f;
        private RectTransform _pin, _pinBob, _pinHead, _pinRing;
        private Image _pinIcon, _pinRingImg;
        private string _pinIconName;
        private bool _pinGo;   // ime dokunuldu: rehber yoksa da oklar bu hedefe
        private float _pinShown;

        private void BuildMapPin()
        {
            _pinRing = Ui.Rect(_labelLayer, "PinRing", Vector2.zero, new Vector2(170f, 64f));
            _pinRingImg = _pinRing.gameObject.AddComponent<Image>(); _pinRingImg.sprite = GoldKit.Annulus; _pinRingImg.raycastTarget = false;
            _pin = Ui.Rect(_labelLayer, "MapPin", Vector2.zero, new Vector2(132f, 210f));
            _pin.pivot = new Vector2(0.5f, 0f);
            _pinBob = Ui.Fill(_pin, "Bob");
            // damla biçimli im: aşağı bakan kırmızı uç + altın çerçeveli krem baş
            var tip = Ui.Rect(_pinBob, "Tip", new Vector2(0.5f, 0f), new Vector2(54f, 54f), new Vector2(0f, 14f));
            tip.localRotation = Quaternion.Euler(0f, 0f, 45f);
            var ti = tip.gameObject.AddComponent<Image>(); ti.color = Theme.Hex("#E9A62A"); ti.raycastTarget = false;   // sarı im (metin "Sarı im")
            _pinHead = Ui.Rect(_pinBob, "Head", new Vector2(0.5f, 0f), new Vector2(124f, 124f), new Vector2(0f, 36f));
            var rim = GoldKit.RimDisc(_pinHead, Theme.Hex("#FFD84D"), Theme.Hex("#E9A62A"), 7f);
            var face = Ui.Rect(rim, "Face", new Vector2(0.5f, 0.5f), new Vector2(92f, 92f));
            GoldKit.RimDisc(face, Theme.Hex("#FFFDF2"), Theme.Hex("#FBE6B0"), 4f);
            _pinIcon = Ui.IconImage(face, "ui_star", new Vector2(0.5f, 0.5f), 70f).GetComponent<Image>();
            GoldKit.Ribbon(_pinBob, T("map.pin"), GoldKit.Tone.Green, 50f, 28, new Vector2(0.5f, 0f), new Vector2(0f, 168f));   // "Buradasın" kırmızı, hedef yeşil
            var hit = _pin.gameObject.AddComponent<Image>(); hit.color = new Color(1f, 1f, 1f, 0f);
            var b = _pin.gameObject.AddComponent<Button>(); b.targetGraphic = hit; b.transition = Selectable.Transition.None;
            b.onClick.AddListener(PinTapped);
            _pin.gameObject.AddComponent<PressBounce>();
            _pin.gameObject.SetActive(false); _pinRing.gameObject.SetActive(false);
        }

        /// <summary>İmin adadaki yeri ve simgesi; gösterilecek iş yoksa null.</summary>
        private Vector2? PinTarget(out string icon)
        {
            icon = "ui_star";
            if (_world.Walker == null) return null;
            var g = Guide.Current(App.State, App.Level);
            if (g != null)
            {
                var w = GuideWorld(g);   // besle/yıka/giydir: hedef Okti'nin kendisi ("Buradasın" yeter)
                if (w.HasValue) icon = PinIcon(g);
                return w;
            }
            if (SunStoneBook.Available(App.State.SunStones) > 0 && App.Data.SunBook.Next(App.State.SunStones) is SunSpotDef spot)
            {
                icon = "ui_sunstone";
                return SpotDoor(spot);
            }
            if (_boardCount > 0) { icon = "ui_board"; return DoorOf("region_task_board"); }
            return null;
        }

        private string PinIcon(GuideStep g)
        {
            switch (g.Id)
            {
                case "home": case "tidy": case "play": return "ui_home";
                case "shop": return "ui_shop";
                case "kiskac": case "deliver": return "res_crab";
                case "coconut": return "food_coconut";
                case "gather":
                {
                    var n = NearestNode(NeededForHut) ?? NearestNode(x => x.Kind != GatherKind.Coconut);
                    return n != null ? "mat_" + Gathering.Rule(n.Kind).Material : "mat_wood";
                }
                case "hut": return "ui_hut";
                case "fire": return "mat_wood";
                case "board": return "ui_board";
                case "stone": case "clear": return "ui_sunstone";
                case "gift": return "ui_gift";
                default: return "ui_star";
            }
        }

        private void UpdateMapPin(Camera cam, float scale)
        {
            if (_pin == null) return;
            var icon = "ui_star";
            var target = _overview && !_cine ? PinTarget(out icon) : null;
            var on = target.HasValue;
            if (on)
            {
                if (icon != _pinIconName) { _pinIconName = icon; var sp = Ui.Icon(icon); if (sp != null) _pinIcon.sprite = sp; }
                var at = _world.World(target.Value.x, target.Value.y);
                var foot = cam.WorldToScreenPoint(at);
                var head = cam.WorldToScreenPoint(at + Vector3.up * 2.5f);
                // ekran dışındaysa kenara yaslanır (harita kaydırılmış olabilir); halka yalnız ekrandayken
                var w = Root.rect.width; var h = Root.rect.height;
                var inView = foot.z > 0f && foot.x >= 0f && foot.x <= Screen.width && foot.y >= 0f && foot.y <= Screen.height;
                var px = foot.z > 0f ? head.x * scale : w * 0.5f;
                var py = foot.z > 0f ? head.y * scale : 80f;
                _pin.anchoredPosition = new Vector2(Mathf.Clamp(px, 90f, w - 90f), Mathf.Clamp(py, 40f, h - 300f));
                _pinRing.gameObject.SetActive(inView);
                _pinRing.anchoredPosition = new Vector2(foot.x * scale, foot.y * scale);
                var t = Mathf.Repeat(Time.unscaledTime + 0.7f, 1.4f) / 1.4f;
                _pinRing.localScale = Vector3.one * Mathf.Lerp(0.4f, 1.6f, t);
                _pinRingImg.color = new Color(1f, 0.8f, 0.25f, 0.9f * (1f - t));
                _pinBob.anchoredPosition = new Vector2(0f, Theme.ReduceMotion ? 0f : Mathf.Abs(Mathf.Sin(Time.unscaledTime * 3.4f + 1f)) * 18f);
            }
            else _pinRing.gameObject.SetActive(false);
            if (_pin.gameObject.activeSelf != on) { _pin.gameObject.SetActive(on); _pinShown = 0f; if (on) Bump.Play(_pin, 0.35f); }
            // ilk kez: im göründükten kısa süre sonra el ime dokunur (kuşbakışında UpdateTips çalışmaz)
            if (on && (_pinShown += Time.deltaTime) > 0.8f && _coach == null && !StoryPlayer.Playing && Onboarding.Pending(App.State, Onboarding.MapPin))
                Tip(Onboarding.MapPin, TipGesture.Tap, () => UiScreen(_pinHead));
        }

        /// <summary>İme dokunuldu: harita kapanır, yerde oklar hemen yolu gösterir.</summary>
        private void PinTapped()
        {
            Audio.Sfx.Play(Audio.SfxKind.Tap);
            TipDone(Onboarding.MapPin);
            _pinGo = true;
            if (_overview) ToggleMode();
            _toast.Say(T("map.pin_go"));
        }

        /// <summary>Ok hedefi rehber dışından (taş, pano) yalnız ime dokunulduysa; varınca söner.</summary>
        private Vector2? PinChase()
        {
            if (!_pinGo) return null;
            var t = PinTarget(out _);
            if (!t.HasValue || Vector2.Distance(_world.Walker.Position, t.Value) < 4f) { _pinGo = false; return null; }
            return t;
        }

        /// <summary>
        /// UpdateTips içinden (adada): hedef uzaktayken ve çocuk birkaç saniye durunca el Harita düğmesini gösterir, bir kez.
        /// Bir ipucu açıldıysa true.
        /// </summary>
        private bool MapFarTip(bool basicsDone)
        {
            if (!basicsDone || !Onboarding.Pending(App.State, Onboarding.MapFar) || _idleFor < 4f) return false;
            var t = PinTarget(out _);
            if (!t.HasValue || Vector2.Distance(_world.Walker.Position, t.Value) < PinFar) return false;
            Tip(Onboarding.MapFar, TipGesture.Tap, () => UiScreen(_mapBtn));
            if (_coach == null) return false;
            Spotlight.Show((RectTransform)_coach.transform, () => UiScreen(_mapBtn), 120f);
            return true;
        }

        // ------------------------------------------------------------------ sis işareti (GB18-5)
        // "Koydaki sisi aç" deniyor ama sis kadrajda değil: sıradaki Güneş Taşı noktasının sisi üstünde süzülen taş rozeti
        // (kalan taş sayısıyla); sis ekran dışındaysa rozet ekran kenarına yaslanır ve ok sisin yönünü gösterir.
        // Dokununca kamera sise döner, yerde oklar yolu gösterir.
        private RectTransform _beacon, _beaconBob, _beaconTip;
        private Text _beaconNum;
        private float _beaconOff, _turnLeft;
        private float? _turnTo;
        private bool _beaconEdge;

        private void BuildStoneBeacon()
        {
            _beacon = Ui.Rect(_labelLayer, "StoneBeacon", Vector2.zero, new Vector2(140f, 140f));
            _beaconBob = Ui.Fill(_beacon, "Bob");
            _beaconTip = Ui.Rect(_beaconBob, "Tip", new Vector2(0.5f, 0.5f), new Vector2(40f, 40f), new Vector2(0f, -62f));
            _beaconTip.localRotation = Quaternion.Euler(0f, 0f, 45f);
            var ti = _beaconTip.gameObject.AddComponent<Image>(); ti.color = Theme.Hex("#F2B63A"); ti.raycastTarget = false;
            var disc = Ui.Rect(_beaconBob, "Disc", new Vector2(0.5f, 0.5f), new Vector2(124f, 124f));
            GoldKit.RimDisc(disc, Theme.Hex("#FFFDF2"), Theme.Hex("#FBE6B0"), 6f);
            Ui.IconImage(disc, "ui_sunstone", new Vector2(0.5f, 0.5f), 88f);
            _beaconNum = GoldKit.Gem(disc, 50f);
            var hit = _beacon.gameObject.AddComponent<Image>(); hit.color = new Color(1f, 1f, 1f, 0f);
            var b = _beacon.gameObject.AddComponent<Button>(); b.targetGraphic = hit; b.transition = Selectable.Transition.None;
            b.onClick.AddListener(BeaconTapped);
            _beacon.gameObject.AddComponent<PressBounce>();
            _beacon.gameObject.SetActive(false);
        }

        /// <summary>İşaret konacak nokta: taş varken ve rehber başka işte değilken sıradaki sisli bölge.</summary>
        private SunSpotDef BeaconSpot()
        {
            if (SunStoneBook.Available(App.State.SunStones) <= 0) return null;
            var g = Guide.Current(App.State, App.Level);
            if (g != null && g.Id != "stone" && g.Id != "clear") return null;   // rehber başka işteyken dikkati dağıtmaz
            var spot = App.Data.SunBook.Next(App.State.SunStones);
            return spot != null && _world.Fog.TryGetValue(spot.Region, out var f) && f != null ? spot : null;
        }

        private Vector3 BeaconWorld(SunSpotDef spot)
        {
            var c = SpotPos(spot);
            return c.HasValue ? _world.World(c.Value.x, c.Value.y) + Vector3.up * 7.5f : Vector3.zero;   // sis perdelerinin üstü
        }

        private void UpdateStoneBeacon(Camera cam, float scale, float dt)
        {
            if (_beacon == null) return;
            if (_turnTo.HasValue)
            {
                // dokununca kamera sise yumuşakça döner
                _camYaw = Mathf.MoveTowardsAngle(_camYaw, _turnTo.Value, dt * 140f);
                _lookHold = 1.5f;
                if (Mathf.Abs(Mathf.DeltaAngle(_camYaw, _turnTo.Value)) < 0.5f || (_turnLeft -= dt) <= 0f) _turnTo = null;
            }
            var spot = !_overview && !_cine && _world.Walker != null ? BeaconSpot() : null;
            var on = spot != null;
            if (on)
            {
                var c0 = SpotPos(spot) ?? _world.Walker.Position;
                var near = Vector2.Distance(_world.Walker.Position, c0) < 7f;   // yanındayken eylem tuşu "Taşı koy" yeter
                var sp = cam.WorldToScreenPoint(BeaconWorld(spot));
                var w = Root.rect.width; var h = Root.rect.height;
                var inView = sp.z > 0f && sp.x > 0f && sp.x < Screen.width && sp.y > 0f && sp.y < Screen.height;
                _beaconOff = inView ? 0f : _beaconOff + dt;
                on = !near && (inView || _beaconOff > 0.6f);
                if (on)
                {
                    _beaconNum.text = Mathf.Max(1, spot.Cost - SunStoneBook.PlacedIn(App.State.SunStones, spot.Id)).ToString();
                    _beaconEdge = !inView;
                    if (inView)
                    {
                        _beacon.anchoredPosition = new Vector2(sp.x * scale, sp.y * scale + 70f);
                        _beaconTip.anchoredPosition = new Vector2(0f, -62f);
                        _beaconBob.anchoredPosition = new Vector2(0f, Theme.ReduceMotion ? 0f : Mathf.Sin(Time.unscaledTime * 2.4f) * 8f);
                    }
                    else
                    {
                        // ekran kenarına (köşelerdeki göstergelerden uzak) yaslan, uç sise baksın
                        var c = new Vector2(w, h) * 0.5f;
                        var d = new Vector2(sp.x, sp.y) * scale - c;
                        if (sp.z < 0f) d = -d;
                        if (d.sqrMagnitude < 1f) d = Vector2.up;
                        float mx = c.x - 170f, my = d.y > 0f ? c.y - 250f : c.y - 140f;
                        var k = Mathf.Min(mx / Mathf.Max(0.001f, Mathf.Abs(d.x)), my / Mathf.Max(0.001f, Mathf.Abs(d.y)));
                        _beacon.anchoredPosition = c + d * k;
                        var a = Mathf.Atan2(d.y, d.x);
                        _beaconTip.anchoredPosition = new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * 64f;
                        _beaconBob.anchoredPosition = Theme.ReduceMotion ? Vector2.zero : new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * Mathf.Abs(Mathf.Sin(Time.unscaledTime * 3f)) * 10f;
                    }
                }
            }
            if (_beacon.gameObject.activeSelf != on) { _beacon.gameObject.SetActive(on); if (on) Bump.Play(_beacon, 0.3f); }
        }

        /// <summary>Rehberin / ilk gün ipucunun taş hedefi: rozet görünüyorsa rozet (kenarda da olsa), değilse bölge.</summary>
        private Vector2 StoneTipScreen()
        {
            if (_beacon != null && _beacon.gameObject.activeInHierarchy) return UiScreen(_beacon);
            var c = SpotPos(App.Data.SunBook.Next(App.State.SunStones));
            return c.HasValue ? (Vector2)App.Stage.Camera.WorldToScreenPoint(_world.World(c.Value.x, c.Value.y) + Vector3.up * 3f) : RegionScreen("region_task_board");
        }

        private void BeaconTapped()
        {
            Audio.Sfx.Play(Audio.SfxKind.Tap);
            var spot = BeaconSpot();
            if (spot == null || _world.Walker == null) return;
            var c = SpotPos(spot);
            if (!c.HasValue) return;
            var p = _world.Walker.Position;
            _turnTo = Mathf.Atan2(c.Value.x - p.x, c.Value.y - p.y) * Mathf.Rad2Deg;
            _turnLeft = 2.5f;
            _pinGo = true;
            _toast.Say(T("map.fog_here", SpotName(spot)));
        }
    }
}
