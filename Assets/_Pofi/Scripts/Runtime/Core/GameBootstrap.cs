using System;
using System.Threading.Tasks;
using Pofi.Logic.App;
using Pofi.Logic.Core;
using Pofi.Logic.Data;
using Pofi.Logic.Economy;
using Pofi.Logic.Island;
using Pofi.Logic.Pet;
using Pofi.Logic.Progression;
using Pofi.Logic.Services;
using Pofi.Logic.Services.Mock;
using Pofi.Logic.State;
using Pofi.Screens;
using Pofi.UI;
using Pofi.World;
using UnityEngine;

namespace Pofi.Core
{
    /// <summary>
    /// Açılış sahnesindeki tek bileşen ve uygulamanın kökü: veriyi yükler, servisleri kurar,
    /// 3B sahneyi ve arayüzü koddan oluşturur, <see cref="AppFlow"/> kararına göre ekran değiştirir.
    /// Sahne dosyası düzenlenmez (CLAUDE.md "kod olarak proje").
    /// </summary>
    public sealed class GameBootstrap : MonoBehaviour
    {
        public static EventBus Events { get; private set; }

        public GameData Data { get; private set; }
        public Localization Loc { get; private set; }
        public PetNameRules NameRules { get; private set; }
        public StarterKit Starter { get; private set; }
        public LevelTable Levels { get; private set; }
        public IslandMap Map { get; private set; }

        /// <summary>Açık mini oyunun kimliği (coconut, help_pet, swim, surf, ski).</summary>
        public string MiniGameId { get; private set; }
        public StatDecayConfig Decay { get; } = StatDecayConfig.Default;
        public IAuthService Auth { get; private set; }
        public ISecureStore Store { get; private set; }
        public ChildSession Session { get; private set; }
        public GameState State { get; private set; }
        public Theme Theme { get; private set; } = Theme.Default;
        public Stage Stage { get; private set; }
        public Canvas Canvas { get; private set; }
        public Canvas Overlay { get; private set; }
        public string BuildLabel { get; private set; }

        /// <summary>Sahte sunucu (M4'te Supabase servisleriyle değişecek). Ebeveyn rolü: <see cref="DemoParent"/>.</summary>
        public MockBackend Backend { get; private set; }
        public SyncCoordinator Sync { get; private set; }
        public AppPage Page { get; private set; } = AppPage.Map;   // ana merkez ada (14 Ekim 2026)

        /// <summary>Her senkrondan sonra (görev olayları, kazanılan coin).</summary>
        public event Action<SyncReport> Synced;

        private ScreenBase _screen;
        private float _autosave, _autosync;
        private bool _syncing;

        private static string SaveKey(string childId) => "pofi.save." + childId;
        private static string ServerKey(string childId) => "pofi.mockserver." + childId;

        private async void Awake()
        {
            Application.targetFrameRate = 60;
            Events = new EventBus();

            Data = GameData.Load(ReadData);
            Loc = new Localization(ReadData("tr.json"));
            NameRules = new PetNameRules(ReadData("name_blocklist.json"));
            Starter = new StarterKit(ReadData("start.json"));
            Levels = new LevelTable(Data.Levels);
            Map = new IslandMap(ReadData("regions.json"), Levels);
            Store = new PrefsStore();
            Auth = new MockAuthService(Store);   // M4'te SupabaseAuthService ile değişecek
            var build = Resources.Load<TextAsset>("build_number");
            BuildLabel = GameVersion.Display(build != null ? build.text.Trim() : null);

            Stage = Stage.Create(Theme.Sky);
            Stage.ItemLookup = Data.Item;
            Ui.EnsureEventSystem();
            Canvas = Ui.CreateCanvas("Canvas", 0);
            Overlay = Ui.CreateCanvas("Overlay", 10);

            var restored = await Auth.RestoreAsync();
            if (restored != null) OnSignedIn(restored, route: false);
            Route();
        }

        private static string ReadData(string file)
        {
            var asset = Resources.Load<TextAsset>("Data/" + System.IO.Path.GetFileNameWithoutExtension(file));
            if (asset == null) throw new Exception("Veri dosyası bulunamadı: " + file);
            return asset.text;
        }

        public DateTime UtcNow => DateTime.UtcNow;
        public DateTime LocalNow => DateTime.Now;

        public int Level => Levels.LevelFor(State != null ? State.Xp.TotalXp : 0);
        public GrowthStage Growth => Levels.StageFor(Level);

