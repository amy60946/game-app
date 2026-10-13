using System.Linq;
using Pofi.Logic.App;
using Pofi.Logic.Core;
using Pofi.Logic.Progression;
using Pofi.UI;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.Screens
{
    /// <summary>
    /// 12 pet karuseli: odaktaki pet canlı 3B (parmakla çevrilir), oklar/kaydırma/nokta ile değişir; seçim son onayla kesinleşir.
    /// Önceki pet sahneden silinir, bellekte yalnızca odaktaki kalır.
    /// </summary>
    public sealed class PetSelectScreen : ScreenBase
    {
        private PetPicker _picker;
        private Text _name, _species, _feature;
        private Image[] _dots;
        private RectTransform _confirm;

        protected override void Build()
        {
            _picker = new PetPicker(App.Data.Pets.Select(p => p.Id).ToList());
            if (!string.IsNullOrEmpty(App.State.PetId)) _picker.JumpTo(App.State.PetId);
            App.Stage.AllowDrag = true;
            App.Stage.SetCamera(new Vector3(0f, 0.46f, -6.23f), 0f);
            App.Stage.Swiped = dir => { if (dir < 0) _picker.Next(); else _picker.Prev(); Show(); };

            var white = Color.white;
            Ui.Label(Root, T("pet.pick_title"), Th.Font(84), white, new Vector2(0.5f, 0.915f), new Vector2(1000f, 120f), FontStyle.Bold)
                .gameObject.AddComponent<Shadow>().effectDistance = new Vector2(0f, -5f);
            Ui.Label(Root, T("pet.pick_hint"), Th.Font(38), white, new Vector2(0.5f, 0.865f), new Vector2(1000f, 60f));

            Ui.Button(Root, Th, "<", new Vector2(0.09f, 0.5f), new Vector2(130f, 170f), () => { _picker.Prev(); Show(); }, false, default, 80);
            Ui.Button(Root, Th, ">", new Vector2(0.91f, 0.5f), new Vector2(130f, 170f), () => { _picker.Next(); Show(); }, false, default, 80);

            var card = Ui.Rect(Root, "Info", new Vector2(0.5f, 0.205f), new Vector2(960f, 330f));
            Ui.Panel(card, Th.Panel, Th.Radius);
            _name = Ui.Label(card, "", Th.Font(78), Th.Text, new Vector2(0.5f, 0.8f), new Vector2(900f, 100f), FontStyle.Bold);
            _species = Ui.Label(card, "", Th.Font(40), Th.SubtleText, new Vector2(0.5f, 0.56f), new Vector2(900f, 60f));
            _feature = Ui.Label(card, "", Th.Font(34), Th.SubtleText, new Vector2(0.5f, 0.3f), new Vector2(880f, 100f), FontStyle.Italic);

            _dots = new Image[_picker.Count];
            for (var i = 0; i < _picker.Count; i++)
            {
                var def = App.Data.Pets[i];
                var x = (i - (_picker.Count - 1) / 2f) * 86f;
                var dot = Ui.PortraitIcon(Root, def.Id, Color.Lerp(Theme.Hex(def.MainColor), Color.white, 0.55f), new Vector2(0.5f, 0.335f), 78f, new Vector2(x, 0f));
                _dots[i] = dot.GetComponent<Image>();
                var btn = dot.gameObject.AddComponent<Button>();
                btn.targetGraphic = _dots[i];
                var id = def.Id;
                btn.onClick.AddListener(() => { _picker.JumpTo(id); Show(); });
                dot.gameObject.AddComponent<Outline>().effectColor = new Color(1f, 1f, 1f, 0.9f);
            }

            Ui.Button(Root, Th, T("pet.pick_button"), new Vector2(0.5f, 0.075f), new Vector2(760f, 140f), AskConfirm);
            Show();
        }

        private void Show()
        {
            var def = App.Data.Pet(_picker.Current);
            App.Stage.ShowPet(def, GrowthStage.Genc);
            _name.text = def.Name;
            _species.text = def.Species;
            _feature.text = def.Feature;
            for (var i = 0; i < _dots.Length; i++)
                _dots[i].rectTransform.localScale = Vector3.one * (i == _picker.Index ? 1.3f : 0.9f);
        }

        private void AskConfirm()
        {
            if (_confirm != null) return;
            var def = App.Data.Pet(_picker.Current);
            App.Stage.AllowDrag = false;
            App.Stage.Hop();
            _confirm = Ui.Fill(Root, "Confirm");
            var dim = _confirm.gameObject.AddComponent<Image>();
            dim.color = new Color(0f, 0.1f, 0.25f, 0.35f);
            var box = Ui.Rect(_confirm, "Box", new Vector2(0.5f, 0.2f), new Vector2(960f, 520f));
            Ui.Panel(box, Color.white, Th.Radius);
            Ui.Label(box, T("pet.pick_confirm", TurkishSuffix.Accusative(def.Name)), Th.Font(56), Th.Text, new Vector2(0.5f, 0.78f), new Vector2(880f, 160f), FontStyle.Bold);
            Ui.Button(box, Th, T("pet.pick_yes"), new Vector2(0.5f, 0.43f), new Vector2(700f, 130f), () =>
            {
                PetChange.Choose(App.State, def.Id, App.Data);
                App.Save();
                App.Stage.Swiped = null;
                App.Route();
            });
            Ui.Button(box, Th, T("pet.pick_no"), new Vector2(0.5f, 0.15f), new Vector2(700f, 110f), () =>
            {
                Destroy(_confirm.gameObject);
                _confirm = null;
                App.Stage.AllowDrag = true;
            }, false, default, 44);
        }

        private void OnDestroy()
        {
            if (App != null && App.Stage != null) App.Stage.Swiped = null;
        }
    }
}
