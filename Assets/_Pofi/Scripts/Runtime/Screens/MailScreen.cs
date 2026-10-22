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
            { "thanks", "ui_heart" }, { "hug", "ui_heart" },
        };
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
            if (MailBox.UnreadCount(list) > 0) { await App.Mail.MarkReadAsync(); App.MailRead(); }
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
            var r = await App.Mail.SendAsync(kind, kind == MailBox.Text ? body.Trim() : body);
            _sending = false;
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
}
