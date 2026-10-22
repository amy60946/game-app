using System.Linq;
using Pofi.Logic.App;
using Pofi.Logic.Core;
using Pofi.Logic.Meta;
using Pofi.UI;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.Screens
{
    /// <summary>
    /// Defter (M7, FR-META-1/2): koleksiyon (böcek, kabuk, ada sakini, balık), rozetler, Okti'nin günlüğü (H5) ve hikâye
    /// (izlenen sahneler + fener bekçisinin bulunan sayfaları, H3).
    /// </summary>
    public sealed class AlbumScreen : ScreenBase
    {
        private const int TabCollection = 0, TabBadges = 1, TabDiary = 2, TabStory = 3;
        private static int _tab;

        /// <summary>Defter rozetler sekmesiyle açılsın (adadaki pet kartına dokununca, XP takibi M4).</summary>
        public static void ShowBadges() => _tab = TabBadges;
        private RectTransform _list;
        private readonly Button[] _tabs = new Button[4];
        private static readonly string[] Cats = { "bug", "shell", "resident", "fish" };

        protected override void Build()
        {
            App.Stage.SetPetVisible(false);
            Header(T("album.title"));
            var names = new[] { "album.tab.collection", "album.tab.badges", "album.tab.diary", "album.tab.story" };
            for (var i = 0; i < _tabs.Length; i++)
            {
                var k = i;
                _tabs[i] = Ui.Button(Root, Th, T(names[i]), new Vector2(0f, 1f), new Vector2(300f, 96f), () => { _tab = k; Fill(); }, _tab == i, default, 36, false);
                var rt = (RectTransform)_tabs[i].transform;
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
            for (var i = 0; i < _tabs.Length; i++) Tab(_tabs[i], _tab == i);
            Ui.Clear(_list);
            if (_tab == TabBadges) Badges();
            else if (_tab == TabDiary) DiaryPage();
            else if (_tab == TabStory) StoryPage();
            else Collection();
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

        // ------------------------------------------------------------------ H5 Okti'nin günlüğü
        private void DiaryPage()
        {
            Logic.Story.Diary.Record(App.State.Story, App.State.Counters, App.LocalNow);   // bugünün sayfası güncel
            var days = App.State.Story.Diary;
            if (days.Count == 0) { Note(T("diary.empty", App.State.PetName)); return; }
            for (var i = days.Count - 1; i >= 0; i--)
            {
                var e = days[i];
                var date = new System.DateTime(e.Day * System.TimeSpan.TicksPerDay);
                var h = 96f + e.Lines.Count * 66f;
                var row = Ui.Row(_list, "Day" + e.Day, h);
                Ui.Panel(row, new Color(1f, 0.97f, 0.88f, 0.96f), Th.Radius);
                Ui.Label(row, date.ToString("d MMMM", new System.Globalization.CultureInfo("tr-TR")), Th.Font(40), Theme.Hex("#8A5A22"),
                    new Vector2(0.5f, 1f), new Vector2(1180f, 80f), FontStyle.Bold, TextAnchor.MiddleLeft).rectTransform.anchoredPosition = new Vector2(0f, -44f);
                for (var j = 0; j < e.Lines.Count; j++)
                {
                    var l = e.Lines[j];
                    var t = Ui.Label(row, "• " + T(l.Key, l.Args), Th.Font(38), Theme.Hex("#4A2C0A"), new Vector2(0.5f, 1f), new Vector2(1180f, 64f), FontStyle.Normal, TextAnchor.MiddleLeft);
                    t.rectTransform.anchoredPosition = new Vector2(0f, -110f - j * 66f);
                }
            }
        }

        // ------------------------------------------------------------------ hikâye: bölümler, izlenen sahneler, bekçinin sayfaları
        private void StoryPage()
        {
            var book = App.Data.Story;
            var st = App.State.Story;
            var chapter = book.ChapterFor(App.Level);
            foreach (var c in book.Chapters)
            {
                var open = c.Number <= chapter;
                var row = Ui.Row(_list, "Ch" + c.Number, 90f);
                Ui.Stretch(Ui.Label(row, open ? T("story.chapter", c.Number, c.Title) : T("story.chapter_locked", c.Number, c.Level), Th.Font(42),
                    open ? Color.white : new Color(1f, 1f, 1f, 0.6f), new Vector2(0.5f, 0.5f), Vector2.zero, FontStyle.Bold, TextAnchor.MiddleLeft).rectTransform);
                if (!open) continue;
                foreach (var sc in book.Scenes)
                {
                    if (sc.Chapter != c.Number || !st.Seen.Contains(sc.Id)) continue;
                    var r = Ui.Row(_list, sc.Id, 110f);
                    Ui.Panel(r, Th.Panel, Th.Radius);
                    Ui.Label(r, sc.Summary, Th.Font(36), Th.Text, new Vector2(0.45f, 0.5f), new Vector2(1000f, 100f), FontStyle.Normal, TextAnchor.MiddleLeft);
                    var scene = sc;
                    Ui.Button(r, Th, T("story.replay"), new Vector2(0.9f, 0.5f), new Vector2(200f, 80f), () => Replay(scene), true, default, 32, false);
                }
            }
            if (st.IntroSeen && book.Scenes.Count > 0 && book.Scenes[0].Trigger == Logic.Story.StoryDirector.Intro)
            {
                var r = Ui.Row(_list, "intro", 110f);
                Ui.Panel(r, Th.Panel, Th.Radius);
                Ui.Label(r, T("story.intro"), Th.Font(36), Th.Text, new Vector2(0.45f, 0.5f), new Vector2(1000f, 100f), FontStyle.Normal, TextAnchor.MiddleLeft);
                var intro = book.Scenes[0];
                Ui.Button(r, Th, T("story.replay"), new Vector2(0.9f, 0.5f), new Vector2(200f, 80f), () => Replay(intro), true, default, 32, false);
            }
            var pages = Logic.Story.LorePages.Found(book, st);
            var head = Ui.Row(_list, "PagesHead", 90f);
            Ui.Stretch(Ui.Label(head, T("lore.title", pages.Count, book.Pages.Count), Th.Font(42), Color.white, new Vector2(0.5f, 0.5f), Vector2.zero, FontStyle.Bold, TextAnchor.MiddleLeft).rectTransform);
            if (pages.Count == 0) { Note(T("lore.none")); return; }
            foreach (var p in pages)
            {
                var r = Ui.Row(_list, p.Id, 150f);
                Ui.Panel(r, new Color(1f, 0.95f, 0.82f, 0.97f), Th.Radius);
                Ui.Label(r, p.Number + ".  " + p.Text, Th.Font(34), Theme.Hex("#4A2C0A"), new Vector2(0.5f, 0.5f), new Vector2(1220f, 140f), FontStyle.Italic, TextAnchor.MiddleLeft);
            }
        }

        /// <summary>İzlenmiş sahneyi yeniden oku (yaş grubuna göre metin). Sahne sunumu (S1/S2) onaylanınca oyun içi sunumla değişir.</summary>
        private void Replay(Logic.Story.StoryScene scene)
        {
            var root = Modal(1100f, out var box);
            var band = Th.Band;
            var lines = scene.Lines.Select(l => (l.Who == "narrator" ? "" : App.Data.Story.NameOf(l.Who).Replace("{pet}", App.State.PetName) + ": ") + Logic.Story.StoryDirector.Text(l, band));
            var t = Ui.Label(box, string.Join("\n\n", lines), Th.Font(38), Th.Text, new Vector2(0.5f, 0.56f), new Vector2(1000f, 560f), FontStyle.Normal, TextAnchor.MiddleLeft);
            t.horizontalOverflow = HorizontalWrapMode.Wrap;
            Ui.Button(box, Th, T("common.ok"), new Vector2(0.5f, 0.1f), new Vector2(300f, 100f), () => Destroy(root.gameObject), true, default, 40, false);
        }

        private void Note(string text)
        {
            var row = Ui.Row(_list, "Note", 180f);
            Ui.Panel(row, Th.Panel, Th.Radius);
            Ui.Stretch(Ui.Label(row, text, Th.Font(40), Th.SubtleText, new Vector2(0.5f, 0.5f), Vector2.zero).rectTransform);
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
