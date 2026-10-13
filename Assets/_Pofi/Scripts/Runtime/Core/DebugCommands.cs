using System;
using Pofi.Logic.App;
using Pofi.Logic.Economy;
using Pofi.Logic.Services.Mock;
using UnityEngine;

namespace Pofi.Core
{
    /// <summary>
    /// Otomatik test kancası (yalnızca sahte arka uçla): tarayıcıdan
    /// <c>unityInstance.SendMessage("Bootstrap", "PofiDebug", "login A1A1A1")</c> ile çağrılır. Gerçek sunucuda kapalıdır.
    /// Komutlar: login KOD · pick pet_XX · name İSİM · open Sayfa · xp N · approve · minigame ID · state
    /// </summary>
    public static class DebugCommands
    {
        public static async void Run(GameBootstrap app, string line)
        {
            if (!(app.Auth is MockAuthService)) return;
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
                    case "pick":
                        PetChange.Choose(app.State, arg, app.Data);
                        app.Save(); app.Route();
                        break;
                    case "name":
                        app.State.PetName = arg;
                        app.Starter.GiveOnce(app.State, app.Data);
                        app.Save(); app.Route();
                        break;
                    case "open":
                        app.Open((AppPage)Enum.Parse(typeof(AppPage), arg));
                        break;
                    case "minigame":
                        app.OpenMiniGame(arg);
                        break;
                    case "xp":
                        app.GrantXp(int.Parse(arg), XpSource.Achievement);
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
