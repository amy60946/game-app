using System;
using System.Collections.Generic;

namespace Pofi.Logic.Core
{
    /// <summary>
    /// Sistemler arası tipli olay yolu. Sistemler birbirini doğrudan çağırmaz;
    /// olay yayınlar ve dinler (ör. TaskApproved → EconomySystem → CoinsChanged → UI).
    /// </summary>
    public sealed class EventBus
    {
        private readonly Dictionary<Type, List<Delegate>> _handlers = new Dictionary<Type, List<Delegate>>();

        public IDisposable Subscribe<T>(Action<T> handler)
        {
            if (handler == null) throw new ArgumentNullException(nameof(handler));
            if (!_handlers.TryGetValue(typeof(T), out var list))
            {
                list = new List<Delegate>();
                _handlers[typeof(T)] = list;
            }
            list.Add(handler);
            return new Subscription(() => list.Remove(handler));
        }

        public void Publish<T>(T evt)
        {
            if (!_handlers.TryGetValue(typeof(T), out var list)) return;
            // Dinleyici yayın sırasında abonelikten çıkabilir; kopya üzerinde dolaş.
            foreach (var h in list.ToArray()) ((Action<T>)h)(evt);
        }

        public int HandlerCount<T>() => _handlers.TryGetValue(typeof(T), out var list) ? list.Count : 0;

        private sealed class Subscription : IDisposable
        {
            private Action _dispose;
            public Subscription(Action dispose) { _dispose = dispose; }
            public void Dispose() { _dispose?.Invoke(); _dispose = null; }
        }
    }
}
