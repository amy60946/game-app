using System.Collections.Generic;
using System.Linq;
using Pofi.Logic.App;
using Pofi.Logic.Mail;
using Pofi.UI;
using UnityEngine;
using UnityEngine.Networking;
using UnityEngine.UI;

namespace Pofi.Screens
{
    /// <summary>
    /// Posta kutusu (H2 / Ö6, 23 Ekim 2026): ParentApp'ten gelen yazı, çıkartma, fotoğraf ve sesli mesajlar; çocuk çıkartmayla
    /// (9 yaş ve üstü yazıyla da) yanıtlar. Açınca ebeveyn mesajları okundu olur. Sözleşme: ortak/sozlesme/akislar.md P10.
    /// </summary>
    public sealed class MailScreen : ScreenBase
    {
        private RectTransform _list;
        private InputField _input;
        private Text _status;
        private bool _sending;
        private static readonly Dictionary<string, string> StickerIcons = new Dictionary<string, string>
        {
            { "heart", "ui_heart" }, { "star", "ui_star" }, { "party", "ui_gift" }, { "thumbs_up", "ui_check" }, { "love_you", "ui_heart" },
        };   // diğerleri (gülümseme, kahkaha, vay, üzgün, uykulu, sarılma, teşekkür) kodla çizilen yüz: StickerFace
        private static readonly string[] StickerColors = { "#FFB3C7", "#FFE27A", "#A8E6A1", "#FFC9A8", "#BFE3FF", "#FFD6F0", "#D9C8FF", "#C7D3E6", "#C8D9FF", "#FFDF9E", "#B8F0D8", "#FFB8B8" };

        protected override void Build()
        {
            App.Stage.SetPetVisible(false);
            Header(T("mail.title"));
            var write = MailBox.CanWrite(Th.Band);
            _list = Ui.ScrollList(CenterColumn("List", 1300f, HeaderHeight, NavHeight + (write ? 300f : 190f), true), Vector2.zero, Vector2.one, 16f);
            _status = Ui.Label(Root, T("mail.loading"), Th.Font(40), Th.SubtleText, new Vector2(0.5f, 0.6f), new Vector2(1000f, 80f));
            BuildReply(write);
            NavBar(AppPage.Map);
            Load();
        }

        private async void Load()
        {
            var list = await App.RefreshMail();
            if (this == null) return;
            if (list == null) { _status.text = T("mail.offline"); return; }
            Render(list);
            if (MailBox.UnreadCount(list) > 0)
            {
                try { await App.Mail.MarkReadAsync(); } catch (System.Exception) { return; }   // çevrimdışı: sonra yeniden denenir
                App.MailRead();
            }
        }

        private void Render(List<MailMessage> list)
        {
            Ui.Clear(_list);
            _status.gameObject.SetActive(list.Count == 0);
            if (list.Count == 0) _status.text = T("mail.empty");
            foreach (var m in list.Skip(System.Math.Max(0, list.Count - 60))) Bubble(m);
            Canvas.ForceUpdateCanvases();
            var sr = _list.GetComponentInParent<ScrollRect>();
            if (sr != null) sr.verticalNormalizedPosition = 0f;   // en yeni altta
        }

