using System.Linq;
using Pofi.Logic.App;
using Pofi.Logic.Home;
using Pofi.UI;
using Pofi.World;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.Screens
{
    /// <summary>
    /// Evi süsle (FR-ISL-3): üstten görünüş ızgarası. Alttan eşya seç → boş kareye dokun; yerleşmiş eşyaya dokun → seç,
    /// başka kareye dokun → taşı; Döndür / Kaldır. Ortadaki kareler petin yeri.
    /// </summary>
    public sealed class DecorateScreen : ScreenBase
    {
        private RectTransform _board, _tray;
        private string _selected;          // seçili eşya (yerleşmiş ya da tepside)
        private SpeechBubble _bubble;
        private Button _rotate, _remove;

        private bool Expanded => App.Levels.IsUnlocked("home_expansion", App.Level);

        protected override void Build()
        {
            App.Stage.SetPetVisible(false);
            Header(T("decor.title"));
            _bubble = Bubble(new Vector2(0.36f, 0.93f));
            // Yatay: solda üstten ızgara, sağda eşya tepsisi ve araçlar
            _board = Ui.Rect(Root, "Board", new Vector2(0.36f, 0.5f), new Vector2(1000f, 760f), new Vector2(0f, 10f));
            Ui.Panel(_board, Theme.Hex("#F5DEB3"), Th.Radius);
            var tools = Ui.Rect(Root, "Tools", new Vector2(1f, 1f), new Vector2(700f, 110f));
            tools.pivot = new Vector2(1f, 1f);
            tools.anchoredPosition = new Vector2(-36f, -(HeaderHeight + 10f));
            _rotate = Ui.Button(tools, Th, T("decor.rotate"), new Vector2(0.25f, 0.5f), new Vector2(320f, 96f), () => { HomeLayout.Rotate(App.State, _selected); Done(); }, false, default, 36, false);
            _remove = Ui.Button(tools, Th, T("decor.remove"), new Vector2(0.75f, 0.5f), new Vector2(320f, 96f), () => { HomeLayout.Remove(App.State, _selected); _selected = null; Done(); }, false, default, 36, false);
            var trayArea = Ui.Rect(Root, "Tray", new Vector2(1f, 0f), new Vector2(700f, 600f));
            trayArea.pivot = new Vector2(1f, 0f);
            trayArea.anchoredPosition = new Vector2(-36f, NavHeight + 20f);
            Ui.Panel(trayArea, Th.Panel, Th.Radius);
            _tray = trayArea;
            NavBar(AppPage.Home);
            _bubble.Say(T("decor.hint"), 4f);
            Fill();
        }

        private void Done()
        {
            App.Save();
            Fill();
        }

        private void Fill()
        {
            Ui.Clear(_board);
            Ui.Clear(_tray);
            var expanded = Expanded;
            var (w, h) = HomeLayout.Size(expanded);
            var cell = Mathf.Min(960f / w, 720f / h);
            for (var y = 0; y < h; y++)
            for (var x = 0; x < w; x++)
            {
                var cx = x; var cy = y;
                var pos = new Vector2((x - (w - 1) / 2f) * cell, ((h - 1) / 2f - y) * cell);
                var rt = Ui.Rect(_board, $"c{x}_{y}", new Vector2(0.5f, 0.5f), new Vector2(cell - 10f, cell - 10f), pos);
                var pet = HomeLayout.IsPetCell(x, y, expanded);
                var placed = HomeLayout.At(App.State, x, y);
                Color col = pet ? Theme.Hex("#FFE3B8") : new Color(1f, 1f, 1f, 0.55f);
                if (placed != null) col = placed.ItemId == _selected ? Th.Primary : ItemColor(placed.ItemId);
                var img = Ui.Panel(rt, col, 18f);
                if (pet && x == w / 2 - 1 && y == (h - 1) / 2)
                    Ui.Label(rt, App.State.PetName, Th.Font(30), Th.SubtleText, new Vector2(1f, 0f), new Vector2(cell * 2f, 60f), FontStyle.Bold);
                if (placed != null)
                {
                    var item = App.Data.Item(placed.ItemId);
                    Ui.Label(rt, item != null ? item.Name : placed.ItemId, Th.Font(26), Color.white, new Vector2(0.5f, 0.5f), new Vector2(cell - 16f, cell - 16f), FontStyle.Bold);
                }
                if (pet) { img.raycastTarget = false; continue; }
                var b = rt.gameObject.AddComponent<Button>();
                b.targetGraphic = img;
                b.onClick.AddListener(() => TapCell(cx, cy));
            }

            var free = HomeLayout.Unplaced(App.State, App.Data);
            if (free.Count == 0)
                Ui.Label(_tray, T("decor.none"), Th.Font(36), Th.SubtleText, new Vector2(0.5f, 0.5f), new Vector2(640f, 300f));
            for (var i = 0; i < free.Count && i < 6; i++)
            {
                var it = free[i];
                var sel = it.Id == _selected;
                var b = Ui.Button(_tray, Th, it.Name, new Vector2(i % 2 == 0 ? 0.27f : 0.73f, 0.82f - (i / 2) * 0.32f), new Vector2(300f, 160f), () => { _selected = it.Id; Fill(); }, sel, default, 30, false);
                if (!sel) b.targetGraphic.color = ItemColor(it.Id);
            }
            var placedSel = _selected != null && App.State.Home.Any(p => p.ItemId == _selected);
            _rotate.interactable = placedSel;
            _remove.interactable = placedSel;
        }

        private void TapCell(int x, int y)
        {
            var expanded = Expanded;
            var at = HomeLayout.At(App.State, x, y);
            if (at != null && (_selected == null || _selected == at.ItemId || App.State.Home.Any(p => p.ItemId == _selected)))
            {
                _selected = at.ItemId == _selected ? null : at.ItemId;   // yerleşmiş eşyayı seç / bırak
                Fill();
                return;
            }
            if (_selected == null) { _bubble.Say(T("decor.pick_first")); return; }
            var placed = App.State.Home.Any(p => p.ItemId == _selected);
            var r = placed ? HomeLayout.Move(App.State, _selected, x, y, expanded)
                           : HomeLayout.Place(App.State, App.Data.Item(_selected), x, y, expanded);
            if (r == PlaceResult.Ok)
            {
                App.Stage.Hop();
                if (!placed) App.RecordActivity("home_tidied");
                _selected = null;
                Done();
            }
            else if (r == PlaceResult.Occupied) _bubble.Say(T("decor.occupied"));
        }

        private static Color ItemColor(string id)
        {
            var h = 0;
            foreach (var c in id) h = h * 31 + c;
            return Color.HSVToRGB((h & 0xFFFF) / 65535f, 0.45f, 0.85f);
        }
    }
}
