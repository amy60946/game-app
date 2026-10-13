using NUnit.Framework;
using Pofi.Logic.Core;

namespace Pofi.Tests.Logic
{
    // Bu klasördeki testler Unity'ye bağlı değildir: hem Unity Test Runner'da
    // hem de `dotnet test tests-dotnet` ile çalışır.
    public class EventBusTests
    {
        private struct CoinsChanged { public int Coins; }

        [Test]
        public void Publish_reaches_subscriber()
        {
            var bus = new EventBus();
            var got = -1;
            bus.Subscribe<CoinsChanged>(e => got = e.Coins);
            bus.Publish(new CoinsChanged { Coins = 42 });
            Assert.AreEqual(42, got);
        }

        [Test]
        public void Dispose_unsubscribes()
        {
            var bus = new EventBus();
            var calls = 0;
            var sub = bus.Subscribe<CoinsChanged>(_ => calls++);
            sub.Dispose();
            bus.Publish(new CoinsChanged());
            Assert.AreEqual(0, calls);
            Assert.AreEqual(0, bus.HandlerCount<CoinsChanged>());
        }

        [Test]
        public void Handler_may_unsubscribe_during_publish()
        {
            var bus = new EventBus();
            var calls = 0;
            System.IDisposable sub = null;
            sub = bus.Subscribe<CoinsChanged>(_ => { calls++; sub.Dispose(); });
            bus.Subscribe<CoinsChanged>(_ => calls++);
            bus.Publish(new CoinsChanged());
            bus.Publish(new CoinsChanged());
            Assert.AreEqual(3, calls);
        }

        [Test]
        public void Version_display_includes_build()
        {
            StringAssert.Contains("derleme 7", GameVersion.Display("7"));
            StringAssert.StartsWith("v" + GameVersion.Short, GameVersion.Display(null));
        }
    }
}
