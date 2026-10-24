using System;
using System.Collections.Generic;
using System.Linq;
using Pofi.Logic.Data;
using Pofi.Logic.Progression;
using UnityEngine;
using UnityEngine.EventSystems;

namespace Pofi.World
{
    /// <summary>
    /// 3B sahne: kamera, ışıklar, kum adacığı ve ortadaki pet. Pet parmakla sağa sola çevrilir (360°),
    /// boşta hafifçe nefes alır, sevinince zıplar. Ekranlar sahneyi bu sınıf üzerinden kullanır.
    /// </summary>
    public sealed class Stage : MonoBehaviour
    {
        public Camera Camera { get; private set; }
        public Transform Pet { get; private set; }
        public bool AllowDrag = true;

        /// <summary>Eşya kimliği → tanım (giyilenleri çizmek için). Uygulama kökü atar.</summary>
        public Func<string, ItemDef> ItemLookup;
        private PetSpeciesDef _petDef;

        /// <summary>Hızlı yatay kaydırma (karusel için): −1 sola, +1 sağa.</summary>
        public Action<int> Swiped;

        private Transform _holder;
        private float _yaw, _yawVelocity, _hop, _breath, _baseScale = 1f, _appear = 1f;
        private bool _dragging;
        private Vector3 _pressPos, _lastPos;
        private float _pressTime;
        private Material _islandMat, _waterMat;

        /// <summary>Evim zemini modelinin genişliği (m): art/scripts/home_floor.py 2 × A × R_OUT = 2 × 3,3 × 1,12.</summary>
        private const float FloorWidth = 7.392f;

        public static Stage Create(Color sky)
        {
            var go = new GameObject("Stage");
            var s = go.AddComponent<Stage>();
            s.Build(sky);
            return s;
        }

