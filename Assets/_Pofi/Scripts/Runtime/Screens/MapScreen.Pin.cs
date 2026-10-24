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
            var ti = tip.gameObject.AddComponent<Image>(); ti.color = Theme.Hex("#D9412B"); ti.raycastTarget = false;
            _pinHead = Ui.Rect(_pinBob, "Head", new Vector2(0.5f, 0f), new Vector2(124f, 124f), new Vector2(0f, 36f));
            var rim = GoldKit.RimDisc(_pinHead, Theme.Hex("#FF7A5C"), Theme.Hex("#D9412B"), 7f);
            var face = Ui.Rect(rim, "Face", new Vector2(0.5f, 0.5f), new Vector2(92f, 92f));
            GoldKit.RimDisc(face, Theme.Hex("#FFFDF2"), Theme.Hex("#FBE6B0"), 4f);
            _pinIcon = Ui.IconImage(face, "ui_star", new Vector2(0.5f, 0.5f), 70f).GetComponent<Image>();
            GoldKit.Ribbon(_pinBob, T("map.pin"), GoldKit.Tone.Red, 50f, 28, new Vector2(0.5f, 0f), new Vector2(0f, 168f));
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
                return DoorOf(spot.Region);
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
                case "stone": return "ui_sunstone";
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
                _pinRingImg.color = new Color(1f, 0.45f, 0.3f, 0.9f * (1f - t));
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
    }
}
