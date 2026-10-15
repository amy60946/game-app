using System.Linq;
using Pofi.Logic.App;
using Pofi.Logic.Core;
using Pofi.Logic.Cosmetics;
using Pofi.Logic.Data;
using Pofi.UI;
using Pofi.World;
using UnityEngine;
using UnityEngine.UI;

namespace Pofi.Screens
{
    /// <summary>
    /// Dolap / giydirme (FR-SHOP-3, FR-PET-7): yuva sekmeleri, sahip olunan eşyalar. Dokun → giy, tekrar dokun → çıkar.
    /// Pete uymayan eşya gri ve nedenli ("Benli'nin kanatları…"). Uyum kuralları <see cref="CosmeticFit"/>.
    /// </summary>
    public sealed class WardrobeScreen : ScreenBase
    {
        private static string _slot = Slot.Head;



        private SpeechBubble _bubble;
        private PetSpeciesDef _pet;

        private static readonly string[] SlotIcons = { "hat_straw", "glasses_round", "shirt_stripes", "backpack_small", "hand_flag" };
        private static readonly string[] SlotBones = { "head_end", "headfront", "Spine02", "Spine01", "RightHand" };
        private static readonly Vector2[] SlotNudge = { new Vector2(0f, 90f), new Vector2(190f, 10f), new Vector2(200f, -40f), new Vector2(-210f, 0f), new Vector2(-150f, -60f) };
        private readonly RectTransform[] _spots = new RectTransform[5];
        private RectTransform _items;

        protected override void Build()
        {
            _pet = App.Data.Pet(App.State.PetId);
            App.Stage.AllowDrag = false;
            PetCamera(0.4f, 0.1f, 0.86f, World.PetModels.RealHeight * World.PetModels.StageScale(App.Growth));   // pet ekranın ortasında ve büyük (büyüme evresine göre)
            App.Stage.ShowPet(_pet, App.Growth, App.State.Inventory.Equipped.Values);

            Candy.Caption(Root, T("wardrobe.title"), 64, new Vector2(0f, 1f), new Vector2(500f, 90f), new Vector2(290f, -66f));
            _bubble = Bubble(new Vector2(0.4f, 0.92f));

            // petin üzerindeki yuva noktaları (kemiklerin ekran konumunu izler)
            for (var i = 0; i < Slot.All.Length; i++)
            {
                var slot = Slot.All[i];
                var b = Candy.Round(Root, Candy.White, SlotIcons[i], 136f, Vector2.zero, Vector2.zero, () => { _slot = slot; SpotsTipDone(); Fill(); });
                _spots[i] = (RectTransform)b.transform;
            }
            _items = Ui.Fill(Root, "Items");
            NavBar(AppPage.Wardrobe);
            Fill();
            if (Onboarding.Pending(App.State, Onboarding.WardrobeSpots))
                _coach = Coach.Show(Root, Onboarding.WardrobeSpots, T("tip.wardrobe_spots"), TipGesture.Tap,
                    () => RectTransformUtility.WorldToScreenPoint(null, _spots[0].position));
        }

        private Coach _coach;

        private void SpotsTipDone()
        {
            if (!Onboarding.Pending(App.State, Onboarding.WardrobeSpots)) return;
            Onboarding.Done(App.State, Onboarding.WardrobeSpots); App.Save();
            if (_coach != null) { _coach.Done(); _coach = null; }
        }

        private void LateUpdate()
        {
            var pet = App.Stage.Pet;
            if (pet == null) return;
            var cam = App.Stage.Camera;
            var k = Root.rect.width / Mathf.Max(1f, Screen.width);
            var bounds = World.RealAssets.WorldBounds(pet);
            for (var i = 0; i < _spots.Length; i++)
            {
                var bone = Find(pet, SlotBones[i]);
                Vector3 w;
                if (bone != null) w = bone.position;
                else w = bounds.center + Vector3.up * bounds.extents.y * (i == 0 ? 0.9f : i == 1 ? 0.5f : i == 2 ? -0.1f : i == 3 ? 0f : -0.2f);
                var sp = cam.WorldToScreenPoint(w);
                _spots[i].anchoredPosition = new Vector2(sp.x * k, sp.y * k) + SlotNudge[i];
            }
        }

