using System.Linq;
using Pofi.Logic.App;
using Pofi.Logic.Island;
using Pofi.Logic.State;
using Pofi.Logic.Tasks;
using Pofi.UI;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.Screens
{
    /// <summary>
    /// Ev Görevleri panosu (FR-TASK-2..5): ebeveynin verdiği gerçek görevler. Çocuk "Yaptım" / "Yapamam" der, ebeveyn onaylar,
    /// coin yalnızca onaydan sonra gelir. Değişiklik önce yerelde görünür, sonra senkronla gönderilir (çevrimdışı kuyruk).
    /// Üstte Güneş Taşı şeridi (Ö1): onayla gelen taş buradan adadaki sıradaki onarım noktasına yerleştirilir.
    /// </summary>
    public sealed class TasksScreen : ScreenBase
    {
        private RectTransform _list;
        private Text _coins;
        private Coach _coach;
        private RectTransform _firstDone;   // ilk "Yaptım" düğmesi (ilk gün ipucu)

        protected override void Build()
        {
            App.Stage.SetPetVisible(false);
            _coins = Header(T("tasks.title"));
            var listArea = CenterColumn("ListArea", 1200f);
            _list = Ui.ScrollList(listArea, Vector2.zero, Vector2.one, 20f);

            if (App.Backend != null) CornerButton(T("demo.parent_button"), () => ParentGate(OpenDemoPanel));
            NavBar(AppPage.Tasks);
            if (Onboarding.Pending(App.State, Onboarding.Board)) { Onboarding.Done(App.State, Onboarding.Board); App.Save(); }
            App.RecordActivity("board_opened");
            App.Synced += OnSynced;
            Fill();
            _ = App.SyncNow();
        }

        private void OnSynced(SyncReport r)
        {
            if (this == null) return;
            Fill();
        }

        private void Fill()
        {
            _coins.text = App.State.Wallet.Available.ToString();
            if (_coach != null) { _coach.Done(); _coach = null; }
            _firstDone = null;
            Ui.Clear(_list);
            StonesRow();
            var local = App.LocalNow;
            var today = DemoParent.Day(local);
            var tasks = App.State.Tasks.ForDisplay(local).Where(t => t.Date == today).ToList();
            if (tasks.Any(t => t.Status == ChildTaskStatus.ChildDone)) InfoRow("Pigeon", T("task.waiting_pigeon"));
            if (tasks.Count == 0)
            {
                var row = Ui.Row(_list, "Empty", 220f);
                Ui.Panel(row, Th.Panel, Th.Radius);
                var t = Ui.Label(row, T("tasks.empty"), Th.Font(40), Th.SubtleText, new Vector2(0.5f, 0.5f), new Vector2(900f, 200f));
                Ui.Stretch(t.rectTransform);
                return;
            }
            foreach (var task in tasks) Card(task, local);
            var day = FirstDay.Current(App.State, local, App.UtcNow);
            if (_coach == null && _firstDone != null && day == FirstDayStep.Mark && Onboarding.Pending(App.State, Onboarding.Mark))
            {
                var b = _firstDone;
                _coach = Coach.Show(Root, Onboarding.Mark, T("tip.mark"), TipGesture.Tap, () => RectTransformUtility.WorldToScreenPoint(null, b.position));
            }
        }

        // ---- Güneş Taşı (Ö1) ----
        private void StonesRow()
        {
            var st = App.State.SunStones;
            var book = App.Data.SunBook;
            var have = SunStoneBook.Available(st);
            var next = book.Next(st);
            var row = Ui.Row(_list, "SunStones", 230f);
            Ui.Panel(row, Theme.Hex("#FFF4C9"), Th.Radius);
            var title = Ui.Label(row, T("stones.title") + ": " + have, Th.Font(46), Theme.Hex("#8A5A00"), new Vector2(0f, 1f), new Vector2(700f, 80f), FontStyle.Bold, TextAnchor.MiddleLeft);
            title.rectTransform.pivot = new Vector2(0f, 1f);
            title.rectTransform.anchoredPosition = new Vector2(36f, -18f);

            var info = next == null ? T("stones.all_done")
                : have == 0 && SunStoneBook.PlacedIn(st, next.Id) == 0 ? T("stones.none")
                : T("stones.next", next.Name, SunStoneBook.PlacedIn(st, next.Id), next.Cost);
            var stars = string.Join(", ", RealTaskRewards.Ranked(App.State.Skills).Take(3).Select(kv => SkillCatalog.Label(kv.Key) + " " + kv.Value));
            if (stars.Length > 0) info += "\n" + T("skill.summary", stars);
            var sub = Ui.Label(row, info, Th.Font(32), Th.SubtleText, new Vector2(0f, 0f), new Vector2(780f, 120f), FontStyle.Normal, TextAnchor.MiddleLeft);
            sub.rectTransform.pivot = new Vector2(0f, 0f);
            sub.rectTransform.anchoredPosition = new Vector2(36f, 16f);

            if (next == null || have <= 0) return;
            // yerleştirme adada (kullanıcı, 20 Ekim 2026): çocuk taşı sisli yere (köprü, mağara yolu, fener…) götürür
            var place = Btn(row, T("stones.go"), true, new Vector2(-28f, 60f), new Vector2(320f, 110f), () => App.Open(AppPage.Map));
            if (Onboarding.Pending(App.State, Onboarding.Stone))
                _coach = Coach.Show(Root, Onboarding.Stone, T("tip.stone_go", next.Name), TipGesture.Tap, () => RectTransformUtility.WorldToScreenPoint(null, place.position));
        }

        private void InfoRow(string name, string text)
        {
            var row = Ui.Row(_list, name, 150f);
            Ui.Panel(row, new Color(1f, 1f, 1f, 0.85f), Th.Radius);
            var t = Ui.Label(row, text, Th.Font(34), Th.Primary, new Vector2(0.5f, 0.5f), new Vector2(1100f, 140f), FontStyle.Bold);
            Ui.Stretch(t.rectTransform);
        }

        private void Card(ChildTask task, System.DateTime local)
        {
            var row = Ui.Row(_list, task.Key, 240f);
            var missed = task.IsMissed(local);
            var faded = missed || task.Status == ChildTaskStatus.RejectedByParent || task.Status == ChildTaskStatus.DeclinedByChild;
            Ui.Panel(row, faded ? new Color(1f, 1f, 1f, 0.75f) : Th.Panel, Th.Radius);

            var title = Ui.Label(row, task.Title, Th.Font(46), Th.Text, new Vector2(0f, 1f), new Vector2(640f, 90f), FontStyle.Bold, TextAnchor.MiddleLeft);
            title.rectTransform.pivot = new Vector2(0f, 1f);
            title.rectTransform.anchoredPosition = new Vector2(36f, -22f);

            // ödül
            // ödül: coin simgesi + miktar (yazı yok)
            var pill = Ui.Rect(row, "Reward", new Vector2(1f, 1f), new Vector2(190f, 80f));
            pill.pivot = new Vector2(1f, 1f);
            pill.anchoredPosition = new Vector2(-28f, -20f);
            Ui.Panel(pill, Theme.Hex("#FFD23F"), 40f).raycastTarget = false;
            Ui.IconImage(pill, "ui_coin", new Vector2(0f, 0.5f), 70f, new Vector2(42f, 0f));
            Ui.Label(pill, T("tasks.coin", task.RewardCoins), Th.Font(44), Theme.Hex("#5A3B00"), new Vector2(0.62f, 0.5f), new Vector2(110f, 74f), FontStyle.Bold);

            string status = null;
            Color statusColor = Th.SubtleText;
            if (missed) status = T("task.missed");
            else
            {
                switch (task.Status)
                {
                    case ChildTaskStatus.Assigned:
                        var done = Btn(row, T("task.done"), true, new Vector2(-28f, 22f), new Vector2(330f, 100f), () => Mark(task, ChildTaskStatus.ChildDone));
                        if (_firstDone == null) _firstDone = done;
                        Btn(row, T("task.decline"), false, new Vector2(-380f, 22f), new Vector2(250f, 100f), () => Mark(task, ChildTaskStatus.DeclinedByChild));
                        break;
                    case ChildTaskStatus.ChildDone:
                        status = T("task.waiting");
                        statusColor = Th.Primary;
                        Btn(row, T("task.undo"), false, new Vector2(-28f, 22f), new Vector2(250f, 100f), () => Mark(task, ChildTaskStatus.Assigned));
                        break;
                    case ChildTaskStatus.DeclinedByChild:
                        status = T("tasks.declined");
                        Btn(row, T("task.undo"), false, new Vector2(-28f, 22f), new Vector2(250f, 100f), () => Mark(task, ChildTaskStatus.Assigned));
                        break;
                    case ChildTaskStatus.Approved:
                        status = T("task.approved", task.RewardCoins);
                        statusColor = Theme.Hex("#2E9E4F");
                        break;
                    case ChildTaskStatus.RejectedByParent:
                        status = T("task.rejected", task.ParentNote ?? "");
                        statusColor = Th.Danger;
                        break;
                }
            }
            if (status != null)
            {
                var st = Ui.Label(row, status, Th.Font(36), statusColor, new Vector2(0f, 0f), new Vector2(620f, 100f), FontStyle.Bold, TextAnchor.MiddleLeft);
                st.rectTransform.pivot = new Vector2(0f, 0f);
                var withCoin = task.Status == ChildTaskStatus.Approved;
                st.rectTransform.anchoredPosition = new Vector2(withCoin ? 100f : 36f, 26f);
                if (withCoin) Ui.IconImage(row, "ui_coin", new Vector2(0f, 0f), 64f, new Vector2(64f, 76f));
            }
        }

        private RectTransform Btn(RectTransform row, string text, bool primary, Vector2 offsetFromBottomRight, Vector2 size, System.Action onClick)
        {
            var b = Ui.Button(row, Th, text, new Vector2(1f, 0f), size, onClick, primary, default, 40, false);
            var rt = (RectTransform)b.transform;
            rt.pivot = new Vector2(1f, 0f);
            rt.anchoredPosition = offsetFromBottomRight;
            return rt;
        }

        private void Mark(ChildTask task, ChildTaskStatus to)
        {
            var r = App.State.Tasks.Mark(task.Key, to, App.LocalNow, App.UtcNow);
            if (r != ChangeResult.Ok) { Fill(); return; }
            if (to == ChildTaskStatus.ChildDone && Onboarding.Pending(App.State, Onboarding.Mark)) Onboarding.Done(App.State, Onboarding.Mark);
            App.Save();
            Fill();
            _ = App.SyncNow();
        }

        // ---- deneme ebeveyn paneli (yalnızca sahte sunucu) ----
        private void OpenDemoPanel()
        {
            var root = Modal(820f, out var box);
            Ui.Label(box, T("demo.title"), Th.Font(54), Th.Text, new Vector2(0.5f, 0.9f), new Vector2(880f, 80f), FontStyle.Bold);
            Ui.Label(box, T("demo.info"), Th.Font(32), Th.SubtleText, new Vector2(0.5f, 0.79f), new Vector2(860f, 110f));
            var pending = Ui.Label(box, T("demo.pending", DemoParent.Pending(App.Backend)), Th.Font(44), Th.Text, new Vector2(0.5f, 0.64f), new Vector2(860f, 70f), FontStyle.Bold);
            Ui.Button(box, Th, T("demo.approve_all"), new Vector2(0.5f, 0.5f), new Vector2(700f, 120f), async () =>
            {
                DemoParent.ApproveAll(App.Backend);
                Destroy(root.gameObject);
                await App.SyncNow();
            });
            Ui.Button(box, Th, T("demo.new_tasks"), new Vector2(0.5f, 0.355f), new Vector2(700f, 100f), async () =>
            {
                DemoParent.EnsureToday(App.Backend, App.LocalNow);
                Destroy(root.gameObject);
                await App.SyncNow();
            }, false, default, 40);
            Ui.Button(box, Th, T("demo.give_rewards"), new Vector2(0.5f, 0.225f), new Vector2(700f, 100f), async () =>
            {
                DemoParent.GiveRewards(App.Backend);
                Destroy(root.gameObject);
                await App.SyncNow();
            }, false, default, 40);
            Ui.Button(box, Th, T("demo.close"), new Vector2(0.5f, 0.09f), new Vector2(400f, 100f), () => Destroy(root.gameObject), false, default, 40);
            pending.name = "Pending";
        }

        private void OnDestroy()
        {
            if (App != null) App.Synced -= OnSynced;
        }
    }
}
