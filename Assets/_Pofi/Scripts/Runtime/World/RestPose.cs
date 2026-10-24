using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// Modelin dinlenme duruşu (FBX'teki kemik duruşu, animasyon başlamadan önce kaydedilir). Eşyalar bu duruşta yerleşir:
    /// oturma kuralları (art/meshy/scripts/okti_fit_rules.json) ve Blender denemeleri bu duruşta ölçüldü. Kıyafet × hareket denemesi
    /// (24 Ekim 2026): dolapta eşya değişirken pet bekleme hareketinin herhangi bir karesinde olabiliyordu; o anki duruşta takılan
    /// şapka/gözlük kemiğe eğik bağlanıp sonra kayık duruyordu.
    /// </summary>
    public sealed class RestPose : MonoBehaviour
    {
        private Transform[] _t;
        private Vector3[] _p, _s;
        private Quaternion[] _r;

        /// <summary>Animasyon oynamadan hemen önce çağrılır (RealAssets.Pet).</summary>
        public static RestPose Capture(GameObject model)
        {
            var rp = model.GetComponent<RestPose>() ?? model.AddComponent<RestPose>();
            // modelin kendi dönüş/ölçeği dışarıdan değişebilir (sığdırma, büyüme sahnesi): yalnız alt kemikler ve ağlar
            rp._t = System.Array.FindAll(model.GetComponentsInChildren<Transform>(true), t => t != model.transform);
            var n = rp._t.Length;
            rp._p = new Vector3[n]; rp._r = new Quaternion[n]; rp._s = new Vector3[n];
            for (var i = 0; i < n; i++) { rp._p[i] = rp._t[i].localPosition; rp._r[i] = rp._t[i].localRotation; rp._s[i] = rp._t[i].localScale; }
            return rp;
        }

        /// <summary>Dinlenme duruşuna geçer; dönen kapsam kapanınca (using) o anki animasyon duruşu geri gelir.</summary>
        public Scope Hold()
        {
            var n = _t.Length;
            var p = new Vector3[n]; var r = new Quaternion[n]; var s = new Vector3[n];
            for (var i = 0; i < n; i++)
            {
                var t = _t[i];
                if (t == null) continue;
                p[i] = t.localPosition; r[i] = t.localRotation; s[i] = t.localScale;
                t.localPosition = _p[i]; t.localRotation = _r[i]; t.localScale = _s[i];
            }
            return new Scope(_t, p, r, s);
        }

        public readonly struct Scope : System.IDisposable
        {
            private readonly Transform[] _t; private readonly Vector3[] _p, _s; private readonly Quaternion[] _r;
            public Scope(Transform[] t, Vector3[] p, Quaternion[] r, Vector3[] s) { _t = t; _p = p; _r = r; _s = s; }
            public void Dispose()
            {
                if (_t == null) return;
                for (var i = 0; i < _t.Length; i++)
                    if (_t[i] != null) { _t[i].localPosition = _p[i]; _t[i].localRotation = _r[i]; _t[i].localScale = _s[i]; }
            }
        }
    }
}
