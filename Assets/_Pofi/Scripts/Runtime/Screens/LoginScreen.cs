using System;
using Pofi.Logic.Auth;
using Pofi.Logic.Services;
using Pofi.Logic.Services.Mock;
using Pofi.UI;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.Screens
{
    /// <summary>Kodla giriş (FR-AUTH-1): ebeveynin Fidan'da ürettiği 6 karakterlik kod. Hatalı denemede bekleme süresi artar.</summary>
    public sealed class LoginScreen : ScreenBase
    {
        private InputField _code;
        private Button _go;
        private Text _error;
        private bool _busy;

        protected override void Build()
        {
            App.Stage.AllowDrag = true;
            // Yatay: solda pet, sağda kod kartı
            PetCamera(0.3f, 0.1f, 0.78f);
            App.Stage.ShowPet(App.Data.Pet("pet_01"), Logic.Progression.GrowthStage.Genc);

            var white = Color.white;
            var title = Ui.Label(Root, T("auth.title"), Th.Font(110), white, new Vector2(0.72f, 0.86f), new Vector2(900f, 150f), FontStyle.Bold);
            title.gameObject.AddComponent<Shadow>().effectDistance = new Vector2(0f, -6f);
            Ui.Label(Root, T("auth.code_prompt"), Th.Font(46), white, new Vector2(0.72f, 0.76f), new Vector2(900f, 70f));

            var card = Ui.Rect(Root, "Card", new Vector2(0.72f, 0.42f), new Vector2(820f, 520f));
            Ui.Panel(card, Th.Panel, Th.Radius);
            _code = Ui.Input(card, Th, T("auth.placeholder"), new Vector2(0.5f, 0.76f), new Vector2(640f, 150f), ChildCode.Length,
                InputField.ContentType.Alphanumeric, 80);
            _code.onValueChanged.AddListener(OnTyped);
            _code.onEndEdit.AddListener(_ => { if (ChildCode.IsWellFormed(ChildCode.Normalize(_code.text))) Submit(); });
            _error = Ui.Label(card, "", Th.Font(36), Th.Danger, new Vector2(0.5f, 0.48f), new Vector2(880f, 110f), FontStyle.Bold);
            _go = Ui.Button(card, Th, T("auth.button"), new Vector2(0.5f, 0.2f), new Vector2(640f, 140f), Submit);
            _go.interactable = false;

            // Önizleme Mock arka uçla çalışır: deneme kodlarını göster.
            if (App.Router.DemoCodesEnabled)
                Ui.Label(Root, T("auth.demo_hint"), Th.Font(28), white, new Vector2(0.72f, 0.1f), new Vector2(900f, 80f));
            Footer();
        }

        private void OnTyped(string raw)
        {
            var norm = ChildCode.Normalize(raw);
            if (norm != raw) { _code.SetTextWithoutNotify(norm); _code.caretPosition = norm.Length; }
            _go.interactable = !_busy && ChildCode.IsWellFormed(norm);
            _error.text = "";
        }

        private async void Submit()
        {
            if (_busy) return;
            var code = ChildCode.Normalize(_code.text);
            if (!ChildCode.IsWellFormed(code)) return;
            _busy = true;
            _go.interactable = false;
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
            _go.interactable = true;
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
                default: return T("auth.invalid");
            }
        }
    }
}
