using System;
using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// 3B adalı (K, 23 Ekim 2026, kullanıcı: Kıskaç a, Mavi c, Pus c): Meshy görselden 3B modeli (Resources/Env/res_*), iskeletsiz;
    /// hareketler kodla. Kıskaç yan yan sallanır, Mavi başını çevirip seker, Pus havada süzülür ve yumuşakça esner.
    /// Okti yaklaşınca ona döner (A1 dili); dokununca zıplayıp sallanır. Mavi rehberli adımda hedefe önden uçar (N2), sonra yerine döner.
    /// Dokunma için "resident_&lt;ad&gt;" collider.
    /// </summary>
    public sealed class Resident3D : MonoBehaviour
    {
        public string Who;
        private Transform _model;
        private Vector3 _home, _modelBase, _modelScale;
        private float _homeYaw, _yaw, _t, _hop = -1f, _seed;
        private Func<float, float, float> _ground;
        private Transform _pet;
        private bool _flyer;

        // N2: önden uçma; Hover: Okti'nin başının yanında kanat çırparak süzülür (akış haritası yorumu, 25 Ekim 2026)
        private enum Fly { Home, Guide, Land, Back, Hover }
        private Fly _fly = Fly.Home;
        private Vector3 _target;
        private float _landFor;

        public bool Busy => _fly != Fly.Home || _follow != null;

        // kanatlar (res_mavi: wing_l / wing_r alt nesneleri; yoksa yalnız gövde yalpası)
        private Transform _wingL, _wingR;
        private Quaternion _wingL0, _wingR0;
        private float _flap;   // 0 dinlenme … 1 tam çırpma (yumuşak geçiş)

        // Hover: Okti'nin başının yanında (kameraya göre sağ üst), süre dolunca eve döner
        private float _hoverFor, _petTop = 1.4f;
        private Camera _cam;

        // Follow (Kıskaç): Okti'nin yanında yürür (rehberde panoya birlikte gidilir)
        private Transform _follow;
        private float _walkPhase;

        public static Resident3D Create(Transform parent, string who, string model, Vector3 local, float height, float yaw,
            Func<float, float, float> ground, Transform pet, bool flyer = false)
        {
            var root = new GameObject("resident_" + who).transform;
            root.SetParent(parent, false);
            root.localPosition = local;
            var m = RealAssets.Env(model, root, height);
            if (m == null) { Destroy(root.gameObject); return null; }
            var r = root.gameObject.AddComponent<Resident3D>();
            r.Who = who; r._model = m; r._modelBase = m.localPosition; r._modelScale = m.localScale; r._home = local;
            r._homeYaw = r._yaw = yaw; r._ground = ground; r._pet = pet; r._flyer = flyer;
            r._seed = (who.GetHashCode() & 255) / 40f;
            root.localRotation = Quaternion.Euler(0f, yaw, 0f);
            r._wingL = Deep(m, "wing_l"); r._wingR = Deep(m, "wing_r");
            if (r._wingL != null) r._wingL0 = r._wingL.localRotation;
            if (r._wingR != null) r._wingR0 = r._wingR.localRotation;
            var col = root.gameObject.AddComponent<CapsuleCollider>();
            col.center = new Vector3(0f, height * 0.5f, 0f); col.height = height * 1.2f; col.radius = height * 0.55f;
            foreach (var mr in m.GetComponentsInChildren<MeshRenderer>()) mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.On;
            return r;
        }

        /// <summary>Dokununca: küçük zıplama + sallanma.</summary>
        public void React()
        {
            _hop = 0f;
            Audio.Sfx.Play(Audio.SfxKind.Chime);
        }

        /// <summary>N2: Okti'nin önünde, hedefe doğru uç (her kare çağrılabilir; hedef değişirse izler).</summary>
        public void Guide(Vector3 petLocal, Vector3 targetLocal)
        {
            if (!_flyer) return;
            _target = targetLocal;
            var d = new Vector3(targetLocal.x - petLocal.x, 0f, targetLocal.z - petLocal.z);
            var len = d.magnitude;
            // Okti'den en çok 6 m önde, hedefe yaklaşınca hedefin üstünde
            var ahead = len < 0.01f ? targetLocal : petLocal + d / len * Mathf.Min(6f, len);
            _guideAt = ahead;
            if (_fly == Fly.Home || _fly == Fly.Back) _fly = Fly.Guide;
        }

        private Vector3 _guideAt;
        private float? _homeYawOverride;

        /// <summary>N2 bitti (vardı ya da adım değişti): hedefe kon, biraz bekle, eve dön.</summary>
        public void EndGuide(bool arrived)
        {
            if (_fly != Fly.Guide) return;
            if (arrived) { _fly = Fly.Land; _landFor = 2.2f; }
            else _fly = Fly.Back;
        }

        /// <summary>Kondurduysa biraz daha kalsın (hikâye konuşması bitene kadar).</summary>
        public void Linger(float seconds)
        {
            if (_fly == Fly.Land) _landFor = Mathf.Max(_landFor, seconds);
            if (_fly == Fly.Hover) _hoverFor = Mathf.Max(_hoverFor, seconds);
        }

        /// <summary>
        /// Okti'nin başının yanında, kameraya göre sağ üstte kanat çırparak süzül (<paramref name="seconds"/> sn; her çağrı uzatır).
        /// <paramref name="petTop"/>: Okti'nin boyu (m). Uçan adalı değilse yok sayılır.
        /// </summary>
        public void Hover(float seconds, float petTop, Camera cam)
        {
            if (!_flyer || _pet == null) return;
            _petTop = petTop; _cam = cam;
            _hoverFor = Mathf.Max(_hoverFor, seconds);
            _fly = Fly.Hover;
        }

        /// <summary>Gökyüzünden gelsin: önce bu noktaya (yerel) konur, sonra uçarak yaklaşır (kadrajın içinden görünerek gelir).</summary>
        public void Appear(Vector3 local) { transform.localPosition = local; }

        /// <summary>Okti'nin yanında yürü (null: eve dön).</summary>
        public void Follow(Transform pet)
        {
            _follow = pet;
        }

        /// <summary>Uzaktaysa Okti'nin yanına "pof" diye gelir (yerel konum).</summary>
        public void Teleport(Vector3 local) { transform.localPosition = local; _hop = 0f; }

        private void Update()
        {
            var dt = Time.deltaTime;
            _t += dt;
            // dünya içi konum (uçan ise)
            if (_flyer) UpdateFly(dt);
            else UpdateFollow(dt);
            var p = transform.localPosition;
            // Okti'ye dönme (yakınsa), yoksa evdeki yöne
            var wantYaw = _homeYaw;
            if (_fly == Fly.Guide || _fly == Fly.Back)
            {
                var v = (_fly == Fly.Guide ? _guideAt : _home) - p;
                if (new Vector2(v.x, v.z).sqrMagnitude > 0.04f) wantYaw = Mathf.Atan2(v.x, v.z) * Mathf.Rad2Deg;
            }
            else if (_fly == Fly.Hover && _homeYawOverride.HasValue) wantYaw = _homeYawOverride.Value;
            else if (_walkTo.HasValue)
            {
                var v = _walkTo.Value - p;
                if (new Vector2(v.x, v.z).sqrMagnitude > 0.04f) wantYaw = Mathf.Atan2(v.x, v.z) * Mathf.Rad2Deg;
            }
            else if (_pet != null && !Rooted)   // palmiyeler kökünden döner gibi olmasın
            {
                var lp = transform.parent.InverseTransformPoint(_pet.position) - p;
                var dist = new Vector2(lp.x, lp.z).magnitude;
                if (dist < 7f && dist > 0.3f) wantYaw = Mathf.Atan2(lp.x, lp.z) * Mathf.Rad2Deg;
            }
            _yaw = Mathf.MoveTowardsAngle(_yaw, wantYaw, dt * 160f);
            transform.localRotation = Quaternion.Euler(0f, _yaw, 0f);

            // kendi canlılığı
            var hopY = 0f; var wiggle = 0f;
            if (_hop >= 0f)
            {
                _hop += dt / 0.55f;
                var k = Mathf.Clamp01(_hop);
                hopY = Mathf.Sin(k * Mathf.PI) * 0.32f;
                wiggle = Mathf.Sin(k * Mathf.PI * 4f) * (1f - k) * 10f;
                if (_hop >= 1f) _hop = -1f;
            }
            var t = _t + _seed;
            var off = Vector3.zero; var rot = Quaternion.identity; var sc = Vector3.one;
            switch (Who)
            {
                case "kiskac":   // yan yan sallanır, arada kıskaç selamı gibi eğilir; yürürken tıpış tıpış zıplar
                    if (_walkTo.HasValue)
                    {
                        off.y = Mathf.Abs(Mathf.Sin(_walkPhase)) * 0.08f;
                        rot = Quaternion.Euler(0f, 0f, Mathf.Sin(_walkPhase) * 7f + wiggle);
                        break;
                    }
                    off.x = Mathf.Sin(t * 1.4f) * 0.05f;
                    rot = Quaternion.Euler(0f, 0f, Mathf.Sin(t * 1.4f) * 4f + wiggle);
                    break;
                case "mavi":     // başını çevirir gibi gövde dönüşü, minik sekme; uçarken kanat çırpar, havada süzülürken iner kalkar
                    if (_fly == Fly.Hover) { off.y = Mathf.Sin(t * 3.1f) * 0.12f; rot = Quaternion.Euler(4f, 0f, Mathf.Sin(t * 1.7f) * 6f + wiggle); }
                    else if (_fly == Fly.Guide || _fly == Fly.Back) rot = Quaternion.Euler(10f, 0f, Mathf.Sin(t * 14f) * 6f);
                    else
                    {
                        off.y = Mathf.Max(0f, Mathf.Sin(t * 2.2f)) * 0.025f;
                        rot = Quaternion.Euler(0f, Mathf.Sin(t * 0.7f) * 14f, wiggle);
                    }
                    break;
                case "tosbi":    // yaşlı kaplumbağa: ağır ağır başını sallar, alçak zıplar
                    hopY *= 0.45f;
                    rot = Quaternion.Euler(Mathf.Sin(t * 0.8f) * 3f, Mathf.Sin(t * 0.35f) * 6f, wiggle * 0.6f);
                    break;
                case "pitir":    // geveze palmiye: rüzgârda canlı sallanır; dokununca titrer (zıplamaz)
                    hopY = 0f;
                    rot = Quaternion.Euler(Mathf.Sin(t * 1.3f) * 1.5f, 0f, Mathf.Sin(t * 0.9f) * 3.5f + wiggle * 1.4f);
                    break;
                case "hisir":    // utangaç palmiye: yavaş, küçük salınım, arada hafifçe yana bakar
                    hopY = 0f;
                    rot = Quaternion.Euler(0f, Mathf.Sin(t * 0.4f) * 5f, Mathf.Sin(t * 0.7f) * 2f + wiggle);
                    break;
                default:         // Pus: süzülür, nefes alır gibi esner
                    off.y = Mathf.Sin(t * 0.9f) * 0.18f;
                    var s = Mathf.Sin(t * 1.8f) * 0.035f;
                    sc = new Vector3(1f + s, 1f - s, 1f + s);
                    rot = Quaternion.Euler(0f, 0f, Mathf.Sin(t * 0.6f) * 3f + wiggle);
                    break;
            }
            _model.localPosition = _modelBase + off + Vector3.up * hopY;
            _model.localRotation = rot;
            _model.localScale = Vector3.Scale(_modelScale, sc);
            Flap(dt);
        }

        /// <summary>Kanat çırpma: uçarken hızlı (≈3 kez/sn), süzülürken daha yavaş ve geniş; yerde arada bir küçük kanat silkme.</summary>
        private void Flap(float dt)
        {
            if (_wingL == null && _wingR == null) return;
            var flying = _fly == Fly.Guide || _fly == Fly.Back || _fly == Fly.Hover || (_fly == Fly.Land && transform.localPosition.y > Ground(transform.localPosition.x, transform.localPosition.z) + 0.3f);
            _flap = Mathf.MoveTowards(_flap, flying ? 1f : 0f, dt * 3f);
            var speed = _fly == Fly.Hover ? 13f : 19f;
            var a = _flap * (Mathf.Sin(_t * speed) * 0.5f + 0.5f) * 62f;
            if (!flying && _flap < 0.01f) a = Mathf.Max(0f, Mathf.Sin(_t * 9f)) * (Mathf.Repeat(_t + _seed, 6f) < 0.7f ? 14f : 0f);   // yerde kanat silkme
            if (_wingL != null) _wingL.localRotation = _wingL0 * Quaternion.AngleAxis(a * WingSign, WingAxis);
            if (_wingR != null) _wingR.localRotation = _wingR0 * Quaternion.AngleAxis(-a * WingSign, WingAxis);
        }

        /// <summary>Kanadı dışarı/yukarı açan yerel eksen ve yön (res_mavi kanat dönme noktası omuzda).</summary>
        public static Vector3 WingAxis = Vector3.forward;
        public static float WingSign = 1f;

        private static Transform Deep(Transform t, string name)
        {
            if (t.name == name) return t;
            for (var i = 0; i < t.childCount; i++) { var r = Deep(t.GetChild(i), name); if (r != null) return r; }
            return null;
        }

        private Vector3? _walkTo;

        /// <summary>Kıskaç Okti'nin yanında yürür (Follow); bırakılınca evine yürür, varınca durur.</summary>
        private void UpdateFollow(float dt)
        {
            Vector3? goal = null;
            var cur = transform.localPosition;
            if (_follow != null)
            {
                var pp = transform.parent.InverseTransformPoint(_follow.position);
                var fwd = transform.parent.InverseTransformDirection(_follow.forward); fwd.y = 0f;
                fwd = fwd.sqrMagnitude > 0.01f ? fwd.normalized : Vector3.forward;
                var side = new Vector3(fwd.z, 0f, -fwd.x);                    // Okti'nin sağı
                var want = pp + side * 1.5f - fwd * 0.4f;
                if (new Vector2(want.x - cur.x, want.z - cur.z).magnitude > 0.6f) goal = want;
            }
            else if (new Vector2(_home.x - cur.x, _home.z - cur.z).magnitude > 0.3f && _walkTo.HasValue) goal = _home;
            _walkTo = goal;
            if (!goal.HasValue) return;
            var g = goal.Value;
            var d = new Vector2(g.x - cur.x, g.z - cur.z);
            var sp = Mathf.Clamp(d.magnitude * 2.2f, 1.2f, 4.6f);
            var step = Vector2.ClampMagnitude(d, sp * dt);
            var nx = cur.x + step.x; var nz = cur.z + step.y;
            transform.localPosition = new Vector3(nx, _ground != null ? _ground(nx, nz) : cur.y, nz);
            _walkPhase += dt * sp * 4.5f;
        }


        private void UpdateFly(float dt)
        {
            var cur = transform.localPosition;
            switch (_fly)
            {
                case Fly.Guide:
                {
                    var g = _guideAt; g.y = Ground(g.x, g.z) + 2.6f;
                    transform.localPosition = Vector3.MoveTowards(cur, g, dt * 7f);
                    break;
                }
                case Fly.Hover:
                {
                    if (_pet == null || (_hoverFor -= dt) <= 0f) { _fly = Fly.Back; break; }
                    var pp = transform.parent.InverseTransformPoint(_pet.position);
                    var right = _cam != null ? transform.parent.InverseTransformDirection(_cam.transform.right) : Vector3.right;
                    right.y = 0f; right = right.sqrMagnitude > 0.01f ? right.normalized : Vector3.right;
                    var back = _cam != null ? transform.parent.InverseTransformDirection(-_cam.transform.forward) : Vector3.back;
                    back.y = 0f; back = back.sqrMagnitude > 0.01f ? back.normalized : Vector3.back;
                    var g = pp + right * 0.95f + back * 0.25f + Vector3.up * (_petTop + 0.35f);
                    transform.localPosition = Vector3.Lerp(cur, g, 1f - Mathf.Exp(-4f * dt));
                    // Okti'nin baktığı yöne bakar (birlikte gidiyorlar)
                    var f = transform.parent.InverseTransformDirection(_pet.forward);
                    if (new Vector2(f.x, f.z).sqrMagnitude > 0.01f) _homeYawOverride = Mathf.Atan2(f.x, f.z) * Mathf.Rad2Deg;
                    break;
                }
                case Fly.Land:
                {
                    var g = _target; g.y = Ground(g.x, g.z) + 0.05f;
                    transform.localPosition = Vector3.MoveTowards(cur, g, dt * 5f);
                    if (Vector3.Distance(transform.localPosition, g) < 0.05f && (_landFor -= dt) <= 0f) _fly = Fly.Back;
                    break;
                }
                case Fly.Back:
                {
                    // eve yüksekten dön, son metrede alçal
                    var h = _home;
                    var flat = new Vector2(h.x - cur.x, h.z - cur.z).magnitude;
                    var g = flat > 1.2f ? new Vector3(h.x, Ground(h.x, h.z) + 2.6f, h.z) : h;
                    transform.localPosition = Vector3.MoveTowards(cur, g, dt * 7f);
                    if (Vector3.Distance(transform.localPosition, h) < 0.05f) { transform.localPosition = h; _fly = Fly.Home; }
                    break;
                }
            }
        }

        /// <summary>Yere kök salmış adalı (konuşan palmiyeler Pıtır, Hışır): Okti'ye dönmez, zıplamaz, sallanır.</summary>
        private bool Rooted => Who == "pitir" || Who == "hisir";

        private float Ground(float x, float z) => _ground != null ? Mathf.Max(0f, _ground(x, z)) : 0f;
    }
}
