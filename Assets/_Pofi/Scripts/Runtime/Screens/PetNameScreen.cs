using Pofi.Logic.Pet;
using Pofi.Logic.Progression;
using Pofi.UI;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.Screens
{
    /// <summary>İsim verme: türün adı önerilir, çocuk değiştirebilir. Uygunsuz isim filtresi <see cref="PetNameRules"/>.</summary>
    public sealed class PetNameScreen : ScreenBase
    {
        private InputField _field;
        private Text _error;

        protected override void Build()
        {
            var def = App.Data.Pet(App.State.PetId);
            App.Stage.AllowDrag = true;
            PetCamera(0.3f, 0.12f, 0.8f);   // yatay: pet solda, isim kartı sağda
            App.Stage.ShowPet(def, GrowthStage.Genc);

            Candy.Caption(Root, T("pet.name_title"), 72, new Vector2(0.72f, 0.84f), new Vector2(1000f, 180f), new Vector2(0f, 0f), Candy.Deep(Candy.Orange));
            StarSparkles.Around(Root, new Vector2(0.3f, 0.48f), new Vector2(0.14f, 0.3f), 8, 5);
            Ui.Button(Root, Th, "<", new Vector2(0.04f, 0.93f), new Vector2(110f, 100f), () =>
            {
                App.State.PetId = null;
                App.Save();
                App.Route();
            }, false, default, 60);

            var card = Ui.Rect(Root, "Card", new Vector2(0.72f, 0.42f), new Vector2(820f, 520f));
            Candy.Shell(card, Candy.White).raycastTarget = false;
            _field = Ui.Input(card, Th, T("pet.name_placeholder"), new Vector2(0.5f, 0.76f), new Vector2(680f, 140f), PetNameRules.Max,
                InputField.ContentType.Name, 70);
            _field.text = def.Name;
            _field.onValueChanged.AddListener(_ => _error.text = "");
            _error = Ui.Label(card, "", Th.Font(36), Th.Danger, new Vector2(0.5f, 0.48f), new Vector2(880f, 110f), FontStyle.Bold);
            Candy.Pill(card, Candy.Green, T("pet.name_button"), new Vector2(0.5f, 0.2f), new Vector2(640f, 140f), Vector2.zero, Submit, null, 54).gameObject.AddComponent<Pulse>();
            Footer();
        }

        private void Submit()
        {
            var check = App.NameRules.Check(_field.text);
            if (check != NameCheck.Ok)
            {
                _error.text = Message(check);
                return;
            }
            App.State.PetName = PetNameRules.Tidy(_field.text);
            App.Starter.GiveOnce(App.State, App.Data);
            App.Save();
            App.Stage.Hop();
            App.Route();
        }

        private string Message(NameCheck c)
        {
            switch (c)
            {
                case NameCheck.TooShort: return T("pet.name.too_short");
                case NameCheck.TooLong: return T("pet.name.too_long");
                case NameCheck.InvalidCharacters: return T("pet.name.invalid");
                default: return T("pet.name.not_allowed");
            }
        }
    }
}
