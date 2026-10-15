using System;
using System.Threading;
using System.Threading.Tasks;
using Pofi.Logic.Services;

namespace Pofi.Logic.State
{
    public sealed class RemoteRestoreResult
    {
        /// <summary>Sunucuya ulaşıldı mı? Ulaşılamadıysa senkron (ve yedek yükleme) başlamaz, sonra tekrar denenir.</summary>
        public bool Reached;
        /// <summary>Yerel kayıt yerine kullanılacak sunucu yedeği; yereli korunacaksa null.</summary>
        public GameState Adopt;
    }

    /// <summary>
    /// Telefon değişince ilerleme kaybolmasın (M4): girişten sonra, ilk senkrondan ÖNCE sunucudaki yedeğe bakılır.
    /// Böylece yeni cihazdaki boş kayıt sunucudaki yedeğin üstüne yazılmaz.
    /// </summary>
    public static class SaveRestore
    {
        /// <summary>Sunucu yedeği yerelin yerine geçmeli mi? (yerel bilgiler giriş anındaki haliyle verilir)</summary>
        public static bool PreferRemote(GameState remote, string childId, bool localHasPet, long localSavedUtcTicks)
        {
            if (remote == null || remote.ChildId != childId || !remote.HasPet) return false;
            if (!localHasPet) return true;                                // yeni cihaz / boş kayıt
            return remote.LastSavedUtcTicks > localSavedUtcTicks;          // başka cihazda daha yeni oynanmış
        }

        public static async Task<RemoteRestoreResult> CheckAsync(ISaveService save, string childId, bool localHasPet,
            long localSavedUtcTicks, CancellationToken ct = default)
        {
            string json;
            try { json = await save.LoadRemoteAsync(ct); }
            catch (OperationCanceledException) when (!ct.IsCancellationRequested) { return new RemoteRestoreResult(); }
            var remote = SaveCodec.Deserialize(json);
            return new RemoteRestoreResult
            {
                Reached = true,
                Adopt = PreferRemote(remote, childId, localHasPet, localSavedUtcTicks) ? remote : null,
            };
        }
    }
}