        private void Bubble(MailMessage m)
        {
            var mine = !m.FromParent;
            var width = 860f;
            var text = m.Kind == MailBox.Text ? m.Body ?? "" : null;
            var bodyH = 110f;
            Text probe = null;
            if (text != null)
            {
                probe = Ui.Label(Root, text, Th.Font(40), Th.Text, new Vector2(0.5f, 0.5f), new Vector2(width - 60f, 10f), FontStyle.Normal, TextAnchor.UpperLeft);
                bodyH = Mathf.Max(70f, probe.preferredHeight + 10f);
                Destroy(probe.gameObject);
            }
            else if (m.Kind == MailBox.Sticker) bodyH = 190f;
            else if (m.Kind == MailBox.Image) bodyH = 380f;
            var h = bodyH + 90f;
            var row = Ui.Row(_list, "Msg " + m.Id, h);
            var box = Ui.Rect(row, "Bubble", new Vector2(mine ? 1f : 0f, 0.5f), new Vector2(width, h - 10f));
            box.pivot = new Vector2(mine ? 1f : 0f, 0.5f);
            box.anchoredPosition = new Vector2(mine ? -10f : 10f, 0f);
            Ui.Panel(box, mine ? Theme.Hex("#DDEBFF") : Theme.Hex("#FFF6E0"), 36f).raycastTarget = false;
            var who = mine ? App.State.PetName + " · " + T("mail.me") : (string.IsNullOrEmpty(m.FromName) ? T("mail.family") : m.FromName);
            Ui.Label(box, who + "   " + m.CreatedAt.ToLocalTime().ToString("HH:mm"), Th.Font(30), Theme.Hex(mine ? "#2B5EA8" : "#9A6B30"),
                new Vector2(0.5f, 1f), new Vector2(width - 60f, 50f), FontStyle.Bold, TextAnchor.MiddleLeft, new Vector2(0f, -32f));
            var body = Ui.Rect(box, "Body", new Vector2(0.5f, 1f), new Vector2(width - 60f, bodyH), new Vector2(0f, -66f - bodyH * 0.5f));
            switch (m.Kind)
            {
                case MailBox.Text:
                    Ui.Stretch(Ui.Label(body, text, Th.Font(40), Theme.Hex("#3A2508"), new Vector2(0.5f, 0.5f), Vector2.zero, FontStyle.Normal, TextAnchor.UpperLeft).rectTransform);
                    break;
                case MailBox.Sticker:
                    Sticker(body, m.Body, new Vector2(mine ? 1f : 0f, 0.5f), 170f);
                    break;
                case MailBox.Image:
                    var pic = Ui.Rect(body, "Photo", new Vector2(0.5f, 0.5f), new Vector2(width - 60f, bodyH));
                    var img = pic.gameObject.AddComponent<RawImage>(); img.color = new Color(1f, 1f, 1f, 0.25f); img.raycastTarget = false;
                    var hint = Ui.Label(pic, T("mail.photo"), Th.Font(38), Th.SubtleText, new Vector2(0.5f, 0.5f), new Vector2(600f, 80f));
                    LoadPhoto(m.MediaPath, img, hint);
                    break;
                case MailBox.Audio:
                    var secs = Mathf.Max(1, Mathf.RoundToInt(m.DurationMs / 1000f));
                    Ui.Button(body, Th, T("mail.voice", secs), new Vector2(mine ? 0.75f : 0.25f, 0.5f), new Vector2(420f, 96f), () => PlayVoice(m.MediaPath), true, default, 36, false);
                    break;
            }
        }

        private void Sticker(RectTransform parent, string key, Vector2 anchor, float size)
        {
            var idx = System.Array.FindIndex(MailBox.Stickers, s => s.Key == key);
            var c = Ui.Rect(parent, "Sticker " + key, anchor, new Vector2(size, size));
            c.pivot = anchor;
            Ui.Panel(c, Theme.Hex(StickerColors[Mathf.Max(0, idx) % StickerColors.Length]), size * 0.5f).raycastTarget = false;
            if (StickerIcons.TryGetValue(key ?? "", out var icon)) Ui.IconImage(c, icon, new Vector2(0.5f, 0.6f), size * 0.55f);
            else if (StickerFace.For(key) is Sprite face)
            {
                var f = Ui.Rect(c, "Face", new Vector2(0.5f, 0.6f), new Vector2(size * 0.58f, size * 0.58f));
                var fi = f.gameObject.AddComponent<Image>(); fi.sprite = face; fi.preserveAspect = true; fi.raycastTarget = false;
            }
            Ui.Label(c, MailBox.StickerLabel(key), Th.Font((int)(size * 0.15f)), Theme.Hex("#3A2508"), new Vector2(0.5f, 0.2f), new Vector2(size + 40f, size * 0.3f), FontStyle.Bold);
        }

        private void BuildReply(bool write)
        {
            var bar = Ui.Rect(Root, "Reply", new Vector2(0.5f, 0f), new Vector2(1500f, write ? 290f : 180f), new Vector2(0f, NavHeight + (write ? 150f : 95f)));
            Ui.Panel(bar, new Color(1f, 0.97f, 0.9f, 0.96f), 40f).raycastTarget = true;
            for (var i = 0; i < MailBox.Stickers.Length; i++)
            {
                var key = MailBox.Stickers[i].Key;
                var x = (i + 0.5f) / MailBox.Stickers.Length;
                var holder = Ui.Rect(bar, "S" + i, new Vector2(x, write ? 0.7f : 0.5f), new Vector2(118f, 118f));
                Sticker(holder, key, new Vector2(0.5f, 0.5f), 104f);
                var hit = holder.gameObject.AddComponent<Image>(); hit.color = new Color(1f, 1f, 1f, 0.001f);
                var b = holder.gameObject.AddComponent<Button>(); b.targetGraphic = hit; b.transition = Selectable.Transition.None;
                holder.gameObject.AddComponent<PressBounce>();
                b.onClick.AddListener(() => Send(MailBox.Sticker, key));
            }
            if (!write) return;
            _input = Ui.Input(bar, Th, T("mail.write"), new Vector2(0.4f, 0.24f), new Vector2(1000f, 96f), MailBox.ChildTextMax, InputField.ContentType.Standard, 40);
            Ui.Button(bar, Th, T("mail.send"), new Vector2(0.86f, 0.24f), new Vector2(260f, 96f), () => Send(MailBox.Text, _input.text), true, default, 40, false);
        }

