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
            PetCamera(0.4f, 0.06f, 0.82f, World.PetModels.RealHeight * World.PetModels.StageScale(Logic.Progression.GrowthStage.Yetiskin));
            App.Stage.ShowPet(_pet, App.Growth, App.State.Inventory.Equipped.Values);

            Candy.Caption(Root, T("wardrobe.title"), 64, new Vector2(0f, 1f), new Vector2(500f, 90f), new Vector2(290f, -66f));
            _bubble = Bubble(new Vector2(0.4f, 0.92f));

            // petin üzerindeki yuva noktaları (kemiklerin ekran konumunu izler)
            for (var i = 0; i < Slot.All.Length; i++)
            {
                var slot = Slot.All[i];
                var b = Candy.Round(Root, Candy.White, SlotIcons[i], 104f, Vector2.zero, Vector2.zero, () => { _slot = slot; Fill(); });
                _spots[i] = (RectTransform)b.transform;
            }
            _items = Ui.Fill(Root, "Items");
            NavBar(AppPage.Wardrobe);
            Fill();
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
                _spots[i].GetComponent<Image>().color = on ? Candy.Orange : Candy.White;
                _spots[i].localScale = Vector3.one * (on ? 1.15f : 1f);
            }
            Ui.Clear(_items);
            inv.Equipped.TryGetValue(_slot, out var equipped);
            var owned = inv.Owned.Select(App.Data.Item).Where(i => i != null && i.IsWearable && i.Slot == _slot).ToList();
            // sahip olunmayanlar soluk ve fiyatlı: dokununca dükkân
            var more = App.Data.Items.Where(i => i.IsWearable && i.Slot == _slot && !i.Premium && !inv.Owns(i.Id) && i.Level <= App.Level)
                .OrderBy(i => i.Price).Take(Mathf.Max(0, 6 - owned.Count)).ToList();
            var all = owned.Concat(more).Take(6).ToList();
            for (var n = 0; n < all.Count; n++)
            {
                var item = all[n];
                var have = owned.Contains(item);
                var on = item.Id == equipped;
                var pos = new Vector2(-250f - (n % 2) * 190f, 300f - n * 120f);
                var b = Candy.Round(_items, on ? new Color(1f, 0.93f, 0.6f) : Candy.White, item.Id, on ? 170f : 150f, new Vector2(1f, 0.5f), pos,
                    have ? (System.Action)(() => Toggle(item, on)) : () => App.Open(AppPage.Shop));
                var fit = CosmeticFit.Evaluate(_pet, item);
                if (!have || !fit.Allowed) foreach (var img in b.GetComponentsInChildren<Image>()) img.color *= new Color(1f, 1f, 1f, 0.5f);
                if (!have) Candy.Badge(b.transform, "ui_coin", item.Price.ToString(), new Vector2(0.5f, 0f), new Vector2(0.5f, 1f), new Vector2(0f, 6f), 52f, 150f);
            }
            if (owned.Count == 0) _bubble.Say(T("wardrobe.empty"));
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
