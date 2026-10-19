using Pofi.Audio;
using Pofi.Logic.App;
using Pofi.UI;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.Screens
{
    /// <summary>
    /// Ayarlar (FR-SET-1..3, M9 erişilebilirlik): ses, yazı boyutu, hareketi azalt, pet değiştir, çıkış.
    /// Ekrana yalnızca ebeveyn sorusu geçilerek gelinir.
    /// </summary>
    public sealed class SettingsScreen : ScreenBase
    {
        private RectTransform _list;

        protected override void Build()
        {
            App.Stage.SetPetVisible(false);
            Header(T("settings.title"));
            _list = Ui.ScrollList(CenterColumn("List", 1200f), Vector2.zero, Vector2.one, 20f);
            NavBar(AppPage.Home);
            Fill();
        }

        private void Fill()
        {
            Ui.Clear(_list);
            var st = App.State.Settings;
            Choice(T("settings.sfx"), new[] { T("settings.off"), T("settings.low"), T("settings.high") },
                st.SfxVolume <= 0.01f ? 0 : st.SfxVolume < 0.75f ? 1 : 2,
                i => { st.SfxVolume = i == 0 ? 0f : i == 1 ? 0.5f : 1f; Sfx.Volume = st.SfxVolume; Sfx.Play(SfxKind.Pop); });
            Choice(T("settings.text"), new[] { T("settings.normal"), T("settings.large") }, st.TextScale > 1.05f ? 1 : 0,
                i => { st.TextScale = i == 0 ? 1f : 1.15f; App.Theme.TextScale = st.TextScale; });
            Choice(T("settings.motion"), new[] { T("settings.on"), T("settings.off") }, st.ReduceMotion ? 1 : 0,
                i => { st.ReduceMotion = i == 1; Theme.ReduceMotion = st.ReduceMotion; });

            Action(T("settings.change_pet"), T("settings.change_pet_hint"), () =>
            {
                PetChange.Begin(App.State);
                App.Save();
                App.Route();
            });
            Action(T("settings.sign_out"), T("settings.sign_out_hint"), App.SignOut);
            // önizleme test erişimi: XP biriktirmeden tüm seviyeler, eşyalar, coin (yalnız sahte arka uçta)
            if (App.Backend != null)
                Action(T("settings.test"), T("settings.test_hint"), async () =>
                {
                    var added = Logic.App.TestAccess.GiveAllItems(App.Data, App.State.Inventory);
                    App.Backend.TestGrantCoins(Logic.App.TestAccess.Coins);
                    App.Backend.TestGrantStones(Logic.App.TestAccess.SunStones);   // tüm onarım noktaları için yeterli taş
                    var xp = Logic.App.TestAccess.XpToMax(App.Levels, App.State.Xp.TotalXp);
                    if (xp > 0) App.GrantXp(xp, Logic.Economy.XpSource.Achievement);
                    App.Save();
                    await App.SyncNow();
                    Debug.Log(T("settings.test_done", App.Level, added));
                    Fill();
                });

            var info = Ui.Row(_list, "Info", 140f);
            Ui.Stretch(Ui.Label(info, App.BuildLabel + "\n" + T("settings.child", App.Session.DisplayName), Th.Font(30), Color.white,
                new Vector2(0.5f, 0.5f), Vector2.zero).rectTransform);
        }

        private void Choice(string title, string[] options, int selected, System.Action<int> onPick)
        {
            var row = Ui.Row(_list, title, 230f);
            Ui.Panel(row, Th.Panel, Th.Radius);
            Ui.Label(row, title, Th.Font(42), Th.Text, new Vector2(0.5f, 0.78f), new Vector2(940f, 70f), FontStyle.Bold, TextAnchor.MiddleLeft);
            var w = 900f / options.Length;
            for (var i = 0; i < options.Length; i++)
            {
                var idx = i;
                Ui.Button(row, Th, options[i], new Vector2(0.5f, 0.3f), new Vector2(w - 20f, 100f), () =>
                {
                    onPick(idx);
                    App.Save();
                    App.Route();   // yazı boyutu vb. hemen görünsün
                }, i == selected, new Vector2((i - (options.Length - 1) / 2f) * w, 0f), 38, false);
            }
        }

        private void Action(string title, string hint, System.Action onClick)
        {
            var row = Ui.Row(_list, title, 200f);
            Ui.Panel(row, Th.Panel, Th.Radius);
            Ui.Label(row, hint, Th.Font(32), Th.SubtleText, new Vector2(0.33f, 0.5f), new Vector2(560f, 160f), FontStyle.Normal, TextAnchor.MiddleLeft);
            Ui.Button(row, Th, title, new Vector2(0.8f, 0.5f), new Vector2(330f, 110f), onClick, false, default, 36, false);
        }
    }
}
