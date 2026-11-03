using System;

namespace Pofi.Logic.Island
{
    /// <summary>
    /// Ada kamerasının yön kuralı (GB21-2, kullanıcı 3 Kasım 2026: "kamera karakteri hep arkasından takip etsin, hızlıca arkasına
    /// konumlansın, optimal uzaklığı korusun; parmağımı alt kenara çekince gittiğim yeri görmüyorum"). Benchmark (alt ajan raporu,
    /// 3 Kasım): Roblox Follow (~23° eşik), Unity Cinemachine FreeLook (1 sn bekle, 2 sn ortala), Roblox elle çevirmeden 2 sn sonra
    /// otomatik; Mario 3D World paralel kamera ve Xbox erişilebilirlik kılavuzu 117 (otomatik ortalama baş döndürebilir → hız/ivme sınırı).
    /// Kural: Okti yürürken yana sapma (&gt;15°) 0,4 sn sürerse kamera en çok 120°/sn (dokun-yürü 60°/sn), 240°/sn² ivmeyle yumuşakça
    /// arkasına döner; küçük sapmayı yavaşça izler. Kameraya doğru yürürken (&gt;110°) önce görüş açılır (<see cref="Back"/>; çağıran
    /// bakışı yükseltir, önden bakışı yürüme yönüne verir), 0,8 sn sürerse en çok 100°/sn ile kısa taraftan arkaya geçer. Yeni dokunuşun
    /// ilk 0,3 sn'sinde dönmez; joystick yönü dokunuş başında kilitli (döngü olmaz). Okti dururken kamera yerinde kalır.
    /// </summary>
    public sealed class FollowCam
    {
        public const float SideAngle = 15f, BackAngle = 110f, DeadZone = 2f;
        public const float SideDelay = 0.4f, BackDelay = 0.8f, TouchGrace = 0.3f, SmoothTime = 0.35f;
        public const float SideSpeed = 120f, BackSpeed = 100f, TapWalkSpeed = 60f, DriftSpeed = 12f, Accel = 240f;

        private float _waited, _vel;

        /// <summary>Okti kameraya doğru yürüyor mu (çağıran görüşü açar: bakış yükselir, önden bakış yürüme yönünde)?</summary>
        public bool Back { get; private set; }

        /// <summary>Şu anki açısal hız (°/sn; testler ve ayıklama için).</summary>
        public float Velocity => _vel;

        /// <param name="byStick">Joystickle mi yürüyor (yoksa dokun-yürü rotası)?</param>
        /// <param name="touchAge">Joystick dokunuşunun yaşı (sn); dokun-yürüde büyük bir sayı.</param>
        public float Step(float camYaw, float heading, bool moving, bool byStick, float touchAge, float dt)
        {
            Back = false;
            if (!moving || dt <= 0f) { _waited = 0f; _vel = 0f; return camYaw; }
            var diff = DeltaAngle(camYaw, heading);
            var ad = Math.Abs(diff);
            Back = ad >= BackAngle;
            if (ad <= DeadZone) { _waited = 0f; _vel = 0f; return heading; }
            if (byStick && touchAge < TouchGrace) { _vel = 0f; return camYaw; }
            float max;
            if (ad <= SideAngle) { _waited = 0f; max = DriftSpeed; }             // küçük sapma: yavaşça izle
            else
            {
                _waited += dt;
                if (_waited < (Back ? BackDelay : SideDelay)) { _vel = 0f; return camYaw; }
                max = Back ? BackSpeed : byStick ? SideSpeed : TapWalkSpeed;
            }
            var want = Math.Sign(diff) * Math.Min(max, ad / SmoothTime);          // yaklaştıkça yavaşlar
            _vel = MoveTowards(_vel, want, Accel * dt);
            var step = _vel * dt;
            if (Math.Abs(step) >= ad && Math.Sign(step) == Math.Sign(diff)) { _vel = 0f; return heading; }
            return camYaw + step;
        }

        private static float MoveTowards(float cur, float target, float maxDelta) =>
            Math.Abs(target - cur) <= maxDelta ? target : cur + Math.Sign(target - cur) * maxDelta;

        /// <summary>Unity'deki Mathf.DeltaAngle gibi: a'dan b'ye en kısa işaretli fark (−180..180].</summary>
        public static float DeltaAngle(float a, float b)
        {
            var d = (b - a) % 360f;
            if (d > 180f) d -= 360f;
            if (d <= -180f) d += 360f;
            return d;
        }
    }
}