        private void Build(Color sky)
        {
            var camGo = new GameObject("Main Camera");
            camGo.tag = "MainCamera";
            camGo.transform.SetParent(transform, false);
            Camera = camGo.AddComponent<Camera>();
            camGo.AddComponent<AudioListener>();   // sahnedeki tek dinleyici: yoksa Unity hiçbir sesi çalmaz (iPhone'da ses yoktu)
            Camera.clearFlags = CameraClearFlags.SolidColor;
            Camera.backgroundColor = sky;
            Camera.fieldOfView = 34f;
            Look.Init(Camera);   // görsel stil (yeni/eski) + renk ayarı; malzemeler kurulmadan önce
            // Gökyüzü: kodla çizilen geçiş + güneş + bulut tülü (Pofi/Sky); yoksa düz renk
            var skySh = Shader.Find("Pofi/Sky");
            if (skySh != null)
            {
                _skyMat = new Material(skySh);
                RenderSettings.skybox = _skyMat;
                Camera.clearFlags = CameraClearFlags.Skybox;
            }
            SetCamera(new Vector3(0f, 1.25f, -6.2f), 7f);

            var sun = new GameObject("Sun").AddComponent<Light>();
            sun.transform.SetParent(transform, false);
            sun.type = LightType.Directional;
            sun.color = new Color(1f, 0.95f, 0.86f);
            sun.intensity = 1.25f;
            sun.shadows = LightShadows.Soft;
            sun.transform.rotation = Quaternion.Euler(42f, -32f, 0f);
            var rim = new GameObject("Rim").AddComponent<Light>();
            rim.transform.SetParent(transform, false);
            rim.type = LightType.Directional;
            rim.color = new Color(0.5f, 0.9f, 1f);
            rim.intensity = 0.55f;
            rim.shadows = LightShadows.None;
            rim.transform.rotation = Quaternion.Euler(20f, 150f, 0f);
            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(0.62f, 0.78f, 1f);
            RenderSettings.ambientEquatorColor = new Color(1f, 0.85f, 0.72f);
            RenderSettings.ambientGroundColor = new Color(0.95f, 0.8f, 0.55f);

            _waterMat = PetModels.NewMaterial(new Color(0.25f, 0.75f, 0.95f), 0.9f);
            _islandMat = PetModels.NewMaterial(new Color(1f, 0.86f, 0.6f), 0.15f);
            var water = Cylinder("Water", new Vector3(0f, -0.12f, 0f), new Vector3(40f, 0.02f, 40f), _waterMat);
            water.GetComponent<Renderer>().shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            // Evim zemini (24 Ekim 2026, kullanıcı): kodla boyanmış kum — tepecik, rüzgâr çizgisi, kabuk, çakıl, petin altında hasır,
            // kenarda ıslak kum ve köpük (art/scripts/home_floor.py). Üst yüzü eski silindirle aynı elips ve yükseklikte (y 0,01);
            // Blender (x, y) → Unity (x, z) için 180°. Dosya yoksa eski düz kum silindiri.
            var floor = RealAssets.EnvFootprint("floor_home", transform, FloorWidth, 180f);
            if (floor != null)
            {
                floor.name = "Island";
                floor.localPosition = new Vector3(0f, 0f, 0.9f);
                foreach (var r in floor.GetComponentsInChildren<Renderer>()) r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            }
            else
            {
                var island = Cylinder("Island", new Vector3(0f, -0.05f, 0.9f), new Vector3(6.6f, 0.06f, 6.2f), _islandMat);   // ev eşyaları için geniş
                island.GetComponent<Renderer>().shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            }

            // Gerçek çevre varlıkları varsa (Meshy): arkada ada parçası ve palmiyeler
            var env = new GameObject("Scenery").transform;
            _scenery = env;
            env.SetParent(transform, false);
            var chunk = RealAssets.Env("island_chunk", env, 1.5f);
            if (chunk != null)
            {
                chunk.localPosition = new Vector3(2.6f, -0.5f, 7.5f);
                chunk.localRotation = Quaternion.Euler(0f, 30f, 0f);
                var c2 = RealAssets.Env("island_chunk", env, 1.2f);
                if (c2 != null) { c2.localPosition = new Vector3(-3.0f, -0.6f, 9f); c2.localRotation = Quaternion.Euler(0f, -50f, 0f); }
                var p1 = RealAssets.Env("palm", env, 2.6f);
                if (p1 != null) { p1.localPosition = new Vector3(-1.45f, -0.05f, 2.4f); p1.localRotation = Quaternion.Euler(0f, 60f, 0f); }
                var p2 = RealAssets.Env("palm", env, 2.1f);
                if (p2 != null) { p2.localPosition = new Vector3(1.5f, -0.05f, 3.2f); p2.localRotation = Quaternion.Euler(0f, -140f, 0f); }
            }
            // Petin çevresinde alçak süsler ve arkada ev (gerçek modeller varsa)
            void Prop(string name, float footprint, Vector3 pos, float yaw)
            {
                var t = RealAssets.EnvFootprint(name, env, footprint, yaw);
                if (t != null) t.localPosition = pos;
            }
            Prop("b_home", 2.6f, new Vector3(-3.6f, -0.08f, 6.2f), 215f);
            Prop("p_flowers", 0.8f, new Vector3(-2.9f, -0.05f, 0.5f), 190f);
            Prop("p_rock", 0.8f, new Vector3(2.95f, -0.05f, 1.4f), 160f);
            Prop("p_lantern", 0.5f, new Vector3(2.5f, -0.05f, 3.1f), 200f);
            // ön kenarda hafif 3B süsler (24 Ekim 2026; art/scripts/home_floor.py FRONT_PROPS ile aynı): deniz yıldızı, iki çakıl
            Prop("p_starfish", 0.36f, new Vector3(-1.55f, 0f, -1.15f), 25f);
            Prop("r_pebble", 0.22f, new Vector3(1.3f, 0f, -1.2f), 40f);
            Prop("r_pebble", 0.15f, new Vector3(1.5f, 0f, -1.02f), 160f);

            Clouds.Spawn(transform, Vector3.zero, 60f, 6, 9f, 17f, 6f, 3, 35f, 145f);   // adacığın arkasında pofuduk bulutlar

            _holder = new GameObject("PetHolder").transform;
            _holder.SetParent(transform, false);
        }

