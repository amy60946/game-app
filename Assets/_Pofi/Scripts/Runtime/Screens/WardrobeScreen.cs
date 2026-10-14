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

        private RectTransform _list;
        private Button[] _tabs;
        private SpeechBubble _bubble;
        private PetSpeciesDef _pet;

        protected override void Build()
        {
            _pet = App.Data.Pet(App.State.PetId);
            App.Stage.AllowDrag = true;
            PetCamera(0.28f, 0.16f, 0.8f);   // yatay: pet solda, dolap paneli sağda
            App.Stage.ShowPet(_pet, App.Growth, App.State.Inventory.Equipped.Values);

            var title = Ui.Label(Root, T("wardrobe.title"), Th.Font(64), Color.white, new Vector2(0.28f, 1f), new Vector2(800f, 120f), FontStyle.Bold);
            title.rectTransform.pivot = new Vector2(0.5f, 1f);
            title.rectTransform.anchoredPosition = new Vector2(0f, -24f);
            title.gameObject.AddComponent<Shadow>().effectDistance = new Vector2(0f, -5f);
            _bubble = Bubble(new Vector2(0.28f, 0.86f));

            var panel = Ui.Rect(Root, "Panel", new Vector2(1f, 0f), new Vector2(1040f, 1080f - NavHeight - 60f));
            panel.pivot = new Vector2(1f, 0f);
            panel.anchoredPosition = new Vector2(-36f, NavHeight + 20f);
            Ui.Panel(panel, Th.Panel, Th.Radius);

            _tabs = new Button[Slot.All.Length];
            for (var i = 0; i < Slot.All.Length; i++)
            {
                var slot = Slot.All[i];
                _tabs[i] = Ui.Button(panel, Th, T("wardrobe.slot." + slot), new Vector2(0.1f + i * 0.2f, 0.9f), new Vector2(190f, 88f),
                    () => { _slot = slot; Fill(); }, slot == _slot, default, 34, false);
            }
            var area = Ui.Area(panel, "ListArea", Vector2.zero, new Vector2(1f, 0.8f));
            _list = Ui.ScrollList(area, Vector2.zero, Vector2.one, 20f, 3, new Vector2(310f, 190f));

            NavBar(AppPage.Wardrobe);
            Fill();
        }

        private void Fill()
        {
            for (var i = 0; i < Slot.All.Length; i++)
            {
                var on = Slot.All[i] == _slot;
                _tabs[i].targetGraphic.color = on ? Th.Primary : Th.Secondary;
                _tabs[i].GetComponentInChildren<Text>().color = on ? Th.PrimaryText : Th.SecondaryText;
            }
            Ui.Clear(_list);
            var inv = App.State.Inventory;
            var owned = inv.Owned.Select(App.Data.Item).Where(i => i != null && i.IsWearable && i.Slot == _slot).ToList();
            if (owned.Count == 0)
            {
                var go = new GameObject("Empty", typeof(RectTransform));
                go.transform.SetParent(_list, false);
                var b = go.AddComponent<Button>();
                var img = Ui.Panel((RectTransform)go.transform, Th.Secondary, Th.Radius);
                b.targetGraphic = img;
                b.onClick.AddListener(() => App.Open(AppPage.Shop));
                Ui.Label(go.transform, T("nav.shop"), Th.Font(40), Th.SecondaryText, new Vector2(0.5f, 0.5f), new Vector2(300f, 180f), FontStyle.Bold);
                _bubble.Say(T("wardrobe.empty"));
                return;
            }
            inv.Equipped.TryGetValue(_slot, out var equipped);
            foreach (var item in owned) Chip(item, item.Id == equipped);
        }

        private void Chip(ItemDef item, bool on)
        {
            var fit = CosmeticFit.Evaluate(_pet, item);
            var go = new GameObject(item.Id, typeof(RectTransform));
            go.transform.SetParent(_list, false);
            var col = CosmeticModels.ColorOf(item.Id);
            if (!fit.Allowed) col = Color.Lerp(col, Color.gray, 0.7f);
            var img = Ui.Panel((RectTransform)go.transform, on ? Th.Primary : Color.white, Th.Radius);
            var dot = Ui.Rect(go.transform, "Swatch", new Vector2(0.5f, 0.66f), new Vector2(90f, 90f));
            Ui.Panel(dot, col, 45f).raycastTarget = false;
            Ui.Label(go.transform, item.Name, Th.Font(30), on ? Th.PrimaryText : Th.Text, new Vector2(0.5f, 0.2f), new Vector2(300f, 70f), FontStyle.Bold);
            var b = go.AddComponent<Button>();
            b.targetGraphic = img;
            b.onClick.AddListener(() => Toggle(item, on));
            go.AddComponent<PressBounce>();
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
