using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json.Linq;

namespace Pofi.Logic.Mail
{
    /// <summary>
    /// Ebeveynin Güneş Taşı ile gönderdiği oyun içi hediye (ParentApp, 27 Ekim 2026; ortak 20261027140000_parent_tasks_gifts,
    /// akislar.md 17). Posta kutusunda paket olarak bekler; çocuk açınca eşya envantere girer.
    /// </summary>
    public sealed class ParentGift
    {
        public string Id;
        public string ItemId;
        public string FromName;
        public string Note;
        public DateTime CreatedAt;
    }

    public interface IGiftService
    {
        /// <summary>Kapatılmamış hediyeler (eskiden yeniye). null: ağ yok ya da sunucuda işlev henüz yok (oyun hediyesiz sürer).</summary>
        Task<List<ParentGift>> PendingGiftsAsync(CancellationToken ct = default);

        /// <summary>Hediyeyi sunucuda kapatır: true ilk kez, false zaten kapalı, null ağ/işlev yok (sonraki eşitlemede yeniden).</summary>
        Task<bool?> ClaimGiftAsync(string id, CancellationToken ct = default);
    }

    /// <summary>Cihazdaki hediye kaydı (kayıt yedeğine de gider): aynı hediye iki kez girmez, haberi bir kez verilir.</summary>
    [Serializable]
    public sealed class GiftState
    {
        public List<string> Opened = new List<string>();   // açılan hediye kimlikleri (eşya envantere girdi)
        public List<string> Told = new List<string>();     // haberi verilmiş hediye kimlikleri
        public List<string> Items = new List<string>();    // hediye gelen eşyalar (seviye kilidi yok; kullanıcı kararı 27 Ekim 2026)
    }

    public static class GiftBook
    {
        /// <summary>child_gifts_pending yanıtı: [{id, item_id, from_name, note, created_at}]. Bozuk satır atlanır.</summary>
        public static List<ParentGift> Parse(string json)
        {
            var list = new List<ParentGift>();
            JArray arr;
            try { arr = JArray.Parse(string.IsNullOrWhiteSpace(json) ? "[]" : json); }
            catch (Newtonsoft.Json.JsonException) { return list; }
            foreach (var t in arr)
            {
                if (!(t is JObject o)) continue;
                var id = (string)o["id"];
                var item = (string)o["item_id"];
                if (string.IsNullOrEmpty(id) || string.IsNullOrEmpty(item)) continue;
                list.Add(new ParentGift
                {
                    Id = id, ItemId = item, FromName = ((string)o["from_name"] ?? "").Trim(), Note = ((string)o["note"])?.Trim(),
                    CreatedAt = o["created_at"]?.Type == JTokenType.Date ? ((DateTime)o["created_at"]).ToUniversalTime()
                        : DateTime.TryParse((string)o["created_at"], System.Globalization.CultureInfo.InvariantCulture,
                            System.Globalization.DateTimeStyles.AdjustToUniversal | System.Globalization.DateTimeStyles.AssumeUniversal, out var at) ? at : DateTime.MinValue,
                });
            }
            return list;
        }

        /// <summary>Kutuda açılmayı bekleyenler: henüz açılmamış ve bu sürümün tanıdığı eşyalar (yeni eşya sonraki sürümde gelir).</summary>
        public static List<ParentGift> Unopened(GiftState s, IEnumerable<ParentGift> pending, Func<string, bool> known) =>
            (pending ?? Enumerable.Empty<ParentGift>()).Where(g => g != null && !s.Opened.Contains(g.Id) && known(g.ItemId)).ToList();

        /// <summary>Haberi verilmemiş hediyeler (bir kez): sayısı döner, işaretlenir.</summary>
        public static List<ParentGift> Tell(GiftState s, IEnumerable<ParentGift> unopened)
        {
            var fresh = (unopened ?? Enumerable.Empty<ParentGift>()).Where(g => !s.Told.Contains(g.Id)).ToList();
            foreach (var g in fresh) s.Told.Add(g.Id);
            return fresh;
        }

        /// <summary>Açılmış ama sunucuda hâlâ açık görünenler (kapatma gitmedi): yeniden kapatılır, eşya ikinci kez eklenmez.</summary>
        public static List<ParentGift> NeedsClaim(GiftState s, IEnumerable<ParentGift> pending) =>
            (pending ?? Enumerable.Empty<ParentGift>()).Where(g => g != null && s.Opened.Contains(g.Id)).ToList();

        /// <summary>
        /// Paketi aç: eşya envantere girer (seviye kilidi aşılır: sahip olunan eşya giyilir/yerleştirilir), kimlik kaydedilir.
        /// false: zaten açılmış ya da eşya bu sürümde yok.
        /// </summary>
        public static bool Open(State.GameState st, Data.GameData data, ParentGift g)
        {
            if (st == null || g == null || st.Gifts.Opened.Contains(g.Id)) return false;
            var item = data?.Item(g.ItemId);
            if (item == null) return false;
            st.Inventory.Add(item);
            st.Gifts.Opened.Add(g.Id);
            if (!st.Gifts.Items.Contains(item.Id)) st.Gifts.Items.Add(item.Id);
            return true;
        }

        /// <summary>Hediye gelmiş yerleştirilebilir eşya var mı (ev süsleme, seviyesi gelmeden de açılır).</summary>
        public static bool HasPlaceable(GiftState s, Data.GameData data) =>
            s != null && data != null && s.Items.Any(id => data.Item(id)?.IsPlaceable == true);
    }
}