        private GameObject Cylinder(string n, Vector3 p, Vector3 s, Material m)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            go.name = n;
            go.transform.SetParent(transform, false);
            go.transform.localPosition = p;
            go.transform.localScale = s;
            go.GetComponent<Renderer>().sharedMaterial = m;
            Destroy(go.GetComponent<Collider>());
            return go;
        }

        /// <summary>Kamerayı konuma koyar ve petin göğüs hizasına baktırır.</summary>
        public void SetCamera(Vector3 position, float pitch, float fov = 34f)
        {
            Camera.transform.SetPositionAndRotation(position, Quaternion.Euler(pitch, 0f, 0f));
            Camera.fieldOfView = fov;
        }

        private Material _skyMat;

        /// <summary>Gökyüzü tonu: gündüz varsayılan geçiş; koyu renk verilirse (gece) geçiş o renge göre koyulaşır.</summary>
        public void SetSky(Color sky)
        {
            Camera.backgroundColor = sky;
            if (_skyMat == null) return;
            if (sky.grayscale > 0.45f)
            {
                // gündüz: stilize açık mavi (Pofi/Sky varsayılanları)
                _skyMat.SetColor("_Zenith", new Color(0.33f, 0.66f, 0.97f));
                _skyMat.SetColor("_Mid", new Color(0.52f, 0.8f, 1f));
                _skyMat.SetColor("_Horizon", new Color(0.76f, 0.92f, 1f));
                _skyMat.SetColor("_Ground", new Color(0.45f, 0.75f, 0.95f));
                _skyMat.SetColor("_CloudLit", new Color(1f, 0.99f, 0.96f));
                _skyMat.SetColor("_CloudShade", new Color(0.66f, 0.75f, 0.89f));   // doğal kümülüs tabanı (sky v4)
                _skyMat.SetFloat("_Clouds", 0.62f);
                _skyMat.SetFloat("_Sun", 1f);
            }
            else
            {
                // gece: verilen koyu tona göre; bulutlar soluk mavi, güneş yok
                _skyMat.SetColor("_Zenith", sky * 0.55f);
                _skyMat.SetColor("_Mid", sky * 0.8f);
                _skyMat.SetColor("_Horizon", Color.Lerp(sky, Color.white, 0.25f));
                _skyMat.SetColor("_Ground", sky * 0.8f);
                _skyMat.SetColor("_CloudLit", Color.Lerp(sky, Color.white, 0.45f));
                _skyMat.SetColor("_CloudShade", Color.Lerp(sky, Color.white, 0.2f));
                _skyMat.SetFloat("_Clouds", 0.4f);
                _skyMat.SetFloat("_Sun", 0f);
            }
        }

        private GrowthStage _petStage = GrowthStage.Genc;

        public void ShowPet(PetSpeciesDef def, GrowthStage stage, IEnumerable<string> equipped = null, bool resetYaw = true)
        {
            _petStage = stage;
            ClearPet();
            _petDef = def;
            Pet = PetModels.Build(def, _holder, stage);
            _life = Pet.gameObject.AddComponent<PetLife>();
            _life.Sleeping = _sleeping;
            SetCosmetics(equipped);
            _baseScale = PetModels.StageScale(stage);
            _appear = 0f;
            if (resetYaw) { _yaw = -18f; _yawVelocity = 0f; }
        }

        /// <summary>Giyilenleri yeniler (pet yeniden kurulmaz, dönüş korunur).</summary>
        public void SetCosmetics(IEnumerable<string> equipped)
        {
            if (Pet == null || _petDef == null) return;
            var items = equipped == null || ItemLookup == null ? null : equipped.Select(ItemLookup).Where(i => i != null).ToList();
            CosmeticModels.Apply(Pet, _petDef, items, _petStage);
        }

        private Transform _scenery, _backdrop;

        /// <summary>Petin arkasına büyük bir yapı koyar (ör. dükkân tezgâhı); adacık süsleri gizlenir. null: kaldırır.</summary>
        /// <summary>Arka plan yapısının kökü (yoksa null): dükkânda Kıskaç tezgâhın yanına konur.</summary>
        public Transform Backdrop => _backdrop;