        private async void Send(string kind, string body)
        {
            if (_sending) return;
            var err = MailBox.Check(kind, body, Th.Band);
            if (err != null)
            {
                Toast.Post(App.Overlay.transform, Th, err == "empty" ? T("mail.err_empty") : err == "too_long" ? T("mail.err_too_long") : T("mail.err_not_allowed"));
                return;
            }
            _sending = true;
            MailSend r;
            try { r = await App.Mail.SendAsync(kind, kind == MailBox.Text ? body.Trim() : body); }
            catch (System.Exception) { r = new MailSend { Ok = false, Error = "offline" }; }
            finally { _sending = false; }
            if (this == null) return;
            if (!r.Ok) { Toast.Post(App.Overlay.transform, Th, T(r.Error == "offline" ? "mail.offline" : "mail.err_server")); return; }
            Audio.Sfx.Play(Audio.SfxKind.Whoosh);
            if (_input != null && kind == MailBox.Text) _input.text = "";
            App.RecordActivity("mail_sent");
            var list = await App.RefreshMail();
            if (this != null && list != null) Render(list);
        }

        private async void LoadPhoto(string path, RawImage img, Text hint)
        {
            var url = await App.Mail.MediaUrlAsync(path);
            if (this == null || img == null) return;
            if (url == null) { hint.text = T("mail.photo_later"); return; }
            using (var req = UnityWebRequestTexture.GetTexture(url))
            {
                var op = req.SendWebRequest();
                while (!op.isDone) await System.Threading.Tasks.Task.Yield();
                if (this == null || img == null) return;
                if (req.result != UnityWebRequest.Result.Success) { hint.text = T("mail.photo_later"); return; }
                var tex = DownloadHandlerTexture.GetContent(req);
                img.texture = tex; img.color = Color.white; hint.gameObject.SetActive(false);
                var rt = img.rectTransform; var k = Mathf.Min(rt.sizeDelta.x / tex.width, rt.sizeDelta.y / tex.height);
                rt.sizeDelta = new Vector2(tex.width * k, tex.height * k);
            }
        }

        private AudioSource _voice;

        private async void PlayVoice(string path)
        {
            var url = await App.Mail.MediaUrlAsync(path);
            if (this == null) return;
            if (url == null) { Toast.Post(App.Overlay.transform, Th, T("mail.voice_later")); return; }
            using (var req = UnityWebRequestMultimedia.GetAudioClip(url, AudioType.UNKNOWN))
            {
                var op = req.SendWebRequest();
                while (!op.isDone) await System.Threading.Tasks.Task.Yield();
                if (this == null) return;
                if (req.result != UnityWebRequest.Result.Success) { Toast.Post(App.Overlay.transform, Th, T("mail.voice_later")); return; }
                var clip = DownloadHandlerAudioClip.GetContent(req);
                if (_voice == null) _voice = gameObject.AddComponent<AudioSource>();
                _voice.clip = clip; _voice.Play();
            }
        }
    }

    /// <summary>
    /// Çıkartma yüzleri (H2): simgesi olmayan duygular için kodla çizilen sarı yüz (göz + ağız biçimi duyguya göre, yanak pembesi).
    /// 128 px, 2×2 örnekle yumuşak kenar; bir kez çizilir, saklanır.
    /// </summary>
    public static class StickerFace
    {
        private static readonly Dictionary<string, Sprite> Cache = new Dictionary<string, Sprite>();
        private static readonly string[] Kinds = { "smile", "laugh", "wow", "sad", "sleepy", "hug", "thanks" };

        public static Sprite For(string key)
        {
            if (key == null || System.Array.IndexOf(Kinds, key) < 0) return null;
            if (Cache.TryGetValue(key, out var sp) && sp != null) return sp;
            const int n = 128;
            var tex = new Texture2D(n, n, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, name = "sticker_" + key };
            var px = new Color32[n * n];
            for (var y = 0; y < n; y++)
                for (var x = 0; x < n; x++)
                {
                    var acc = new Color(0f, 0f, 0f, 0f);
                    for (var sy = 0; sy < 2; sy++)
                        for (var sx = 0; sx < 2; sx++)
                        {
                            var u = ((x + 0.25f + sx * 0.5f) / n) * 2f - 1f;
                            var v = ((y + 0.25f + sy * 0.5f) / n) * 2f - 1f;
                            var c = Sample(key, u, v);
                            acc += new Color(c.r * c.a, c.g * c.a, c.b * c.a, c.a);
                        }
                    acc /= 4f;
                    px[y * n + x] = acc.a > 0.001f ? new Color(acc.r / acc.a, acc.g / acc.a, acc.b / acc.a, acc.a) : new Color(0f, 0f, 0f, 0f);
                }
            tex.SetPixels32(px); tex.Apply();
            return Cache[key] = Sprite.Create(tex, new Rect(0, 0, n, n), new Vector2(0.5f, 0.5f), 100f);
        }

