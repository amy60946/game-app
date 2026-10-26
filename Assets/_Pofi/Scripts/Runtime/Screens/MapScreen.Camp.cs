using System.Linq;
using Pofi.Logic.App;
using Pofi.Logic.Island;
using Pofi.UI;
using Pofi.World;
using UnityEngine;

namespace Pofi.Screens
{
    /// <summary>
    /// Kamp ateşini harla (kullanıcı GB18, 24 Ekim 2026): toplanan odun kamp ateşine atılır → XP. 2 odun bir harlama, günde en çok
    /// 3 (Logic/Island/CampfireRules). Ateşin yanında eylem düğmesi "Harla"; alev büyür, kıvılcım XP küreleri XP çubuğuna uçar.
    /// Rehberde kulübeden sonraki adım ("fire"): odun yoksa oklar kütüğe, varsa ateşe götürür.
    /// </summary>
    public sealed partial class MapScreen
    {
        private const float FireReach = 4.8f;   // ateşin çevresi kütük oturaklarla çevrili: çocuk 4–4,5 m'de durur
        private Vector2? _firePos;

        /// <summary>Kamp ateşinin yeri (pişmiş adanın süslerinden; yoksa null).</summary>
        private Vector2? FirePos
        {
            get
            {
                if (_firePos.HasValue) return _firePos;
                var p = _terrain.Baked?.Layout?.Props?.FirstOrDefault(x => x != null && x.Asset == "p_campfire");
                if (p != null) _firePos = new Vector2(p.X, p.Z);
                return _firePos;
            }
        }

        private void BuildCampfire()
        {
            if (Campfire.Instance != null) Campfire.Instance.SetHeat(CampfireRules.Heat(App.State.Campfire, App.UtcNow));
        }

        /// <summary>Eylem düğmesi: ateşin yanındaysa "Harla".</summary>
        private bool CampfireAction(Vector2 p, out System.Action act)
        {
            act = null;
            var f = FirePos;
            if (!f.HasValue || Vector2.Distance(p, f.Value) > FireReach) return false;
            act = StokeFire;
            return true;
        }

        private void StokeFire()
        {
            var f = FirePos;
            if (!f.HasValue) return;
            var st = App.State;
            var day = Day;
            switch (CampfireRules.CanStoke(st.Campfire, st.Gather, day))
            {
                case CampfireRules.Check.NeedWood: _toast.Say(T("fire.need_wood", CampfireRules.WoodPerStoke)); Audio.Sfx.Play(Audio.SfxKind.Fail); return;
                case CampfireRules.Check.DoneToday: _toast.Say(T("fire.done_today")); return;
            }
            if (!CampfireRules.Stoke(st.Campfire, st.Gather, day, App.UtcNow)) return;
            _world.Walker.Face(f.Value.x, f.Value.y);
            _world.Walker.Swing();
            if (Campfire.Instance != null)   // odunlar Okti'nin elinden ateşe uçar, alev taşar, kıvılcım + duman (zengin harlama)
                Campfire.Instance.StokeFx(_world.Walker.transform.position + Vector3.up * 1.0f, CampfireRules.Heat(st.Campfire, App.UtcNow), Ui.Icon("mat_wood"), App.Stage.Camera);
            Audio.Sfx.Play(Audio.SfxKind.Whoosh);
            Audio.Haptics.Medium();
            var at = _world.World(f.Value.x, f.Value.y) + Vector3.up * 1.2f;
            _xpFrom = at;   // XP küreleri ateşten çubuğa uçar
            var sp = App.Stage.Camera.WorldToScreenPoint(at);
            StarSparkles.Around(Root, new Vector2(sp.x / Mathf.Max(1f, Screen.width), sp.y / Mathf.Max(1f, Screen.height)), new Vector2(0.08f, 0.14f), 8, 31);
            App.Save();
            RefreshTracker();
            App.GrantXp(CampfireRules.Xp, Logic.Economy.XpSource.Achievement);
            App.RecordActivity("fire_stoked");
            _toast.Say(T("fire.stoked", CampfireRules.Xp));
        }

        /// <summary>Rehberin "fire" adımı: odun yetmiyorsa en yakın kütüğe, yetiyorsa ateşe.</summary>
        private Vector2? FireGuideWorld()
        {
            if (Gathering.Count(App.State.Gather, Gathering.Wood) < CampfireRules.WoodPerStoke)
            {
                var log = NearestNode(n => n.Kind == GatherKind.Log || n.Kind == GatherKind.BigLog);
                if (log != null) return new Vector2(log.X, log.Z);
            }
            return FirePos;
        }

        private Vector2 FireGuideScreen()
        {
            var w = FireGuideWorld();
            return w.HasValue ? (Vector2)App.Stage.Camera.WorldToScreenPoint(_world.World(w.Value.x, w.Value.y) + Vector3.up * 1.2f) : PetScreen();
        }
    }
}