        public void SetBackdrop(string asset, float footprint = 5f, float z = 3.2f)
        {
            if (_backdrop != null) { Destroy(_backdrop.gameObject); _backdrop = null; }
            if (_scenery != null) _scenery.gameObject.SetActive(string.IsNullOrEmpty(asset));
            if (string.IsNullOrEmpty(asset)) return;
            _backdrop = new GameObject("Backdrop").transform;
            _backdrop.SetParent(transform, false);
            var m = RealAssets.EnvFootprint(asset, _backdrop, footprint, 180f);
            if (m != null) m.localPosition = new Vector3(0f, -0.1f, z);
        }

        private Transform _picture;
        private float _pictureAspect = 16f / 9f;

        /// <summary>
        /// Petin arkasına tam ekran 3B çizim görseli (pet seçme: kumsal sahnesi; 23 Ekim 2026). Kameraya bağlı uzak bir yüzey,
        /// ekranı her oranda doldurur; adacık süsleri gizlenir. null: kaldırır.
        /// </summary>
        public void SetPicture(Texture2D tex)
        {
            if (_picture != null) { Destroy(_picture.gameObject); _picture = null; }
            if (_scenery != null) _scenery.gameObject.SetActive(tex == null && _backdrop == null);
            if (tex == null || Camera == null) return;
            var q = GameObject.CreatePrimitive(PrimitiveType.Quad);
            Destroy(q.GetComponent<Collider>());
            q.name = "Picture";
            _picture = q.transform;
            _picture.SetParent(Camera.transform, false);
            var r = q.GetComponent<MeshRenderer>();
            r.sharedMaterial = InkHeart.SpriteMat(tex);
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
            _pictureAspect = tex.width / (float)Mathf.Max(1, tex.height);
            FitPicture();
        }

        private void FitPicture()
        {
            if (_picture == null || Camera == null) return;
            const float d = 40f;
            var h = 2f * d * Mathf.Tan(Camera.fieldOfView * 0.5f * Mathf.Deg2Rad);
            var w = h * Camera.aspect;
            float sw, sh;
            if (Camera.aspect > _pictureAspect) { sw = w; sh = w / _pictureAspect; } else { sh = h; sw = h * _pictureAspect; }
            _picture.localPosition = new Vector3(0f, 0f, d);
            _picture.localRotation = Quaternion.identity;
            _picture.localScale = new Vector3(sw * 1.02f, sh * 1.02f, 1f);
        }

        public void SetPetVisible(bool visible)
        {
            _holder.gameObject.SetActive(visible);
            if (_props != null) _props.gameObject.SetActive(visible);
        }

        private Transform _props;

        /// <summary>Ev eşyalarını adacığa yerleştirir (boş liste: temizler).</summary>
        public void SetHomeItems(IEnumerable<Logic.State.Placement> placements, bool expanded)
        {
            if (_props == null)
            {
                _props = new GameObject("Home").transform;
                _props.SetParent(transform, false);
            }
            HomeProps.Apply(_props, placements ?? Enumerable.Empty<Logic.State.Placement>(), expanded);
        }

        public void ClearPet()
        {
            if (Pet == null) return;
            foreach (var r in Pet.GetComponentsInChildren<Renderer>())
                foreach (var m in r.sharedMaterials) if (m != null && !RealAssets.IsShared(m)) Destroy(m);
            Destroy(Pet.gameObject);
            Pet = null;
        }

        private PetLife _life;
        private bool _sleeping;
        private Ambient _ambient;

        /// <summary>Gece: pet uyur (gözler kapalı, yavaş nefes).</summary>
        public void SetSleeping(bool sleeping)
        {
            _sleeping = sleeping;
            if (_life != null) _life.Sleeping = sleeping;
            RealAssets.Play(Pet, sleeping ? "sleep" : "idle", false);
        }

        /// <summary>Ada sakinleri (yengeç, martı): yalnızca ev ekranında.</summary>
        public void SetAmbient(bool on)
        {
            if (on && _ambient == null) _ambient = Ambient.Create(transform);
            else if (!on && _ambient != null) { Destroy(_ambient.gameObject); _ambient = null; }
        }

