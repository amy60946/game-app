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
    }
}
