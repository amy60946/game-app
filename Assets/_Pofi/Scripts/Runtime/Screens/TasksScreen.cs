using System.Linq;
using Pofi.Logic.App;
using Pofi.Logic.State;
using Pofi.Logic.Tasks;
using Pofi.UI;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.Screens
{
    /// <summary>
    /// Görev panosu (FR-TASK-2..5): ebeveynin verdiği gerçek görevler. Çocuk "Yaptım" / "Yapamam" der, ebeveyn onaylar,
    /// coin yalnızca onaydan sonra gelir. Değişiklik önce yerelde görünür, sonra senkronla gönderilir (çevrimdışı kuyruk).
    /// </summary>
    public sealed class TasksScreen : ScreenBase
    {
        private RectTransform _list;
        private Text _coins;

        protected override void Build()
        {
            App.Stage.SetPetVisible(false);
            _coins = Header(T("tasks.title"));
            var listArea = Ui.Area(Root, "ListArea", new Vector2(0f, 0f), new Vector2(1f, 1f));
            listArea.offsetMin = new Vector2(0f, NavHeight + 150f);
            listArea.offsetMax = new Vector2(0f, -180f);
            _list = Ui.ScrollList(listArea, Vector2.zero, Vector2.one, 24f);

            if (App.Backend != null)
            {
                var demo = Ui.Button(Root, Th, T("demo.parent_button"), new Vector2(0.5f, 0f), new Vector2(560f, 100f),
                    () => ParentGate(OpenDemoPanel), false, default, 38);
                ((RectTransform)demo.transform).anchoredPosition = new Vector2(0f, NavHeight + 75f);
            }
            NavBar(AppPage.Tasks);
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
            Ui.Clear(_list);
            var local = App.LocalNow;
            var today = DemoParent.Day(local);
            var tasks = App.State.Tasks.ForDisplay(local).Where(t => t.Date == today).ToList();
            if (tasks.Count == 0)
            {
                var row = Ui.Row(_list, "Empty", 220f);
                Ui.Panel(row, Th.Panel, Th.Radius);
                var t = Ui.Label(row, T("tasks.empty"), Th.Font(40), Th.SubtleText, new Vector2(0.5f, 0.5f), new Vector2(900f, 200f));
                Ui.Stretch(t.rectTransform);
                return;
            }
            foreach (var task in tasks) Card(task, local);
        }

        private void Card(ChildTask task, System.DateTime local)
        {
            var row = Ui.Row(_list, task.Key, 250f);
            var missed = task.IsMissed(local);
            var faded = missed || task.Status == ChildTaskStatus.RejectedByParent || task.Status == ChildTaskStatus.DeclinedByChild;
            Ui.Panel(row, faded ? new Color(1f, 1f, 1f, 0.75f) : Th.Panel, Th.Radius);

            var title = Ui.Label(row, task.Title, Th.Font(46), Th.Text, new Vector2(0f, 1f), new Vector2(640f, 90f), FontStyle.Bold, TextAnchor.MiddleLeft);
            title.rectTransform.pivot = new Vector2(0f, 1f);
            title.rectTransform.anchoredPosition = new Vector2(36f, -22f);

            // ödül
            var pill = Ui.Rect(row, "Reward", new Vector2(1f, 1f), new Vector2(170f, 74f));
            pill.pivot = new Vector2(1f, 1f);
            pill.anchoredPosition = new Vector2(-28f, -26f);
            Ui.Panel(pill, Theme.Hex("#FFD23F"), 37f).raycastTarget = false;
            Ui.Label(pill, T("tasks.coin", task.RewardCoins), Th.Font(40), Theme.Hex("#5A3B00"), new Vector2(0.5f, 0.5f), new Vector2(160f, 70f), FontStyle.Bold);

            string status = null;
            Color statusColor = Th.SubtleText;
            if (missed) status = T("task.missed");
            else
            {
                switch (task.Status)
                {
                    case ChildTaskStatus.Assigned:
                        Btn(row, T("task.done"), true, new Vector2(-28f, 28f), new Vector2(330f, 110f), () => Mark(task, ChildTaskStatus.ChildDone));
                        Btn(row, T("task.decline"), false, new Vector2(-380f, 28f), new Vector2(250f, 110f), () => Mark(task, ChildTaskStatus.DeclinedByChild));
                        break;
                    case ChildTaskStatus.ChildDone:
                        status = T("task.waiting");
                        statusColor = Th.Primary;
                        Btn(row, T("task.undo"), false, new Vector2(-28f, 28f), new Vector2(250f, 100f), () => Mark(task, ChildTaskStatus.Assigned));
                        break;
                    case ChildTaskStatus.DeclinedByChild:
                        status = T("tasks.declined");
                        Btn(row, T("task.undo"), false, new Vector2(-28f, 28f), new Vector2(250f, 100f), () => Mark(task, ChildTaskStatus.Assigned));
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
                st.rectTransform.anchoredPosition = new Vector2(36f, 26f);
            }
        }

        private void Btn(RectTransform row, string text, bool primary, Vector2 offsetFromBottomRight, Vector2 size, System.Action onClick)
        {
            var b = Ui.Button(row, Th, text, new Vector2(1f, 0f), size, onClick, primary, default, 40, false);
            var rt = (RectTransform)b.transform;
            rt.pivot = new Vector2(1f, 0f);
            rt.anchoredPosition = offsetFromBottomRight;
        }

        private void Mark(ChildTask task, ChildTaskStatus to)
        {
            var r = App.State.Tasks.Mark(task.Key, to, App.LocalNow, App.UtcNow);
            if (r != ChangeResult.Ok) { Fill(); return; }
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
            Ui.Button(box, Th, T("demo.approve_all"), new Vector2(0.5f, 0.47f), new Vector2(700f, 120f), async () =>
            {
                DemoParent.ApproveAll(App.Backend);
                Destroy(root.gameObject);
                await App.SyncNow();
            });
            Ui.Button(box, Th, T("demo.new_tasks"), new Vector2(0.5f, 0.3f), new Vector2(700f, 110f), async () =>
            {
                DemoParent.EnsureToday(App.Backend, App.LocalNow);
                Destroy(root.gameObject);
                await App.SyncNow();
            }, false, default, 40);
            Ui.Button(box, Th, T("demo.close"), new Vector2(0.5f, 0.11f), new Vector2(400f, 100f), () => Destroy(root.gameObject), false, default, 40);
            pending.name = "Pending";
        }

        private void OnDestroy()
        {
            if (App != null) App.Synced -= OnSynced;
        }
    }
}
