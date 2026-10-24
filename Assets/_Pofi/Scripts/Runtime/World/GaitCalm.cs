using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// Sakin yürüyüş (kullanıcı 24 Ekim 2026: "karakterin yürürken uzuvları gereksiz sallanmasın"). Meshy'nin yürüme/koşu
    /// klipleri insan ölçüsünde: kol 45° / 112°, önkol 54°, baş 17° / 23°, gövde 15° / 37° dönüyor; kısa kollu oyuncak Okti'de
    /// çırpınma gibi duruyordu (ölçü: art/meshy/scripts/anim_fit_test.py). Animasyondan sonra (LateUpdate) kol, omuz, baş ve boyun
    /// kemikleri klibin kendi ortalama duruşuna doğru çekilir; bacak, kalça ve gövde klipteki gibi kalır (adım ve ayak teması aynı).
    /// Oran = klipten kalan pay (1 = olduğu gibi); yürüme/koşu ağırlığıyla karışır, beklemeye geçişte kendiliğinden söner.
    /// </summary>
    public sealed class GaitCalm : MonoBehaviour
    {
        private static readonly (string bone, float walk, float run)[] Keep =
        {
            ("LeftShoulder", 0.6f, 0.5f), ("RightShoulder", 0.6f, 0.5f),
            ("LeftArm", 0.5f, 0.42f), ("RightArm", 0.5f, 0.42f),
            ("LeftForeArm", 0.45f, 0.4f), ("RightForeArm", 0.45f, 0.4f),
            ("LeftHand", 0.45f, 0.4f), ("RightHand", 0.45f, 0.4f),
            ("Neck", 0.7f, 0.6f), ("Head", 0.7f, 0.6f),
        };   // gövde (Spine*) klipteki gibi: yumuşatınca sırt çantası yetişkin koşusunda sırta giriyordu (Blender ölçüsü)
        private const int Samples = 24;

        private Animation _anim;
        private Transform[] _bones;
        private Quaternion[] _walkMean, _runMean;
        private float[] _kWalk, _kRun;
        private bool _ready;

        public static void Add(GameObject model)
        {
            if (model.GetComponent<GaitCalm>() == null) model.AddComponent<GaitCalm>();
        }

        private void Start()
        {
            _anim = GetComponent<Animation>();
            if (_anim == null) { enabled = false; return; }
            var n = Keep.Length;
            _bones = new Transform[n]; _kWalk = new float[n]; _kRun = new float[n];
            for (var i = 0; i < n; i++) { _bones[i] = Find(transform, Keep[i].bone); _kWalk[i] = Keep[i].walk; _kRun[i] = Keep[i].run; }
            _walkMean = Means(_anim.GetClip("walk"));
            _runMean = Means(_anim.GetClip("run"));
            _ready = _walkMean != null || _runMean != null;
        }

        /// <summary>Klibin kemik başına ortalama yerel dönüşü (24 örnek). Klip yoksa null.</summary>
        private Quaternion[] Means(AnimationClip clip)
        {
            if (clip == null) return null;
            var acc = new Vector4[_bones.Length];
            var first = new Quaternion[_bones.Length];
            for (var k = 0; k < Samples; k++)
            {
                clip.SampleAnimation(gameObject, clip.length * k / Samples);
                for (var i = 0; i < _bones.Length; i++)
                {
                    if (_bones[i] == null) continue;
                    var q = _bones[i].localRotation;
                    if (k == 0) first[i] = q;
                    if (Quaternion.Dot(first[i], q) < 0f) q = new Quaternion(-q.x, -q.y, -q.z, -q.w);   // aynı yarı küre
                    acc[i] += new Vector4(q.x, q.y, q.z, q.w);
                }
            }
            var m = new Quaternion[_bones.Length];
            for (var i = 0; i < m.Length; i++)
            {
                var a = acc[i];
                m[i] = a.sqrMagnitude > 1e-8f ? new Quaternion(a.x, a.y, a.z, a.w).normalized : Quaternion.identity;
            }
            return m;
        }

        private void LateUpdate()
        {
            if (!_ready) return;
            var ww = Weight("walk", _walkMean); var wr = Weight("run", _runMean);
            if (ww + wr < 0.01f) return;
            for (var i = 0; i < _bones.Length; i++)
            {
                var b = _bones[i];
                if (b == null) continue;
                var q = b.localRotation;
                if (ww > 0f) q = Quaternion.Slerp(q, _walkMean[i], ww * (1f - _kWalk[i]));
                if (wr > 0f) q = Quaternion.Slerp(q, _runMean[i], wr * (1f - _kRun[i]));
                b.localRotation = q;
            }
        }

        private float Weight(string clip, Quaternion[] mean)
        {
            if (mean == null) return 0f;
            var st = _anim[clip];
            return st != null && st.enabled ? Mathf.Clamp01(st.weight) : 0f;
        }

        private static Transform Find(Transform t, string name)
        {
            if (t.name == name || t.name.EndsWith(":" + name)) return t;
            for (var i = 0; i < t.childCount; i++)
            {
                var r = Find(t.GetChild(i), name);
                if (r != null) return r;
            }
            return null;
        }
    }
}
