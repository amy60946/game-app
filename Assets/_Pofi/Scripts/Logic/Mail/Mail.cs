using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json.Linq;
using Pofi.Logic.Profile;
using Pofi.Logic.Services;

namespace Pofi.Logic.Mail
{
    // Posta kutusu (H2 / Ö6, 23 Ekim 2026): ParentApp mesajları oyunda Evim'in önündeki kutudan okunur.
    // Sözleşme: ortak/sozlesme/akislar.md P10, durumlar.md P13 (migrations/20261022120000_messages.sql).

    public sealed class MailMessage
    {
        public string Id;
        public string Sender;        // parent | child
        public string Kind;          // text | sticker | image | audio
        public string Body;
        public string MediaPath;     // image/audio: "mail" kovasında
        public int DurationMs;
        public DateTime CreatedAt;
        public DateTime? ReadAt;
        public string FromName;      // ebeveynin takma adı (ör. Annem)

        public bool FromParent => Sender == "parent";
        public bool Unread => FromParent && ReadAt == null;
    }

    public sealed class MailSend
    {
        public bool Ok;
        public string Error;         // offline | too_long | empty | not_allowed | server
        public string Id;
    }

    public interface IMailService
    {
        Task<List<MailMessage>> MessagesAsync(int limit = 100, CancellationToken ct = default);
        Task<int> MarkReadAsync(CancellationToken ct = default);
        Task<MailSend> SendAsync(string kind, string body, CancellationToken ct = default);
        /// <summary>Fotoğraf/ses için kısa ömürlü imzalı adres (yoksa null).</summary>
        Task<string> MediaUrlAsync(string mediaPath, CancellationToken ct = default);
    }

    public static class MailBox
    {
        public const int ChildTextMax = 500;
        public const string Text = "text", Sticker = "sticker", Image = "image", Audio = "audio";

        /// <summary>Çıkartma anahtarları ve Türkçe etiketleri (durumlar.md P13; görseli her uygulama kendi çizer).</summary>
        public static readonly (string Key, string Label)[] Stickers =
        {
            ("heart", "Kalp"), ("star", "Yıldız"), ("thumbs_up", "Harika"), ("hug", "Sarılma"), ("smile", "Gülümseme"), ("laugh", "Kahkaha"),
            ("wow", "Vay"), ("sad", "Üzgün"), ("sleepy", "Uykulu"), ("party", "Kutlama"), ("thanks", "Teşekkürler"), ("love_you", "Seni seviyorum"),
        };

        public static string StickerLabel(string key) => Stickers.FirstOrDefault(s => s.Key == key).Label ?? key;
        public static bool IsSticker(string key) => Stickers.Any(s => s.Key == key);

        /// <summary>Yazıyla yanıt yalnız 9 yaş ve üstü (B, C); küçükler çıkartmayla yanıtlar (okuma-yazma yükü yok).</summary>
        public static bool CanWrite(AgeBand band) => band == AgeBand.B || band == AgeBand.C;

        public static int UnreadCount(IEnumerable<MailMessage> all) => all?.Count(m => m.Unread) ?? 0;

        /// <summary>Göndermeden önce yerel denetim (sunucu da aynısını denetler).</summary>
        public static string Check(string kind, string body, AgeBand band)
        {
            if (kind == Sticker) return IsSticker(body) ? null : "not_allowed";
            if (kind != Text || !CanWrite(band)) return "not_allowed";
            var t = (body ?? "").Trim();
            if (t.Length == 0) return "empty";
            return t.Length > ChildTextMax ? "too_long" : null;
        }

        /// <summary>child_messages yanıtı (eskiden yeniye dizi; boşsa null).</summary>
        public static List<MailMessage> Parse(string json)
        {
            var list = new List<MailMessage>();
            if (string.IsNullOrWhiteSpace(json) || json.Trim() == "null") return list;
            JArray a;
            try { a = JArray.Parse(json); }
            catch (Newtonsoft.Json.JsonException) { return list; }
            foreach (var o in a.OfType<JObject>())
            {
                list.Add(new MailMessage
                {
                    Id = (string)o["id"], Sender = (string)o["sender"], Kind = (string)o["kind"] ?? Text, Body = (string)o["body"],
                    MediaPath = (string)o["media_path"], DurationMs = (int?)o["duration_ms"] ?? 0,
                    CreatedAt = (DateTime?)o["created_at"] ?? DateTime.MinValue, ReadAt = (DateTime?)o["read_at"], FromName = (string)o["from_name"],
                });
            }
            return list.OrderBy(m => m.CreatedAt).ToList();
        }
    }
}