        public void Hop()
        {
            Audio.Sfx.Play(Audio.SfxKind.Pop);
            // gerçek modelde sevinç; evrede ek hareket varsa arada bir onlardan biri (dans, dönerek zıplama…)
            var fun = new[] { "dance", "dance2", "spin", "genie" };
            var pick = fun[UnityEngine.Random.Range(0, fun.Length)];
            if (UnityEngine.Random.value < 0.4f && RealAssets.Play(Pet, pick)) return;
            if (RealAssets.Play(Pet, "happy")) return;
            if (!UI.Theme.ReduceMotion) _hop = 1f;
        }

        /// <summary>Petin kafa üstünün ekran konumu (konuşma balonu için).</summary>
        public Vector2 PetHeadScreenPoint()
        {
            var top = _holder.position + Vector3.up * (1.75f * _baseScale);
            return (Vector2)Camera.WorldToScreenPoint(top);
        }

        private void Update()
        {
            var dt = Time.deltaTime;
            if (_picture != null) FitPicture();   // ekran döndü / kamera görüş açısı değişti
            HandleDrag(dt);

            if (!_dragging)
            {
                _yaw += _yawVelocity * dt;
                _yawVelocity = Mathf.Lerp(_yawVelocity, 0f, 1f - Mathf.Exp(-3f * dt));
            }

            _appear = Mathf.Min(1f, _appear + dt * 3.5f);
            var pop = 1f + Mathf.Sin(_appear * Mathf.PI) * 0.12f * (1f - _appear * 0.3f);
            _breath += dt * (_sleeping ? 0.9f : 2.2f);
            var breath = UI.Theme.ReduceMotion ? 1f : 1f + Mathf.Sin(_breath) * (_sleeping ? 0.03f : 0.015f);
            _hop = Mathf.Max(0f, _hop - dt * 1.6f);
            var hopY = Mathf.Sin(_hop * Mathf.PI) * 0.35f * _hop;

            _holder.localRotation = Quaternion.Euler(0f, _yaw, 0f);
            _holder.localPosition = new Vector3(0f, hopY, 0f);
            var s = _baseScale * Mathf.SmoothStep(0.2f, 1f, _appear) * pop;
            _holder.localScale = new Vector3(s / breath, s * breath, s / breath);
        }

        private void HandleDrag(float dt)
        {
            if (!AllowDrag) { _dragging = false; return; }
            if (Input.GetMouseButtonDown(0) && !OverUi())
            {
                _dragging = true;
                _pressPos = _lastPos = Input.mousePosition;
                _pressTime = Time.unscaledTime;
                _yawVelocity = 0f;
            }
            if (_dragging && Input.GetMouseButton(0))
            {
                var dx = Input.mousePosition.x - _lastPos.x;
                var deg = -dx / Mathf.Max(1f, Screen.width) * 360f;
                _yaw += deg;
                if (dt > 0f) _yawVelocity = Mathf.Lerp(_yawVelocity, deg / dt, 0.5f);
                _lastPos = Input.mousePosition;
            }
            if (_dragging && Input.GetMouseButtonUp(0))
            {
                _dragging = false;
                var total = Input.mousePosition.x - _pressPos.x;
                var quick = Time.unscaledTime - _pressTime < 0.35f;
                if (quick && Mathf.Abs(total) > Screen.width * 0.22f && Swiped != null)
                {
                    _yawVelocity = 0f;
                    Swiped(total < 0 ? -1 : 1);
                }
            }
        }

        private static bool OverUi()
        {
            var es = EventSystem.current;
            if (es == null) return false;
            if (Input.touchCount > 0) return es.IsPointerOverGameObject(Input.GetTouch(0).fingerId);
            return es.IsPointerOverGameObject();
        }

        private void OnDestroy()
        {
            ClearPet();
            if (_islandMat != null) Destroy(_islandMat);
            if (_waterMat != null) Destroy(_waterMat);
        }
    }
}
