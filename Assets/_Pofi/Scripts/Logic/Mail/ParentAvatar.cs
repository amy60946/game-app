using System;
using System.Linq;

namespace Pofi.Logic.Mail
{
    /// <summary>
    /// Ebeveynin oyundaki yüzü (kullanıcı seçimi 27 Ekim 2026; ortak sozlesme/durumlar.md §6a): Okti'nin üç anne ve üç baba hâli.
    /// Sunucu değeri (profiles.avatar → child_messages / child_gifts_pending <c>from_avatar</c>) görsel kimliğine çevrilir; görseller
    /// Resources/UI/Avatars/&lt;kimlik&gt; (art/parent_avatars/to_game.py). Eski değerler gösterimde eşlenir, veri değişmez.
    /// </summary>
    public static class ParentAvatar
    {
        public const string Default = "okti";   // seçilmemiş, tanınmayan, photo: ya da alan hiç gelmedi (eski sunucu)

        public static readonly string[] Ids = { "okti_anne_1", "okti_anne_2", "okti_anne_3", "okti_baba_1", "okti_baba_2", "okti_baba_3" };

        public static string Resolve(string value)
        {
            var v = (value ?? "").Trim().ToLowerInvariant();
            if (Ids.Contains(v)) return v;
            switch (v)
            {
                case "kadın":
                case "kadin":
                    return "okti_anne_1";
                case "erkek":
                    return "okti_baba_1";
                default:
                    return Default;   // photo:… dahil: oyun ebeveyn fotoğrafı göstermez
            }
        }
    }
}