        /// <summary>Girişten sonra: tema, çocuğa ait kayıt (yoksa yeni) ve ekran.</summary>
        public void OnSignedIn(ChildSession session, bool route = true)
        {
            Session = session;
            Theme = Theme.For(session.AgeBand);
            var saved = SaveCodec.Deserialize(Store.Get(SaveKey(session.ChildId)));
            State = AppFlow.BelongsTo(saved, session) ? saved : GameState.NewFor(session.ChildId, UtcNow);
            State.Stats ??= PetStats.New(UtcNow);
            Theme.TextScale = State.Settings.TextScale;
            Theme.ReduceMotion = State.Settings.ReduceMotion;
            Audio.Sfx.Volume = State.Settings.SfxVolume;
            Stage.SetSky(Theme.Sky);
            State.Stats.Tick(UtcNow, Decay);

            Backend = new MockBackend(Data);
            Backend.Import(Store.Get(ServerKey(session.ChildId)));
            DemoParent.EnsureToday(Backend, LocalNow);
            Sync = new SyncCoordinator(Backend, Backend, Backend, Data);
            Page = AppPage.Map;
            _ = SyncNow();
            if (route) Route();
        }

        /// <summary>Görevleri, harcamaları ve bakiyeyi sunucuyla eşitler. Aynı anda tek senkron.</summary>
        public async Task<SyncReport> SyncNow()
        {
            if (Sync == null || State == null || _syncing) return null;
            _syncing = true;
            SyncReport report;
            try { report = await Sync.SyncAsync(State, LocalNow, UtcNow); }
            catch (Exception e) { Debug.LogException(e); report = null; }
            finally { _syncing = false; }
            _autosync = 0f;
            if (report == null || State == null) return report;
            if (Session != null) Store.Set(ServerKey(Session.ChildId), Backend.Export());
            Save();
            if (report.CoinsEarned > 0) CoinBurst.Play(Overlay.transform, Theme, Loc.Get("tasks.earned", report.CoinsEarned));
            var approved = 0;
            foreach (var ev in report.TaskEvents) if (ev.Kind == Logic.Tasks.TaskEventKind.Approved) approved++;
            if (approved > 0) RecordActivity("tasks_approved", approved);
            Synced?.Invoke(report);
            return report;
        }

        /// <summary>Haritadaki bölgeye gir. Henüz yapılmamış yerler için petin söyleyeceği cümle <paramref name="say"/>'e gider.</summary>
        public void Enter(RegionDef region, Action<string> say)
        {
            switch (IslandMap.KindOf(region.Target, out var arg))
            {
                case RegionTargetKind.Page:
                    Open(arg == "shop" ? AppPage.Shop : arg == "tasks" ? AppPage.Tasks : arg == "wardrobe" ? AppPage.Wardrobe
                        : arg == "garden" ? AppPage.Garden : arg == "album" ? AppPage.Album
                        : arg == "festival" ? AppPage.Festival : arg == "lighthouse" ? AppPage.Lighthouse : AppPage.Home);
                    break;
                case RegionTargetKind.MiniGame:
                    if (MiniGameScreen.Supports(arg)) { MiniGameId = arg; Open(AppPage.MiniGame); }
                    else say(Loc.Get("map.soon", region.Name));
                    break;
                case RegionTargetKind.Cards:
                    if (CardsScreen.Available) Open(AppPage.Cards);
                    else say(Loc.Get("map.soon", region.Name));
                    break;
                default:
                    say(Loc.Get("map.soon", region.Name));
                    break;
            }
        }

        public void OpenMiniGame(string id)
        {
            MiniGameId = id;
            Open(AppPage.MiniGame);
        }

        /// <summary>XP kazancı (mini oyun, masa oyunu…): günlük sınır, seviye atlama ve kutlama burada.</summary>
        /// <summary>XP kazanıldı (miktar): arayüz "+N ★" gösterir.</summary>
        public event System.Action<int> XpGained;

        public XpResult GrantXp(int amount, XpSource source)
        {
            var r = Progress.Grant(State, Levels, Session.AgeBand, amount, source, LocalNow);
            Save();
            if (r.Grant.Granted > 0) XpGained?.Invoke(r.Grant.Granted);
            if (r.LevelUp != null) LevelUpCelebration.Show(this, r.LevelUp);
            return r;
        }

