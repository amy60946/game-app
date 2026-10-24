using System;
using System.Linq;
using Pofi.Logic.App;
using Pofi.Logic.Data;
using Pofi.Logic.Garden;
using Pofi.UI;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.Screens
{
    /// <summary>Bahçe (M7, FR-MINI-4): tohum ek → sula → gerçek zamanda büyür → hasat (yiyecek). Tarla sayısı seviyeyle artar.</summary>
    public sealed class GardenScreen : ScreenBase
    {
        private RectTransform _grid, _tools;
        private SpeechBubble _bubble;
        private float _refresh;
        private readonly System.Collections.Generic.List<RectTransform> _cells = new System.Collections.Generic.List<RectTransform>();
        private Coach _coach;
        private int _dragDone;   // bu sürüklemede ekilen/toplanan tarla sayısı

        protected override void Build()
        {
            App.Stage.SetPetVisible(false);
            App.Stage.SetBackdrop("b_garden", 6f, 3.4f);   // bahçe yapısı arka planda (dükkân gibi)
            Header(T("garden.title"));
            _bubble = Bubble(new Vector2(0.5f, 0.9f));
            _grid = ContentArea("Plots");
            // D2 (23 Ekim 2026): alt rafta tohum torbaları ve toplama eli; tarlaların üstünden sürükleyince eker / toplar.
            // Tarlaya dokunmak da çalışır (sula, tek tek ek).
            _tools = Ui.Rect(Root, "Tools", new Vector2(0.5f, 0f), new Vector2(1200f, 170f), new Vector2(0f, 110f));
            NavBar(AppPage.Map);
            Fill();
        }

        private void BuildTools()
        {
            Ui.Clear(_tools);
            var seeds = App.State.Inventory.Counts.Where(kv => kv.Value > 0).Select(kv => App.Data.Item(kv.Key))
                .Where(it => it != null && it.Category == ItemCategory.Seed).Take(5).ToList();
            var n = seeds.Count + 1;
            for (var i = 0; i < n; i++)
            {
                var x = (i - (n - 1) / 2f) * 170f;
                var harvest = i == seeds.Count;
                var seed = harvest ? null : seeds[i];
                var b = Candy.Round(_tools, Candy.White, harvest ? "tool_hand" : seed.Id, 140f, new Vector2(0.5f, 0.5f), new Vector2(x, 0f), null);
                if (!harvest) Candy.Count(b.transform).text = App.State.Inventory.CountOf(seed.Id).ToString();
                b.gameObject.AddComponent<PressBounce>();
                var d = b.gameObject.AddComponent<DragItem>();
                d.IconId = harvest ? "tool_hand" : seed.Id; d.Layer = Root;
                d.Dragging = pos => Sweep(pos, seed);
                d.Dropped = pos => { var any = _dragDone > 0; EndSweep(seed); return any; };
                d.Tapped = () => _bubble.Say(T(harvest ? "tip.harvest" : "tip.plant"));
            }
        }

        /// <summary>Sürüklerken parmağın altındaki tarla: tohumla boşsa ekilir, elle hazırsa toplanır (tarla parlar, zıplar).</summary>
        private void Sweep(Vector2 screen, ItemDef seed)
        {
            var g = App.State.Garden;
            for (var i = 0; i < _cells.Count && i < g.Plots.Count; i++)
            {
                if (_cells[i] == null || !RectTransformUtility.RectangleContainsScreenPoint(_cells[i], screen, null)) continue;
                var p = g.Plots[i];
                var cur = string.IsNullOrEmpty(p.SeedId) ? null : App.Data.Item(p.SeedId);
                var state = cur == null ? PlotState.Empty : p.StateAt(App.UtcNow, cur);
                if (seed != null && state == PlotState.Empty && App.State.Inventory.CountOf(seed.Id) > 0 && g.Plant(i, seed, App.State.Inventory) == GardenResult.Ok)
                {
                    _dragDone++; Bump.Play(_cells[i], 0.2f); Audio.Sfx.Play(Audio.SfxKind.Tap); Audio.Haptics.Light();
                }
                else if (seed == null && state == PlotState.Ready && g.Harvest(i, App.UtcNow, App.Data.Item, App.State.Inventory, out _) == GardenResult.Ok)
                {
                    _dragDone++; Bump.Play(_cells[i], 0.2f); Audio.Sfx.Play(Audio.SfxKind.Coin); Audio.Haptics.Light();
                    App.RecordActivity("harvests");
                }
                return;
            }
        }

        private void EndSweep(ItemDef seed)
        {
            if (_dragDone == 0) return;
            _bubble.Say(seed != null ? T("garden.planted") : T("garden.harvested", GardenState.HarvestYield * _dragDone, "ürün"));
            Onboarding.Done(App.State, seed != null ? Onboarding.Plant : Onboarding.Harvest);
            if (_coach != null) { _coach.Done(); _coach = null; }
            _dragDone = 0;
            App.Save();
            Fill();
        }

        /// <summary>D2 parmak ipucu: ilk kez boş tarla + tohum (ek) ya da hasada hazır ürün (topla) varken el aleti tutup tarlaya sürükler.</summary>
        private void DragHint()
        {
            if (_coach != null || _tools.childCount == 0) return;
            var g = App.State.Garden;
            int empty = -1, ready = -1;
            for (var i = 0; i < g.Plots.Count && i < _cells.Count; i++)
            {
                var p = g.Plots[i];
                var cur = string.IsNullOrEmpty(p.SeedId) ? null : App.Data.Item(p.SeedId);
                var st = cur == null ? PlotState.Empty : p.StateAt(App.UtcNow, cur);
                if (st == PlotState.Empty && empty < 0) empty = i;
                if (st == PlotState.Ready && ready < 0) ready = i;
            }
            var seedTool = _tools.childCount > 1 ? (RectTransform)_tools.GetChild(0) : null;
            var hand = (RectTransform)_tools.GetChild(_tools.childCount - 1);
            if (ready >= 0 && Onboarding.Pending(App.State, Onboarding.Harvest))
            {
                var to = _cells[ready];
                _coach = Coach.Show(Root, Onboarding.Harvest, T("tip.harvest"), TipGesture.Drag, () => ScreenOf(hand), () => ScreenOf(to), 99);
            }
            else if (empty >= 0 && seedTool != null && Onboarding.Pending(App.State, Onboarding.Plant))
            {
                var to = _cells[empty];
                var seed = seedTool.GetComponentsInChildren<Image>().Select(im => im.sprite).LastOrDefault(sp => sp != null);   // el tohumu taşır
                _coach = Coach.Show(Root, Onboarding.Plant, T("tip.plant"), TipGesture.Drag, () => ScreenOf(seedTool), () => ScreenOf(to), 99, null, null, null, seed);
            }
        }

        private static Vector2 ScreenOf(RectTransform rt) => rt != null ? RectTransformUtility.WorldToScreenPoint(null, rt.position) : Vector2.zero;

        private void OnDestroy()
        {
            if (App != null && App.Stage != null) App.Stage.SetBackdrop(null);
        }

        private void Update()
        {
            _refresh += Time.deltaTime;
            var dragging = Input.touchCount > 0 || Input.GetMouseButton(0);   // sürükleme sürerken raf yeniden kurulmasın
            if (_refresh > 5f && !dragging) { _refresh = 0f; Fill(); }
        }

        private void Fill()
        {
            Ui.Clear(_grid);
            _cells.Clear();
            var g = App.State.Garden;
            g.EnsurePlots(App.Level);
            for (var i = 0; i < g.Plots.Count; i++)
            {
                var idx = i;
                var p = g.Plots[i];
                var seed = string.IsNullOrEmpty(p.SeedId) ? null : App.Data.Item(p.SeedId);
                var state = seed == null ? PlotState.Empty : p.StateAt(App.UtcNow, seed);
                var col = i % 3;
                var row = i / 3;
                var cell = Ui.Rect(_grid, "Plot" + i, new Vector2(0.5f, 0.5f), new Vector2(440f, 360f),
                    new Vector2((col - 1) * 480f, row == 0 ? 195f : -195f));
                _cells.Add(cell);
                // v3 görünüm (kullanıcı, 19 Ekim 2026: bahçede görseller görünmüyordu): krem kart, içinde toprak yatağı; ekili
                // tohumun simgesi büyüdükçe büyür, hasada hazır ürün zıplar; boş yatakta silik "+"
                var card = cell.gameObject.AddComponent<Image>(); card.raycastTarget = false;
                if (Skin.Card != null) { Skin.Apply(card, Skin.Card, 360f); card.color = Color.white; }
                else { card.sprite = Ui.Rounded; card.type = Image.Type.Sliced; card.color = new Color(1f, 0.96f, 0.86f); }
                cell.gameObject.AddComponent<Shadow>().effectDistance = new Vector2(0f, -8f);
                var bed = Ui.Rect(cell, "Soil", new Vector2(0.5f, 0.56f), new Vector2(380f, 190f));
                var bedImg = bed.gameObject.AddComponent<Image>(); bedImg.sprite = Ui.Rounded; bedImg.type = Image.Type.Sliced; bedImg.raycastTarget = false;
                bedImg.color = Theme.Hex(state == PlotState.NeedsWater || state == PlotState.Empty ? "#B07A4C" : "#6E4527");   // sulanınca koyu, nemli toprak
                for (var f = 0; f < 3; f++)   // toprak sıraları
                {
                    var furrow = Ui.Rect(bed, "Row" + f, new Vector2(0.5f, 0.25f + f * 0.25f), new Vector2(330f, 10f));
                    var fi = furrow.gameObject.AddComponent<Image>(); fi.sprite = Ui.Rounded; fi.type = Image.Type.Sliced; fi.raycastTarget = false;
                    fi.color = new Color(0f, 0f, 0f, 0.14f);
                }
                if (seed != null)
                {
                    var produce = App.Data.Item(seed.Grows);
                    var size = state == PlotState.Ready ? 190f : state == PlotState.Growing ? 130f : 90f;
                    var icon = state == PlotState.Ready && produce != null ? produce.Id : seed.Id;
                    var img = Ui.IconImage(cell, icon, new Vector2(0.5f, 0.6f), size);
                    if (img == null)
                        Ui.Panel(Ui.Rect(cell, "Plant", new Vector2(0.5f, 0.6f), new Vector2(size, size)), state == PlotState.Ready ? Theme.Hex("#FF9F43") : Theme.Hex("#46D063"), size / 2f).raycastTarget = false;
                    else
                    {
                        img.gameObject.AddComponent<Shadow>().effectDistance = new Vector2(0f, -6f);
                        if (state == PlotState.Ready) img.gameObject.AddComponent<Pulse>();
                    }
                    if (state == PlotState.NeedsWater) Ui.IconImage(cell, "clean_soap", new Vector2(0.82f, 0.74f), 70f);   // su damlası yerine köpük: "sula" ipucu
                    Candy.Caption(cell, produce != null ? produce.Name : seed.Name, 34, new Vector2(0.5f, 0.92f), new Vector2(420f, 56f));
                }
                else
                {
                    Ui.IconImage(cell, "ui_plus", new Vector2(0.5f, 0.58f), 110f, default, new Color(1f, 1f, 1f, 0.75f));
                }
                string label;
                switch (state)
                {
                    case PlotState.Empty: label = T("garden.empty"); break;
                    case PlotState.NeedsWater: label = T("garden.water"); break;
                    case PlotState.Growing:
                        var ready = new DateTime(p.WateredUtcTicks, DateTimeKind.Utc).AddMinutes(seed.GrowMinutes);
                        label = T("garden.growing", Math.Max(1, (int)Math.Ceiling((ready - App.UtcNow).TotalMinutes)));
                        break;
                    default: label = T("garden.ready"); break;
                }
                var b = Ui.Button(cell, Th, label, new Vector2(0.5f, 0.15f), new Vector2(380f, 100f), () => Tap(idx), state != PlotState.Growing, default, 40, false);
                b.interactable = state != PlotState.Growing;
            }
            BuildTools();
            if (_coach != null) { _coach.Done(); _coach = null; }   // tarlalar yeniden kuruldu: ipucu yeni hedefe
            DragHint();
        }

        private void Tap(int i)
        {
            var g = App.State.Garden;
            var p = g.Plots[i];
            var seed = string.IsNullOrEmpty(p.SeedId) ? null : App.Data.Item(p.SeedId);
            var state = seed == null ? PlotState.Empty : p.StateAt(App.UtcNow, seed);
            switch (state)
            {
                case PlotState.Empty: PickSeed(i); break;
                case PlotState.NeedsWater:
                    if (g.Water(i, App.UtcNow) == GardenResult.Ok)
                    {
                        _bubble.Say(T("garden.watered"));
                        App.Save();
                        App.RecordActivity("plants_watered");
                    }
                    break;
                case PlotState.Ready:
                    if (g.Harvest(i, App.UtcNow, App.Data.Item, App.State.Inventory, out var produce) == GardenResult.Ok)
                    {
                        _bubble.Say(T("garden.harvested", GardenState.HarvestYield, produce.Name));
                        App.Save();
                        App.RecordActivity("harvests");
                    }
                    break;
            }
            Fill();
        }

        private void PickSeed(int plot)
        {
            var seeds = App.State.Inventory.Counts.Where(kv => kv.Value > 0).Select(kv => App.Data.Item(kv.Key))
                .Where(it => it != null && it.Category == ItemCategory.Seed).ToList();
            if (seeds.Count == 0) { _bubble.Say(T("garden.no_seed")); return; }
            var root = Modal(300f + seeds.Count * 150f, out var box);
            ModalTitle(box, T("garden.pick_seed"));
            for (var i = 0; i < seeds.Count; i++)
            {
                var seed = seeds[i];
                var b = Ui.Button(box, Th, seed.Name + "  x" + App.State.Inventory.CountOf(seed.Id), new Vector2(0.5f, 1f), new Vector2(760f, 120f), () =>
                {
                    Destroy(root.gameObject);
                    if (App.State.Garden.Plant(plot, seed, App.State.Inventory) == GardenResult.Ok)
                    {
                        _bubble.Say(T("garden.planted"));
                        App.Save();
                    }
                    Fill();
                }, false, default, 44, false);
                ((RectTransform)b.transform).anchoredPosition = new Vector2(0f, -200f - i * 150f);
            }
        }
    }
}
