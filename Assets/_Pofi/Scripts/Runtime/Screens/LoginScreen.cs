using System;
using Pofi.Logic.Auth;
using Pofi.Logic.Services;
using Pofi.UI;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.Screens
{
    /// <summary>
    /// Kodla giriş (FR-AUTH-1): ebeveynin ParentApp'te ürettiği 6 karakterlik kod. Hatalı denemede bekleme süresi artar.
    /// Görünüş oyunun içindeki pencere diliyle aynı (24 Ekim 2026, kullanıcı; "E · Altın Atölye"): krem kart, üst kenarında
    /// mavi kurdele başlık, altın çerçeveli gömme kod kutusu (altında 6 harf yuvası), tek yeşil ana düğme, Baloo 2.
    /// Arkada kumsal (<see cref="World.Stage.SetBeach"/>), solda Okti.
    /// </summary>
    public sealed class LoginScreen : ScreenBase
    {
        private static readonly Color Ink = new Color(0.42f, 0.25f, 0.06f), InkSoft = new Color(0.54f, 0.35f, 0.13f),
            PipOff = new Color(0.89f, 0.8f, 0.57f), PipOn = new Color(0.96f, 0.68f, 0.12f), Error = new Color(0.78f, 0.16f, 0.16f);

        private InputField _code;
        private Button _go;
        private Pulse _goPulse;
        private Text _error;
        private Image[] _pips;
        private bool _busy;

        protected override void Build()
        {
            App.Stage.SetBeach(true);
            App.Stage.AllowDrag = true;
            // Yatay: solda pet (kumda), sağda kod kartı
            PetCamera(0.3f, 0.13f, 0.8f);
            App.Stage.ShowPet(App.Data.ActivePets[0], Logic.Progression.GrowthStage.Yavru);   // herkes çocuk Okti ile başlar

            // oyun adı: oyun yazı tarzında (tanışma ekranı başlığıyla aynı), müzik düğmesinin altında kalır
            Candy.Caption(Root, T("auth.title"), 104, new Vector2(0.72f, 0.84f), new Vector2(1000f, 140f), Vector2.zero, Candy.Deep(Candy.Orange));

            // pencere: oyundaki pencerelerle aynı krem kart + mavi kurdele başlık
            var card = Ui.Rect(Root, "Card", new Vector2(0.72f, 0.41f), new Vector2(860f, 600f));
            Candy.Shell(card, new Color(1f, 0.99f, 0.96f));   // gövdenin görünmez dokunma yüzeyi: karta dokunuş peti çevirmez
            ModalTitle(card, T("auth.code_prompt"));
            Ui.Label(card, T("auth.code_hint"), 32, InkSoft, new Vector2(0.5f, 0.8f), new Vector2(760f, 56f), FontStyle.Bold);

            _code = CodeField(card, new Vector2(0.5f, 0.62f), new Vector2(620f, 150f));
            _code.onValueChanged.AddListener(OnTyped);
            _code.onEndEdit.AddListener(_ => { if (ChildCode.IsWellFormed(ChildCode.Normalize(_code.text))) Submit(); });
            _pips = Pips(card, new Vector2(0.5f, 0.44f));
            _error = Ui.Label(card, "", 32, Error, new Vector2(0.5f, 0.33f), new Vector2(780f, 90f), FontStyle.Bold);

            _go = Candy.Pill(card, Candy.Green, T("auth.button"), new Vector2(0.5f, 0.14f), new Vector2(560f, 128f), Vector2.zero, Submit, null, 54);
            _goPulse = _go.gameObject.AddComponent<Pulse>();
            SetReady(false);

            // Önizleme Mock arka uçla çalışır: deneme kodlarını göster.
            if (App.Router.DemoCodesEnabled)
                Candy.Caption(Root, T("auth.demo_hint"), 28, new Vector2(0.72f, 0.06f), new Vector2(1100f, 80f));
            Footer();
        }

        /// <summary>
        /// Kod kutusu (E dili): altın kenarlı, içi gömme krem yüz (üst kenarı gölgeli), kalın kahve harfler. Tek satır, 6 karakter.
        /// </summary>
        private InputField CodeField(RectTransform parent, Vector2 anchor, Vector2 size)
        {
            var rt = Ui.Rect(parent, "Code", anchor, size);
            var r = size.y * 0.32f;
            Ui.Panel(Ui.Rect(rt, "GoldShade", new Vector2(0.5f, 0.5f), size + new Vector2(16f, 16f), new Vector2(0f, -3f)), new Color(0.6f, 0.38f, 0.08f), r + 8f).raycastTarget = false;
            Ui.Panel(Ui.Rect(rt, "Gold", new Vector2(0.5f, 0.5f), size + new Vector2(14f, 14f)), new Color(0.95f, 0.72f, 0.2f), r + 7f).raycastTarget = false;
            Ui.Panel(Ui.Rect(rt, "GoldLight", new Vector2(0.5f, 0.5f), size + new Vector2(8f, 6f), new Vector2(0f, 2f)), new Color(1f, 0.9f, 0.55f), r + 4f).raycastTarget = false;
            Ui.Panel(Ui.Rect(rt, "Well", new Vector2(0.5f, 0.5f), size), new Color(0.88f, 0.77f, 0.56f), r).raycastTarget = false;
            var face = Ui.Panel(Ui.Rect(rt, "Face", new Vector2(0.5f, 0.5f), size - new Vector2(8f, 12f), new Vector2(0f, -4f)), new Color(1f, 0.985f, 0.94f), r - 3f);

            var field = rt.gameObject.AddComponent<InputField>();
            field.targetGraphic = face;
            var cols = field.colors; cols.highlightedColor = Color.white; cols.pressedColor = new Color(0.97f, 0.95f, 0.9f); field.colors = cols;
            var inner = Ui.Fill(rt, "Area");
            inner.offsetMin = new Vector2(30f, 6f); inner.offsetMax = new Vector2(-30f, -10f);
            var ph = Ui.Label(inner, T("auth.placeholder"), 80, new Color(Ink.r, Ink.g, Ink.b, 0.28f), new Vector2(0.5f, 0.5f), Vector2.zero, FontStyle.Bold);
            Ui.Stretch(ph.rectTransform);
            var txt = Ui.Label(inner, "", 80, Ink, new Vector2(0.5f, 0.5f), Vector2.zero, FontStyle.Bold);
            Ui.Stretch(txt.rectTransform);
            txt.supportRichText = false;
            txt.horizontalOverflow = HorizontalWrapMode.Overflow;
            field.textComponent = txt;
            field.placeholder = ph;
            field.characterLimit = ChildCode.Length;
            field.contentType = InputField.ContentType.Alphanumeric;
            field.lineType = InputField.LineType.SingleLine;
            field.caretWidth = 5;
            field.customCaretColor = true;
            field.caretColor = new Color(0.85f, 0.5f, 0.05f);
            field.selectionColor = new Color(1f, 0.82f, 0.35f, 0.6f);
            return field;
        }

        /// <summary>6 harf yuvası: yazılan harf sayısı kadarı altın yanar (çocuk kaç harf kaldığını görür).</summary>
        private static Image[] Pips(RectTransform parent, Vector2 anchor)
        {
            var pips = new Image[ChildCode.Length];
            const float w = 64f, gap = 16f;
            for (var i = 0; i < pips.Length; i++)
            {
                var x = (i - (pips.Length - 1) / 2f) * (w + gap);
                var rt = Ui.Rect(parent, "Pip" + i, anchor, new Vector2(w, 20f), new Vector2(x, 0f));
                pips[i] = Ui.Panel(rt, PipOff, 10f);
                pips[i].raycastTarget = false;
                var sh = rt.gameObject.AddComponent<Shadow>(); sh.effectColor = new Color(0.55f, 0.36f, 0.08f, 0.45f); sh.effectDistance = new Vector2(0f, -3f);
            }
            return pips;
        }

        private void SetPips(int n)
        {
            for (var i = 0; i < _pips.Length; i++) _pips[i].color = i < n ? PipOn : PipOff;
        }

        private void SetReady(bool ready)
        {
            _go.interactable = ready;
            _goPulse.enabled = ready;
            if (!ready) _go.transform.localScale = Vector3.one;
        }

        private void OnTyped(string raw)
        {
            var norm = ChildCode.Normalize(raw);
            if (norm != raw) { _code.SetTextWithoutNotify(norm); _code.caretPosition = norm.Length; }
            SetPips(norm.Length);
            SetReady(!_busy && ChildCode.IsWellFormed(norm));
            _error.text = "";
        }

        private async void Submit()
        {
            if (_busy) return;
            var code = ChildCode.Normalize(_code.text);
            if (!ChildCode.IsWellFormed(code)) return;
            _busy = true;
            SetReady(false);
            AuthResult r;
            try { r = await App.Auth.SignInWithCodeAsync(code); }
            catch (Exception e) { Debug.LogException(e); r = AuthResult.Fail(AuthErrorKind.Unknown); }
            _busy = false;
            if (this == null) return;   // ekran bu arada kapandı
            if (r.Ok)
            {
                App.OnSignedIn(r.Session);
                return;
            }
            _error.text = ErrorText(r.Error);
            SetReady(true);
            App.Stage.Hop();
        }

        private string ErrorText(AuthErrorKind e)
        {
            switch (e)
            {
                case AuthErrorKind.Throttled:
                    var secs = (int)Math.Ceiling(App.Router.ThrottleRemaining(DateTime.UtcNow).TotalSeconds);
                    return T("auth.throttled", Math.Max(1, secs));
                case AuthErrorKind.Revoked: return T("auth.revoked");
                case AuthErrorKind.Network: return T("auth.offline");
                case AuthErrorKind.CodeExpired: return T("auth.expired");
                case AuthErrorKind.CodeUsed: return T("auth.used");
                default: return T("auth.invalid");
            }
        }
    }
}
