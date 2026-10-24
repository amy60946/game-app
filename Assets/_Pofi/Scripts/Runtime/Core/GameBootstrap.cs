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
using Pofi.Logic.Services.Supabase;
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
        /// <summary>Pişmiş v6 adası (Resources/Data/island_v6.bytes + island_v6_layout.json); yoksa null (eski prosedürel ada).</summary>
        public BakedIsland Island { get; private set; }

        /// <summary>Açık mini oyunun kimliği (coconut, help_pet, swim, surf, ski).</summary>
        public string MiniGameId { get; private set; }
        public StatDecayConfig Decay { get; } = StatDecayConfig.Default;
        public IAuthService Auth => Router;
        /// <summary>Giriş: deneme kodları sahte arka uca, diğer kodlar gerçek sunucuya (Resources/Data/server.json).</summary>
        public RoutedAuthService Router { get; private set; }
        public ServerConfig Server { get; private set; }
        /// <summary>Gerçek sunucuya bağlı oturum mu? (değilse sahte arka uç: önizleme, deneme kodları, test erişimi)</summary>
        public bool OnServer => Router != null && Router.IsServer;
        public ISecureStore Store { get; private set; }
        public ChildSession Session { get; private set; }
        public GameState State { get; private set; }
        public Theme Theme { get; private set; } = Theme.Default;
        public Stage Stage { get; private set; }
        public Canvas Canvas { get; private set; }
        public Canvas Overlay { get; private set; }
        public string BuildLabel { get; private set; }

        /// <summary>Sahte sunucu (deneme kodlarıyla girişte). Gerçek sunucu oturumunda null. Ebeveyn rolü: <see cref="DemoParent"/>.</summary>
        public MockBackend Backend { get; private set; }

        /// <summary>Gerçek ödüller (Ö7): gerçek sunucu ya da sahte sunucu; oturum yoksa null.</summary>
        public Logic.Rewards.IRewardService Rewards => (Logic.Rewards.IRewardService)_remote ?? Backend;
        /// <summary>Görev ekleri: 2× XP teklif kaydı (Y2), haftalık hedef (Y6).</summary>
        public Logic.Tasks.IGoalService Goals => (Logic.Tasks.IGoalService)_remote ?? Backend;
        /// <summary>Posta kutusu (H2): ParentApp mesajları.</summary>
        public Logic.Mail.IMailService Mail => (Logic.Mail.IMailService)_remote ?? Backend;
        /// <summary>Okunmamış ebeveyn mesajı (adadaki kutunun bayrağı). <see cref="RefreshMail"/> günceller.</summary>
        public int MailUnread { get; private set; }

        public async System.Threading.Tasks.Task<System.Collections.Generic.List<Logic.Mail.MailMessage>> RefreshMail()
        {
            var svc = Mail;
            if (svc == null) return null;
            System.Collections.Generic.List<Logic.Mail.MailMessage> list;
            try { list = await svc.MessagesAsync(); }
            catch (Exception e) { Debug.LogException(e); return null; }
            if (list != null) MailUnread = Logic.Mail.MailBox.UnreadCount(list);
            return list;
        }

        public void MailRead() => MailUnread = 0;
        public SyncCoordinator Sync { get; private set; }
        public AppPage Page { get; private set; } = AppPage.Map;   // ana merkez ada (14 Ekim 2026)

        /// <summary>
        /// Petin adada en son durduğu yer (x, z, yön, kamera açısı). Bir pencere açılıp çarpıyla kapanınca pet buradan devam eder
        /// (22 Ekim 2026, kullanıcı: "oyun akışını bozmayalım"). Yalnız bu oturumda tutulur; uygulama yeniden açılınca son bölgenin kapısı.
        /// </summary>
        public MapSpot? MapSpot { get; set; }

        /// <summary>Her senkrondan sonra (görev olayları, kazanılan coin).</summary>
        public event Action<SyncReport> Synced;

        private ScreenBase _screen;
        private float _autosave, _autosync;

        /// <summary>Oyun içi haberler (yeni görev, onay, ödül): sakin anda gösterilir (Logic/App/Notices).</summary>
        public NoticeInbox Notices { get; } = new NoticeInbox();

        /// <summary>Mini oyun, kart oyunu, etkinlik ve giriş sırasında haber gösterilmez (oyun bölünmez).</summary>
        private bool CalmMoment => Page == AppPage.Map || Page == AppPage.Home || Page == AppPage.Tasks || Page == AppPage.Shop
                                   || Page == AppPage.Wardrobe || Page == AppPage.Garden || Page == AppPage.Album;
        private bool _syncing;
        private SupabaseGameService _remote;      // gerçek sunucu oturumunda
        private bool _remoteChecked;              // sunucu yedeğine bakıldı mı (bakılmadan senkron/yedekleme yok)
        private IHttp _http;

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
            var field = Resources.Load<TextAsset>("Data/island_v6");
            var layout = Resources.Load<TextAsset>("Data/island_v6_layout");
            if (field != null && layout != null)
            {
                try { Island = BakedIsland.Load(field.bytes, layout.text); }
                catch (Exception e) { Debug.LogException(e); Island = null; }
            }
            Store = new SecureStore();   // iOS: oturum belirteci Keychain (güvenlik M4)
            Server = ServerConfig.Parse(ReadOptional("server.json"));
            _http = new UnityHttp();
            var server = Server.IsConfigured ? new SupabaseAuthService(Server.Url, Server.PublishableKey, _http, Store) : null;
            Router = new RoutedAuthService(new MockAuthService(Store), server, Store, Server.DemoCodes);
            var build = Resources.Load<TextAsset>("build_number");
            BuildLabel = GameVersion.Display(build != null ? build.text.Trim() : null);

            Stage = Stage.Create(Theme.Sky);
            Stage.ItemLookup = Data.Item;
            Ui.EnsureEventSystem();
            Canvas = Ui.CreateCanvas("Canvas", 0);
            Overlay = Ui.CreateCanvas("Overlay", 10);
            Audio.Haptics.InitAudioSession();                        // iOS: sessiz düğmesine rağmen ses (WebGL'de index.html yapar)
            Audio.Music.Init(Audio.Music.DefaultVolume);           // arka plan müziği (ilk dokunuşta duyulur)
            var safeOverlay = Ui.Fill(Overlay.transform, "Safe");     // iPhone çentiği: köşe düğmeleri güvenli alanda
            safeOverlay.gameObject.AddComponent<SafeArea>();
            MusicButton.Create(safeOverlay, this);
            LongPressInfo.UseLayer(Overlay.transform);              // E4 uzun bas bilgi baloncukları en üstte
            LookToggle.Create(safeOverlay);                          // görsel stil çalışması (kapalı: Look.StudyToggle)
