using System.Collections;
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
    /// Pet seçme / tanışma ekranı. Arkada kumsal (<see cref="World.Stage.SetBeach"/>: tepecikli kum, ıslak kum şeridi, köpük izi,
    /// denizde parıltı), önde canlı 3B pet (parmakla çevrilir). Görünüş oyun içi pencere dilinde (24 Ekim 2026): başlık mavi
    /// kurdelede, bilgi krem kartta (adı kartın kurdelesinde), tek yeşil ana düğme. Tek pet (Okti) varken ok, küçük resim yok.
    /// Ad sorulmaz (kullanıcı: "Ad hep Okti kalsın"): "Tanışalım!" ile ad Okti olur, hoş geldin hediyesi verilir, ada açılır.
    /// Birden çok pet olursa karusel (oklar, kaydırma, küçük resimler) geri gelir. İlk açılışta önce giriş filmi (F) oynar.
    /// </summary>
    public sealed class PetSelectScreen : ScreenBase
    {
        private static readonly Color Ink = new Color(0.42f, 0.25f, 0.06f), InkSoft = new Color(0.6f, 0.42f, 0.19f);

        private PetPicker _picker;
        private RectTransform _card, _nameRibbon;
        private Text _species, _feature;
        private Image[] _dots;
        private RectTransform _confirm;
        private bool _going;

        protected override void Build()
        {
            _picker = new PetPicker(App.Data.ActivePets.Select(p => p.Id).ToList());
            if (!string.IsNullOrEmpty(App.State.PetId)) _picker.JumpTo(App.State.PetId);
            App.Stage.AllowDrag = true;
            var single = _picker.Count <= 1;
            App.Stage.SetBeach(true);   // kumsal sahnesi (Meshy görseli + kodla zenginleştirildi, karaktersiz)
            PetCamera(0.36f, 0.16f, 0.82f);   // yatay: pet sol-ortada kumda, bilgi kartı sağda
            if (!single) App.Stage.Swiped = dir => { if (dir < 0) _picker.Next(); else _picker.Prev(); Show(); };

            // başlık: oyundaki pencere başlıkları gibi mavi kurdele; altında kısa ipucu. Petin çevresinde parıldayan yıldızlar
            Candy.Ribbon(Root, T(single ? "pet.meet_title" : "pet.pick_title"), new Vector2(0.5f, 1f), new Vector2(0f, -84f), 130f, 54);
            Candy.Caption(Root, T(single ? "pet.meet_hint" : "pet.pick_hint"), 34, new Vector2(0.5f, 0.835f), new Vector2(1300f, 50f));
            StarSparkles.Around(Root, new Vector2(0.36f, 0.5f), new Vector2(0.16f, 0.26f), 9, 3);

            if (!single)
            {
                var prev = Candy.Round(Root, Candy.Orange, null, 140f, new Vector2(0.12f, 0.55f), Vector2.zero, () => { _picker.Prev(); Show(); });
                Candy.Caption(prev.transform, "<", 80, new Vector2(0.5f, 0.52f), new Vector2(140f, 140f));
                var next = Candy.Round(Root, Candy.Orange, null, 140f, new Vector2(0.6f, 0.55f), Vector2.zero, () => { _picker.Next(); Show(); });
                Candy.Caption(next.transform, ">", 80, new Vector2(0.5f, 0.52f), new Vector2(140f, 140f));
            }

            // bilgi kartı: krem pencere kartı, adı üst kenardaki kurdelede; tür ve tek cümle
            _card = Ui.Rect(Root, "Info", new Vector2(0.8f, single ? 0.53f : 0.6f), new Vector2(620f, 380f));
            Candy.Shell(_card, new Color(1f, 0.99f, 0.96f));   // görünmez dokunma yüzeyi: karta dokunuş peti çevirmez
            _species = Ui.Label(_card, "", Th.Font(34), InkSoft, new Vector2(0.5f, 0.72f), new Vector2(540f, 56f), FontStyle.Bold);
            _feature = Ui.Label(_card, "", Th.Font(40), Ink, new Vector2(0.5f, 0.38f), new Vector2(530f, 170f), FontStyle.Bold);
            _feature.resizeTextForBestFit = true; _feature.resizeTextMinSize = 24; _feature.resizeTextMaxSize = Th.Font(40);   // uzun yazı kutudan taşmasın
            _feature.lineSpacing = 0.92f;

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

            // tek yeşil ana düğme (oyundaki "Al", "Yaptım" ile aynı)
            Candy.Pill(Root, Candy.Green, T(single ? "pet.meet_button" : "pet.pick_button"), new Vector2(0.8f, single ? 0.2f : 0.3f), new Vector2(540f, 136f), Vector2.zero, AskConfirm, null, 54).gameObject.AddComponent<Pulse>();
            Show();
            if (Logic.App.FirstDay.Current(App.State, App.LocalNow, App.UtcNow) == Logic.App.FirstDayStep.Story) IntroFilm();
        }

        /// <summary>İlk açılış (Ö5 + F): giriş filmi. Bir kez gösterilir; Defter → Hikâye'den yeniden izlenir.</summary>
        private void IntroFilm()
        {
            var book = App.Data.Story;
            var intro = book != null ? book.Scenes.FirstOrDefault(s => s.Trigger == Logic.Story.StoryDirector.Intro) : null;
            UI.FilmPlayer.Play(App.Overlay.transform, Th, intro, Th.Band, PetRoster.Name, T("story.skip"), T("story.go"), () =>
            {
                Logic.App.Onboarding.Done(App.State, Logic.App.Onboarding.Story);
                App.State.Story.IntroSeen = true; App.State.Story.Seen.Add(Logic.Story.StoryDirector.Intro);   // adada yeniden oynamasın
                App.Save();
            });
        }

        private void Show()
        {
            var def = App.Data.Pet(_picker.Current);
            App.Stage.ShowPet(def, GrowthStage.Yavru);   // herkes çocuk Okti ile başlar (Sv 5 ergen, Sv 10 yetişkin)
            // ad kurdelesi yazıya göre uzar: pet değişince yeniden kurulur
            if (_nameRibbon != null) Destroy(_nameRibbon.gameObject);
            _nameRibbon = (RectTransform)ModalTitle(_card, def.Name).transform.parent;
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
            if (_confirm != null || _going) return;
            var def = App.Data.Pet(_picker.Current);
            if (_picker.Count <= 1)
            {
                // tek arkadaş: soru sormadan tanışma; ad Okti, hoş geldin hediyesi, Okti sevinir ve ada açılır (ad ekranı yok)
                Meet(def.Id);
                return;
            }
            App.Stage.AllowDrag = false;
            App.Stage.Hop();
            RectTransform box;
            _confirm = Modal(620f, out box, true, CloseConfirm);
            ModalTitle(box, def.Name);
            ModalClose(box, CloseConfirm);
            Ui.Label(box, T("pet.pick_confirm", TurkishSuffix.Accusative(def.Name)), 52, Ink, new Vector2(0.5f, 0.68f), new Vector2(840f, 180f), FontStyle.Bold);
            Candy.Pill(box, Candy.Green, T("pet.pick_yes"), new Vector2(0.5f, 0.36f), new Vector2(520f, 130f), Vector2.zero, () => Meet(def.Id), null, 52);
            Candy.Pill(box, new Color(1f, 0.96f, 0.86f), T("pet.pick_no"), new Vector2(0.5f, 0.14f), new Vector2(520f, 104f), Vector2.zero, CloseConfirm, null, 40);
        }

        private void CloseConfirm()
        {
            if (_confirm == null) return;
            Destroy(_confirm.gameObject);
            _confirm = null;
            App.Stage.AllowDrag = true;
        }

        /// <summary>Seçim tamam: ad <see cref="PetRoster.Name"/>, hediye bir kez; kısa sevinçten sonra ada.</summary>
        private void Meet(string petId)
        {
            if (_going) return;
            _going = true;
            PetChange.Choose(App.State, petId, App.Data, App.Starter);
            App.Save();
            App.Stage.Swiped = null;
            App.Stage.AllowDrag = false;
            App.Stage.Hop();
            StartCoroutine(GoAfter(0.5f));
        }

        private IEnumerator GoAfter(float seconds)
        {
            yield return new WaitForSecondsRealtime(seconds);
            App.Route();
        }

        private void OnDestroy()
        {
            UI.FilmPlayer.Stop();
        }
    }
}