        private static readonly Color Skin = new Color(1f, 0.84f, 0.29f), Rim = new Color(0.91f, 0.62f, 0.2f), Ink = new Color(0.29f, 0.17f, 0.05f),
            Blush = new Color(1f, 0.55f, 0.55f), Mouth = new Color(0.6f, 0.18f, 0.2f), Tongue = new Color(1f, 0.5f, 0.55f);

        private static Color Sample(string k, float u, float v)
        {
            var r = Mathf.Sqrt(u * u + v * v);
            if (r > 0.94f) return new Color(0f, 0f, 0f, 0f);
            var c = r > 0.86f ? Rim : Color.Lerp(Skin, Color.white, Mathf.Clamp01(0.35f - Dist(u, v, -0.3f, 0.38f) * 1.2f));   // sol üst parıltı
            var happyEyes = k == "laugh" || k == "hug" || k == "thanks";
            var blush = k == "hug" || k == "thanks" || k == "laugh";
            if (blush && (Dist(u, v, -0.52f, -0.16f) < 0.14f || Dist(u, v, 0.52f, -0.16f) < 0.14f)) c = Color.Lerp(c, Blush, 0.75f);
            // gözler
            for (var side = -1; side <= 1; side += 2)
            {
                var ex = side * 0.32f;
                if (happyEyes || k == "sleepy")
                {
                    // ∩ (mutlu) ya da ∪ (uykulu) kapalı göz: yay çizgisi
                    var cy = k == "sleepy" ? 0.22f : 0.12f;
                    var d = Mathf.Abs(Dist(u, v, ex, cy) - 0.12f);
                    var upper = k == "sleepy" ? v < cy : v > cy;
                    if (d < 0.035f && upper) c = Ink;
                }
                else
                {
                    var ry = k == "wow" ? 0.15f : 0.13f; var rx = k == "wow" ? 0.12f : 0.09f;
                    var ey = k == "sad" ? 0.12f : 0.18f;
                    var q = Mathf.Pow((u - ex) / rx, 2f) + Mathf.Pow((v - ey) / ry, 2f);
                    if (q < 1f) c = Ink;
                    if (Mathf.Pow((u - ex + rx * 0.35f) / (rx * 0.35f), 2f) + Mathf.Pow((v - ey - ry * 0.35f) / (ry * 0.35f), 2f) < 1f) c = Color.white;   // göz ışığı
                    if (k == "sad" && Mathf.Abs((v - 0.36f) - side * (u - ex) * -0.35f) < 0.03f && Mathf.Abs(u - ex) < 0.13f) c = Ink;   // eğik kaş
                }
            }
            // ağız
            switch (k)
            {
                case "smile": case "hug": case "thanks":
                    if (Mathf.Abs(Dist(u, v, 0f, 0.02f) - 0.42f) < 0.045f && v < -0.18f) c = Ink;
                    break;
                case "laugh":
                    if (Dist(u, v, 0f, -0.14f) < 0.4f && v < -0.14f) c = Dist(u, v, 0f, -0.62f) < 0.2f ? Tongue : Mouth;
                    break;
                case "wow":
                    if (Mathf.Pow(u / 0.13f, 2f) + Mathf.Pow((v + 0.38f) / 0.17f, 2f) < 1f) c = Mouth;
                    break;
                case "sad":
                    if (Mathf.Abs(Dist(u, v, 0f, -0.78f) - 0.36f) < 0.045f && v > -0.5f) c = Ink;
                    break;
                case "sleepy":
                    if (Mathf.Pow(u / 0.09f, 2f) + Mathf.Pow((v + 0.36f) / 0.07f, 2f) < 1f) c = Mouth;
                    break;
            }
            if (k == "thanks")
            {
                // teşekkür: sağ üstte küçük kalp ((x²+y²−1)³ − x²y³ < 0)
                var hx = (u - 0.5f) / 0.2f; var hy = (v - 0.46f) / 0.2f; var a = hx * hx + hy * hy - 1f;
                if (a * a * a - hx * hx * hy * hy * hy < 0f) c = new Color(0.93f, 0.25f, 0.32f);
            }
            return c;
        }

        private static float Dist(float u, float v, float x, float y) => Mathf.Sqrt((u - x) * (u - x) + (v - y) * (v - y));
    }
}
