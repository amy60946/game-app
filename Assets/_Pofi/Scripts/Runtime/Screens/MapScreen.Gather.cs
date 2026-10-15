using System.Collections.Generic;
using System.Linq;
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
        private readonly Text[] _trackNum = new Text[3];
        private readonly RectTransform[] _trackFill = new RectTransform[3];
        private float _respawnT;
        private int _gTarget = int.MinValue;                // en yakın erişilebilir: düğüm indeksi, -1 kulübe yeri, MinValue yok

        private const float Reach = 2.1f, SiteReach = 4.4f, BubbleRange = 11f;

        private static string ToolIcon(string tool) => tool == "axe" ? "tool_axe" : tool == "pickaxe" ? "tool_pickaxe" : "tool_hand";
        private static string MatIcon(string m) => m == Gathering.Wood ? "mat_wood" : m == Gathering.Branch ? "mat_branch" : "mat_stone";

        private void BuildGather()
        {
            var st = App.State.Gather;
            var now = App.UtcNow;
            _gNodes = Gathering.Place(_terrain);
            foreach (var n in _gNodes)
            {
                var spot = GatherSpot.Create(_world.transform, n, new Vector3(n.X, _terrain.Height(n.X, n.Z) - 0.05f, n.Z));
                spot.gameObject.SetActive(Gathering.Available(st, n.Index, now));
                _gSpots[n.Index] = spot;
            }
            _sitePos = Gathering.HutSite(_terrain);
            // kapı meydana baksın (model önü -z: Blender'da -y)
            var face = Mathf.Atan2(_terrain.PlazaX - _sitePos.x, _terrain.PlazaZ - _sitePos.z) * Mathf.Rad2Deg + 180f;
            _site = GatherSpot.CreateSite(_world.transform, new Vector3(_sitePos.x, _terrain.Height(_sitePos.x, _sitePos.z) - 0.05f, _sitePos.z), face, st.HutBuilt);
            if (_world.Walker != null) _world.Walker.Blocked = Blocked;

            // nesne üstü baloncuklar (HUD'un altında)
            _gLayer = Ui.Fill(Root, "GatherBubbles");
            foreach (var n in _gNodes)
            {
                var i = n.Index;
                var b = Candy.Round(_gLayer, Candy.White, ToolIcon(Gathering.Rule(n.Kind).Tool), 112f, Vector2.zero, Vector2.zero, () => TapNode(i));
                b.gameObject.SetActive(false);
                _gBubbles[i] = b;
            }
            _siteBubble = Candy.Round(_gLayer, Candy.White, "tool_hammer", 124f, Vector2.zero, Vector2.zero, TapSite);
            _siteBubble.gameObject.SetActive(false);
        }

        /// <summary>Joystickle yürürken engel: nesnenin içine doğru ilerlenmez (içindeyse dışarı çıkılabilir).</summary>
        private bool Blocked(float x, float z)
        {
            var cur = _world.Walker != null ? _world.Walker.Position : new Vector2(x, z);
            foreach (var s in _gSpots.Values) if (s.gameObject.activeSelf && Inside(s, x, z, cur)) return true;
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
            _tracker = Ui.Rect(hud, "Tracker", new Vector2(1f, 1f), new Vector2(330f, 420f), new Vector2(-195f, -490f));
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

        private void RefreshTracker()
        {
            if (_tracker == null) return;
            var st = App.State.Gather;
            _tracker.gameObject.SetActive(!st.HutBuilt && !_overview);
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
                    if (!_gSpots[n.Index].gameObject.activeSelf && Gathering.Available(st, n.Index, now)) _gSpots[n.Index].PopIn();
                if (_tracker != null) _tracker.gameObject.SetActive(!st.HutBuilt && !_overview);
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
            if (!st.HutBuilt && Vector2.Distance(p, new Vector2(_sitePos.x, _sitePos.z)) < SiteReach && _gTarget == int.MinValue) _gTarget = -1;

            var cam = App.Stage.Camera;
            var k = Root.rect.width / Mathf.Max(1f, Screen.width);
            foreach (var n in _gNodes)
            {
                var b = _gBubbles[n.Index]; var s = _gSpots[n.Index];
                var show = !_overview && s.gameObject.activeSelf && Vector2.Distance(p, new Vector2(n.X, n.Z)) < BubbleRange;
                if (show) show = Place(b, s, cam, k, n.Index == _gTarget);
                if (b.gameObject.activeSelf != show) b.gameObject.SetActive(show);
            }
            var siteShow = !_overview && !st.HutBuilt && Vector2.Distance(p, new Vector2(_sitePos.x, _sitePos.z)) < BubbleRange + 4f;
            if (siteShow) siteShow = Place(_siteBubble, _site, cam, k, _gTarget == -1);
            if (_siteBubble.gameObject.activeSelf != siteShow) _siteBubble.gameObject.SetActive(siteShow);

            // ilk yaklaşmada kısa ipucu (her alet için bir kez)
            if (_gTarget >= 0)
            {
                var tool = Gathering.Rule(_gNodes[_gTarget].Kind).Tool;
                var tipKey = "gather.tip_" + tool;   // gather.tip_axe / tip_hand / tip_pickaxe
                if (_gTipShown.Add(tool)) _toast.Say(T(tipKey));
            }
            else if (_gTarget == -1 && _gTipShown.Add("site")) _toast.Say(T(Gathering.CanBuild(st) ? "gather.tip_build" : "gather.tip_site"));
        }

        private bool Place(Button b, GatherSpot s, Camera cam, float k, bool target)
        {
            var sp = cam.WorldToScreenPoint(s.transform.position + Vector3.up * (s.Top + 0.55f));
            if (sp.z <= 0f) return false;
            var rt = (RectTransform)b.transform;
            var bob = target ? Mathf.Sin(Time.time * 5f) * 8f : 0f;
            rt.anchoredPosition = new Vector2(sp.x * k, sp.y * k + bob);
            rt.localScale = Vector3.one * (target ? 1.25f : 0.9f);
            b.targetGraphic.color = target ? new Color(0.62f, 0.93f, 0.72f) : Candy.White;
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
            if (hits < rule.Hits) { _gHits[i] = hits; return; }
            _gHits.Remove(i);
            var got = Gathering.Harvest(st, n, App.UtcNow);
            spot.Vanish();
            if (got > 0)
            {
                Gain(rule.Material, got, spot);
                Audio.Sfx.Play(Audio.SfxKind.Pop);
                App.RecordActivity("gathered", got);
                App.Save();
                RefreshTracker();
                if (Gathering.CanBuild(st)) _toast.Say(T("gather.ready"));
            }
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
