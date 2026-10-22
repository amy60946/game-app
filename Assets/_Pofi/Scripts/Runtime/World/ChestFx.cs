using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// Günlük sandık açılışı (XP takibi S2, 22 Ekim 2026; tasarım: "sandık sallanır, kapak açılır, ödül havaya yükselip pete akar"):
    /// petin önünde küçük ahşap sandık belirir, iki kez sallanır, kapağı açılır, içinden ışık ve ödülün simgesi yükselir,
    /// simge yay çizerek pete akar; sandık küçülüp kaybolur. Bitince <c>done</c> (ödül haberi, ses) çağrılır.
    /// </summary>
    public sealed class ChestFx : MonoBehaviour
    {
        private Transform _pet, _lid, _prize, _glow;
        private float _height, _t;
        private Vector3 _prizeFrom;
        private Quaternion _baseRot;
        private bool _landed, _risen;
        private System.Action _done;

        private const float Appear = 0.3f, Shake = 0.7f, OpenT = 0.35f, Rise = 0.7f, Fly = 0.45f, Vanish = 0.4f;

        public static void Play(Transform pet, float petHeight, Sprite prize, System.Action done)
        {
            if (pet == null) { done?.Invoke(); return; }
            var root = new GameObject("DailyChest").transform;
            var cam = Camera.main;
            // petin kameraya bakan yanında, biraz önde (kameradan görünsün)
            var toCam = cam != null ? cam.transform.position - pet.position : Vector3.back;
            toCam.y = 0f;
            toCam = toCam.sqrMagnitude > 0.01f ? toCam.normalized : Vector3.back;
            var side = Vector3.Cross(Vector3.up, toCam);
            root.position = pet.position + toCam * (petHeight * 0.9f + 0.4f) + side * (petHeight * 0.6f);
            root.rotation = Quaternion.LookRotation(toCam, Vector3.up);
            var fx = root.gameObject.AddComponent<ChestFx>();
            fx.Build(pet, petHeight, prize, done);
        }

        private void Build(Transform pet, float h, Sprite prize, System.Action done)
        {
            _pet = pet; _height = h; _done = done; _baseRot = transform.rotation;
            var s = Mathf.Clamp(h * 0.45f, 0.35f, 0.8f);
            var wood = _wood = PetModels.NewMaterial(new Color(0.62f, 0.38f, 0.20f), 0.35f);
            var band = _band = PetModels.NewMaterial(new Color(1f, 0.80f, 0.30f), 0.85f);
            band.SetFloat("_Rim", 1.6f);
            Box(transform, "Body", new Vector3(0f, 0.3f, 0f), new Vector3(1f, 0.6f, 0.7f), wood, s);
            Box(transform, "BandL", new Vector3(-0.3f, 0.3f, 0f), new Vector3(0.1f, 0.62f, 0.72f), band, s);
            Box(transform, "BandR", new Vector3(0.3f, 0.3f, 0f), new Vector3(0.1f, 0.62f, 0.72f), band, s);
            Box(transform, "Lock", new Vector3(0f, 0.5f, 0.36f), new Vector3(0.16f, 0.2f, 0.06f), band, s);
            // kapak: arka kenarından döner (menteşe)
            _lid = new GameObject("Hinge").transform;
            _lid.SetParent(transform, false);
            _lid.localPosition = new Vector3(0f, 0.6f, -0.35f) * s;
            Box(_lid, "Lid", new Vector3(0f, 0.12f, 0.35f), new Vector3(1.04f, 0.24f, 0.74f), wood, s);
            Box(_lid, "LidBand", new Vector3(0f, 0.12f, 0.35f), new Vector3(0.1f, 0.26f, 0.76f), band, s);
            _glow = GainFx.Glow(transform, GainFx.StoneColor, 0.9f, false);
            _glow.localPosition = new Vector3(0f, 0.7f, 0f) * s;
            _glow.localScale = Vector3.zero;
            if (prize != null)
            {
                var go = new GameObject("Prize");
                go.transform.SetParent(transform, false);
                var sr = go.AddComponent<SpriteRenderer>();
                sr.sprite = prize;
                go.AddComponent<FaceCamera>();
                _prize = go.transform;
                _prize.localPosition = new Vector3(0f, 0.4f, 0f) * s;
                var px = Mathf.Max(prize.rect.width, prize.rect.height) / Mathf.Max(1f, prize.pixelsPerUnit);
                _prize.localScale = Vector3.one * (s * 0.9f / Mathf.Max(0.01f, px));
                _prize.gameObject.SetActive(false);
            }
            transform.localScale = Vector3.zero;
        }

        private static void Box(Transform parent, string name, Vector3 pos, Vector3 size, Material m, float s)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = name;
            Destroy(go.GetComponent<Collider>());
            go.transform.SetParent(parent, false);
            go.transform.localPosition = pos * s;
            go.transform.localScale = size * s;
            var r = go.GetComponent<Renderer>();
            r.sharedMaterial = m;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.On;
        }

        private void Update()
        {
            _t += Time.deltaTime;
            var t = _t;
            // 1) belirir (yaylanarak)
            var k = Mathf.Clamp01(t / Appear);
            var pop = k < 1f ? Mathf.Sin(k * Mathf.PI * 0.5f) * (1f + 0.15f * Mathf.Sin(k * Mathf.PI)) : 1f;
            t -= Appear;
            // 2) sallanır
            var shake = t > 0f && t < Shake ? Mathf.Sin(t * 38f) * 9f * (1f - t / Shake) : 0f;
            transform.rotation = _baseRot * Quaternion.Euler(0f, 0f, shake);
            if (t > 0f && t < Shake) transform.localScale = Vector3.one * (1f + Mathf.Abs(Mathf.Sin(t * 19f)) * 0.06f);
            else transform.localScale = Vector3.one * pop;
            t -= Shake;
            // 3) kapak açılır, ışık doğar
            var o = Mathf.Clamp01(t / OpenT);
            _lid.localRotation = Quaternion.Euler(-110f * (1f - (1f - o) * (1f - o)), 0f, 0f);
            _glow.localScale = Vector3.one * (o * 1.6f * (1f + Mathf.Sin(_t * 6f) * 0.08f));
            if (o > 0f && _prize != null && !_prize.gameObject.activeSelf) { _prize.gameObject.SetActive(true); Audio.Sfx.Play(Audio.SfxKind.Sparkle); HitStop.Do(); }
            t -= OpenT;
            // 4) ödül yükselir (döner gibi esner)
            if (_prize != null && t > 0f)
            {
                var r = Mathf.Clamp01(t / Rise);
                var up = 1f - (1f - r) * (1f - r);
                _prize.localPosition = Vector3.up * Mathf.Lerp(0.4f, 1.9f, up) * Mathf.Clamp(_height * 0.45f, 0.35f, 0.8f);
                if (!_risen) _prizeFrom = _prize.position;
                if (r >= 1f) _risen = true;
            }
            t -= Rise;
            // 5) ödül pete akar
            if (_prize != null && t > 0f && _pet != null)
            {
                var f = Mathf.Clamp01(t / Fly);
                var target = _pet.position + Vector3.up * (_height * 0.6f);
                var mid = Vector3.Lerp(_prizeFrom, target, 0.5f) + Vector3.up * 0.6f;
                var a = Vector3.Lerp(_prizeFrom, mid, f); var b = Vector3.Lerp(mid, target, f);
                _prize.position = Vector3.Lerp(a, b, f);
                _prize.localScale *= 1f - Time.deltaTime * 1.5f;
                if (f >= 1f && !_landed)
                {
                    _landed = true;
                    _prize.gameObject.SetActive(false);
                    PetGlow.Play(_pet, _height, GainFx.StoneColor);
                    _done?.Invoke(); _done = null;
                }
            }
            else if (_prize == null && t > 0f && !_landed) { _landed = true; _done?.Invoke(); _done = null; }
            t -= Fly;
            // 6) sandık küçülüp kaybolur
            if (t > 0f)
            {
                var v = Mathf.Clamp01(t / Vanish);
                transform.localScale = Vector3.one * (1f - v);
                if (v >= 1f) Destroy(gameObject);
            }
        }

        private Material _wood, _band;

        private void OnDestroy()
        {
            _done?.Invoke();
            if (_wood != null) Destroy(_wood);
            if (_band != null) Destroy(_band);
        }
    }
}
