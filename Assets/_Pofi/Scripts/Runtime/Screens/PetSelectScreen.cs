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
    /// Pet seçme / tanışma ekranı. Arkada yükleme görselleriyle aynı dilde tam ekran 3B kumsal (Art/pick_stage, 23 Ekim 2026),
    /// önde canlı 3B pet (parmakla çevrilir). Tek pet (Okti) varken ok, küçük resim yok: ad, tür, bir cümle ve tek yeşil düğme.
    /// Birden çok pet olursa karusel (oklar, kaydırma, küçük resimler) geri gelir. İlk açılışta önce giriş filmi (F) oynar.
    /// </summary>
    public sealed class PetSelectScreen : ScreenBase
    {
        private PetPicker _picker;
        private Text _name, _species, _feature;
        private Image[] _dots;
        private RectTransform _confirm;

        protected override void Build()
        {
            _picker = new PetPicker(App.Data.ActivePets.Select(p => p.Id).ToList());
            if (!string.IsNullOrEmpty(App.State.PetId)) _picker.JumpTo(App.State.PetId);
            App.Stage.AllowDrag = true;
            var single = _picker.Count <= 1;
            App.Stage.SetPicture(Resources.Load<Texture2D>("Art/pick_stage"));   // kumsal sahnesi (Meshy, karaktersiz)
            PetCamera(0.36f, 0.16f, 0.82f);   // yatay: pet sol-ortada kumda, bilgi kartı sağda
            if (!single) App.Stage.Swiped = dir => { if (dir < 0) _picker.Next(); else _picker.Prev(); Show(); };

            // oyun yazı tarzında başlık; petin çevresinde parıldayan yıldızlar
            Candy.Caption(Root, T(single ? "pet.meet_title" : "pet.pick_title"), 84, new Vector2(0.5f, 0.92f), new Vector2(1500f, 110f), new Vector2(0f, 0f), Candy.Deep(Candy.Orange));
            Candy.Caption(Root, T(single ? "pet.meet_hint" : "pet.pick_hint"), 34, new Vector2(0.5f, 0.85f), new Vector2(1300f, 50f));
            StarSparkles.Around(Root, new Vector2(0.36f, 0.5f), new Vector2(0.16f, 0.26f), 9, 3);

            if (!single)
            {
                var prev = Candy.Round(Root, Candy.Orange, null, 140f, new Vector2(0.12f, 0.55f), Vector2.zero, () => { _picker.Prev(); Show(); });
                Candy.Caption(prev.transform, "<", 80, new Vector2(0.5f, 0.52f), new Vector2(140f, 140f));
                var next = Candy.Round(Root, Candy.Orange, null, 140f, new Vector2(0.6f, 0.55f), Vector2.zero, () => { _picker.Next(); Show(); });
                Candy.Caption(next.transform, ">", 80, new Vector2(0.5f, 0.52f), new Vector2(140f, 140f));
            }

            var card = Ui.Rect(Root, "Info", new Vector2(0.8f, single ? 0.56f : 0.64f), new Vector2(600f, 400f));
            Candy.Shell(card, Candy.White).raycastTarget = false;
            _name = Ui.Label(card, "", Th.Font(72), Th.Text, new Vector2(0.5f, 0.82f), new Vector2(520f, 100f), FontStyle.Bold);
            _species = Ui.Label(card, "", Th.Font(38), Th.SubtleText, new Vector2(0.5f, 0.62f), new Vector2(520f, 60f));
            _feature = Ui.Label(card, "", Th.Font(32), Th.SubtleText, new Vector2(0.5f, 0.32f), new Vector2(500f, 160f), FontStyle.Italic);

            _dots = new Image[single ? 0 : _picker.Count];
            // iri şeker çerçeveli küçük resimler (ekran genişliğine göre en çok 170): çocuk kolayca seçer
            var step = Mathf.Min(176f, (Width - 60f) / _picker.Count);
            var size = step - 14f;
            for (var i = 0; i < _dots.Length; i++)
            {
                var def = App.Data.ActivePets[i];
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

            Candy.Pill(Root, Candy.Green, T(single ? "pet.meet_button" : "pet.pick_button"), new Vector2(0.8f, single ? 0.24f : 0.3f), new Vector2(560f, 140f), Vector2.zero, AskConfirm, null, 52).gameObject.AddComponent<Pulse>();
            Show();
            if (Logic.App.FirstDay.Current(App.State, App.LocalNow, App.UtcNow) == Logic.App.FirstDayStep.Story) IntroFilm();
        }

        /// <summary>İlk açılış (Ö5 + F): giriş filmi. Bir kez gösterilir; Defter → Hikâye'den yeniden izlenir.</summary>
        private void IntroFilm()
        {
            var book = App.Data.Story;
            var intro = book != null ? book.Scenes.FirstOrDefault(s => s.Trigger == Logic.Story.StoryDirector.Intro) : null;
            UI.FilmPlayer.Play(App.Overlay.transform, Th, intro, Th.Band, App.State.PetName, T("story.skip"), T("story.go"), () =>
            {
                Logic.App.Onboarding.Done(App.State, Logic.App.Onboarding.Story);
                App.State.Story.IntroSeen = true; App.State.Story.Seen.Add(Logic.Story.StoryDirector.Intro);   // adada yeniden oynamasın
                App.Save();
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
                _dots[i].color = on ? Candy.Gold : Color.Lerp(Theme.Hex(App.Data.ActivePets[i].MainColor), Color.white, 0.45f);
            }
        }

        private void AskConfirm()
        {
            if (_confirm != null) return;
            var def = App.Data.Pet(_picker.Current);
            if (_picker.Count <= 1)
            {
                // tek arkadaş: soru sormadan tanışma (zıplar, ad ekranına geçer)
                App.Stage.Hop();
                PetChange.Choose(App.State, def.Id, App.Data);
                App.Save();
                App.Stage.Swiped = null;
                App.Route();
                return;
            }
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
            UI.FilmPlayer.Stop();
            if (App != null && App.Stage != null) { App.Stage.Swiped = null; App.Stage.SetPicture(null); }
        }
    }
}
