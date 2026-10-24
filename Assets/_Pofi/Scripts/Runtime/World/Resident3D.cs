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

        // N2: önden uçma
        private enum Fly { Home, Guide, Land, Back }
        private Fly _fly = Fly.Home;
        private Vector3 _target;
        private float _landFor;

        public bool Busy => _fly != Fly.Home;

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
        }

        private void Update()
        {
            var dt = Time.deltaTime;
            _t += dt;
            // dünya içi konum (uçan ise)
            if (_flyer) UpdateFly(dt);
            var p = transform.localPosition;
            // Okti'ye dönme (yakınsa), yoksa evdeki yöne
            var wantYaw = _homeYaw;
            if (_fly == Fly.Guide || _fly == Fly.Back)
            {
                var v = (_fly == Fly.Guide ? _guideAt : _home) - p;
                if (new Vector2(v.x, v.z).sqrMagnitude > 0.04f) wantYaw = Mathf.Atan2(v.x, v.z) * Mathf.Rad2Deg;
            }
            else if (_pet != null)
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
                case "kiskac":   // yan yan sallanır, arada kıskaç selamı gibi eğilir
                    off.x = Mathf.Sin(t * 1.4f) * 0.05f;
                    rot = Quaternion.Euler(0f, 0f, Mathf.Sin(t * 1.4f) * 4f + wiggle);
                    break;
                case "mavi":     // başını çevirir gibi gövde dönüşü, minik sekme; uçarken kanat çırpar gibi yalpalar
                    if (_fly == Fly.Guide || _fly == Fly.Back) rot = Quaternion.Euler(10f, 0f, Mathf.Sin(t * 14f) * 9f);
                    else
                    {
                        off.y = Mathf.Max(0f, Mathf.Sin(t * 2.2f)) * 0.025f;
                        rot = Quaternion.Euler(0f, Mathf.Sin(t * 0.7f) * 14f, wiggle);
                    }
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

        private float Ground(float x, float z) => _ground != null ? Mathf.Max(0f, _ground(x, z)) : 0f;
    }
}
