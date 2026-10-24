using System.Linq;
using NUnit.Framework;
using Pofi.Logic.App;
using Pofi.Logic.State;

namespace Pofi.Tests.Logic
{
    public class OnboardingTests
    {
        [Test]
        public void Ipucu_bir_kez_tamamlanir()
        {
            var s = new GameState();
            Assert.IsTrue(Onboarding.Pending(s, Onboarding.Feed));
            Onboarding.Done(s, Onboarding.Feed);
            Assert.IsFalse(Onboarding.Pending(s, Onboarding.Feed));
            Assert.IsTrue(Onboarding.Pending(s, Onboarding.Wash));
        }

        [Test]
        public void Her_ipucunun_altyazisi_var_ve_kimlikler_benzersiz()
        {
            var tr = TestData.ReadText("tr.json");
            foreach (var t in Onboarding.All) StringAssert.Contains("\"" + t.CaptionKey + "\"", tr, t.Id);
            Assert.AreEqual(Onboarding.All.Count, Onboarding.All.Select(t => t.Id).Distinct().Count());
            Assert.GreaterOrEqual(Onboarding.All.Count, 12);
        }

        [Test]
        public void Gorevler_penceresi_tanitimi_tanimli_ve_ilk_gunde_acik()
        {
            Assert.AreEqual(new[] { Onboarding.TasksHome, Onboarding.TasksDone, Onboarding.TasksGame }, Onboarding.TasksIntro.ToArray());
            foreach (var id in Onboarding.TasksIntro)
            {
                var t = Onboarding.Get(id);
                Assert.IsNotNull(t, id);
                Assert.AreEqual("tasks", t.Where, id);
                Assert.AreEqual(TipGesture.Tap, t.Gesture, id);
                Assert.IsTrue(FirstDay.AllowsTip(FirstDayStep.Mark, id), id);
            }
            var s = new GameState();
            Onboarding.Done(s, Onboarding.TasksDone);
            Assert.IsTrue(Onboarding.Pending(s, Onboarding.Mark), "pencere ipucu ilk gün Yaptım ipucunu tamamlamaz");
        }
    }
}
