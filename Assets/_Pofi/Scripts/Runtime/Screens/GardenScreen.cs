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
        private RectTransform _grid;
        private SpeechBubble _bubble;
        private float _refresh;

        protected override void Build()
        {
            App.Stage.SetPetVisible(false);
            Header(T("garden.title"));
            _bubble = Bubble(new Vector2(0.5f, 0.84f));
            var area = Ui.Area(Root, "Plots", Vector2.zero, Vector2.one);
            area.offsetMin = new Vector2(0f, NavHeight + 30f);
            area.offsetMax = new Vector2(0f, -320f);
            _grid = area;
            NavBar(AppPage.Map);
            Fill();
        }

        private void Update()
        {
            _refresh += Time.deltaTime;
            if (_refresh > 5f) { _refresh = 0f; Fill(); }
        }

        private void Fill()
        {
            Ui.Clear(_grid);
            var g = App.State.Garden;
            g.EnsurePlots(App.Level);
            for (var i = 0; i < g.Plots.Count; i++)
            {
                var idx = i;
                var p = g.Plots[i];
                var seed = string.IsNullOrEmpty(p.SeedId) ? null : App.Data.Item(p.SeedId);
                var state = seed == null ? PlotState.Empty : p.StateAt(App.UtcNow, seed);
                var col = i % 2;
                var row = i / 2;
                var cell = Ui.Rect(_grid, "Plot" + i, new Vector2(col == 0 ? 0.27f : 0.73f, 1f), new Vector2(460f, 380f),
                    new Vector2(0f, -210f - row * 410f));
                var soil = Ui.Panel(cell, Theme.Hex(state == PlotState.NeedsWater || state == PlotState.Empty ? "#A9744A" : "#7A4F2E"), Th.Radius);
                if (seed != null)
                {
                    var produce = App.Data.Item(seed.Grows);
                    var size = state == PlotState.Ready ? 200f : state == PlotState.Growing ? 120f : 60f;
                    var plant = Ui.Rect(cell, "Plant", new Vector2(0.5f, 0.6f), new Vector2(size, size));
                    Ui.Panel(plant, state == PlotState.Ready ? Theme.Hex("#FF9F43") : Theme.Hex("#46D063"), size / 2f).raycastTarget = false;
                    Ui.Label(cell, produce != null ? produce.Name : seed.Name, Th.Font(34), Color.white, new Vector2(0.5f, 0.88f), new Vector2(440f, 60f), FontStyle.Bold);
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
            Ui.Label(box, T("garden.pick_seed"), Th.Font(52), Th.Text, new Vector2(0.5f, 1f), new Vector2(880f, 120f), FontStyle.Bold)
                .rectTransform.anchoredPosition = new Vector2(0f, -80f);
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
