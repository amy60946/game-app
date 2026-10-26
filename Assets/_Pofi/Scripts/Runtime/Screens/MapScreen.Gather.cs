using System.Collections.Generic;
using System.Linq;
using Pofi.Logic.App;
using Pofi.Logic.Island;
using Pofi.UI;
using Pofi.World;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.Screens
{
    /// <summary>
    /// Ada aksiyonları (kullanıcı isteği 15 Ekim 2026, madde 3-4; mantık: Logic/Island/Gathering):
    /// kütüğü baltayla kes, çalıdan dal topla, taşı kazmayla kır, malzemelerle kulübe inşa et.
    /// Yakındaki nesnenin üstünde alet simgeli baloncuk belirir (en yakını yeşil ve büyük); sağ alttaki eylem düğmesi
    /// o aletin simgesine döner. Sağda "Kulübe yap" malzeme listesi (n/ihtiyaç + çubuk). Yeni aksiyonlar aynı yapıya eklenir.
    /// </summary>
    public sealed partial class MapScreen
    {
        private List<GatherNode> _gNodes = new List<GatherNode>();
        private readonly Dictionary<int, GatherSpot> _gSpots = new Dictionary<int, GatherSpot>();
        private readonly Dictionary<int, Button> _gBubbles = new Dictionary<int, Button>();
        private readonly Dictionary<int, int> _gHits = new Dictionary<int, int>();
        private readonly HashSet<string> _gTipShown = new HashSet<string>();
        private GatherSpot _site;
        private Button _siteBubble;
        private (float x, float z) _sitePos;
        private RectTransform _gLayer, _tracker;
        private RectTransform _req;                         // E3 gereksinim kartı (kulübe yerinde)
        private readonly Text[] _reqNum = new Text[3];
        private readonly Outline[] _reqEdge = new Outline[3];
        private readonly GameObject[] _reqOk = new GameObject[3];
        private Button _reqGo;
        private readonly Text[] _trackNum = new Text[3];
        private readonly RectTransform[] _trackFill = new RectTransform[3];
        private float _respawnT;
        private int _gTarget = int.MinValue;                // en yakın erişilebilir: düğüm indeksi, -1 kulübe yeri, MinValue yok
        private int _gCalmFor = int.MaxValue;               // CalmBubbles en son hangi hedefe göre çalıştı

        private const float Reach = 2.1f, SiteReach = 4.4f, BubbleRange = 11f;

        private static string ToolIcon(string tool) => tool == "axe" ? "tool_axe" : tool == "pickaxe" ? "tool_pickaxe" : "tool_hand";
        private string ToolInfo(string tool) => tool == "axe" ? T("info.tool_axe") : tool == "pickaxe" ? T("info.tool_pickaxe") : T("info.tool_hand");
        private static string MatIcon(string m) => m == Gathering.Wood ? "mat_wood" : m == Gathering.Branch ? "mat_branch" : "mat_stone";

        private void BuildGather()
        {
            var st = App.State.Gather;
            var now = App.UtcNow;
            _gNodes = Gathering.Place(_terrain);
            foreach (var n in _gNodes)
            {
                var spot = GatherSpot.Create(_world.transform, n, new Vector3(n.X, _terrain.Height(n.X, n.Z) - 0.05f, n.Z));
                spot.gameObject.SetActive(Gathering.Available(st, n.Index, now) && Shown(n));
                _gSpots[n.Index] = spot;
            }
            _sitePos = Gathering.HutSite(_terrain);
            // kapı meydana baksın (model önü -z: Blender'da -y)
            var face = Mathf.Atan2(_terrain.PlazaX - _sitePos.x, _terrain.PlazaZ - _sitePos.z) * Mathf.Rad2Deg + 180f;
            _site = GatherSpot.CreateSite(_world.transform, new Vector3(_sitePos.x, _terrain.Height(_sitePos.x, _sitePos.z) - 0.05f, _sitePos.z), face, st.HutBuilt);
            BuildSiteFog();   // GB19: hediye taş konana kadar kulübe yeri sisli, şantiye görünmez
            if (_world.Walker != null) _world.Walker.Blocked = Blocked;

            // nesne üstü baloncuklar (HUD'un altında)
            _gLayer = Ui.Fill(Root, "GatherBubbles");
            foreach (var n in _gNodes)
            {
                var i = n.Index;
                var nut = n.Kind == GatherKind.Coconut;   // ceviz: baloncukta alet değil cevizin kendisi
                var b = Candy.Round(_gLayer, Candy.White, nut ? Gathering.CoconutItem : ToolIcon(Gathering.Rule(n.Kind).Tool), 112f, Vector2.zero, Vector2.zero, () => TapNode(i));
                b.gameObject.SetActive(false);
                Hover.On(b, 6f);
                LongPressInfo.Add(b.gameObject, nut ? T("info.coconut") : ToolInfo(Gathering.Rule(n.Kind).Tool));   // E4: "Balta: kütükten odun"
                _gBubbles[i] = b;
            }
            _siteBubble = Candy.Round(_gLayer, Candy.White, "tool_hammer", 124f, Vector2.zero, Vector2.zero, TapSite);
            _siteBubble.gameObject.SetActive(false);
            Hover.On(_siteBubble, 6f);
            BuildReqCard();
            CalmBubbles();
        }

        /// <summary>
        /// Kulübe malzemeleri (kütük, çalı, taş) kulübe yerindeki sis kalkana kadar adada görünmez (akış haritası yorumu, 25 Ekim 2026:
        /// "önceki görevlerde dikkat dağıtmasın"); hindistan cevizi her zaman görünür. Sis kalkınca ada yeniden kurulur, hepsi belirir.
        /// </summary>
        private bool Shown(GatherNode n) => n.Kind == GatherKind.Coconut || !SiteFogged;

        /// <summary>Çocuk toplamayı öğrendiyse (≈3 nesne) alet baloncukları sakinleşir; yalnız hedefteki canlı kalır.</summary>
        private void CalmBubbles()
        {
            var learned = App.State.Counters.Total("gathered") >= 9;
            foreach (var kv in _gBubbles) kv.Value.GetComponent<Hover>().Calm(learned && kv.Key != _gTarget);
            _siteBubble.GetComponent<Hover>().Calm(learned && _gTarget != -1);
        }

        /// <summary>Joystickle yürürken engel: nesnenin içine doğru ilerlenmez (içindeyse dışarı çıkılabilir).</summary>
        private bool Blocked(float x, float z)
        {
            var cur = _world.Walker != null ? _world.Walker.Position : new Vector2(x, z);
            foreach (var s in _gSpots.Values) if (s.gameObject.activeSelf && Inside(s, x, z, cur)) return true;
            // K: yerdeki adalıların (Kıskaç, konmuş Mavi, palmiyeler, Tosbi) içinden geçilmez
            foreach (var r in new[] { _kiskac, _mavi, _tosbi, _pitir, _hisir })
            {
                if (r == null || r.Busy) continue;
                var c = new Vector2(r.transform.localPosition.x, r.transform.localPosition.z);
                var dn = Vector2.Distance(new Vector2(x, z), c);
                if (dn < 0.75f && dn < Vector2.Distance(cur, c)) return true;
            }
            return _site != null && _site.Radius > 0f && Inside(_site, x, z, cur);
        }

        private static bool Inside(GatherSpot s, float x, float z, Vector2 cur)
        {
            var c = new Vector2(s.transform.localPosition.x, s.transform.localPosition.z);
            var dn = Vector2.Distance(new Vector2(x, z), c);
            return dn < s.Radius && dn < Vector2.Distance(cur, c);
        }

        /// <summary>Malzeme listesi (sağda, Görev/Kuşbakışı altında): kulübe yapılana kadar görünür.</summary>
        private void BuildTracker(RectTransform hud)
        {
            _tracker = Ui.Rect(hud, "Tracker", new Vector2(1f, 1f), new Vector2(330f, 420f), new Vector2(-172f, -480f));
            var title = Ui.Rect(_tracker, "Title", new Vector2(0.5f, 1f), new Vector2(330f, 70f), new Vector2(0f, -35f));
            Candy.Tag(title, T("gather.hut"), new Color(0.1f, 0.36f, 0.68f, 0.9f), 34, 64f);
            Ui.IconImage(title, "tool_hammer", new Vector2(0f, 0.5f), 78f, new Vector2(4f, 0f));
            for (var i = 0; i < Gathering.HutRecipe.Length; i++)
            {
                var (m, need) = Gathering.HutRecipe[i];
                var row = Ui.Rect(_tracker, m, new Vector2(0.5f, 1f), new Vector2(330f, 104f), new Vector2(0f, -130f - i * 114f));
                var bg = row.gameObject.AddComponent<Image>(); bg.sprite = Ui.Rounded; bg.type = Image.Type.Sliced; bg.color = new Color(1f, 0.98f, 0.93f, 0.95f); bg.raycastTarget = false;
                row.gameObject.AddComponent<Shadow>().effectDistance = new Vector2(0f, -6f);
                Ui.IconImage(row, MatIcon(m), new Vector2(1f, 0.5f), 86f, new Vector2(-52f, 6f));
                RewardFlight.Register(m, row);   // O1: toplanan malzeme kendi satırına uçar
                _trackNum[i] = Ui.Label(row, "", Th.Font(36), new Color(0.24f, 0.2f, 0.18f), new Vector2(0f, 0.5f), new Vector2(230f, 60f), FontStyle.Bold);
                ((RectTransform)_trackNum[i].transform).anchoredPosition = new Vector2(130f, 14f);
                _trackNum[i].alignment = TextAnchor.MiddleLeft;
                var bar = Ui.Rect(row, "Bar", new Vector2(0f, 0f), new Vector2(220f, 18f), new Vector2(130f, 24f));
                var bb = bar.gameObject.AddComponent<Image>(); bb.sprite = Ui.Rounded; bb.type = Image.Type.Sliced; bb.color = new Color(0.33f, 0.33f, 0.36f); bb.raycastTarget = false;
                var fill = Ui.Rect(bar, "Fill", new Vector2(0f, 0.5f), new Vector2(0f, 18f));
                fill.pivot = new Vector2(0f, 0.5f); fill.anchorMin = new Vector2(0f, 0f); fill.anchorMax = new Vector2(0f, 1f); fill.sizeDelta = Vector2.zero;
                var fi = fill.gameObject.AddComponent<Image>(); fi.sprite = Ui.Rounded; fi.type = Image.Type.Sliced; fi.color = new Color(0.3f, 0.75f, 0.62f); fi.raycastTarget = false;
                _trackFill[i] = fill;
            }
            RefreshTracker();
        }

        /// <summary>
        /// E3 gereksinim kartı (23 Ekim 2026, kullanıcı onayı): kulübe yerine gelince şantiyenin üstünde küçük krem kart.
        /// Her malzeme resimli bir kutu; tamamlanan yeşil kenar + tik, eksik turuncu kenar. Hepsi tamamsa tek yeşil "Yap" açılır.
        /// </summary>
        private void BuildReqCard()
        {
            const float slot = 150f, gap = 18f;
            var n = Gathering.HutRecipe.Length;
            var w = n * slot + (n - 1) * gap + 60f;
            _req = Ui.Rect(_gLayer, "HutNeeds", Vector2.zero, new Vector2(w, 330f));
            _req.pivot = new Vector2(0.5f, 0f);
            var bg = _req.gameObject.AddComponent<Image>(); bg.raycastTarget = true;   // kartın üstüne dokununca yere yürümesin
            if (Skin.Card != null) { Skin.Apply(bg, Skin.Card, 330f); bg.color = Color.white; }
            else { bg.sprite = Ui.Rounded; bg.type = Image.Type.Sliced; bg.color = new Color(1f, 0.96f, 0.86f); }
            _req.gameObject.AddComponent<Shadow>().effectDistance = new Vector2(0f, -8f);
            var title = Ui.Rect(_req, "Title", new Vector2(0.5f, 1f), new Vector2(240f, 64f), new Vector2(0f, 4f));
            Candy.Tag(title, T("gather.hut_short"), new Color(0.1f, 0.42f, 0.78f, 0.95f), 34, 64f);
            Ui.IconImage(title, "ui_hut", new Vector2(0f, 0.5f), 76f, new Vector2(-10f, 4f));
            for (var i = 0; i < n; i++)
            {
                var (m, _) = Gathering.HutRecipe[i];
                var x = -((n - 1) * (slot + gap)) * 0.5f + i * (slot + gap);
                var c = Ui.Rect(_req, "Need " + m, new Vector2(0.5f, 1f), new Vector2(slot, slot), new Vector2(x, -128f));
                var ci = c.gameObject.AddComponent<Image>(); ci.sprite = Ui.Rounded; ci.type = Image.Type.Sliced; ci.color = new Color(1f, 1f, 1f, 0.92f); ci.raycastTarget = false;
                _reqEdge[i] = c.gameObject.AddComponent<Outline>(); _reqEdge[i].effectDistance = new Vector2(5f, -5f);
                Ui.IconImage(c, MatIcon(m), new Vector2(0.5f, 0.6f), 96f);
                _reqNum[i] = Ui.Label(c, "", Th.Font(34), new Color(0.35f, 0.2f, 0.06f), new Vector2(0.5f, 0f), new Vector2(slot, 48f), FontStyle.Bold);
                ((RectTransform)_reqNum[i].transform).anchoredPosition = new Vector2(0f, 26f);
                var ok = Ui.IconImage(c, "ui_check", new Vector2(1f, 1f), 58f, new Vector2(-6f, -6f));
                _reqOk[i] = ok != null ? ok.gameObject : null;
                LongPressInfo.Add(c.gameObject, T("gather." + m));   // E4: malzemenin adı
            }
            _reqGo = Candy.Pill(_req, Candy.Green, T("gather.make"), new Vector2(0.5f, 0f), new Vector2(230f, 84f), new Vector2(0f, 12f), BuildHut);
            _req.gameObject.AddComponent<PopIn>();
            _req.gameObject.SetActive(false);
            RefreshReq();
        }

        private void RefreshReq()
        {
            if (_req == null) return;
            var st = App.State.Gather;
            for (var i = 0; i < Gathering.HutRecipe.Length; i++)
            {
                var (m, need) = Gathering.HutRecipe[i];
                var have = Gathering.Count(st, m);
                var done = have >= need;
                _reqNum[i].text = Mathf.Min(have, need) + "/" + need;
                _reqNum[i].color = done ? new Color(0.13f, 0.5f, 0.24f) : new Color(0.72f, 0.33f, 0.04f);
                _reqEdge[i].effectColor = done ? new Color(0.25f, 0.72f, 0.35f, 0.95f) : new Color(1f, 0.55f, 0.12f, 0.95f);
                if (_reqOk[i] != null) _reqOk[i].SetActive(done);
            }
            var can = Gathering.CanBuild(st);
            _reqGo.interactable = can;
            _reqGo.targetGraphic.color = can ? Color.white : new Color(0.72f, 0.72f, 0.72f, 0.85f);
        }

        private void RefreshTracker()
        {
            var st = App.State.Gather;
            if (_site != null && !st.HutBuilt)
                _site.SetProgress(Gathering.Count(st, Gathering.Wood), Gathering.Count(st, Gathering.Branch), Gathering.Count(st, Gathering.Stone), Gathering.HutProgress(st));
            RefreshReq();
            if (_hutChip != null)
            {
                var show = !st.HutBuilt && !SiteFogged && !_overview && (_req == null || !_req.gameObject.activeSelf);
                if (_hutChip.gameObject.activeSelf != show) _hutChip.gameObject.SetActive(show);
                var got = 0; var all = 0;
                foreach (var (m, need) in Gathering.HutRecipe) { got += Mathf.Min(Gathering.Count(st, m), need); all += need; }
                _hutText.text = T("gather.hut_short") + " " + got + "/" + all;
                _hutRing.fillAmount = all > 0 ? got / (float)all : 0f;
            }
            if (_tracker == null) return;
            _tracker.gameObject.SetActive(!st.HutBuilt && !_overview && (_req == null || !_req.gameObject.activeSelf));
            for (var i = 0; i < Gathering.HutRecipe.Length; i++)
            {
                var (m, need) = Gathering.HutRecipe[i];
                var have = Gathering.Count(st, m);
                _trackNum[i].text = Mathf.Min(have, need) + "/" + need + "  " + T("gather." + m);
                _trackFill[i].anchorMax = new Vector2(Mathf.Clamp01(have / (float)need), 1f);
            }
        }

        /// <summary>Her kare: yeniden çıkan noktalar, baloncukların yeri ve en yakın hedef.</summary>
        private void UpdateGather()
        {
            if (_world.Walker == null) return;
            var st = App.State.Gather;
            if ((_respawnT -= Time.deltaTime) <= 0f)
            {
                _respawnT = 2f;
                var now = App.UtcNow;
                foreach (var n in _gNodes)
                    if (!_gSpots[n.Index].gameObject.activeSelf && Gathering.Available(st, n.Index, now) && Shown(n)) _gSpots[n.Index].PopIn();
                if (_tracker != null) _tracker.gameObject.SetActive(!st.HutBuilt && !_overview && (_req == null || !_req.gameObject.activeSelf));
            }
            var p = _world.Walker.Position;
            // en yakın erişilebilir hedef
            _gTarget = int.MinValue; var best = float.MaxValue;
            foreach (var n in _gNodes)
            {
                if (!_gSpots[n.Index].gameObject.activeSelf) continue;
                var d = Vector2.Distance(p, new Vector2(n.X, n.Z));
                if (d < Reach + _gSpots[n.Index].Radius * 0.5f && d < best) { best = d; _gTarget = n.Index; }
            }
            var siteOpen = !st.HutBuilt && !SiteFogged;   // sisliyken şantiye yok (önce hediye taş)
            if (siteOpen && Vector2.Distance(p, new Vector2(_sitePos.x, _sitePos.z)) < SiteReach && _gTarget == int.MinValue) _gTarget = -1;
            if (_gTarget != _gCalmFor) { _gCalmFor = _gTarget; CalmBubbles(); }

            var cam = App.Stage.Camera;
            var k = Root.rect.width / Mathf.Max(1f, Screen.width);
            foreach (var n in _gNodes)
            {
                var b = _gBubbles[n.Index]; var s = _gSpots[n.Index];
                var show = !_overview && s.gameObject.activeSelf && Vector2.Distance(p, new Vector2(n.X, n.Z)) < BubbleRange;
                if (show) show = Place(b, s, cam, k, n.Index == _gTarget);
                if (b.gameObject.activeSelf != show) b.gameObject.SetActive(show);
            }
            // E3: şantiyedeyken alet baloncuğu yerine gereksinim kartı
            var atSite = !_overview && siteOpen && _gTarget == -1;
            var siteShow = !_overview && siteOpen && !atSite && Vector2.Distance(p, new Vector2(_sitePos.x, _sitePos.z)) < BubbleRange + 4f;
            if (siteShow) siteShow = Place(_siteBubble, _site, cam, k, false);
            if (_siteBubble.gameObject.activeSelf != siteShow) _siteBubble.gameObject.SetActive(siteShow);
            if (_req != null)
            {
                var reqShow = atSite && PlaceReq(cam, k);
                if (_req.gameObject.activeSelf != reqShow)
                {
                    _req.gameObject.SetActive(reqShow);
                    if (reqShow) RefreshReq();
                    if (_tracker != null) _tracker.gameObject.SetActive(!st.HutBuilt && !_overview && !reqShow);
                    if (_hutChip != null) _hutChip.gameObject.SetActive(siteOpen && !_overview && !reqShow);
                }
            }

            // ilk yaklaşmada kısa ipucu (her alet için bir kez)
            if (_gTarget >= 0)
            {
                var kind = _gNodes[_gTarget].Kind;
                var tool = kind == GatherKind.Coconut ? "coconut" : kind == GatherKind.BigLog ? "biglog" : Gathering.Rule(kind).Tool;
                var tipKey = "gather.tip_" + tool;   // gather.tip_axe / tip_hand / tip_pickaxe / tip_coconut
                if (_gTipShown.Add(tool)) _toast.Say(T(tipKey));
            }
            else if (_gTarget == -1 && _req == null && _gTipShown.Add("site")) _toast.Say(T(Gathering.CanBuild(st) ? "gather.tip_build" : "gather.tip_site"));   // E3 kartı varken gerek yok
        }

        private bool Place(Button b, GatherSpot s, Camera cam, float k, bool target)
        {
            var sp = cam.WorldToScreenPoint(s.transform.position + Vector3.up * (s.Top + 0.55f));
            if (sp.z <= 0f) return false;
            var rt = (RectTransform)b.transform;
            rt.anchoredPosition = new Vector2(sp.x * k, sp.y * k);   // süzülme + nefes: Hover
            rt.localScale = Vector3.one * (target ? 1.25f : 0.9f);
            b.targetGraphic.color = target ? new Color(0.62f, 0.93f, 0.72f) : Candy.White;
            return true;
        }

        /// <summary>Kart şantiyenin üstünde, ekran içinde kalır (üstte HUD'a, yanlarda kenara taşmaz).</summary>
        private bool PlaceReq(Camera cam, float k)
        {
            var sp = cam.WorldToScreenPoint(_site.transform.position + Vector3.up * (_site.Top + 0.4f));
            if (sp.z <= 0f) return false;
            var half = _req.sizeDelta.x * 0.5f;
            var x = Mathf.Clamp(sp.x * k, half + 40f, Root.rect.width - half - 40f);
            var y = Mathf.Clamp(sp.y * k, 160f, Root.rect.height - _req.sizeDelta.y - 190f);
            _req.anchoredPosition = new Vector2(x, y);
            return true;
        }

        /// <summary>Eylem düğmesi için: yakında aksiyon varsa anahtar, simge ve eylem.</summary>
        private bool GatherAction(out string key, out string icon, out System.Action act)
        {
            key = icon = null; act = null;
            if (_gTarget >= 0)
            {
                var n = _gNodes[_gTarget];
                var rule = Gathering.Rule(n.Kind);
                key = rule.Tool == "axe" ? "hud.chop" : rule.Tool == "pickaxe" ? "hud.mine" : "hud.collect";
                icon = ToolIcon(rule.Tool);
                var i = n.Index; act = () => Hit(i);
                return true;
            }
            if (_gTarget == -1)
            {
                key = "hud.build"; icon = "tool_hammer"; act = BuildHut;
                return true;
            }
            return false;
        }

        private void TapNode(int i)
        {
            var n = _gNodes.FirstOrDefault(x => x.Index == i);
            if (n == null || _world.Walker == null) return;
            if (_gTarget == i) { Hit(i); return; }
            var p = _world.Walker.Position;
            var dir = (p - new Vector2(n.X, n.Z)).normalized;
            var stand = new Vector2(n.X, n.Z) + dir * (_gSpots[i].Radius + 0.7f);
            GoTo(stand.x, stand.y, () => Hit(i));
        }

        private void TapSite()
        {
            if (_world.Walker == null) return;
            if (SiteFogged) { _toast.Say(T("map.site_fog")); return; }
            if (_gTarget == -1) { BuildHut(); return; }
            var p = _world.Walker.Position;
            var c = new Vector2(_sitePos.x, _sitePos.z);
            var stand = c + (p - c).normalized * 3.8f;   // kulübenin dışında (4.2 m genişlik + veranda)
            GoTo(stand.x, stand.y, BuildHut);
        }

        /// <summary>Bir vuruş: pet döner ve vurur, nesne sallanır, ses + titreşim; son vuruşta malzeme kazanılır.</summary>
        private void Hit(int i)
        {
            var n = _gNodes.FirstOrDefault(x => x.Index == i);
            if (n == null || !_gSpots[i].gameObject.activeSelf) return;
            var st = App.State.Gather;
            if (!Gathering.Available(st, i, App.UtcNow)) return;
            var rule = Gathering.Rule(n.Kind);
            var spot = _gSpots[i];
            _world.Walker.Face(n.X, n.Z);
            _world.Walker.Swing();
            ToolSwing(ToolIcon(rule.Tool), spot);
            spot.Hit();
            Audio.Sfx.Play(n.Kind == GatherKind.Log ? Audio.SfxKind.Chop : n.Kind == GatherKind.Bush ? Audio.SfxKind.Rustle : Audio.SfxKind.Clink);
            Audio.Haptics.Medium();
            _gHits.TryGetValue(i, out var hits);
            hits++;
            if (hits < rule.Hits)
            {
                _gHits[i] = hits;
                if (rule.Hits > 3) _toast.Say(T("gather.big_hit", hits, rule.Hits));   // büyük kütük: kaçıncı vuruş (GB18)
                return;
            }
            _gHits.Remove(i);
            var got = Gathering.Harvest(st, n, App.UtcNow);
            spot.Vanish();
            if (got > 0 && rule.Material == Gathering.Coconut) { PickCoconut(got, spot); return; }
            if (got > 0)
            {
                Gain(rule.Material, got, spot);
                var from = App.Stage.Camera.WorldToScreenPoint(spot.transform.position + Vector3.up * (spot.Top * 0.6f));
                RewardFlight.Fly(App.Overlay.transform, rule.Material, MatIcon(rule.Material), got, from);
                Audio.Sfx.Play(Audio.SfxKind.Pop);
                App.RecordActivity("gathered", got);
                CalmBubbles();
                App.Save();
                RefreshTracker();
                if (Gathering.CanBuild(st)) { _toast.Say(T("gather.ready")); App.RecordActivity("hut_ready"); }
            }
        }

        /// <summary>Yerden hindistan cevizi (GB17): envantere yiyecek olarak girer, çantaya uçar; 2 olunca Kıskaç'a götürme sırası.</summary>
        private void PickCoconut(int got, GatherSpot spot)
        {
            var item = App.Data.Item(Gathering.CoconutItem);
            if (item == null) return;
            App.State.Inventory.Add(item, got);
            var from = App.Stage.Camera.WorldToScreenPoint(spot.transform.position + Vector3.up * 0.4f);
            RewardFlight.Fly(App.Overlay.transform, Gathering.Coconut, Gathering.CoconutItem, got, from);
            Audio.Sfx.Play(Audio.SfxKind.Pop);
            App.RecordActivity("coconut_picked", got);
            App.Save();
            if (!CheckCoconuts()) _toast.Say(T("gather.coconut_got"));
        }

        /// <summary>Elde Kıskaç'ın istediği kadar ceviz var mı? Varsa (rehberde sırası geldiyse) adım biter, çocuğa söylenir.</summary>
        private bool CheckCoconuts()
        {
            if (App.State.Inventory.CountOf(Gathering.CoconutItem) < Guide.CoconutsNeeded) return false;
            if (!Guide.Is(App.State, App.Level, "coconut")) return false;
            App.RecordActivity("coconuts_ready");
            _toast.Say(T("gather.coconut_ready"));
            return true;
        }

        private void BuildHut()
        {
            var st = App.State.Gather;
            if (st.HutBuilt) { _toast.Say(T("gather.built_already")); return; }
            if (!Gathering.Build(st))
            {
                var missing = Gathering.HutRecipe.Where(r => Gathering.Count(st, r.material) < r.count)
                    .Select(r => (r.count - Gathering.Count(st, r.material)) + " " + T("gather." + r.material).ToLowerInvariant());
                _toast.Say(T("gather.need", string.Join(", ", missing)));
                Audio.Sfx.Play(Audio.SfxKind.Fail);
                return;
            }
            if (_world.Walker != null)
            {
                // pet kulübenin içinde kalmasın: meydana bakan tarafa, kulübenin dışına al
                var c = new Vector2(_sitePos.x, _sitePos.z);
                var p = _world.Walker.Position;
                if (Vector2.Distance(p, c) < 3.4f)
                {
                    var dir = new Vector2(_terrain.PlazaX, _terrain.PlazaZ) - c;
                    var q = c + (dir.sqrMagnitude > 0.01f ? dir.normalized : Vector2.up) * 3.8f;
                    _world.Walker.Teleport(q.x, q.y, 0f);
                }
                _world.Walker.Face(_sitePos.x, _sitePos.z); _world.Walker.Jump();
            }
            _site.BuildHut();
            Audio.Sfx.Play(Audio.SfxKind.Success);
            Audio.Haptics.Medium();
            var sp = App.Stage.Camera.WorldToScreenPoint(_site.transform.position + Vector3.up * 2f);
            StarSparkles.Around(Root, new Vector2(sp.x / Mathf.Max(1f, Screen.width), sp.y / Mathf.Max(1f, Screen.height)), new Vector2(0.14f, 0.2f), 10, 7);
            _xpFrom = _site.transform.position + Vector3.up * 1.5f;
            App.GrantXp(Gathering.HutXp, Logic.Economy.XpSource.Achievement);
            App.RecordActivity("hut_built");
            App.Save();
            RefreshTracker();
            _toast.Say(T("gather.built"));
        }

        private Vector2 UiFromWorld(Vector3 w)
        {
            var sp = App.Stage.Camera.WorldToScreenPoint(w);
            var k = Root.rect.width / Mathf.Max(1f, Screen.width);
            return new Vector2(sp.x * k, sp.y * k);
        }

        /// <summary>"+2 Odun" yazısı nesnenin üstünden yükselir.</summary>
        private void Gain(string material, int n, GatherSpot spot)
        {
            var f = Ui.Rect(Root, "Gain", Vector2.zero, new Vector2(330f, 96f), UiFromWorld(spot.transform.position + Vector3.up * (spot.Top + 0.3f)));
            var bg = f.gameObject.AddComponent<Image>(); bg.sprite = Ui.Rounded; bg.type = Image.Type.Sliced; bg.color = new Color(1f, 0.98f, 0.93f, 0.96f); bg.raycastTarget = false;
            Ui.IconImage(f, MatIcon(material), new Vector2(0f, 0.5f), 84f, new Vector2(52f, 0f));
            var t = Ui.Label(f, T("gather.gain", n, T("gather." + material)), Th.Font(40), new Color(0.2f, 0.55f, 0.25f), new Vector2(0.5f, 0.5f), new Vector2(230f, 90f), FontStyle.Bold);
            ((RectTransform)t.transform).anchoredPosition = new Vector2(40f, 0f);
            f.gameObject.AddComponent<FloatUp>();
        }

        /// <summary>Alet simgesi nesnenin yanında bir kez sallanır (vuruş hissi).</summary>
        private void ToolSwing(string icon, GatherSpot spot)
        {
            var at = UiFromWorld(spot.transform.position + Vector3.up * (spot.Top * 0.7f + 0.3f));
            var rt = Ui.Rect(Root, "Swing", Vector2.zero, new Vector2(150f, 150f), at + new Vector2(70f, 40f));
            var img = rt.gameObject.AddComponent<Image>(); img.sprite = Ui.Icon(icon); img.preserveAspect = true; img.raycastTarget = false;
            rt.pivot = new Vector2(0.2f, 0.15f);
            rt.gameObject.AddComponent<SwingOnce>();
        }

        /// <summary>Test: en yakın aksiyonu yap (yoksa en yakın düğüme yürü), malzeme ver.</summary>
        public string DebugGather(string arg)
        {
            var st = App.State.Gather;
            if (arg == "give") { foreach (var (m, n) in Gathering.HutRecipe) st.Materials[m] = Gathering.Count(st, m) + n; RefreshTracker(); return "verildi"; }
            if (arg == "near")
            {
                var p = _world.Walker.Position;
                var n = _gNodes.Where(x => _gSpots[x.Index].gameObject.activeSelf).OrderBy(x => Vector2.Distance(p, new Vector2(x.X, x.Z))).FirstOrDefault();
                if (n != null) TapNode(n.Index);
                return n != null ? n.Kind + " " + n.Index : "yok";
            }
            if (arg == "site") { TapSite(); return "kulübe yeri"; }
            if (arg == "nut" || arg == "kiskac")   // GB17 çekimleri: en yakın yerdeki cevizin / Kıskaç'ın 3 m yanına ışınlan, ona dön
            {
                Vector2 c;
                if (arg == "kiskac") { if (_kiskac == null) return "Kıskaç yok"; c = KiskacPos; }
                else
                {
                    var p = _world.Walker.Position;
                    var nut = _gNodes.Where(x => x.Kind == GatherKind.Coconut && _gSpots[x.Index].gameObject.activeSelf).OrderBy(x => Vector2.Distance(p, new Vector2(x.X, x.Z))).FirstOrDefault();
                    if (nut == null) return "ceviz yok";
                    c = new Vector2(nut.X, nut.Z);
                }
                var from = c + new Vector2(0f, -2.4f);
                _world.Walker.Teleport(from.x, from.y, 0f);
                _world.Walker.Face(c.x, c.y);
                return arg + " " + c.x.ToString("0.0") + " " + c.y.ToString("0.0");
            }
            if (arg == "state") return $"hedef={_gTarget} eylem={_actionKey} odun={Gathering.Count(st, Gathering.Wood)} dal={Gathering.Count(st, Gathering.Branch)} taş={Gathering.Count(st, Gathering.Stone)} kulübe={st.HutBuilt}";
            _actionDo?.Invoke();
            return "eylem " + _actionKey;
        }
    }

    /// <summary>Alet simgesi: yukarıdan aşağı tek vuruş yayı, sonra söner.</summary>
    public sealed class SwingOnce : MonoBehaviour
    {
        private float _t;
        private Image _img;
        private void Start() => _img = GetComponent<Image>();
        private void Update()
        {
            _t += Time.unscaledDeltaTime / 0.32f;
            var a = Mathf.Lerp(55f, -35f, Mathf.SmoothStep(0f, 1f, Mathf.Clamp01(_t * 1.4f)));
            transform.localRotation = Quaternion.Euler(0f, 0f, a);
            if (_img != null) { var c = _img.color; c.a = 1f - Mathf.Clamp01((_t - 0.7f) * 3f); _img.color = c; }
            if (_t >= 1f) Destroy(gameObject);
        }
    }
}
