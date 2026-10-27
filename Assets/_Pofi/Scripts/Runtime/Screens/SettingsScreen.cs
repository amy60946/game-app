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
            // hikâye sahneleri (kapalıyken yalnız tek satırlık özet balonu; Defter'den yine okunur)
            Choice(T("settings.story"), new[] { T("settings.on"), T("settings.off") }, st.StoryOn ? 0 : 1, i => st.StoryOn = i == 0);
            // sesli okuma (herkeste açık; çocuk balon köşesindeki hoparlörden de kapatır)
            Choice(T("settings.voice"), new[] { T("settings.on"), T("settings.off") }, st.VoiceOn ? 0 : 1, i => Voice.SetEnabled(i == 0));

            Action(T("settings.change_pet"), T("settings.change_pet_hint"), () =>
            {
                PetChange.Begin(App.State);
                App.Save();
                App.Route();
            });
            Action(T("settings.sign_out"), T("settings.sign_out_hint"), App.SignOut);
            // hukuk (ortak hukuk/50-uygulama-ici-metinler.md §10; taslak, avukat onayı bekler): çocuğa kısa not + veliye bilgi + belgeler
            Action(T("settings.info"), T("settings.info_hint"), ShowInfo);
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

            // sesli okuma atfı (Ahenk CC BY 4.0 zorunlu; seslerin yapay olduğu belirtilir)
            var credits = Ui.Row(_list, "Credits", 190f);
            Ui.Stretch(Ui.Label(credits, T("settings.voice_credits"), Th.Font(26), Color.white, new Vector2(0.5f, 0.5f), Vector2.zero).rectTransform);
            var info = Ui.Row(_list, "Info", 140f);
            Ui.Stretch(Ui.Label(info, App.BuildLabel + "\n" + T("settings.child", App.Session.DisplayName), Th.Font(30), Color.white,
                new Vector2(0.5f, 0.5f), Vector2.zero).rectTransform);
        }

        // ------------------------------------------------------------------ Bilgi (ebeveyn kapısının arkası)

        /// <summary>Belge anahtarı → sunucudaki herkese açık metin (alan adı alınınca kendi adresimize taşınır). Sunucu yoksa null.</summary>
        private string LegalUrl(string doc) =>
            App.Server != null && App.Server.IsConfigured ? App.Server.Url.TrimEnd('/') + "/functions/v1/legal?doc=" + doc : null;

        private static readonly (string doc, string key)[] LegalDocs =
        {
            ("gizlilik", "info.link.gizlilik"), ("kosullar-gameapp", "info.link.kosullar"),
            ("aydinlatma-cocuk", "info.link.aydinlatma"), ("kvkk-basvuru", "info.link.kvkk"),
        };

        /// <summary>
        /// Bilgi penceresi: en üstte çocuğa kısa not (büyük yazı, sesli okunur; aydinlatma-cocuk Kısım B), altında ebeveynler için
        /// bilgi ve belge bağlantıları (tarayıcıda açılır, önce haber verilir). Çocuk hiçbir metni onaylamaz: onay velinin, ParentApp'te.
        /// </summary>
        private void ShowInfo()
        {
            RectTransform box;
            var root = Modal(980f, out box, true);
            box.sizeDelta = new Vector2(1400f, box.sizeDelta.y);
            ModalTitle(box, T("info.title"));
            ModalClose(box, () => { Voice.StopIf(T("info.child")); Destroy(root.gameObject); });
            var list = Ui.ScrollList(box, Vector2.zero, Vector2.one, 18f);
            var area = (RectTransform)list.parent;
            if (area != box) { area.offsetMin = new Vector2(48f, 36f); area.offsetMax = new Vector2(-48f, -96f); }
            const float w = 1230f;   // satır genişliği (kutu 1400 − kenar payları)

            // çocuğa kısa not
            var child = T("info.child");
            var ch = TextHeight(child, Th.Font(40), w - 120f) + 60f;
            var crow = Ui.Row(list, "Child", ch);
            Ui.Panel(crow, Theme.Hex("#E7F3FF"), 36f).raycastTarget = false;
            var cl = Ui.Label(crow, child, Th.Font(40), Theme.Hex("#1F3F6E"), new Vector2(0.5f, 0.5f), new Vector2(w - 120f, ch - 40f),
                FontStyle.Bold, TextAnchor.MiddleLeft);
            VoiceButton.Attach(cl.rectTransform);
            Voice.Say(child, true);

            // ebeveynler için
            Ui.Label(Ui.Row(list, "ParentsTitle", 70f), T("info.parents_title"), Th.Font(38), Theme.Hex("#5A3A10"), new Vector2(0.5f, 0.5f),
                new Vector2(w, 64f), FontStyle.Bold, TextAnchor.MiddleLeft);
            var parents = T("info.parents", App.Session != null ? App.Session.DisplayName : "");
            var ph = TextHeight(parents, Th.Font(32), w - 40f) + 20f;
            Ui.Label(Ui.Row(list, "Parents", ph), parents, Th.Font(32), Theme.Hex("#3A2508"), new Vector2(0.5f, 0.5f), new Vector2(w - 40f, ph),
                FontStyle.Normal, TextAnchor.UpperLeft);

            // belgeler (sunucuya bağlı sürümde)
            var linkRow = Ui.Row(list, "Links", 130f);
            if (LegalUrl("gizlilik") == null)
                Ui.Label(linkRow, T("info.no_server"), Th.Font(30), Th.SubtleText, new Vector2(0.5f, 0.5f), new Vector2(w, 110f));
            else
                for (var i = 0; i < LegalDocs.Length; i++)
                {
                    var d = LegalDocs[i];
                    Ui.Button(linkRow, Th, T(d.key), new Vector2((i + 0.5f) / LegalDocs.Length, 0.5f), new Vector2(w / LegalDocs.Length - 20f, 110f),
                        () => OpenLegal(LegalUrl(d.doc)), false, default, 26, false);
                }
            Ui.Label(Ui.Row(list, "Version", 60f), T("info.version", App.BuildLabel), Th.Font(26), Th.SubtleText, new Vector2(0.5f, 0.5f), new Vector2(w, 56f));
        }

        /// <summary>Bağlantı tarayıcıda açılır; önce haber verilir (hukuk/50 §10).</summary>
        private void OpenLegal(string url)
        {
            if (string.IsNullOrEmpty(url)) return;
            RectTransform box;
            var root = Modal(420f, out box, true);
            Ui.Label(box, T("info.open_browser"), Th.Font(40), Th.Text, new Vector2(0.5f, 0.66f), new Vector2(860f, 140f), FontStyle.Bold);
            Ui.Button(box, Th, T("info.cancel"), new Vector2(0.28f, 0.22f), new Vector2(320f, 110f), () => Destroy(root.gameObject), false, default, 34, false);
            Candy.Pill(box, Candy.Green, T("info.open"), new Vector2(0.72f, 0.22f), new Vector2(320f, 110f), Vector2.zero, () =>
            {
                Application.OpenURL(url);
                Destroy(root.gameObject);
            }, null, 40);
        }

        private float TextHeight(string text, int size, float width)
        {
            var probe = Ui.Label(Root, text, size, Color.white, new Vector2(0.5f, 0.5f), new Vector2(width, 10f), FontStyle.Normal, TextAnchor.UpperLeft);
            var h = probe.preferredHeight;
            Destroy(probe.gameObject);
            return Mathf.Ceil(h);
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
