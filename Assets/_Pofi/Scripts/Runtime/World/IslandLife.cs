using System.Collections.Generic;
using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// Büyük ada (v6) süsleri 24 m'lik hücrelere ayrılır; kameradan uzak hücreler kapatılır (iPhone üçgen/çizim bütçesi).
    /// Kuşbakışında yarıçap büyür (bütün ada görünür, uzaktan bakıldığı için ayrıntı az fark edilir).
    /// </summary>
    public sealed class PropCuller : MonoBehaviour
    {
        public const float CellSize = 24f;
        /// <summary>Görünür yarıçap (m). MapScreen kuşbakışında büyütür.</summary>
        public static float Radius = 95f;
        private readonly Dictionary<long, Transform> _cells = new Dictionary<long, Transform>();
        private float _t;

        public Transform Cell(Transform parent, float x, float z)
        {
            var ci = Mathf.FloorToInt(x / CellSize); var cj = Mathf.FloorToInt(z / CellSize);
            var key = ((long)ci << 32) ^ (uint)cj;
            if (_cells.TryGetValue(key, out var c)) return c;
            c = new GameObject("cell_" + ci + "_" + cj).transform;
            c.SetParent(parent, false);
            c.localPosition = new Vector3((ci + 0.5f) * CellSize, 0f, (cj + 0.5f) * CellSize);
            _cells[key] = c;
            return c;
        }

        private void Update()
        {
            _t -= Time.unscaledDeltaTime;
            if (_t > 0f) return;
            _t = 0.25f;
            var cam = Camera.main;
            if (cam == null) return;
            var p = transform.InverseTransformPoint(cam.transform.position);
            var f = transform.InverseTransformDirection(cam.transform.forward);
            var look = new Vector2(p.x + f.x * 30f, p.z + f.z * 30f);   // önü (bakılan yer) merkez: arkadaki hücreler daha erken kapanır
            var r2 = Radius * Radius;
            foreach (var c in _cells.Values)
            {
                var lp = c.localPosition;
                var on = (new Vector2(lp.x, lp.z) - look).sqrMagnitude < r2;
                if (c.gameObject.activeSelf != on) c.gameObject.SetActive(on);
            }
        }
    }

    /// <summary>
    /// Kamera önünü açık tutar (geri bildirim 11, 22 Ekim 2026: patikada ağaçlar görüşü kapatıyordu): kamerayla pet arasındaki
    /// çizgiye giren ağaç/iri kaya titreşimli soldurmayla (Pofi/Toon _Fade) yumuşakça kaybolur, çizgiden çıkınca geri gelir.
    /// Soldurma yalnız o anda değişen nesnelerde MaterialPropertyBlock ile; tam görünürken blok kaldırılır (SRP toplu çizimi bozulmaz).
    /// </summary>
    public sealed class CameraClear : MonoBehaviour
    {
        private sealed class Entry { public Renderer[] R; public Vector2 C; public float Rad, Y0, Y1, Fade = 1f, Target = 1f; }
        private const float Cell = 8f;
        private readonly Dictionary<long, List<Entry>> _grid = new Dictionary<long, List<Entry>>();
        private readonly List<Entry> _active = new List<Entry>();
        private MapWorld _world;
        private MaterialPropertyBlock _mpb;
        private static readonly int FadeId = Shader.PropertyToID("_Fade");

        public void Init(MapWorld world) { _world = world; _mpb = new MaterialPropertyBlock(); }

        public void Add(Transform t)
        {
            var rs = t.GetComponentsInChildren<Renderer>(true);
            if (rs.Length == 0) return;
            var b = rs[0].bounds;
            for (var i = 1; i < rs.Length; i++) b.Encapsulate(rs[i].bounds);
            var e = new Entry { R = rs, C = new Vector2(b.center.x, b.center.z), Rad = Mathf.Max(b.extents.x, b.extents.z) * 0.8f, Y0 = b.min.y, Y1 = b.max.y };
            var key = Key(Mathf.FloorToInt(e.C.x / Cell), Mathf.FloorToInt(e.C.y / Cell));
            if (!_grid.TryGetValue(key, out var l)) _grid[key] = l = new List<Entry>();
            l.Add(e);
        }

        private static long Key(int i, int j) => ((long)i << 32) ^ (uint)j;

        private void LateUpdate()
        {
            var cam = Camera.main;
            if (cam == null || _world == null || _world.Walker == null) return;
            var a = cam.transform.position;
            var b = _world.Walker.transform.position + Vector3.up * 0.9f;
            // çizgi yakınındaki hücreler: hedefe yeni giren nesneler aday
            var mn = Vector2.Min(new Vector2(a.x, a.z), new Vector2(b.x, b.z)) - Vector2.one * 6f;
            var mx = Vector2.Max(new Vector2(a.x, a.z), new Vector2(b.x, b.z)) + Vector2.one * 6f;
            foreach (var e in _active) e.Target = 1f;
            var near = (a - b).sqrMagnitude < 30f * 30f;                       // kuşbakışında (uzak kamera) soldurma yok
            if (near)
            for (var i = Mathf.FloorToInt(mn.x / Cell); i <= Mathf.FloorToInt(mx.x / Cell); i++)
            for (var j = Mathf.FloorToInt(mn.y / Cell); j <= Mathf.FloorToInt(mx.y / Cell); j++)
            {
                if (!_grid.TryGetValue(Key(i, j), out var l)) continue;
                foreach (var e in l)
                {
                    if (!e.R[0].gameObject.activeInHierarchy) continue;
                    if (!Blocks(e, a, b)) continue;
                    e.Target = 0f;   // tam kaybolur: 0,15 bırakınca büyük yaprak kartları gökyüzünde noktalı karo gibi kalıyordu
                    if (!_active.Contains(e)) _active.Add(e);
                }
            }
            var k = 1f - Mathf.Exp(-9f * Time.deltaTime);
            for (var n = _active.Count - 1; n >= 0; n--)
            {
                var e = _active[n];
                e.Fade = Mathf.Abs(e.Fade - e.Target) < 0.01f ? e.Target : Mathf.Lerp(e.Fade, e.Target, k);
                if (e.Fade >= 0.999f)
                {
                    foreach (var r in e.R) if (r != null) r.SetPropertyBlock(null);
                    _active.RemoveAt(n);
                    continue;
                }
                _mpb.SetFloat(FadeId, e.Fade);
                foreach (var r in e.R) if (r != null) r.SetPropertyBlock(_mpb);
            }
        }

        /// <summary>Kamera–pet doğru parçası nesnenin dikey silindirinden (taban–tepe, yarıçap) geçiyor mu? Parçanın silindir
        /// içindeki bütün aralığı denenir (GB19 çekimi: tacı petin üstüne taşan ağaçta en yakın nokta pet hizasında kalıyor,
        /// kameraya yakın kısım tacı kesse de solmuyordu). Petin hemen yanı (son %8) sayılmaz: yanındaki çalı yerinde kalır.</summary>
        private static bool Blocks(Entry e, Vector3 a, Vector3 b)
        {
            var a2 = new Vector2(a.x, a.z);
            var ab = new Vector2(b.x - a.x, b.z - a.z); var l2 = ab.sqrMagnitude;
            if (l2 < 1e-4f) return false;
            var r = e.Rad + 0.35f;
            var f = a2 - e.C;
            var bq = Vector2.Dot(f, ab); var cq = f.sqrMagnitude - r * r;
            var disc = bq * bq - l2 * cq;
            if (disc < 0f) return false;
            var s = Mathf.Sqrt(disc);
            var t0 = Mathf.Max(0f, (-bq - s) / l2); var t1 = Mathf.Min(0.92f, (-bq + s) / l2);
            if (t0 > t1) return false;
            var yHi = Mathf.Lerp(a.y, b.y, t0); var yLo = Mathf.Lerp(a.y, b.y, t1);
            if (yHi < yLo) { var q = yHi; yHi = yLo; yLo = q; }
            return yHi > e.Y0 + 0.2f && yLo < e.Y1;
        }
    }

    /// <summary>Kıyı yengeci (madde 10, kullanıcı): pet yaklaşınca yan yan denize koşar ve kaybolur; pet uzaklaşınca bir süre sonra yerine döner.</summary>
    public sealed class CrabFlee : MonoBehaviour
    {
        private MapWorld _world;
        private Vector3 _home;
        private Vector2 _dir;
        private float _hidden, _scuttle, _wanderT = 3f;
        private Vector3 _wanderTo;
        private bool _wandering;
        private enum State { Idle, Flee, Gone }
        private State _state;

        public void Init(MapWorld world) { _world = world; _home = transform.localPosition; CrabLegs.Attach(transform); }

        /// <summary>Kaçarken bacaklar (CrabLegs) hızlanır, gözler yatar, kıskaçlar havaya kalkar.</summary>
        public bool Fleeing => _state == State.Flee;

        /// <summary>Dokununca (O4): dokunulan yerden uzağa, denize doğru kaçar.</summary>
        public void Scare(Vector2 from)
        {
            if (_state != State.Idle || _world == null) return;
            var parent = transform.parent;
            var wpos = parent != null ? parent.localPosition + transform.localPosition : transform.localPosition;
            var me = new Vector2(wpos.x, wpos.z);
            var away = me - from; if (away.sqrMagnitude < 0.01f) away = Random.insideUnitCircle;
            var e = 1.5f;
            var grad = new Vector2(_world.Terrain.Height(me.x + e, me.y) - _world.Terrain.Height(me.x - e, me.y),
                                   _world.Terrain.Height(me.x, me.y + e) - _world.Terrain.Height(me.x, me.y - e));
            _dir = (away.normalized - grad.normalized).normalized;
            if (_dir.sqrMagnitude < 0.01f) _dir = away.normalized;
            _state = State.Flee;
            GetComponent<CrabLegs>()?.Snap();
            Audio.Sfx.Play(Audio.SfxKind.Pop);
        }

        private void Update()
        {
            if (_world == null || _world.Walker == null) return;
            var parent = transform.parent;
            var wpos = parent != null ? parent.localPosition + transform.localPosition : transform.localPosition;
            var me = new Vector2(wpos.x, wpos.z);
            var pet = _world.Walker.Position;
            var dist = Vector2.Distance(me, pet);
            switch (_state)
            {
                case State.Idle:
                    // ara sıra yerinde kıpırdar; 4–9 sn'de bir evinin çevresinde birkaç adım yan yürür (bacaklar CrabLegs ile adım atar)
                    _scuttle += Time.deltaTime;
                    transform.localRotation = Quaternion.Euler(0f, transform.localEulerAngles.y + Mathf.Sin(_scuttle * 3f) * 0.3f, 0f);
                    if (!_wandering && (_wanderT -= Time.deltaTime) <= 0f)
                    {
                        var sideDir = transform.localRotation * Vector3.right;
                        _wanderTo = _home + sideDir * (Random.value < 0.5f ? -1f : 1f) * Random.Range(0.25f, 0.6f);
                        _wanderTo.y = _home.y;
                        _wandering = true;
                    }
                    if (_wandering)
                    {
                        var lp0 = transform.localPosition;
                        var to = new Vector3(_wanderTo.x, lp0.y, _wanderTo.z);
                        var nxt = Vector3.MoveTowards(lp0, to, 0.7f * Time.deltaTime);
                        var py0 = parent != null ? parent.localPosition : Vector3.zero;
                        nxt.y = _world.Terrain.Height(nxt.x + py0.x, nxt.z + py0.z) + 0.04f - py0.y;
                        transform.localPosition = nxt;
                        if ((new Vector2(nxt.x - to.x, nxt.z - to.z)).sqrMagnitude < 0.0004f) { _wandering = false; _wanderT = Random.Range(4f, 9f); }
                    }
                    if (dist < 3.5f)
                    {
                        // denize doğru: araziyi alçalan yöne, petten uzağa
                        var away = (me - pet).normalized;
                        var e = 1.5f;
                        var grad = new Vector2(_world.Terrain.Height(me.x + e, me.y) - _world.Terrain.Height(me.x - e, me.y),
                                               _world.Terrain.Height(me.x, me.y + e) - _world.Terrain.Height(me.x, me.y - e));
                        _dir = (away - grad.normalized * 1.5f).normalized;
                        if (_dir.sqrMagnitude < 0.01f) _dir = away;
                        _state = State.Flee;
                    }
                    break;
                case State.Flee:
                    var step = _dir * 2.4f * Time.deltaTime;
                    me += step;
                    var h = _world.Terrain.Height(me.x, me.y);
                    transform.localPosition += new Vector3(step.x, 0f, step.y);
                    var lp = transform.localPosition;
                    var py = parent != null ? parent.localPosition.y : 0f;
                    transform.localPosition = new Vector3(lp.x, h + 0.04f - py, lp.z);
                    // yengeç yan yürür: gövde yönü hareket yönüne dik
                    var yaw = Mathf.Atan2(_dir.x, _dir.y) * Mathf.Rad2Deg + 90f;
                    transform.localRotation = Quaternion.Euler(0f, yaw, Mathf.Sin(Time.time * 40f) * 4f);
                    if (h < -0.05f || Vector2.Distance(me, pet) > 14f)
                    {
                        _state = State.Gone; _hidden = 0f;
                        foreach (var r in GetComponentsInChildren<Renderer>()) r.enabled = false;
                    }
                    break;
                case State.Gone:
                    _hidden += Time.deltaTime;
                    if (_hidden > 25f && dist > 12f)
                    {
                        transform.localPosition = _home;
                        _wandering = false; _wanderT = Random.Range(3f, 7f);
                        foreach (var r in GetComponentsInChildren<Renderer>()) r.enabled = true;
                        _state = State.Idle;
                    }
                    break;
            }
        }
    }

    /// <summary>
    /// Yengeç v2'nin canlı parçaları (26 Ekim 2026, kullanıcı: "hareket eden yengeçler daha gerçekçi"; art/code3d/crab_v2.py):
    /// modelde ayrı nesne olan 8 bacak (leg_a0..3, leg_b0..3), 2 kıskaç (claw_a/b), oynar parmaklar (finger_a/b, burada kıskaca bağlanır)
    /// ve göz sapları (eye_a/b) eklem yerlerinden döndürülür. Yürürken dörtlü adım (çapraz bacak grupları sırayla kalkar), dururken
    /// ara sıra bacak tıklatma, kıskaç sallama/açıp kapama, göz seğirmesi; kaçarken gözler yatar, kıskaçlar havaya kalkar.
    /// Eksenler kök yengeçe göre bir kez hesaplanır (Blender → FBX → Unity eksen çevirisinden bağımsız).
    /// </summary>
    public sealed class CrabLegs : MonoBehaviour
    {
        private struct Limb { public Transform T; public Quaternion Rest; public Vector3 Up, Lift; public float Phase; public int Kind; }
        private Limb[] _limbs;
        private Vector3 _last;
        private float _speed, _gait, _t, _show, _snap;
        private CrabFlee _flee;

        public static void Attach(Transform root)
        {
            if (root == null || root.GetComponent<CrabLegs>() != null) return;
            root.gameObject.AddComponent<CrabLegs>();
        }

        /// <summary>Dokunulunca / ürkünce kıskaçlar şak diye açılıp kapanır.</summary>
        public void Snap() => _snap = 1f;

        private void Start()
        {
            _flee = GetComponent<CrabFlee>();
            Transform body = null;
            var all = GetComponentsInChildren<Transform>(true);
            foreach (var t in all) if (t.name == "body") body = t;
            if (body == null) { enabled = false; return; }   // eski tek parça model: oynatacak parça yok
            foreach (var t in all)
                if (t.name.StartsWith("finger_"))
                    foreach (var c in all) if (c.name == "claw_" + t.name.Substring(7)) { t.SetParent(c, true); break; }
            var list = new List<Limb>();
            foreach (var t in all)
            {
                var n = t.name;
                var kind = n.StartsWith("leg_") ? 0 : n.StartsWith("claw_") ? 1 : n.StartsWith("finger_") ? 2 : n.StartsWith("eye_") ? 3 : -1;
                if (kind < 0) continue;
                var p = t.parent;
                var up = p.InverseTransformDirection(transform.up).normalized;
                var origin = kind == 2 ? Vector3.zero : p.InverseTransformPoint(body.position);   // parmak: kıskacın orijininden menteşeye
                var outward = Vector3.ProjectOnPlane(t.localPosition - origin, up);
                if (outward.sqrMagnitude < 1e-8f) outward = Vector3.Cross(up, Vector3.right);
                outward.Normalize();
                var lift = Vector3.Cross(up, outward).normalized;
                // pozitif açı uzvu kaldırsın (yönü eksen çevirisinden bağımsız sına)
                if (Vector3.Dot(Quaternion.AngleAxis(10f, lift) * outward, up) < 0f) lift = -lift;
                var side = n.Length > 0 && n[n.Length - (kind == 0 ? 2 : 1)] == 'a' ? 0 : 1;
                var idx = kind == 0 ? n[n.Length - 1] - '0' : 0;
                var phase = kind == 0 ? ((idx + side) % 2) * Mathf.PI : side * 1.7f;
                list.Add(new Limb { T = t, Rest = t.localRotation, Up = up, Lift = lift, Phase = phase + (kind == 0 ? idx * 0.15f : 0f), Kind = kind });
            }
            _limbs = list.ToArray();
            _last = transform.position;
            _t = Random.value * 10f;
        }

        private void Update()
        {
            if (_limbs == null) return;
            var dt = Time.deltaTime;
            if (dt <= 0f) return;
            _t += dt;
            var pos = transform.position;
            var v = (pos - _last).magnitude / dt / Mathf.Max(0.01f, transform.lossyScale.y);   // yengeç boyuna göre (yavru da aynı adımla)
            _last = pos;
            _speed = Mathf.Lerp(_speed, Mathf.Min(v, 30f), 1f - Mathf.Exp(-8f * dt));
            var moving = _speed > 0.4f;
            var flee = (_flee != null && _flee.Fleeing) || _speed > 6f;
            _gait += dt * (moving ? Mathf.Clamp(6f + _speed * 0.9f, 6f, 22f) : 0f);
            _show = Mathf.Max(0f, _show - dt);
            if (!moving && _show <= 0f && Random.value < dt * 0.12f) _show = 1.6f;   // ara sıra kıskaçlarını kaldırıp sallar
            _snap = Mathf.Max(0f, _snap - dt * 3f);
            foreach (var l in _limbs)
            {
                float lift = 0f, swing = 0f;
                switch (l.Kind)
                {
                    case 0:   // bacak
                        if (moving) { var g = _gait + l.Phase; lift = Mathf.Max(0f, Mathf.Sin(g)) * 26f; swing = Mathf.Cos(g) * 14f; }
                        else lift = Mathf.Pow(Mathf.Max(0f, Mathf.Sin(_t * 2.1f + l.Phase * 3.1f)), 12f) * 9f;   // tık tık
                        break;
                    case 1:   // kıskaç
                        lift = flee ? 24f : _show > 0f ? Mathf.Sin(Mathf.Clamp01(_show / 1.6f) * Mathf.PI) * 30f + Mathf.Sin(_t * 9f + l.Phase) * 5f
                                                       : (Mathf.Sin(_t * 0.8f + l.Phase) * 0.5f + 0.5f) * 8f;
                        swing = Mathf.Sin(_t * 0.6f + l.Phase) * 5f;
                        break;
                    case 2:   // oynar parmak: açıp kapar
                        var open = Mathf.Sin(_t * 1.6f + l.Phase) > 0.55f || _show > 0f ? 20f : 3f;
                        lift = Mathf.Max(open, _snap * 28f);
                        break;
                    case 3:   // göz sapı: seğirir, kaçarken yatar
                        lift = flee ? -38f : Mathf.Sin(_t * 2.7f + l.Phase) * 3f + (Mathf.Sin(_t * 0.37f + l.Phase) > 0.97f ? -20f : 0f);
                        swing = Mathf.Sin(_t * 1.3f + l.Phase) * 6f;
                        break;
                }
                l.T.localRotation = Quaternion.AngleAxis(lift, l.Lift) * Quaternion.AngleAxis(swing, l.Up) * l.Rest;
            }
        }
    }

    /// <summary>Kamp ateşi (madde 4): canlı alev dilleri (Pofi/Flame, kodla) + titreşen sıcak ışık. Fener ışığı gibi değil: alçak, turuncu, kısa menzil.</summary>
    public sealed class Campfire : MonoBehaviour
    {
        private Light _light;
        private float _base;

        public static void Light(Transform fire, float scale)
        {
            var sh = Shader.Find("Pofi/Flame");
            if (sh != null)
            {
                var mat = new Material(sh);
                var mesh = FlameMesh();
                var rnd = new System.Random(4);
                for (var k = 0; k < 7; k++)
                {
                    var go = new GameObject("flame");
                    go.transform.SetParent(fire, false);
                    var a = k * 2.4f; var r = k == 0 ? 0f : 0.12f + 0.1f * (float)rnd.NextDouble();
                    var s = (k == 0 ? 1.25f : 0.7f + 0.35f * (float)rnd.NextDouble()) * scale;
                    go.transform.localPosition = new Vector3(Mathf.Cos(a) * r * scale, 0.08f * scale, Mathf.Sin(a) * r * scale);
                    go.transform.localScale = new Vector3(0.55f * s, 1.0f * s, 0.55f * s);
                    go.transform.localRotation = Quaternion.Euler(0f, (float)rnd.NextDouble() * 360f, 0f);
                    go.AddComponent<MeshFilter>().sharedMesh = mesh;
                    var mr = go.AddComponent<MeshRenderer>();
                    var m = new Material(mat); m.SetFloat("_Seed", k * 3.7f);
                    mr.sharedMaterial = m;
                    mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                    mr.receiveShadows = false;
                }
            }
            var lgo = new GameObject("fire_light");
            lgo.transform.SetParent(fire, false);
            lgo.transform.localPosition = new Vector3(0f, 0.6f * scale, 0f);
            var l = lgo.AddComponent<Light>();
            l.type = LightType.Point; l.color = new Color(1f, 0.58f, 0.25f); l.range = 7f * scale; l.intensity = 1.6f; l.shadows = LightShadows.None;
            var c = fire.gameObject.AddComponent<Campfire>(); c._light = l; c._base = l.intensity;
            foreach (Transform ch in fire) if (ch.name == "flame") c._flames.Add((ch, ch.localScale));
            Instance = c;
        }

        /// <summary>Adadaki kamp ateşi (yoksa null).</summary>
        public static Campfire Instance { get; private set; }

        private float _boost, _heat;
        private readonly List<(Transform T, Vector3 S)> _flames = new List<(Transform, Vector3)>();

        /// <summary>Harla (GB18): alevler bir an büyür, ışık parlar; <paramref name="heat"/> 0..1 kalıcı coşku (saatler içinde söner).</summary>
        public void Stoke(float heat)
        {
            _boost = 1f; _heat = Mathf.Clamp01(heat);
        }

        /// <summary>Kayıttan gelen coşku (adaya girerken).</summary>
        public void SetHeat(float heat) => _heat = Mathf.Clamp01(heat);

        /// <summary>
        /// Zengin harlama (akış haritası yorumu, 25 Ekim 2026: "ateşin büyüme animasyonu daha profesyonel ve zengin"): Okti'den iki
        /// odun yay çizerek ateşe düşer; her düşüşte alev "huf" diye taşar, kıvılcımlar dönerek yükselir, yerde sıcak halka yayılır,
        /// ince duman süzülür; sonunda ateş coşkuyla büyük yanmaya devam eder. <paramref name="from"/>: Okti'nin elleri (dünya).
        /// </summary>
        public void StokeFx(Vector3 from, float heat, Sprite wood, Camera cam)
        {
            StartCoroutine(StokeRoutine(from, heat, wood, cam));
        }

        private System.Collections.IEnumerator StokeRoutine(Vector3 from, float heat, Sprite wood, Camera cam)
        {
            var to = transform.position + Vector3.up * 0.35f;
            for (var i = 0; i < 2; i++)
            {
                var log = WoodQuad(wood);
                for (var t = 0f; t < 1f; t += Time.deltaTime / 0.5f)
                {
                    var e = t * t * (3f - 2f * t);
                    log.position = Vector3.Lerp(from, to, e) + Vector3.up * Mathf.Sin(e * Mathf.PI) * 1.3f;
                    if (cam != null) log.rotation = Quaternion.LookRotation(log.position - cam.transform.position) * Quaternion.Euler(0f, 0f, t * 540f + i * 90f);
                    yield return null;
                }
                Destroy(log.gameObject);
                // düşüş: alev taşar, kıvılcım + halka + duman
                _boost = 1.25f; _heat = Mathf.Clamp01(Mathf.Max(_heat, heat * (i + 1) / 2f));
                Ripple.Spawn(transform.position + Vector3.up * 0.06f, 1.1f + i * 0.4f, 2, new Color(1f, 0.6f, 0.25f));
                for (var k = 0; k < 9; k++) StartCoroutine(Ember(k + i * 9));
                for (var k = 0; k < 3; k++) StartCoroutine(Smoke(k));
                Audio.Sfx.Play(Audio.SfxKind.Whoosh);
                yield return new WaitForSeconds(0.18f);
            }
            _heat = Mathf.Clamp01(heat);
        }

        private Transform WoodQuad(Sprite wood)
        {
            var q = GameObject.CreatePrimitive(PrimitiveType.Quad);
            Destroy(q.GetComponent<Collider>());
            q.name = "stoke_wood";
            q.transform.localScale = Vector3.one * 0.7f;
            var r = q.GetComponent<MeshRenderer>();
            r.sharedMaterial = InkHeart.SpriteMat(wood != null ? wood.texture : null);
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            return q.transform;
        }

        /// <summary>Kıvılcım: ateşin içinden dönerek yükselir, savrulur, söner (ParticleSystem yok).</summary>
        private System.Collections.IEnumerator Ember(int seed)
        {
            var rnd = new System.Random(seed * 7919 + (int)(Time.time * 10f));
            var g = GainFx.Glow(transform, new Color(1f, 0.55f + 0.3f * (float)rnd.NextDouble(), 0.15f), 1.2f, false);
            var a = (float)rnd.NextDouble() * Mathf.PI * 2f;
            var v = new Vector3(Mathf.Cos(a) * 0.6f, 2.2f + 1.6f * (float)rnd.NextDouble(), Mathf.Sin(a) * 0.6f);
            var p = new Vector3(Mathf.Cos(a) * 0.15f, 0.4f, Mathf.Sin(a) * 0.15f);
            var life = 0.9f + 0.7f * (float)rnd.NextDouble();
            var size = 0.12f + 0.1f * (float)rnd.NextDouble();
            for (var t = 0f; t < life; t += Time.deltaTime)
            {
                p += v * Time.deltaTime;
                v.y -= 0.8f * Time.deltaTime;
                v.x += Mathf.Sin(t * 9f + seed) * 1.4f * Time.deltaTime;
                g.localPosition = p;
                g.localScale = Vector3.one * size * (1f - t / life) * (0.8f + 0.4f * Mathf.Sin(t * 40f));
                yield return null;
            }
            Destroy(g.gameObject);
        }

        /// <summary>İnce duman topağı: yavaşça yükselir, büyür, söner.</summary>
        private System.Collections.IEnumerator Smoke(int k)
        {
            yield return new WaitForSeconds(0.15f * k);
            var g = GainFx.Glow(transform, new Color(0.55f, 0.52f, 0.5f), 0.35f, false);
            var p = new Vector3((k - 1) * 0.15f, 1.0f, 0f);
            for (var t = 0f; t < 1.6f; t += Time.deltaTime)
            {
                p += new Vector3(0.12f, 0.9f, 0.05f) * Time.deltaTime;
                g.localPosition = p;
                g.localScale = Vector3.one * Mathf.Lerp(0.3f, 1.1f, t / 1.6f) * (1f - t / 1.6f);
                yield return null;
            }
            Destroy(g.gameObject);
        }

        private void OnDestroy() { if (Instance == this) Instance = null; }

        private void Update()
        {
            if (_light == null) return;
            var t = Time.time;
            _boost = Mathf.MoveTowards(_boost, 0f, Time.deltaTime / 2.5f);
            // harlayınca alev boyu: önce taşar (1,25 üstü hızlı söner), sonra coşkuyla yanar; alevler hafifçe dalgalanır
            var over = Mathf.Max(0f, _boost - 1f) * 2.4f;
            var grow = 1f + 0.45f * _heat + 0.9f * Mathf.Sin(Mathf.Clamp01(_boost) * Mathf.PI * 0.5f) + over;
            var i = 0;
            foreach (var (f, s0) in _flames)
            {
                if (f == null) continue;
                var wob = 1f + 0.06f * Mathf.Sin(t * (7f + i) + i * 1.7f) * (0.4f + _heat);
                f.localScale = Vector3.Lerp(f.localScale, new Vector3(s0.x * (0.9f + 0.1f * grow), s0.y * grow * wob, s0.z * (0.9f + 0.1f * grow)), Time.deltaTime * 8f);
                i++;
            }
            _light.intensity = _base * (1f + 0.5f * _heat + 1.2f * _boost) * (0.82f + 0.12f * Mathf.Sin(t * 13f) + 0.08f * Mathf.Sin(t * 29f + 1.3f) + 0.06f * Mathf.PerlinNoise(t * 5f, 0.3f));
        }

        private static Mesh _flame;

        /// <summary>Üç çapraz dikey düzlem (alev dili; gölgelendirici biçimi ve hareketi verir).</summary>
        private static Mesh FlameMesh()
        {
            if (_flame != null) return _flame;
            var v = new List<Vector3>(); var uv = new List<Vector2>(); var t = new List<int>();
            for (var q = 0; q < 3; q++)
            {
                var a = q * Mathf.PI / 3f; var dx = Mathf.Cos(a) * 0.5f; var dz = Mathf.Sin(a) * 0.5f;
                var b = v.Count;
                v.Add(new Vector3(-dx, 0f, -dz)); v.Add(new Vector3(dx, 0f, dz)); v.Add(new Vector3(dx, 1f, dz)); v.Add(new Vector3(-dx, 1f, -dz));
                uv.Add(new Vector2(0f, 0f)); uv.Add(new Vector2(1f, 0f)); uv.Add(new Vector2(1f, 1f)); uv.Add(new Vector2(0f, 1f));
                t.AddRange(new[] { b, b + 2, b + 1, b, b + 3, b + 2 });
            }
            _flame = new Mesh { name = "Flame" };
            _flame.SetVertices(v); _flame.SetUVs(0, uv); _flame.SetTriangles(t, 0);
            _flame.RecalculateBounds();
            return _flame;
        }
    }
}