        /// <summary>
        /// Oyuncu eylemi kaydı: sayaç → rozet ve günlük görev. Kazanılan rozet/görev XP'si verilir ve bildirim gösterilir.
        /// </summary>
        public void RecordActivity(string counter, int n = 1)
        {
            if (State == null) return;
            var r = Activity.Record(State, Data, Levels, counter, n, LocalNow);
            foreach (var b in r.NewBadges) Toast.Post(Overlay.transform, Theme, Loc.Get("badge.earned", b.Name));
            foreach (var q in r.QuestsDone) Toast.Post(Overlay.transform, Theme, q.Text + "  " + Loc.Get("xp.gain", q.Xp));
            if (r.BadgeXp > 0) GrantXp(r.BadgeXp, XpSource.Achievement);
            if (r.QuestXp > 0) GrantXp(r.QuestXp, XpSource.DailyQuest);
            Save();
        }

        /// <summary>Alt menüden sayfa aç (yalnızca pet hazırsa).</summary>
        public void Open(AppPage page)
        {
            Page = page;
            Route();
        }

        public async void SignOut()
        {
            Save();
            await Auth.SignOutAsync();
            Session = null;
            State = null;
            Backend = null;
            Sync = null;
            Theme = Theme.Default;
            Stage.SetSky(Theme.Sky);
            Route();
        }

        public void Save()
        {
            if (Session == null || State == null) return;
            Store.Set(SaveKey(Session.ChildId), SaveCodec.Serialize(State, UtcNow));
            _autosave = 0f;
        }

        public void Route()
        {
            var next = AppFlow.Decide(Session, State);
            if (_screen != null)
            {
                _screen.gameObject.SetActive(false);   // Destroy kare sonunda olur; eski ekran bir kare bile görünmesin
                Destroy(_screen.gameObject);
            }
            Stage.SetPetVisible(true);
            Stage.SetHomeItems(null, false);   // ev eşyaları yalnızca ev ekranında
            Stage.SetAmbient(false);
            Stage.SetSleeping(false);
            Stage.SetBackdrop(null);
            Stage.Swiped = null;
            var root = Ui.Fill(Canvas.transform, "Screen " + next);
            switch (next)
            {
                case AppScreen.Login: _screen = root.gameObject.AddComponent<LoginScreen>(); break;
                case AppScreen.PetSelect: _screen = root.gameObject.AddComponent<PetSelectScreen>(); break;
                case AppScreen.PetName: _screen = root.gameObject.AddComponent<PetNameScreen>(); break;
                default:
                    switch (Page)
                    {
                        case AppPage.Tasks: _screen = root.gameObject.AddComponent<TasksScreen>(); break;
                        case AppPage.Shop: _screen = root.gameObject.AddComponent<ShopScreen>(); break;
                        case AppPage.Wardrobe: _screen = root.gameObject.AddComponent<WardrobeScreen>(); break;
                        case AppPage.Map: _screen = root.gameObject.AddComponent<MapScreen>(); break;
                        case AppPage.MiniGame: _screen = root.gameObject.AddComponent<MiniGameScreen>(); break;
                        case AppPage.Cards: _screen = root.gameObject.AddComponent<CardsScreen>(); break;
                        case AppPage.Garden: _screen = root.gameObject.AddComponent<GardenScreen>(); break;
                        case AppPage.Album: _screen = root.gameObject.AddComponent<AlbumScreen>(); break;
                        case AppPage.Settings: _screen = root.gameObject.AddComponent<SettingsScreen>(); break;
                        case AppPage.Decorate: _screen = root.gameObject.AddComponent<DecorateScreen>(); break;
                        case AppPage.Festival:
                        case AppPage.Lighthouse: _screen = root.gameObject.AddComponent<EventScreen>(); break;
                        default: _screen = root.gameObject.AddComponent<HomeScreen>(); break;
                    }
                    break;
            }
            _screen.Init(this);
        }

        private void Update()
        {
            _autosave += Time.unscaledDeltaTime;
            if (_autosave > 30f) Save();
            if (State != null && State.HasPet)
            {
                _autosync += Time.unscaledDeltaTime;
                if (_autosync > 20f) _ = SyncNow();
            }
        }

        /// <summary>Tarayıcıdan otomatik test komutu (SendMessage). Bkz. <see cref="DebugCommands"/>.</summary>
        public void PofiDebug(string line) => DebugCommands.Run(this, line);

        private void OnApplicationPause(bool paused) { if (paused) Save(); }
        private void OnApplicationQuit() => Save();
    }
}
