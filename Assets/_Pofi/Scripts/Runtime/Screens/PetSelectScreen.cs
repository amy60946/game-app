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
            PetCamera(0.42f, 0.24f, 0.9f);   // yatay: pet sol-ortada ve büyük (çocuğun odağı), bilgi kartı sağda
            App.Stage.Swiped = dir => { if (dir < 0) _picker.Next(); else _picker.Prev(); Show(); };

            // oyun yazı tarzında başlık; petin çevresinde parıldayan yıldızlar
            Candy.Caption(Root, T("pet.pick_title"), 84, new Vector2(0.42f, 0.93f), new Vector2(1100f, 110f), new Vector2(0f, 0f), Candy.Deep(Candy.Orange));
            Candy.Caption(Root, T("pet.pick_hint"), 34, new Vector2(0.42f, 0.865f), new Vector2(1000f, 50f));
            StarSparkles.Around(Root, new Vector2(0.42f, 0.56f), new Vector2(0.17f, 0.27f), 9, 3);

            var prev = Candy.Round(Root, Candy.Orange, null, 140f, new Vector2(0.16f, 0.55f), Vector2.zero, () => { _picker.Prev(); Show(); });
            Candy.Caption(prev.transform, "<", 80, new Vector2(0.5f, 0.52f), new Vector2(140f, 140f));
            var next = Candy.Round(Root, Candy.Orange, null, 140f, new Vector2(0.68f, 0.55f), Vector2.zero, () => { _picker.Next(); Show(); });
            Candy.Caption(next.transform, ">", 80, new Vector2(0.5f, 0.52f), new Vector2(140f, 140f));

            var card = Ui.Rect(Root, "Info", new Vector2(0.84f, 0.64f), new Vector2(560f, 400f));
            Candy.Shell(card, Candy.White).raycastTarget = false;
            _name = Ui.Label(card, "", Th.Font(72), Th.Text, new Vector2(0.5f, 0.82f), new Vector2(520f, 100f), FontStyle.Bold);
            _species = Ui.Label(card, "", Th.Font(38), Th.SubtleText, new Vector2(0.5f, 0.62f), new Vector2(520f, 60f));
            _feature = Ui.Label(card, "", Th.Font(32), Th.SubtleText, new Vector2(0.5f, 0.32f), new Vector2(500f, 160f), FontStyle.Italic);

            _dots = new Image[_picker.Count];
            // iri şeker çerçeveli küçük resimler (ekran genişliğine göre en çok 170): çocuk kolayca seçer
            var step = Mathf.Min(176f, (Width - 60f) / _picker.Count);
            var size = step - 14f;
            for (var i = 0; i < _picker.Count; i++)
            {
                var def = App.Data.Pets[i];
                var x = (i - (_picker.Count - 1) / 2f) * step;
                var frame = Ui.Rect(Root, "Pick " + def.Id, new Vector2(0.5f, 0.11f), new Vector2(size, size), new Vector2(x, 0f));
                _dots[i] = Candy.Shell(frame, Color.Lerp(Theme.Hex(def.MainColor), Color.white, 0.45f));
                Ui.PortraitIcon(frame, def.Id, new Color(1f, 1f, 1f, 0f), new Vector2(0.5f, 0.5f), size * 0.86f);
                var btn = frame.gameObject.AddComponent<Button>();
                btn.targetGraphic = _dots[i];
                frame.gameObject.AddComponent<PressBounce>();
                var id = def.Id;
                btn.onClick.AddListener(() => { _picker.JumpTo(id); Show(); });
            }

            Candy.Pill(Root, Candy.Green, T("pet.pick_button"), new Vector2(0.84f, 0.3f), new Vector2(540f, 140f), Vector2.zero, AskConfirm, null, 52).gameObject.AddComponent<Pulse>();
            Show();
            if (Logic.App.FirstDay.Current(App.State, App.LocalNow, App.UtcNow) == Logic.App.FirstDayStep.Story) StoryCard();
        }

        /// <summary>İlk açılış (Ö5): kısa hikâye girişi. Bir kez gösterilir.</summary>
        private void StoryCard()
        {
            var root = Modal(720f, out var box);
            Candy.Caption(box, T("story.title"), 72, new Vector2(0.5f, 0.85f), new Vector2(880f, 100f), Vector2.zero, Candy.Deep(Candy.Orange));
            Ui.Label(box, T("story.body"), Th.Font(38), Th.Text, new Vector2(0.5f, 0.52f), new Vector2(840f, 330f));
            Ui.Button(box, Th, T("story.start"), new Vector2(0.5f, 0.13f), new Vector2(520f, 120f), () =>
            {
                Logic.App.Onboarding.Done(App.State, Logic.App.Onboarding.Story);
                App.Save();
                Destroy(root.gameObject);
            });
        }

        private void Show()
        {
            var def = App.Data.Pet(_picker.Current);
            App.Stage.ShowPet(def, GrowthStage.Genc);
            _name.text = def.Name;
            _species.text = def.Species;
            _feature.text = def.Feature;
            for (var i = 0; i < _dots.Length; i++)
            {
                var on = i == _picker.Index;
                _dots[i].transform.parent.localScale = Vector3.one * (on ? 1.2f : 0.94f);
                _dots[i].color = on ? Candy.Gold : Color.Lerp(Theme.Hex(App.Data.Pets[i].MainColor), Color.white, 0.45f);
            }
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
            var box = Ui.Rect(_confirm, "Box", new Vector2(0.84f, 0.42f), new Vector2(620f, 560f));
            Ui.Panel(box, Color.white, Th.Radius);
            Ui.Label(box, T("pet.pick_confirm", TurkishSuffix.Accusative(def.Name)), Th.Font(52), Th.Text, new Vector2(0.5f, 0.78f), new Vector2(560f, 180f), FontStyle.Bold);
            Ui.Button(box, Th, T("pet.pick_yes"), new Vector2(0.5f, 0.43f), new Vector2(500f, 130f), () =>
            {
                PetChange.Choose(App.State, def.Id, App.Data);
                App.Save();
                App.Stage.Swiped = null;
                App.Route();
            });
            Ui.Button(box, Th, T("pet.pick_no"), new Vector2(0.5f, 0.15f), new Vector2(500f, 110f), () =>
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
