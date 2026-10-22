using System.Linq;
using NUnit.Framework;
using Pofi.Logic.Mail;
using Pofi.Logic.Profile;
using Pofi.Logic.Services.Mock;

namespace Pofi.Tests.Logic
{
    public class MailTests
    {
        [Test]
        public void Sunucu_yaniti_okunur_eskiden_yeniye()
        {
            const string json = "[{\"id\":\"b\",\"sender\":\"child\",\"kind\":\"sticker\",\"body\":\"heart\",\"created_at\":\"2026-10-23T10:05:00Z\",\"read_at\":null}," +
                                "{\"id\":\"a\",\"sender\":\"parent\",\"kind\":\"text\",\"body\":\"Aferin!\",\"created_at\":\"2026-10-23T10:00:00Z\",\"read_at\":null,\"from_name\":\"Annem\"}," +
                                "{\"id\":\"c\",\"sender\":\"parent\",\"kind\":\"audio\",\"media_path\":\"f1/x.m4a\",\"duration_ms\":4200,\"created_at\":\"2026-10-23T11:00:00Z\",\"read_at\":\"2026-10-23T11:01:00Z\"}]";
            var list = MailBox.Parse(json);
            CollectionAssert.AreEqual(new[] { "a", "b", "c" }, list.Select(m => m.Id));
            Assert.AreEqual("Annem", list[0].FromName);
            Assert.AreEqual(1, MailBox.UnreadCount(list), "çocuğun kendi mesajı ve okunmuş ses sayılmaz");
            Assert.AreEqual(4200, list[2].DurationMs);
            Assert.IsEmpty(MailBox.Parse("null"));
            Assert.IsEmpty(MailBox.Parse("bozuk"));
        }

        [Test]
        public void Kucukler_cikartmayla_buyukler_yaziyla_yanitlar()
        {
            Assert.IsNull(MailBox.Check(MailBox.Sticker, "heart", AgeBand.K));
            Assert.AreEqual("not_allowed", MailBox.Check(MailBox.Sticker, "dragon", AgeBand.B));
            Assert.AreEqual("not_allowed", MailBox.Check(MailBox.Text, "selam", AgeBand.A));
            Assert.IsNull(MailBox.Check(MailBox.Text, "selam", AgeBand.B));
            Assert.AreEqual("empty", MailBox.Check(MailBox.Text, "   ", AgeBand.C));
            Assert.AreEqual("too_long", MailBox.Check(MailBox.Text, new string('a', 501), AgeBand.C));
            Assert.AreEqual(12, MailBox.Stickers.Length);
            Assert.AreEqual("Seni seviyorum", MailBox.StickerLabel("love_you"));
        }

        [Test]
        public void Sahte_sunucuda_okundu_ve_yanit()
        {
            var b = new MockBackend(TestData.Load());
            b.ParentMessage(MailBox.Text, "Odanı topladığın için teşekkürler!");
            Assert.AreEqual(1, MailBox.UnreadCount(b.MessagesAsync().Result));
            Assert.AreEqual(1, b.MarkReadAsync().Result);
            Assert.AreEqual(0, MailBox.UnreadCount(b.MessagesAsync().Result));
            Assert.IsTrue(b.SendAsync(MailBox.Sticker, "hug").Result.Ok);
            Assert.IsFalse(b.SendAsync(MailBox.Image, "x").Result.Ok, "çocuk dosya gönderemez");
            Assert.AreEqual(2, b.MessagesAsync().Result.Count);
        }
    }
}
