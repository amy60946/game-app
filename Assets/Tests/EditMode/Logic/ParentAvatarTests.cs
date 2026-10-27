using System.IO;
using NUnit.Framework;
using Pofi.Logic.Mail;

namespace Pofi.Tests.Logic
{
    public class ParentAvatarTests
    {
        [Test]
        public void Kimlikler_eski_degerler_ve_varsayilan()
        {
            Assert.AreEqual("okti_anne_2", ParentAvatar.Resolve("okti_anne_2"));
            Assert.AreEqual("okti_baba_3", ParentAvatar.Resolve(" OKTI_BABA_3 "));
            Assert.AreEqual("okti_anne_1", ParentAvatar.Resolve("kadın"), "eski değer (durumlar.md §6a)");
            Assert.AreEqual("okti_baba_1", ParentAvatar.Resolve("erkek"), "profiles.avatar varsayılanı");
            Assert.AreEqual(ParentAvatar.Default, ParentAvatar.Resolve(null), "eski sunucu: alan yok");
            Assert.AreEqual(ParentAvatar.Default, ParentAvatar.Resolve("photo:fam/avatars/a.jpg"), "oyun fotoğraf göstermez");
            Assert.AreEqual(ParentAvatar.Default, ParentAvatar.Resolve("flamingo"));
        }

        [Test]
        public void Posta_ve_hediye_yanitinda_from_avatar_okunur()
        {
            var mail = MailBox.Parse(@"[{""id"":""m1"",""sender"":""parent"",""kind"":""text"",""body"":""Selam"",""created_at"":""2026-10-27T10:00:00Z"",
                                        ""from_name"":""Annem"",""from_avatar"":""okti_anne_3""},
                                       {""id"":""m2"",""sender"":""child"",""kind"":""text"",""body"":""Merhaba"",""created_at"":""2026-10-27T10:01:00Z""}]");
            Assert.AreEqual("okti_anne_3", mail[0].FromAvatar);
            Assert.IsNull(mail[1].FromAvatar);
            var gifts = GiftBook.Parse(@"[{""id"":""g1"",""item_id"":""hat_cap"",""from_name"":""Babam"",""from_avatar"":""okti_baba_2""},
                                         {""id"":""g2"",""item_id"":""hat_cap"",""from_name"":""Babam""}]");
            Assert.AreEqual("okti_baba_2", gifts[0].FromAvatar);
            Assert.AreEqual(ParentAvatar.Default, ParentAvatar.Resolve(gifts[1].FromAvatar), "öneri uygulanmadan: varsayılan yüz");
        }

        [Test]
        public void Her_kimligin_gorseli_var()
        {
            var dir = Path.Combine(TestContext.CurrentContext.TestDirectory, "..", "..", "..", "..", "Assets", "_Pofi", "Resources", "UI", "Avatars");
            if (!Directory.Exists(dir)) Assert.Ignore("Avatars klasörü bu çalıştırmada bulunamadı");
            foreach (var id in ParentAvatar.Ids)
                Assert.IsTrue(File.Exists(Path.Combine(dir, id + ".png")), id);
            Assert.IsTrue(File.Exists(Path.Combine(dir, ParentAvatar.Default + ".png")), ParentAvatar.Default);
        }
    }
}
