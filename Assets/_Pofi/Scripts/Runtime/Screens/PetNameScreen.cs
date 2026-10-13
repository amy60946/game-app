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
            App.Stage.SetCamera(new Vector3(0f, 0.46f, -6.23f), 0f);
            App.Stage.ShowPet(def, GrowthStage.Genc);

            Ui.Label(Root, T("pet.name_title"), Th.Font(72), Color.white, new Vector2(0.5f, 0.9f), new Vector2(1000f, 200f), FontStyle.Bold)
                .gameObject.AddComponent<Shadow>().effectDistance = new Vector2(0f, -5f);
            Ui.Button(Root, Th, "<", new Vector2(0.08f, 0.965f), new Vector2(110f, 100f), () =>
            {
                App.State.PetId = null;
                App.Save();
                App.Route();
            }, false, default, 60);

            var card = Ui.Rect(Root, "Card", new Vector2(0.5f, 0.2f), new Vector2(960f, 560f));
            Ui.Panel(card, Th.Panel, Th.Radius);
            _field = Ui.Input(card, Th, T("pet.name_placeholder"), new Vector2(0.5f, 0.76f), new Vector2(760f, 150f), PetNameRules.Max,
                InputField.ContentType.Name, 70);
            _field.text = def.Name;
            _field.onValueChanged.AddListener(_ => _error.text = "");
            _error = Ui.Label(card, "", Th.Font(36), Th.Danger, new Vector2(0.5f, 0.48f), new Vector2(880f, 110f), FontStyle.Bold);
            Ui.Button(card, Th, T("pet.name_button"), new Vector2(0.5f, 0.2f), new Vector2(640f, 140f), Submit);
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