#if !UNITY_WEBGL || UNITY_EDITOR
            var cover = ShowLoadingCover();                          // Y1–Y5 (WebGL'de index.html gösterir)
#endif

            var restored = await Auth.RestoreAsync();
            if (restored != null) OnSignedIn(restored, route: false);
            Route();
#if !UNITY_WEBGL || UNITY_EDITOR
            if (cover != null) cover.Close();
#endif
        }

        private const string LoadArtKey = "pofi.loadart", LoadChapterKey = "pofi.loadart.chapter";

        /// <summary>Açılış görseli: ulaşılan bölümden (son oturumda kaydedilir), bir öncekinden farklı; görseli olmayan atlanır.</summary>
        private LoadingCover ShowLoadingCover()
        {
            var book = Data.Story;
            if (book == null) return null;
            var st = new Logic.Story.StoryState { LastArt = PlayerPrefs.GetString(LoadArtKey, "") };
            var chapter = PlayerPrefs.GetInt(LoadChapterKey, 0);
            var missing = new System.Collections.Generic.HashSet<string>();
            for (var i = 0; i < 12; i++)
            {
                var def = Logic.Story.LoadingArts.Pick(book, st, chapter, Environment.TickCount + i * 7919, id => !missing.Contains(id));
                if (def == null) break;
                var art = Ui.Art("Art/" + def.Id);
                if (art == null) { missing.Add(def.Id); continue; }
                PlayerPrefs.SetString(LoadArtKey, def.Id);
                return LoadingCover.Show(Overlay.transform, Theme, art, def.Tip);
            }
            return LoadingCover.Show(Overlay.transform, Theme, null, null);
        }

        /// <summary>Bir sonraki açılışın görsel havuzu: çocuğun ulaştığı bölüm.</summary>
        private void RememberChapter()
        {
            if (Data.Story == null || State == null) return;
            PlayerPrefs.SetInt(LoadChapterKey, Data.Story.ChapterFor(Level));
        }

        private static string ReadData(string file)
        {
            var asset = Resources.Load<TextAsset>("Data/" + System.IO.Path.GetFileNameWithoutExtension(file));
            if (asset == null) throw new Exception("Veri dosyası bulunamadı: " + file);
            return asset.text;
        }

        private static string ReadOptional(string file)
        {
            var asset = Resources.Load<TextAsset>("Data/" + System.IO.Path.GetFileNameWithoutExtension(file));
            return asset != null ? asset.text : null;
        }

        public DateTime UtcNow => DateTime.UtcNow;
        public DateTime LocalNow => DateTime.Now;

        public int Level => State != null ? Levels.Level(State.Xp) : 1;   // ulaşılan en yüksek seviye düşmez (yaş grubu büyüyünce)
        public GrowthStage Growth => Levels.StageFor(Level);

        /// <summary>Girişten sonra: tema, çocuğa ait kayıt (yoksa yeni) ve ekran.</summary>
        public void OnSignedIn(ChildSession session, bool route = true)
        {
            Session = session;
            MapSpot = null;   // başka çocuk / yeni oturum: kapıdan başla
            Theme = Theme.For(session.AgeBand);
            Levels.UseBand(session.AgeBand);   // seviye eşikleri yaş grubuna göre (S1)
            var saved = SaveCodec.Deserialize(Store.Get(SaveKey(session.ChildId)));
            Adopt(AppFlow.BelongsTo(saved, session) ? saved : GameState.NewFor(session.ChildId, UtcNow));
            Levels.Remember(State.Xp);   // eski kayıtlarda en yüksek seviye yok: bugünkü seviye taban olur

            if (OnServer)
            {
                Backend = null;
                _remote = new SupabaseGameService(Server.Url, Server.PublishableKey, _http, () => Router.Server.AccessToken, Store);
                _remoteChecked = false;
                Sync = new SyncCoordinator(_remote, _remote, _remote, Data, _remote) { Levels = Levels };
            }
            else
            {
                _remote = null;
                _remoteChecked = true;
                Backend = new MockBackend(Data);
                Backend.Import(Store.Get(ServerKey(session.ChildId)));
                DemoParent.EnsureToday(Backend, LocalNow);
                DemoParent.EnsureRewards(Backend);
                DemoParent.EnsureMail(Backend, UtcNow);
                Sync = new SyncCoordinator(Backend, Backend, Backend, Data, Backend) { Levels = Levels };
            }
            Page = AppPage.Map;
            _ = SyncNow();
            if (route) Route();
        }

        private void Adopt(GameState state)
        {
            State = state;
            State.Stats ??= PetStats.New(UtcNow);
            Theme.TextScale = State.Settings.TextScale;
            Theme.ReduceMotion = State.Settings.ReduceMotion;
            Audio.Sfx.Volume = State.Settings.SfxVolume;
            Audio.Voice.Enabled = State.Settings.VoiceOn;   // sesli okuma: herkeste açık, kayıttaki tercih
            Audio.Voice.Persist = on => { if (State == null) return; State.Settings.VoiceOn = on; Save(); };
            Stage.SetSky(Theme.Sky);
            State.Stats.Tick(UtcNow, Decay);
            FirstDay.Start(State, UtcNow);   // ilk gün akışı (Ö5); pet'i olan eski oyuncuda kapanır
            var migrated = PetRoster.Migrate(State, Data);           // emekli pet → Okti (ilerleme korunur)
            migrated |= PetRoster.FixName(State, Starter, Data);     // ad hep Okti (24 Ekim 2026, kullanıcı); eski kayıttaki ad da
            if (migrated) Save();
            Guide.Start(State, Level);       // Sv1–3 rehberli zincir; Sv3'ü geçmiş oyuncuda kapanır
        }

        /// <summary>
        /// Gerçek sunucu: erişim anahtarını tazele; ilk kez ise sunucudaki kayıt yedeğine bak (telefon değiştiyse onu al).
        /// false = sunucuya ulaşılamadı, bu tur senkron yapılmaz (yerel kayıt sunucudakinin üstüne yazılmasın).
        /// </summary>
        private async Task<bool> PrepareServer()
        {
            if (!OnServer || _remote == null) return true;
            var session = Session;
            await Router.Server.EnsureFreshAsync();
            if (_remoteChecked) return true;
            var r = await SaveRestore.CheckAsync(_remote, session.ChildId, State.HasPet, State.LastSavedUtcTicks);
            if (!r.Reached || Session != session || State == null) return false;
            _remoteChecked = true;
            if (r.Adopt != null)
            {
                Adopt(r.Adopt);
                Save();
                Route();
            }
            return true;
        }

        /// <summary>Senkron sunucuya ulaşamadıysa: ebeveyn cihaz bağlantısını kaldırmış olabilir (FR-AUTH-4).</summary>
        private async Task<bool> CheckRevoked()
        {
            if (!OnServer) return false;
            try { if (await Auth.ValidateAsync() != AuthErrorKind.Revoked) return false; }
            catch (Exception e) { Debug.LogException(e); return false; }
            if (!OnServer) return false;
            Toast.Post(Overlay.transform, Theme, Loc.Get("auth.revoked"));
            SignOut();
            return true;
        }

        /// <summary>Görevleri, harcamaları ve bakiyeyi sunucuyla eşitler. Aynı anda tek senkron.</summary>
        public async Task<SyncReport> SyncNow()
        {
            if (Sync == null || State == null || _syncing) return null;
            _syncing = true;
            SyncReport report;
            try
            {
                report = await PrepareServer() ? await Sync.SyncAsync(State, LocalNow, UtcNow) : new SyncReport { Offline = true };
            }
            catch (Exception e) { Debug.LogException(e); report = null; }
            finally { _syncing = false; }
            _autosync = 0f;
            if (report == null || State == null) return report;
            if (report.Offline && await CheckRevoked()) return report;
            if (Session != null && Backend != null) Store.Set(ServerKey(Session.ChildId), Backend.Export());
            Save();
            _ = RefreshMail();   // posta kutusu bayrağı (H2)
            if (report.CoinsEarned > 0) CoinBurst.Play(Overlay.transform, Theme, Loc.Get("tasks.earned", report.CoinsEarned), report.CoinsEarned);
            if (report.SunStonesEarned > 0)
            {
                Toast.Post(Overlay.transform, Theme, Loc.Get("stones.earned", report.SunStonesEarned));
                RewardFlight.Fly(Overlay.transform, "sunstone", "ui_sunstone", report.SunStonesEarned, new Vector2(Screen.width * 0.5f, Screen.height * 0.42f));   // O1
            }
            var shown = 0;
            foreach (var rw in report.RealTaskRewards)
            {
                if (rw.Skill == null || shown++ >= 3) continue;   // çok onay birden gelirse ekran dolmasın
                var skill = Logic.Tasks.SkillCatalog.Label(rw.Skill);
                Toast.Post(Overlay.transform, Theme, rw.NewTier > 0 ? Loc.Get("skill.tier." + rw.NewTier, skill) : Loc.Get("skill.star", skill, rw.Stars));
            }
            Notices.Add(NoticeDigest.Build(report.TaskEvents, report.RewardEvents));
            if (report.RealTaskXp > 0) XpGained?.Invoke(report.RealTaskXp);
            // görünmez günlük pay doldu (M7): sınır değil, ulaşılmış hedef gibi sıcak bir haber
            if (report.RealTaskGoalReached) Toast.Post(Overlay.transform, Theme, Loc.Get("tasks.xp_goal"));
            if (report.SelfStarted > 0) { Toast.Post(Overlay.transform, Theme, Loc.Get("tasks.self_started")); RecordActivity("self_started", report.SelfStarted); }
            if (report.LevelUp != null) { Data.SunBook.FilterLevelUp(report.LevelUp); LevelUpCelebration.Show(this, report.LevelUp); }
            if (!string.IsNullOrEmpty(report.AgeBand)) ApplyAgeBand(Logic.Profile.AgeBandProfile.Parse(report.AgeBand), report.AgeBand);
            var approved = 0;
            foreach (var ev in report.TaskEvents) if (ev.Kind == Logic.Tasks.TaskEventKind.Approved) approved++;
            if (approved > 0) RecordActivity("tasks_approved", approved);
            Synced?.Invoke(report);
            return report;
        }

        /// <summary>
        /// Yaş grubu sunucuda değişti (ebeveyn seçti ya da doğum günü; ortak 20261023040000): önce ulaşılan seviye kaydedilir
        /// (seviye düşmez), sonra eşikler, tema ve saklanan oturum yeni gruba geçer. Açık ekran olduğu gibi kalır.
        /// </summary>
        private void ApplyAgeBand(Logic.Profile.AgeBand band, string raw)
        {
            if (Session == null || State == null || Session.AgeBand == band) return;
            Levels.Remember(State.Xp);
            Session = new ChildSession(Session.ChildId, Session.DisplayName, band, Session.Avatar);
            Theme = Theme.For(band);
            Theme.TextScale = State.Settings.TextScale;
            Theme.ReduceMotion = State.Settings.ReduceMotion;
            Stage.SetSky(Theme.Sky);
            Levels.UseBand(band);
            Router?.Server?.RememberAgeBand(raw);
            Save();
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
        /// <summary>Yeni rozet kazanıldı (adet): adada pet sevinir, kupa göstergesi yaylanır (XP takibi M4).</summary>
        public event System.Action<int> BadgeEarned;
        /// <summary>Günün son oyun içi görevi bitti: günlük sandık açılabilir (S2); Görev düğmesi parlar.</summary>
        public event System.Action ChestReady;

        public XpResult GrantXp(int amount, XpSource source)
        {
            var r = Progress.Grant(State, Levels, Session.AgeBand, amount, source, LocalNow);
            Save();
            if (r.Grant.Granted > 0) XpGained?.Invoke(r.Grant.Granted);
            Data.SunBook.FilterLevelUp(r.LevelUp);   // Güneş Taşı ile açılan içerik seviye kutlamasında yer almaz
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
            Logic.Story.Diary.Record(State.Story, State.Counters, LocalNow);   // H5: günün 2–3 anısı (puan yok)
            foreach (var b in r.NewBadges) Toast.Post(Overlay.transform, Theme, Loc.Get("badge.earned", b.Name));
            if (r.NewBadges.Count > 0) BadgeEarned?.Invoke(r.NewBadges.Count);
            for (var i = 0; i < r.QuestsDone.Count; i++) Toast.Post(Overlay.transform, Theme, r.QuestsDone[i].Text + "  " + Loc.Get("xp.gain", r.QuestXpEach[i]));
            if (r.ChestReady) { Toast.Post(Overlay.transform, Theme, Loc.Get("chest.ready")); ChestReady?.Invoke(); }
            if (r.BadgeXp > 0) GrantXp(r.BadgeXp, XpSource.Achievement);
            if (r.QuestXp > 0) GrantXp(r.QuestXp, XpSource.DailyQuest);
            // rehberli zincir (Sv1–3): sırası gelen adım bu eylemle bittiyse kısa kutlama + XP
            foreach (var g in Guide.OnActivity(State, Level, counter))
            {
                Toast.Post(Overlay.transform, Theme, Loc.Get("guide.done", g.Xp));
                Audio.Sfx.Play(Audio.SfxKind.Success);
                StarSparkles.Around(Overlay.transform, new Vector2(0.5f, 0.55f), new Vector2(0.18f, 0.2f), 10, g.Id.Length * 7);   // küçük kutlama
                GrantXp(g.Xp, XpSource.Achievement);
            }
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
            MapSpot = null;
            Backend = null;
            Sync = null;
            _remote = null;
            Theme = Theme.Default;
            Stage.SetSky(Theme.Sky);
            Route();
        }

        public void Save()
        {
            if (Session == null || State == null) return;
            Store.Set(SaveKey(Session.ChildId), SaveCodec.Serialize(State, UtcNow));
            RememberChapter();   // sonraki açılışın yükleme görseli havuzu
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
            Stage.SetBeach(false);             // kumsal görseli yalnız giriş ve tanışma ekranında (ekran kendisi açar)
            Stage.Swiped = null;
            MusicButton.Place(MusicButton.DefaultX);   // pencere çarpısı yanına kaymışsa geri al
            Audio.Voice.Stop();                         // ekran değişince önceki ekranın cümlesi susar
            MusicButton.SetVisible(true);              // adada gizlenir (avatar menüsünde)
            var root = Ui.Fill(Canvas.transform, "Screen " + next);
            root.gameObject.AddComponent<SafeArea>();                // iPhone çentiği / ev çubuğu
            switch (next)
            {
                case AppScreen.Login: _screen = root.gameObject.AddComponent<LoginScreen>(); break;
                case AppScreen.PetSelect: _screen = root.gameObject.AddComponent<PetSelectScreen>(); break;
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
                        case AppPage.Mail: _screen = root.gameObject.AddComponent<MailScreen>(); break;
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
                if (Notices.Count > 0)
                    foreach (var n in Notices.Drain(CalmMoment))
                    {
                        // yeni ev görevi: adadaysa haberi postacı Mavi getirir (kullanıcı, 24 Ekim 2026)
                        if (n.Key.StartsWith("notice.new_task") && Page == AppPage.Map)
                        {
                            var map = FindAnyObjectByType<Screens.MapScreen>();
                            if (map != null && map.MaviNews(Loc.Get(n.Key == "notice.new_task_one" ? "mavi.news_one" : "mavi.news_many", n.Args))) continue;
                        }
                        Toast.Post(Overlay.transform, Theme, Loc.Get(n.Key, n.Args));
                        if (n.Happy) Audio.Sfx.Play(Audio.SfxKind.Success);
                    }
            }
        }

        /// <summary>Tarayıcıdan otomatik test komutu (SendMessage). Bkz. <see cref="DebugCommands"/>.</summary>
        public void PofiDebug(string line) => DebugCommands.Run(this, line);

        private void OnApplicationPause(bool paused)
        {
            if (paused) { Save(); return; }
            Audio.Haptics.InitAudioSession();   // iOS: Unity öne gelince oturumu "ambient"e çeviriyor; playback'e geri al
            Audio.Music.Resume();
        }
        private void OnApplicationQuit() => Save();
    }

    /// <summary>Adada petin yeri ve bakışı (bkz. <see cref="GameBootstrap.MapSpot"/>).</summary>
    public readonly struct MapSpot
    {
        public readonly float X, Z, Heading, CamYaw;
        public MapSpot(float x, float z, float heading, float camYaw) { X = x; Z = z; Heading = heading; CamYaw = camYaw; }
    }
}
