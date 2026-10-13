using System;
using System.Collections.Generic;
using System.Linq;

namespace Pofi.Logic.Economy
{
    [Serializable]
    public sealed class PendingSpend
    {
        public string TxId;       // istemci üretir; sunucu aynı TxId'yi bir kez işler (çevrimdışı tekrar güvenli)
        public string ItemId;
        public int Quantity;
        public int Amount;        // toplam coin
        public long CreatedUtcTicks;
    }

    public enum SpendResult { Ok, NotEnoughCoins, InvalidAmount }

    /// <summary>
    /// Coin cüzdanı (FR-ECO-1, FR-ECO-3). Bakiye her zaman SUNUCUNUN bakiyesidir; istemci coin ekleyemez.
    /// Harcama önce yerelde "bekleyen" olarak düşülür, sunucu onaylayınca kesinleşir. Çakışmada sunucu kazanır.
    /// </summary>
    [Serializable]
    public sealed class Wallet
    {
        public int ServerCoins;
        public List<PendingSpend> Pending = new List<PendingSpend>();

        public int PendingTotal => Pending.Sum(p => p.Amount);

        /// <summary>Arayüzde gösterilen harcanabilir bakiye.</summary>
        public int Available => Math.Max(0, ServerCoins - PendingTotal);

        public SpendResult TrySpend(string itemId, int quantity, int unitPrice, string txId, DateTime nowUtc, out PendingSpend spend)
        {
            spend = null;
            if (quantity <= 0 || unitPrice <= 0 || string.IsNullOrEmpty(txId)) return SpendResult.InvalidAmount;
            var amount = checked(quantity * unitPrice);
            if (amount > Available) return SpendResult.NotEnoughCoins;
            spend = new PendingSpend { TxId = txId, ItemId = itemId, Quantity = quantity, Amount = amount, CreatedUtcTicks = nowUtc.Ticks };
            Pending.Add(spend);
            return SpendResult.Ok;
        }

        /// <summary>Sunucu harcamayı işledi: bekleyen silinir, sunucu bakiyesi alınır.</summary>
        public void Acknowledge(string txId, int serverBalance)
        {
            Pending.RemoveAll(p => p.TxId == txId);
            ServerCoins = Math.Max(0, serverBalance);
        }

        /// <summary>Sunucu reddetti (ör. bakiye yetmedi). Çağıran, envantere eklenen eşyayı geri almalı.</summary>
        public PendingSpend Reject(string txId, int serverBalance)
        {
            var p = Pending.FirstOrDefault(x => x.TxId == txId);
            Pending.RemoveAll(x => x.TxId == txId);
            ServerCoins = Math.Max(0, serverBalance);
            return p;
        }

        /// <summary>
        /// Senkron: sunucu bakiyesi esastır. Sunucunun zaten işlediği harcamalar bekleyenlerden düşülür.
        /// Coin artışı YALNIZCA bu yolla (ebeveyn onayı sunucuda) gelir.
        /// </summary>
        /// <returns>Sunucu tarafında kazanılan net coin (kutlama için; harcamalar hariç).</returns>
        public int ApplyServerSnapshot(int serverBalance, ICollection<string> processedTxIds)
        {
            var processed = Pending.Where(p => processedTxIds != null && processedTxIds.Contains(p.TxId)).ToList();
            var spentMeanwhile = processed.Sum(p => p.Amount);
            Pending.RemoveAll(p => processed.Contains(p));
            var earned = serverBalance - (ServerCoins - spentMeanwhile);
            ServerCoins = Math.Max(0, serverBalance);
            return Math.Max(0, earned);
        }
    }
}
