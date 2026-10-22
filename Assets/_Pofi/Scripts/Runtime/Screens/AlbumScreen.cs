using System.Linq;
using Pofi.Logic.App;
using Pofi.Logic.Core;
using Pofi.Logic.Meta;
using Pofi.UI;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.Screens
{
    /// <summary>Defter (M7, FR-META-1/2): koleksiyon (böcek, kabuk, ada sakini, balık) ve rozetler.</summary>
    public sealed class AlbumScreen : ScreenBase
    {
        private static bool _badges;

        /// <summary>Defter rozetler sekmesiyle açılsın (adadaki pet kartına dokununca, XP takibi M4).</summary>
        public static void ShowBadges() => _badges = true;
        private RectTransform _list;
        private Button _tabC, _tabB;
        private static readonly string[] Cats = { "bug", "shell", "resident", "fish" };

        protected override void Build()
        {
            App.Stage.SetPetVisible(false);
            Header(T("album.title"));
            _tabC = Ui.Button(Root, Th, T("album.tab.collection"), new Vector2(0f, 1f), new Vector2(300f, 96f), () => { _badges = false; Fill(); }, !_badges, default, 36, false);
            _tabB = Ui.Button(Root, Th, T("album.tab.badges"), new Vector2(0f, 1f), new Vector2(300f, 96f), () => { _badges = true; Fill(); }, _badges, default, 36, false);
            foreach (var (b, i) in new[] { (_tabC, 0), (_tabB, 1) })
            {
                var rt = (RectTransform)b.transform;
                rt.pivot = new Vector2(0f, 1f);
                rt.anchoredPosition = new Vector2(36f, -(HeaderHeight + 10f) - i * 110f);
            }
            _list = Ui.ScrollList(CenterColumn("List", 1300f, HeaderHeight, NavHeight, true), Vector2.zero, Vector2.one, 18f);
            NavBar(AppPage.Home);
            Fill();
        }

        private void Tab(Button b, bool on)
        {
            b.targetGraphic.color = on ? Th.Primary : Th.Secondary;
            b.GetComponentInChildren<Text>().color = on ? Th.PrimaryText : Th.SecondaryText;
        }

        private void Fill()
        {
            Tab(_tabC, !_badges);
            Tab(_tabB, _badges);
            Ui.Clear(_list);
            if (_badges) Badges(); else Collection();
        }

        private void Collection()
        {
            var need = App.Levels.UnlockLevel("collection_book");
            if (App.Level < need)
            {
                var row = Ui.Row(_list, "Locked", 200f);
                Ui.Panel(row, Th.Panel, Th.Radius);
                Ui.Stretch(Ui.Label(row, T("album.locked", need), Th.Font(42), Th.SubtleText, new Vector2(0.5f, 0.5f), Vector2.zero).rectTransform);
                return;
            }
            foreach (var cat in Cats)
            {
                var all = App.Data.Collection.Where(e => e.Category == cat).ToList();
                var (found, total) = CollectionBook.Completion(App.Data.Collection, App.State.Collection, cat);
                var head = Ui.Row(_list, cat, 80f);
                Ui.Stretch(Ui.Label(head, T("album.cat." + cat) + "  " + T("album.count", found, total), Th.Font(46), Color.white, new Vector2(0.5f, 0.5f), Vector2.zero, FontStyle.Bold, TextAnchor.MiddleLeft).rectTransform);
                var row = Ui.Row(_list, cat + "_items", 230f);
                for (var i = 0; i < all.Count; i++)
                {
                    var e = all[i];
                    var have = App.State.Collection.Contains(e.Id);
                    var cell = Ui.Rect(row, e.Id, new Vector2(0.125f + i * 0.25f, 0.5f), new Vector2(230f, 220f));
                    Ui.Panel(cell, have ? Th.Panel : new Color(1f, 1f, 1f, 0.45f), Th.Radius).raycastTarget = false;
                    var dot = Ui.Rect(cell, "Icon", new Vector2(0.5f, 0.62f), new Vector2(110f, 110f));
                    Ui.Panel(dot, have ? RarityColor(e.Rarity) : new Color(0f, 0f, 0f, 0.15f), 55f).raycastTarget = false;
                    var pic = Ui.IconImage(dot, e.Id, new Vector2(0.5f, 0.5f), 130f, default, have ? (Color?)null : new Color(0.1f, 0.12f, 0.2f, 0.45f));   // bulunmayan: siluet
                    if (!have && pic == null) Ui.Label(dot, T("album.unknown"), Th.Font(60), Color.white, new Vector2(0.5f, 0.5f), new Vector2(110f, 110f), FontStyle.Bold);
                    Ui.Label(cell, have ? e.Name : "Sv " + e.Level, Th.Font(28), Th.Text, new Vector2(0.5f, 0.17f), new Vector2(220f, 70f), FontStyle.Bold);
                }
            }
        }

        private static Color RarityColor(int r) => r >= 3 ? Theme.Hex("#A77BFF") : r == 2 ? Theme.Hex("#3DC9FF") : Theme.Hex("#7BD66B");

        private void Badges()
        {
            foreach (var b in App.Data.Badges)
            {
                var have = App.State.Badges.Contains(b.Id);
                var row = Ui.Row(_list, b.Id, 150f);
                Ui.Panel(row, have ? Th.Panel : new Color(1f, 1f, 1f, 0.6f), Th.Radius);
                var medal = Ui.Rect(row, "Medal", new Vector2(0.09f, 0.5f), new Vector2(100f, 100f));
                Ui.Panel(medal, have ? Theme.Hex("#FFC400") : new Color(0f, 0f, 0f, 0.12f), 50f).raycastTarget = false;
                Ui.Label(row, b.Name, Th.Font(42), Th.Text, new Vector2(0.48f, 0.62f), new Vector2(620f, 60f), FontStyle.Bold, TextAnchor.MiddleLeft);
                var prog = Mathf.Min(b.Target, App.State.Counters.Total(b.Counter));
                var bar = Ui.Bar(row, new Vector2(0.48f, 0.28f), new Vector2(620f, 20f), new Color(0f, 0f, 0f, 0.08f), Th.Primary, 10f);
                Ui.SetBar(bar, (float)prog / b.Target);
                Ui.Label(row, T("album.badge_progress", prog, b.Target), Th.Font(36), Th.SubtleText, new Vector2(0.9f, 0.5f), new Vector2(180f, 60f), FontStyle.Bold);
            }
        }
    }
}
