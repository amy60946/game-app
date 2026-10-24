using System.Collections.Generic;
using System.Linq;
using Pofi.Logic.App;
using Pofi.Logic.Data;
using Pofi.Logic.Island;
using Pofi.Logic.Pet;
using Pofi.UI;
using Pofi.World;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.Screens
{
    /// <summary>
    /// V8 sade gösterge (23 Ekim 2026, kullanıcı onayı):
    /// Ç çanta sol kenarın ortasında (joystick alanını kısıtlamaz): toplanan malzemeler ve yiyecek, sabun, tohum içinde; toplanan şey
    /// çantaya uçar, sayı zıplar; dokununca başlıksız küçük baloncuk (simge + sayı), dışına dokununca kapanır. Sağdaki malzeme paneli yok.
    /// G avatar menüsü: avatara dokununca Defter, Ayarlar, Müzik. İ1 ihtiyaç çipi avatarın yanında, İ4 Okti ekran dışındaysa kenarda küçük ok.
    /// K 3B adalılar: Kıskaç dükkânın önünde, Mavi posta kutusunda (2. bölümden sonra), Pus adanın üstünde (1. bölüm sonundan sonra).
    /// </summary>
    public sealed partial class MapScreen
    {
        private RectTransform _bag, _bagPop, _avatarMenu, _needChip, _edge, _homeBtn;
        private Text _bagNum, _needWord;
        private Image _needChipIcon, _edgeNeed;
        private int _bagLast = -1;
        private float _needBounce, _edgeOff;
        private readonly Image[] _gaugeGlow = new Image[4];
        private Resident3D _kiskac, _mavi, _pus, _tosbi, _pitir, _hisir;

        private static readonly string[] BagCats = { ItemCategory.Food, ItemCategory.Cleaning, ItemCategory.Seed };

        // ------------------------------------------------------------------ Ç çanta

        private void BuildBag(RectTransform hud)
        {
            // çerçevesiz 3B simge (kullanıcı, 24 Ekim 2026: Çanta, Görev, Harita çerçevede durmasın)
            var wrap = Shrinkable(hud, new Vector2(0f, 0.5f), new Vector2((34f + 42f) * G, -30f), 84f * G);
            var (b, _, lab) = GoldKit.Icon3D(wrap, "backpack_small", 84f * G, new Vector2(0.5f, 0.5f), Vector2.zero, Theme.Hex("#3E5A1E"), ToggleBag, T("bag.title"), GoldKit.Tone.Blue, 0.5f);
            Label(lab);
            _bag = (RectTransform)b.transform;
            _bagNum = GoldKit.Gem(b.transform);
            LongPressInfo.Add(b.gameObject, T("info.bag"));
            foreach (var m in new[] { Gathering.Wood, Gathering.Branch, Gathering.Stone, Gathering.Coconut }) RewardFlight.Register(m, _bag);   // O1: malzeme çantaya uçar
            RefreshBag();
        }

        /// <summary>Çantadakiler: yiyecek, sabun, tohum (envanter) ve malzemeler; yalnız elde olanlar.</summary>
        private List<(string Id, string Icon, int Count, string Name, string Kind)> BagItems()
        {
            var list = new List<(string, string, int, string, string)>();
            foreach (var cat in BagCats)
                foreach (var kv in App.State.Inventory.Counts.Where(kv => kv.Value > 0))
                {
                    var it = App.Data.Item(kv.Key);
                    if (it != null && it.Category == cat) list.Add((it.Id, it.Id, kv.Value, it.Name, cat));
                }
            var st = App.State.Gather;
            foreach (var m in new[] { Gathering.Wood, Gathering.Branch, Gathering.Stone })
            {
                var n = Gathering.Count(st, m) - RewardFlight.Pending(m);
                if (n > 0) list.Add((m, MatIcon(m), n, T("gather." + m), "material"));
            }
            return list;
        }

        private void RefreshBag()
        {
            if (_bagNum == null) return;
            var total = BagItems().Sum(x => x.Count);
            _bagNum.text = total > 99 ? "99+" : total.ToString();
            _bagNum.transform.parent.gameObject.SetActive(total > 0);
            if (_bagLast >= 0 && total > _bagLast) Bump.Play(_bag, 0.3f);   // yeni gelen her şeyde çanta zıplar
            _bagLast = total;
        }

        private void ToggleBag()
        {
            if (_bagPop != null) { CloseBag(); return; }
            CloseAvatarMenu();
            var items = BagItems();
            if (items.Count == 0) { _toast.Say(T("bag.empty")); return; }
            _bagPop = Ui.Fill(Root, "BagPop");
            var catcher = _bagPop.gameObject.AddComponent<Image>(); catcher.color = new Color(0f, 0f, 0f, 0f);
            var close = _bagPop.gameObject.AddComponent<Button>(); close.transition = Selectable.Transition.None; close.onClick.AddListener(CloseBag);
            const float tile = 124f, gap = 12f;
            var cols = Mathf.Min(5, items.Count); var rows = Mathf.CeilToInt(items.Count / (float)cols);
            var w = cols * tile + (cols - 1) * gap + 40f; var h = rows * tile + (rows - 1) * gap + 40f;
            var pop = Ui.Rect(_bagPop, "Pop", new Vector2(0f, 0.5f), new Vector2(w, h));
            pop.pivot = new Vector2(0f, 0.5f);
            pop.anchoredPosition = new Vector2(200f, -30f);
            CreamCard(pop, h);
            pop.gameObject.AddComponent<ClickSink>();
            // çantaya bakan küçük kuyruk
            var tail = Ui.Rect(pop, "Tail", new Vector2(0f, 0.5f), new Vector2(40f, 40f), new Vector2(-6f, 0f));
            tail.localRotation = Quaternion.Euler(0f, 0f, 45f);
            var ti = tail.gameObject.AddComponent<Image>(); ti.sprite = Ui.Rounded; ti.type = Image.Type.Sliced; ti.color = new Color(1f, 0.95f, 0.82f); ti.raycastTarget = false;
            tail.SetAsFirstSibling();
            RectTransform careCell = null; string careId = null, careTip = null;
            for (var i = 0; i < items.Count; i++)
            {
                var (id, icon, count, name, kind) = items[i];
                var c = i % cols; var r = i / cols;
                var x = 20f + c * (tile + gap) + tile * 0.5f;
                var y = h * 0.5f - 20f - r * (tile + gap) - tile * 0.5f;
                var cell = Ui.Rect(pop, "Item " + id, new Vector2(0f, 0.5f), new Vector2(tile, tile), new Vector2(x, y));
                var bg = cell.gameObject.AddComponent<Image>(); bg.sprite = Ui.Rounded; bg.type = Image.Type.Sliced; bg.color = new Color(1f, 1f, 1f, 0.85f);
                Ui.IconImage(cell, icon, new Vector2(0.5f, 0.55f), 92f);
                var num = Ui.Label(cell, count.ToString(), Th.Font(32), new Color(0.35f, 0.2f, 0.06f), new Vector2(1f, 0f), new Vector2(70f, 40f), FontStyle.Bold, TextAnchor.LowerRight);
                ((RectTransform)num.transform).anchoredPosition = new Vector2(-40f, 24f);
                cell.gameObject.AddComponent<PressBounce>();
                var itemId = id; var itemKind = kind; var itemName = name;
                if (kind == ItemCategory.Food || kind == ItemCategory.Cleaning)
                {
                    // yiyecek/sabun çantadan Okti'nin üstüne sürüklenir (kullanıcı, 24 Ekim 2026); dokununca el nasıl yapılacağını gösterir
                    var action = kind == ItemCategory.Food ? CareAction.Feed : CareAction.Wash;
                    var tip = kind == ItemCategory.Food ? Onboarding.Feed : Onboarding.Wash;
                    var it = App.Data.Item(id);
                    var d = cell.gameObject.AddComponent<DragItem>();
                    d.IconId = icon; d.Layer = Root;
                    d.Dropped = pos => { if (it == null || !OverPet(pos)) return false; CloseBag(); Care(action, it); return true; };
                    var cellRt = cell;
                    d.Tapped = () => { Audio.Sfx.Play(Audio.SfxKind.Tap); _toast.Say(T("tip." + tip, PetGen)); ShowDragTip(tip, cellRt, true, itemId); };
                    var want = _need == (action == CareAction.Feed ? StatKind.Fullness : StatKind.Cleanliness);
                    if (careCell == null || (want && careTip != tip)) { careCell = cell; careId = id; careTip = tip; }
                }
                else
                {
                    var btn = cell.gameObject.AddComponent<Button>(); btn.targetGraphic = bg;
                    btn.onClick.AddListener(() => UseFromBag(itemId, itemKind, itemName));
                }
                LongPressInfo.Add(cell.gameObject, name);
            }
            pop.gameObject.AddComponent<PopIn>();
            Audio.Sfx.Play(Audio.SfxKind.Pop);
            // el gösterimi: ilk kez (öğretici bekliyorsa) ya da Okti o şeye ihtiyaç duyuyorsa, el eşyayı çantadan Okti'ye taşır
            if (careCell != null)
            {
                var needIt = _need == (careTip == Onboarding.Feed ? StatKind.Fullness : StatKind.Cleanliness);
                ShowDragTip(careTip, careCell, needIt, careId);
            }
        }

        /// <summary>Çantadaki şeye dokun (yiyecek/sabun sürüklenir, bkz. ToggleBag): tohum ve malzeme ne işe yaradığını söyler.</summary>
        private void UseFromBag(string id, string kind, string name)
        {
            Audio.Sfx.Play(Audio.SfxKind.Tap);
            if (kind == ItemCategory.Food || kind == ItemCategory.Cleaning)
            {
                CloseBag();
                var it = App.Data.Item(id);
                if (it != null) Care(kind == ItemCategory.Food ? CareAction.Feed : CareAction.Wash, it);
                return;
            }
            _toast.Say(kind == ItemCategory.Seed ? T("bag.seed_tip", name) : T("bag.mat_tip", name));
        }

        private void CloseBag()
        {
            if (_bagPop == null) return;
            if (_coach != null && (_coach.Id == Onboarding.Feed || _coach.Id == Onboarding.Wash)) { _coach.Done(); _coach = null; }
            Destroy(_bagPop.gameObject);
            _bagPop = null;
        }

        private static void CreamCard(RectTransform rt, float height)
        {
            var img = rt.gameObject.AddComponent<Image>();
            if (Skin.Card != null) { Skin.Apply(img, Skin.Card, Mathf.Min(height, 360f)); img.color = Color.white; }
            else { img.sprite = Ui.Rounded; img.type = Image.Type.Sliced; img.color = new Color(1f, 0.96f, 0.86f); }
            rt.gameObject.AddComponent<Shadow>().effectDistance = new Vector2(0f, -8f);
        }

        // ------------------------------------------------------------------ G avatar menüsü

        private void ToggleAvatarMenu()
        {
            if (_avatarMenu != null) { CloseAvatarMenu(); return; }
            CloseBag();
            Audio.Sfx.Play(Audio.SfxKind.Tap);
            _avatarMenu = Ui.Fill(Root, "AvatarMenu");
            var catcher = _avatarMenu.gameObject.AddComponent<Image>(); catcher.color = new Color(0f, 0f, 0f, 0f);
            var close = _avatarMenu.gameObject.AddComponent<Button>(); close.transition = Selectable.Transition.None; close.onClick.AddListener(CloseAvatarMenu);
            var pop = Ui.Rect(_avatarMenu, "Pop", new Vector2(0f, 1f), new Vector2(740f, 230f), new Vector2(390f, -420f));
            CreamCard(pop, 230f);
            pop.gameObject.AddComponent<ClickSink>();
            Item("ui_album", T("menu.diary"), -270f, () => { CloseAvatarMenu(); AlbumScreen.ShowBadges(); App.Open(AppPage.Album); });
            Item("ui_settings", T("menu.settings"), -90f, () => { CloseAvatarMenu(); ParentGate(() => App.Open(AppPage.Settings), msg => _toast.Say(msg)); });
            var music = Item("ui_music", T("menu.music"), 90f, null);
            var musicOff = Slash(music);
            musicOff.SetActive(!Audio.Music.On);
            music.onClick.AddListener(() => { MusicButton.ToggleMusic(); if (musicOff != null) musicOff.SetActive(!Audio.Music.On); });
            // sesli okuma aç/kapa (kullanıcı, 23 Ekim 2026): Müzik'in yanında; balon köşesindeki hoparlörle aynı ayar
            var voice = Item("ui_voice", T("menu.voice"), 270f, null);
            var voiceOff = Slash(voice);
            voiceOff.SetActive(!Audio.Voice.Enabled);
            voice.onClick.AddListener(() =>
            {
                Audio.Voice.SetEnabled(!Audio.Voice.Enabled);
                if (voiceOff != null) voiceOff.SetActive(!Audio.Voice.Enabled);
                _toast.Say(T(Audio.Voice.Enabled ? "voice.on" : "voice.off"));
            });
            pop.gameObject.AddComponent<PopIn>();

            GameObject Slash(Button b) => Candy.OffSlash(b.transform, 110f);   // giriş ekranındaki müzik düğmesiyle aynı kırmızı çizgi

            Button Item(string icon, string label, float x, System.Action act)
            {
                var b = Candy.Round(pop, Candy.White, icon, 128f, new Vector2(0.5f, 0.5f), new Vector2(x, 22f), act, label);
                return b;
            }
        }

        private void CloseAvatarMenu()
        {
            if (_avatarMenu == null) return;
            Destroy(_avatarMenu.gameObject);
            _avatarMenu = null;
        }

        // ------------------------------------------------------------------ İ1 ihtiyaç çipi + nabız, İ4 kenar oku

        private void BuildNeed(RectTransform hud)
        {
            // İ1: halkaların sağında tek simge + tek kelime; her şey yolundaysa görünmez
            _needChip = Ui.Rect(hud, "NeedChip", new Vector2(0f, 1f), new Vector2(250f, 84f), new Vector2((20f + 116f + 12f) * G + 125f, -(12f + 116f) * G - 52f));
            var bg = _needChip.gameObject.AddComponent<Image>(); bg.sprite = Ui.Rounded; bg.type = Image.Type.Sliced; bg.color = new Color(1f, 0.97f, 0.88f, 0.96f);
            _needChip.gameObject.AddComponent<Shadow>().effectDistance = new Vector2(0f, -5f);
            var ic = Ui.IconImage(_needChip, "food_apple", new Vector2(0f, 0.5f), 70f, new Vector2(46f, 2f));
            _needChipIcon = ic != null ? ic.GetComponent<Image>() : null;
            _needWord = Ui.Label(_needChip, "", Th.Font(34), new Color(0.55f, 0.28f, 0.05f), new Vector2(0f, 0.5f), new Vector2(170f, 70f), FontStyle.Bold, TextAnchor.MiddleLeft);
            ((RectTransform)_needWord.transform).anchoredPosition = new Vector2(175f, 0f);
            var btn = _needChip.gameObject.AddComponent<Button>(); btn.targetGraphic = bg;
            btn.onClick.AddListener(() => { Audio.Sfx.Play(Audio.SfxKind.Tap); if (_need == StatKind.Cleanliness) OnWash(); else OnFeed(); });
            _needChip.gameObject.AddComponent<PressBounce>();
            _needChip.gameObject.SetActive(false);
            // nabız: ilgili halkanın arkasında yumuşak turuncu parıltı (1,6 sn; ses ya da titreşim yok)
            for (var i = 0; i < 4; i++)
            {
                if (_gaugeGlow[i] != null) continue;   // Altın Atölye yayında ışık profilde kurulur
                var g = _gauges[i] != null ? _gauges[i].transform.parent as RectTransform : null;
                if (g == null) continue;
                var glow = Ui.Rect(g, "Glow", new Vector2(0.5f, 0.5f), g.sizeDelta * 1.35f);
                glow.SetAsFirstSibling();
                var gi = glow.gameObject.AddComponent<Image>(); gi.sprite = Ui.Rounded; gi.type = Image.Type.Sliced; gi.pixelsPerUnitMultiplier = 0.4f;
                gi.color = new Color(1f, 0.62f, 0.2f, 0f); gi.raycastTarget = false;
                _gaugeGlow[i] = gi;
            }
            // İ4: Okti ekranda değilse kenarda küçük, sade ok (yüzü + ihtiyacı); dokununca kamera Okti'ye döner
            _edge = Ui.Rect(Root, "OktiEdge", Vector2.zero, new Vector2(96f, 96f));
            var eb = _edge.gameObject.AddComponent<Image>(); eb.sprite = Ui.Rounded; eb.type = Image.Type.Sliced; eb.pixelsPerUnitMultiplier = 0.4f; eb.color = new Color(1f, 1f, 1f, 0.92f);
            _edge.gameObject.AddComponent<Shadow>().effectDistance = new Vector2(0f, -4f);
            Ui.PortraitIcon(_edge, App.State.PetId, new Color(1f, 1f, 1f, 0f), new Vector2(0.5f, 0.5f), 80f);
            var tip = Ui.Rect(_edge, "Tip", new Vector2(0.5f, 0.5f), new Vector2(30f, 30f), new Vector2(58f, 0f));
            tip.localRotation = Quaternion.Euler(0f, 0f, 45f);
            var tii = tip.gameObject.AddComponent<Image>(); tii.sprite = Ui.Rounded; tii.type = Image.Type.Sliced; tii.color = new Color(1f, 1f, 1f, 0.92f); tii.raycastTarget = false;
            tip.SetAsFirstSibling();
            var en = Ui.IconImage(_edge, "food_apple", new Vector2(1f, 1f), 44f, new Vector2(-8f, -8f));
            _edgeNeed = en != null ? en.GetComponent<Image>() : null;
            var ebtn = _edge.gameObject.AddComponent<Button>(); ebtn.targetGraphic = eb;
            ebtn.onClick.AddListener(() => { Audio.Sfx.Play(Audio.SfxKind.Tap); if (_overview) ToggleMode(); else SnapCamera(); });
            _edge.gameObject.SetActive(false);
        }

        private void UpdateNeed(float dt)
        {
            if (_needChip == null) return;
            var show = _need != null && !_cine;
            if (_needChip.gameObject.activeSelf != show)
            {
                _needChip.gameObject.SetActive(show);
                if (show) { Bump.Play(_needChip, 0.3f); _needBounce = 0f; }
            }
            if (show)
            {
                var clean = _need == StatKind.Cleanliness;
                if (_needChipIcon != null) _needChipIcon.sprite = Ui.Icon(clean ? "clean_soap" : "food_apple");
                _needWord.text = T(clean ? "need.clean" : "need.food");
                if ((_needBounce += dt) > 3f) { _needBounce = 0f; Bump.Play(_needChip, 0.2f); }   // her 3 sn'de hafif zıplar
            }
            var pulse = (Mathf.Sin(Time.time * Mathf.PI * 2f / 1.6f) * 0.5f + 0.5f) * 0.55f;
            for (var i = 0; i < 4; i++)
            {
                if (_gaugeGlow[i] == null) continue;
                var on = show && HudKinds[i] == _need;
                var c = _gaugeGlow[i].color; c.a = Mathf.MoveTowards(c.a, on ? pulse : 0f, dt * 2f); _gaugeGlow[i].color = c;
            }
            UpdateEdge(show);
        }

        private void UpdateEdge(bool need)
        {
            if (_edge == null || _world.Walker == null) return;
            var cam = App.Stage.Camera;
            var sp = cam.WorldToScreenPoint(_world.Walker.transform.position + Vector3.up * PetHeight * 0.5f);
            var inView = sp.z > 0f && sp.x > 0f && sp.x < Screen.width && sp.y > 0f && sp.y < Screen.height;
            // yarım saniyeden uzun ekran dışındaysa (kamera bir an geride kalınca yanıp sönmesin)
            _edgeOff = inView ? 0f : _edgeOff + Time.deltaTime;
            var show = _edgeOff > 0.6f && !_cine && App.State.PetName != null;
            if (_edge.gameObject.activeSelf != show) _edge.gameObject.SetActive(show);
            if (!show) return;
            var k = Root.rect.width / Mathf.Max(1f, Screen.width);
            var c = new Vector2(Screen.width, Screen.height) * 0.5f;
            var d = new Vector2(sp.x, sp.y) - c;
            if (sp.z < 0f) d = -d;
            if (d.sqrMagnitude < 1f) d = Vector2.down;
            // ekran kenarına (içeriden 70 px) taşı
            var m = 70f / k;
            var sx = (c.x - m) / Mathf.Max(0.001f, Mathf.Abs(d.x)); var sy = (c.y - m) / Mathf.Max(0.001f, Mathf.Abs(d.y));
            var p = c + d * Mathf.Min(sx, sy);
            _edge.anchoredPosition = p * k;
            var tip = _edge.Find("Tip");
            if (tip != null) { var a = Mathf.Atan2(d.y, d.x); tip.localPosition = new Vector3(Mathf.Cos(a) * 52f, Mathf.Sin(a) * 52f, 0f); }
            if (_edgeNeed != null)
            {
                _edgeNeed.gameObject.SetActive(need);
                if (need) _edgeNeed.sprite = Ui.Icon(_need == StatKind.Cleanliness ? "clean_soap" : "food_apple");
            }
        }

        // ------------------------------------------------------------------ L1: seviye eşyası Evim'e uçar

        /// <summary>Seviye eşyasının uçacağı Evim düğmesi: yalnız eşya gelince sağ üstte belirir, dokununca Evim açılır, bir süre sonra çekilir.</summary>
        public RectTransform HomeTarget()
        {
            if (_homeBtn == null)
            {
                var b = Candy.Round(Root, Candy.White, "ui_home", 130f, new Vector2(1f, 1f), new Vector2(-92f, -300f), () => App.Open(AppPage.Home), T("menu.home"));
                _homeBtn = (RectTransform)b.transform;
                Candy.Count(b.transform, 46f);
                _homeBtn.gameObject.AddComponent<PopIn>();
            }
            _homeBtn.gameObject.SetActive(true);
            _homeShowFor = 8f;
            return _homeBtn;
        }

        private float _homeShowFor;

        private void UpdateHomeBtn(float dt)
        {
            if (_homeBtn == null || !_homeBtn.gameObject.activeSelf) return;
            if ((_homeShowFor -= dt) <= 0f) _homeBtn.gameObject.SetActive(false);
        }

        // ------------------------------------------------------------------ K 3B adalılar + N2

        private void BuildResidents()
        {
            var pet = _world.Walker != null ? _world.Walker.transform : null;
            System.Func<float, float, float> ground = (x, z) => _terrain.Height(x, z);
            var seen = App.State.Story.Seen;
            // Kıskaç: dükkânın meydana bakan önünde (meydandan gelen çocuk hemen görür), meydana döner
            var shop = _terrain.Regions.FirstOrDefault(r => r.Id == "region_shop");
            if (shop != null)
            {
                var d = new Vector2(_terrain.PlazaX - shop.X, _terrain.PlazaZ - shop.Z); d = d.sqrMagnitude > 0.01f ? d.normalized : Vector2.up;
                var side = new Vector2(d.y, -d.x) * 1.8f;
                var p = new Vector2(shop.X, shop.Z) + d * (shop.Size * 0.5f + 1.1f) + side;
                var w = _terrain.NearestWalkable(p.x, p.y);
                if (!float.IsNaN(w.x)) p = new Vector2(w.x, w.z);
                _kiskac = Resident3D.Create(_world.transform, "kiskac", "res_kiskac", new Vector3(p.x, _terrain.Height(p.x, p.y), p.y), 1.25f,
                    Mathf.Atan2(d.x, d.y) * Mathf.Rad2Deg, ground, pet);
            }
            // Mavi: posta kutusunun yanında; ilk oyunda Kıskaç'a cevizler teslim edilince uçarak gelir (GB17, MapScreen.Flow)
            var maviCame = seen.Contains("ch2_open") || App.State.Counters.Total("mavi_arrived") > 0
                || (App.Level >= 3 && !Logic.App.Guide.Active(App.State, App.Level));
            if (maviCame) CreateMavi();
            StoryPlayer.Speaker -= OnSpeaker; StoryPlayer.Speaker += OnSpeaker;
            // Pus: 1. bölüm kapanışından sonra adanın üstünde süzülür (gülümseyen, gökkuşaklı hâli). Yükseklik 1,6 m: kamera B'nin
            // görüşüne girer (kullanıcı GB17-14: 3 m'de kadrajın üstünde kalıyordu); meydanın kenarında, yürüyüş yolunun yanında.
            if (seen.Contains("ch1_close") || App.Level >= 2)
            {
                var x = _terrain.PlazaX + 7f; var z = _terrain.PlazaZ + 5f;
                _pus = Resident3D.Create(_world.transform, "pus", "res_pus", new Vector3(x, _terrain.Height(x, z) + 1.6f, z), 1.6f, 200f, ground, pet);
            }
            // GB18-1: konuşan palmiyeler Pıtır (uzun, cıvıl cıvıl) ve Hışır (kısa, utangaç) Hindistan Cevizi Bahçesi'nin girişinde,
            // yolun iki yanında birbirine hafif dönük; Tosbi Dede 4. bölümden sonra iskelenin girişinde (kırık köprünün ucunda)
            var grove = _terrain.Regions.FirstOrDefault(r => r.Id == "region_coconut_grove");
            if (grove != null)
            {
                var (gx, gz) = _terrain.Door(grove);
                var d = new Vector2(gx - grove.X, gz - grove.Z); d = d.sqrMagnitude > 0.01f ? d.normalized : Vector2.down;
                var side = new Vector2(d.y, -d.x);
                var yaw = Mathf.Atan2(d.x, d.y) * Mathf.Rad2Deg;
                _pitir = PlaceResident("pitir", new Vector2(gx, gz) + side * 2.8f - d * 0.4f, 2.5f, yaw - 14f, ground, pet);
                _hisir = PlaceResident("hisir", new Vector2(gx, gz) - side * 2.6f - d * 0.2f, 2.1f, yaw + 14f, ground, pet);
            }
            var pier = _terrain.Regions.FirstOrDefault(r => r.Id == "region_pier");
            if (pier != null && seen.Contains("ch4_open"))
            {
                var (px, pz) = _terrain.Door(pier);
                var d = new Vector2(px - pier.X, pz - pier.Z); d = d.sqrMagnitude > 0.01f ? d.normalized : Vector2.up;
                _tosbi = PlaceResident("tosbi", new Vector2(px, pz) + d * 1.6f + new Vector2(d.y, -d.x) * 1.4f, 1.2f, Mathf.Atan2(d.x, d.y) * Mathf.Rad2Deg, ground, pet);
            }
        }

        /// <summary>Yerde duran adalı (model Env/res_&lt;kim&gt;; yoksa kurulmaz). Yer yürünebilir en yakın noktaya çekilir.</summary>
        private Resident3D PlaceResident(string who, Vector2 p, float height, float yaw, System.Func<float, float, float> ground, Transform pet)
        {
            var w = _terrain.NearestWalkable(p.x, p.y);
            if (!float.IsNaN(w.x) && Vector2.Distance(p, new Vector2(w.x, w.z)) < 3f) p = new Vector2(w.x, w.z);
            return Resident3D.Create(_world.transform, who, "res_" + who, new Vector3(p.x, _terrain.Height(p.x, p.y), p.y), height, yaw, ground, pet);
        }

        /// <summary>Adadaki 3B adalı (yoksa null).</summary>
        private Resident3D ResidentOf(string who) =>
            who == "kiskac" ? _kiskac : who == "mavi" ? _mavi : who == "pus" ? _pus : who == "tosbi" ? _tosbi : who == "pitir" ? _pitir : who == "hisir" ? _hisir : null;

        /// <summary>Mavi posta kutusunun yanında belirir (yerine konmuş hâliyle).</summary>
        private void CreateMavi()
        {
            if (_mavi != null || _mailbox == null) return;
            var pet = _world.Walker != null ? _world.Walker.transform : null;
            System.Func<float, float, float> ground = (x, z) => _terrain.Height(x, z);
            var mb = _mailbox.transform.localPosition;
            var fwd = _mailbox.transform.localRotation * Vector3.forward;
            var right = _mailbox.transform.localRotation * Vector3.right;
            var p = mb + right * 1.2f + fwd * 0.4f;
            p.y = _terrain.Height(p.x, p.z);
            _mavi = Resident3D.Create(_world.transform, "mavi", "res_mavi", p, 1.15f, _mailbox.transform.localEulerAngles.y, ground, pet, flyer: true);
        }

        /// <summary>Hikâye konuşmasında konuşan adalı adadaysa zıplayıp sallanır (S2'de kendisi konuşur gibi).</summary>
        private void OnSpeaker(string who)
        {
            if (this == null) return;
            var r = ResidentOf(who);
            if (r != null) r.React();
        }

        /// <summary>Adalıya dokununca: tepki + kısa selam; açık isteği varsa yanına gidip kartı aç.</summary>
        private void TapResident(GameObject go)
        {
            var r = go.GetComponent<Resident3D>();
            if (r == null) return;
            r.React();
            var book = App.Data.Story;
            var open = book != null ? App.State.Story.Requests.Select(o => book.Requests.FirstOrDefault(d => d.Id == o.Id)).FirstOrDefault(d => d != null && d.Who == r.Who) : null;
            if (open != null && r.Who != "pus")
            {
                var spot = _world.Local(go.transform.position);
                var id = open.Id;
                GoTo(spot.x, spot.y, () => RequestCard(id));
                return;
            }
            var hi = "res.hi_" + r.Who;   // res.hi_kiskac, _mavi, _pus, _tosbi, _pitir, _hisir
            _toast.Say(T(hi, App.State.PetName));
        }

        // ------------------------------------------------------------------ Mavi'nin haberi (Ev Görevleri B, kullanıcı 24 Ekim 2026)
        // Ailenden yeni görev gelince postacı Mavi Okti'nin yanına uçar, krem haber kartı açılır ("Ailenden 2 yeni görev!");
        // karta dokununca Görevler penceresi. Kart 7 sn sonra söner; Mavi konup biraz bekler, yerine döner.
        private RectTransform _news;
        private float _newsT, _maviNewsT;

        /// <summary>Haberi Mavi verir (adadaysa ve sakin bir andaysa). Olmazsa false: çağıran düz bildirim gösterir.</summary>
        public bool MaviNews(string text)
        {
            if (!_built || _world == null || _world.Walker == null || _cine || _overview || StoryPlayer.Playing || !gameObject.activeInHierarchy) return false;
            if (_news != null) Destroy(_news.gameObject);
            _news = Ui.Rect(Root, "MaviNews", new Vector2(1f, 1f), new Vector2(560f, 150f));
            _news.pivot = new Vector2(1f, 1f); _news.anchoredPosition = new Vector2(-40f, -(146f + 60f) * GoldKit.K);
            var inner = GoldKit.RimCapsule(_news, Theme.Hex("#FFF8E4"), Theme.Hex("#F3DDA6"), 6f);
            // Mavi hikâyede henüz gelmediyse (ilk oyun, GB17) haberi pano simgesi verir; geldiyse Mavi'nin yüzü
            var face = _mavi != null ? StoryPlayer.ResidentPortrait("mavi") ?? Ui.Icon("res_seagull") : Ui.Icon("ui_board");
            var pic = Ui.Rect(_news, "Mavi", new Vector2(0f, 0f), new Vector2(170f, 170f), new Vector2(70f, 78f));
            var pi = pic.gameObject.AddComponent<Image>(); pi.sprite = face; pi.preserveAspect = true; pi.raycastTarget = false;
            pic.gameObject.AddComponent<Hover3D>().Amp = 8f;
            var t = Ui.Label(inner, text, 34, Theme.Hex("#5A3000"), new Vector2(0f, 0.5f), new Vector2(380f, 120f), FontStyle.Bold, TextAnchor.MiddleLeft, new Vector2(150f + 190f, 0f));
            t.raycastTarget = false;
            var hit = _news.gameObject.AddComponent<Image>(); hit.color = new Color(1f, 1f, 1f, 0f);
            var b = _news.gameObject.AddComponent<Button>(); b.targetGraphic = hit; b.transition = Selectable.Transition.None;
            b.onClick.AddListener(() => { Audio.Sfx.Play(Audio.SfxKind.Tap); if (_news != null) Destroy(_news.gameObject); QuestPanel(); });
            _news.gameObject.AddComponent<PressBounce>();
            _news.gameObject.AddComponent<PopIn>();
            _newsT = 7f;
            if (_mavi != null) _maviNewsT = 1.8f;   // Mavi Okti'ye uçar
            Audio.Sfx.Play(Audio.SfxKind.Chime);
            Audio.Haptics.Light();
            return true;
        }

        private void UpdateMaviNews(float dt)
        {
            if (_news != null && ((_newsT -= dt) <= 0f || _overview)) { Destroy(_news.gameObject); _news = null; }   // haritada yer adlarını örtmesin
        }

        /// <summary>N2: rehber okları açıkken Mavi hedefe önden uçar; oklar sönünce kona kona yerine döner.</summary>
        private void UpdateMaviGuide(bool active, Vector2 target, bool arrived)
        {
            if (_mavi == null || _world.Walker == null) return;
            if (_maviNewsT > 0f)
            {
                // haber: Okti'nin yanına uç, varınca kon (sonra kendi yerine döner)
                _maviNewsT -= Time.deltaTime;
                var q = _world.Walker.Position;
                var side = q + new Vector2(1.2f, 0.6f);
                _mavi.Guide(new Vector3(q.x, _terrain.Height(q.x, q.y), q.y), new Vector3(side.x, _terrain.Height(side.x, side.y), side.y));
                if (_maviNewsT <= 0f) _mavi.EndGuide(true);
                return;
            }
            if (active)
            {
                var p = _world.Walker.Position;
                _mavi.Guide(new Vector3(p.x, _terrain.Height(p.x, p.y), p.y), new Vector3(target.x, _terrain.Height(target.x, target.y), target.y));
            }
            else _mavi.EndGuide(arrived);
        }
    }
}