        private static Transform Find(Transform t, string name)
        {
            if (t.name == name) return t;
            for (var i = 0; i < t.childCount; i++) { var r = Find(t.GetChild(i), name); if (r != null) return r; }
            return null;
        }

        private void Fill()
        {
            var inv = App.State.Inventory;
            for (var i = 0; i < Slot.All.Length; i++)
            {
                var on = Slot.All[i] == _slot;
                _spots[i].GetComponent<Button>().targetGraphic.color = on ? Candy.Orange : Candy.White;
                _spots[i].localScale = Vector3.one * (on ? 1.15f : 1f);
            }
            Ui.Clear(_items);
            inv.Equipped.TryGetValue(_slot, out var equipped);
            var owned = inv.Owned.Select(App.Data.Item).Where(i => i != null && i.IsWearable && i.Slot == _slot).ToList();
            // sahip olunmayanlar soluk ve fiyatlı: dokununca dükkân
            // düşük seviyede de dolap boş görünmesin: seviyesi gelmeyenler kilitli gösterilir (önce açık olanlar)
            var more = App.Data.Items.Where(i => i.IsWearable && i.Slot == _slot && !i.Premium && !inv.Owns(i.Id))
                .OrderBy(i => i.Level > App.Level ? 1 : 0).ThenBy(i => i.Price).Take(Mathf.Max(0, 6 - owned.Count)).ToList();
            var all = owned.Concat(more).Take(6).ToList();
            for (var n = 0; n < all.Count; n++)
            {
                var item = all[n];
                var have = owned.Contains(item);
                var on = item.Id == equipped;
                // iri kıyafet baloncukları: sağda 2 sütun x 3 sıra
                var pos = new Vector2(-170f - (n % 2) * 240f, 250f - (n / 2) * 230f);
                var locked = !have && item.Level > App.Level;
                var b = Candy.Round(_items, on ? new Color(1f, 0.93f, 0.6f) : Candy.White, item.Id, on ? 225f : 205f, new Vector2(1f, 0.5f), pos,
                    have ? (System.Action)(() => Toggle(item, on))
                    : locked ? () => _bubble.Say(T("wardrobe.locked", item.Level)) : (System.Action)(() => App.Open(AppPage.Shop)));
                if (on) Ui.IconImage(b.transform, "ui_star", new Vector2(0.86f, 0.86f), 70f);   // takılı işareti
                var fit = CosmeticFit.Evaluate(_pet, item);
                if (!have || !fit.Allowed) foreach (var img in b.GetComponentsInChildren<Image>()) img.color *= new Color(1f, 1f, 1f, 0.5f);
                if (locked) Candy.Badge(b.transform, "ui_star", T("wardrobe.level", item.Level), new Vector2(0.5f, 0f), new Vector2(0.5f, 1f), new Vector2(0f, 6f), 52f, 150f);
                else if (!have) Candy.Badge(b.transform, "ui_coin", item.Price.ToString(), new Vector2(0.5f, 0f), new Vector2(0.5f, 1f), new Vector2(0f, 6f), 52f, 150f);
            }
            if (owned.Count == 0) _bubble.Say(T("wardrobe.empty"));
            // takılı eşyayı çıkar (açık düğme; eşyaya tekrar dokunmak da çıkarır)
            if (!string.IsNullOrEmpty(equipped))
            {
                var eq = App.Data.Item(equipped);
                if (eq != null) Candy.Pill(_items, Candy.Pink, T("wardrobe.remove"), new Vector2(1f, 0f), new Vector2(300f, 110f), new Vector2(-290f, 90f), () => Toggle(eq, true));
            }
        }

        private void Toggle(ItemDef item, bool on)
        {
            var inv = App.State.Inventory;
            if (on)
            {
                inv.Unequip(item.Slot);
                _bubble.Say(T("wardrobe.removed"));
            }
            else
            {
                var fit = inv.TryEquip(_pet, item);
                if (!fit.Allowed)
                {
                    _bubble.Say(T(fit.ReasonKey, TurkishSuffix.Genitive(App.State.PetName)), 4.5f);
                    return;
                }
                App.Stage.Hop();
                _bubble.Say(T("wardrobe.looks_good"));
            }
            App.Save();
            App.Stage.SetCosmetics(inv.Equipped.Values);
            Fill();
        }
    }
}
