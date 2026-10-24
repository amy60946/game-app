using System;
using Pofi.Logic.App;
using Pofi.Logic.Economy;
using Pofi.Logic.Services.Mock;
using UnityEngine;
using Object = UnityEngine.Object;

namespace Pofi.Core
{
    /// <summary>
    /// Otomatik test kancası (yalnızca sahte arka uçla): tarayıcıdan
    /// <c>unityInstance.SendMessage("Bootstrap", "PofiDebug", "login A1A1A1")</c> ile çağrılır. Gerçek sunucuda kapalıdır.
    /// Komutlar: login KOD · pick pet_XX · name (ad hep Okti; eski betikler için) · open Sayfa · xp N · approve · minigame ID · tap Etiket · dismiss · maptoggle · walk X Z · tp X Z YAW · hud 0|1 · region ID · wear ID… · place ID… · gather [near|site|give|state] · audio · petpos
    /// </summary>
    public static class DebugCommands
    {
        public static async void Run(GameBootstrap app, string line)
        {
            if (!app.Router.DemoCodesEnabled || app.OnServer) return;   // gerçek sunucu oturumunda kapalı
            var parts = (line ?? "").Trim().Split(new[] { ' ' }, 2);
            var cmd = parts[0];
            var arg = parts.Length > 1 ? parts[1] : "";
            try
            {
                switch (cmd)
                {
                    case "login":
                        var r = await app.Auth.SignInWithCodeAsync(arg);
                        if (r.Ok) app.OnSignedIn(r.Session);
                        break;
                    case "pick":        // ad Okti olur, hoş geldin hediyesi verilir (ad ekranı yok)
                        PetChange.Choose(app.State, arg, app.Data, app.Starter);
                        app.Save(); app.Route();
                        break;
                    case "name":        // eski çekim betikleri için: ad hep Okti (24 Ekim 2026), verilen ad yok sayılır
                        PetRoster.FixName(app.State, app.Starter, app.Data);
                        app.Save(); app.Route();
                        break;
                    case "open":
                        app.Open((AppPage)Enum.Parse(typeof(AppPage), arg));
                        break;
                    case "minigame":
                        app.OpenMiniGame(arg);
                        break;
                    case "maptoggle":   // ada: yürü ↔ kuşbakışı
                        Object.FindAnyObjectByType<Screens.MapScreen>()?.DebugToggle();
                        break;
                    case "walk":        // ada: "walk X Z" (metre)
                        var xz = arg.Split(' ');
                        Object.FindAnyObjectByType<Screens.MapScreen>()?.DebugWalk(
                            float.Parse(xz[0], System.Globalization.CultureInfo.InvariantCulture), float.Parse(xz[1], System.Globalization.CultureInfo.InvariantCulture));
                        break;
                    case "tp":          // ada: "tp X Z YAW" (metre, derece) — görsel kontrol çekimleri
                        var tp = arg.Split(' ');
                        var inv = System.Globalization.CultureInfo.InvariantCulture;
                        Object.FindAnyObjectByType<Screens.MapScreen>()?.DebugTeleport(float.Parse(tp[0], inv), float.Parse(tp[1], inv), tp.Length > 2 ? float.Parse(tp[2], inv) : 0f);
                        break;
                    case "hud":         // görsel karşılaştırma çekimleri: arayüz katmanlarını gizle/göster
                        app.Canvas.enabled = arg != "0"; app.Overlay.enabled = arg != "0";
                        break;
                    case "season":      // görsel deneme: autumn | winter | spring | summer | holiday | auto (adaya yeniden girince)
                        World.SeasonLook.Override = arg == "auto" ? null : arg;
                        break;
                    case "showall":     // görsel karşılaştırma: kilitli bölgeler sissiz/boyasız (ada kurulmadan önce verilir)
                        World.MapWorld.DebugShowAll = arg != "0";
                        break;
                    case "cos":         // son giydirmenin ölçüleri: pet ağı, yüzün önü, eşyaların alt/üst/genişlik (pet boyuna oran)
                        Debug.Log("[PofiDebug] cos " + World.CosmeticModels.Describe());
                        break;
                    case "wear":        // test: eşyayı ver ve giydir ("wear hat_straw glasses_round …")
                        foreach (var id in arg.Split(' '))
                        {
                            var it = app.Data.Item(id);
                            if (it == null) continue;
                            if (!app.State.Inventory.Owns(id)) app.State.Inventory.Add(it);
                            if (it.IsWearable) app.State.Inventory.TryEquip(app.Data.Pet(app.State.PetId), it);
                        }
                        app.Save(); app.Route();
                        break;
                    case "place":       // test: ev eşyasını ver ve evde ilk boş kareye koy
                        foreach (var id in arg.Split(' '))
                        {
                            var it = app.Data.Item(id);
                            if (it != null && !app.State.Inventory.Owns(id)) app.State.Inventory.Add(it);
                        }
                        var exp = app.Levels.IsUnlocked("home_expansion", app.Level);
                        var (hw, hh) = Logic.Home.HomeLayout.Size(exp);
                        foreach (var it in Logic.Home.HomeLayout.Unplaced(app.State, app.Data))
                        {
                            var done = false;
                            for (var yy = hh - 1; yy >= 0 && !done; yy--)
                            for (var xx = 0; xx < hw && !done; xx++)
                                done = Logic.Home.HomeLayout.Place(app.State, it, xx, yy, exp) == Logic.Home.PlaceResult.Ok;
                        }
                        app.Save(); app.Route();
                        break;
                    case "region":      // ada: bölgeye gir
                        Object.FindAnyObjectByType<Screens.MapScreen>()?.EnterById(arg);
                        break;
                    case "xp":
                        app.GrantXp(int.Parse(arg), XpSource.Achievement);
                        break;
                    case "cam":         // kamera denemesi: cam <uzaklık çarpanı> <en az eğim°> <görüş eki°> <bakış yükselmesi m>
                        {
                            var c = arg.Split(' '); var ci = System.Globalization.CultureInfo.InvariantCulture;
                            Screens.MapScreen.CamDistMul = float.Parse(c[0], ci);
                            Screens.MapScreen.CamMinPitch = c.Length > 1 ? float.Parse(c[1], ci) : 0f;
                            Screens.MapScreen.CamFovAdd = c.Length > 2 ? float.Parse(c[2], ci) : 0f;
                            Screens.MapScreen.CamLookUp = c.Length > 3 ? float.Parse(c[3], ci) : 0f;
                        }
                        break;
                    case "news":        // Mavi'nin yeni görev haberi denemesi
                        Object.FindAnyObjectByType<Screens.MapScreen>()?.MaviNews(app.Loc.Get("mavi.news_many", 2));
                        break;
                    case "grow":        // büyüme sahnesi denemesi (kayıt değişmez): grow genc | grow yetiskin
                        Object.FindAnyObjectByType<Screens.MapScreen>()?.PlayGrowUp(arg == "yetiskin" ? Logic.Progression.GrowthStage.Yetiskin : Logic.Progression.GrowthStage.Genc, null);
                        break;
                    case "tap":
                        // Etiketi verilen metne eşit olan ilk etkin düğmeye bas (ör. "tap Başla")
                        foreach (var b in Object.FindObjectsByType<UnityEngine.UI.Button>(FindObjectsSortMode.None))
                        {
                            var t = b.GetComponentInChildren<UnityEngine.UI.Text>();
                            if (b.isActiveAndEnabled && b.interactable && t != null && t.text == arg) { b.onClick.Invoke(); break; }
                        }
                        break;
                    case "gather":      // ada aksiyonları: gather [near|site|give|state] (boş: eylem düğmesine bas)
                        Debug.Log("[PofiDebug] gather " + Object.FindAnyObjectByType<Screens.MapScreen>()?.DebugGather(arg));
                        break;
                    case "audio":       // müzik durumu, adım sesi ve titreşim sayısı
                        Debug.Log($"[PofiDebug] audio {Audio.Music.Describe()} adım={Audio.Sfx.Steps} titreşim={Audio.Haptics.Count}");
                        break;
                    case "surprise":    // test: "surprise N" — N. sürprizin yanına ışınlan; liste günlüğe
                        Debug.Log("[PofiDebug] surprise " + Object.FindAnyObjectByType<Screens.MapScreen>()?.DebugSurprise(int.Parse(string.IsNullOrEmpty(arg) ? "0" : arg)));
                        break;
                    case "pettap":      // test: pete dokun (A1)
                        Debug.Log("[PofiDebug] pettap " + Object.FindAnyObjectByType<Screens.MapScreen>()?.DebugPetTap());
                        break;
                    case "mailbox":     // test: posta kutusunun önüne ışınlan
                        Object.FindAnyObjectByType<Screens.MapScreen>()?.DebugMailbox();
                        break;
                    case "petpos":      // adadaki petin ekran konumu (piksel, sol alt köken) — gerçek dokunma testi için
                        Debug.Log("[PofiDebug] petpos " + Object.FindAnyObjectByType<Screens.MapScreen>()?.DebugPetScreen());
                        break;
                    case "voice":       // sesli okuma: kayıt sayısı, açık mı, son okunan; "voice on|off" aç/kapa
                        if (arg == "on" || arg == "off") Audio.Voice.SetEnabled(arg == "on");
                        Debug.Log("[PofiDebug] voice " + Audio.Voice.Describe() + " hoparlör=" + Object.FindObjectsByType<UI.VoiceButton>(FindObjectsSortMode.None).Length);
                        break;
                    case "lp":          // E4 uzun bas: sayaçlar; "lp <metin>" o yazılı düğmenin bilgisini açar
                        var lps = Object.FindObjectsByType<UI.LongPressInfo>(FindObjectsSortMode.None);
                        if (!string.IsNullOrEmpty(arg))
                            foreach (var l in lps)
                            {
                                var lt = l.GetComponentInChildren<UnityEngine.UI.Text>();
                                if (lt != null && lt.text == arg) { l.DebugShow(); break; }
                            }
                        Debug.Log($"[PofiDebug] lp adet={lps.Length} basış={UI.LongPressInfo.Downs} açılış={UI.LongPressInfo.Shows} basılı={string.Join(",", System.Linq.Enumerable.Select(System.Linq.Enumerable.Where(lps, l => l.Pressed), l => l.name))}");
                        break;
                    case "dismiss":
                        for (var i = app.Overlay.transform.childCount - 1; i >= 0; i--)
                        {
                            var c = app.Overlay.transform.GetChild(i);
                            if (c.name == "LevelUp") Object.Destroy(c.gameObject);
                        }
                        break;
                    case "approve":
                        foreach (var t in app.State.Tasks.Tasks)
                            if (t.Status == Logic.Tasks.ChildTaskStatus.Assigned) app.State.Tasks.Mark(t.Key, Logic.Tasks.ChildTaskStatus.ChildDone, app.LocalNow, app.UtcNow);
                        await app.SyncNow();
                        DemoParent.ApproveAll(app.Backend);
                        await app.SyncNow();
                        break;
                }
                Debug.Log($"[PofiDebug] ok {cmd} | screen={AppFlow.Decide(app.Session, app.State)} page={app.Page} level={app.Level} coins={app.State?.Wallet.Available}");
            }
            catch (Exception e)
            {
                Debug.Log("[PofiDebug] error " + cmd + ": " + e.Message);
            }
        }
    }
}
