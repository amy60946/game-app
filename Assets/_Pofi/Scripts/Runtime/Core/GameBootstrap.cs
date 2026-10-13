using System;
using System.Threading.Tasks;
using Pofi.Logic.App;
using Pofi.Logic.Core;
using Pofi.Logic.Data;
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
        public AppPage Page { get; private set; } = AppPage.Home;

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
            Stage.SetSky(Theme.Sky);
            var saved = SaveCodec.Deserialize(Store.Get(SaveKey(session.ChildId)));
            State = AppFlow.BelongsTo(saved, session) ? saved : GameState.NewFor(session.ChildId, UtcNow);
            State.Stats ??= PetStats.New(UtcNow);
            State.Stats.Tick(UtcNow, Decay);

            Backend = new MockBackend(Data);
            Backend.Import(Store.Get(ServerKey(session.ChildId)));
            DemoParent.EnsureToday(Backend, LocalNow);
            Sync = new SyncCoordinator(Backend, Backend, Backend, Data);
            Page = AppPage.Home;
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
            Synced?.Invoke(report);
            return report;
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

        private void OnApplicationPause(bool paused) { if (paused) Save(); }
        private void OnApplicationQuit() => Save();
    }
}
