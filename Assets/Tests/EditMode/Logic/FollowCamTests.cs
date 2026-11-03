using NUnit.Framework;
using Pofi.Logic.Island;

namespace Pofi.Tests.Logic
{
    /// <summary>GB21-2: kamera Okti'nin hep arkasına geçer (kameraya doğru yürürken de), dururken yerinde kalır, hız/ivme sınırlı.</summary>
    public class FollowCamTests
    {
        private const float Dt = 1f / 60f;

        private static float Run(FollowCam c, float cam, float heading, float seconds, bool moving = true, bool stick = true, float age = 5f)
        {
            for (var t = 0f; t < seconds; t += Dt) { cam = c.Step(cam, heading, moving, stick, age, Dt); age += Dt; }
            return cam;
        }

        private static float Off(float cam, float heading) => System.Math.Abs(FollowCam.DeltaAngle(cam, heading));

        [Test]
        public void Yana_yururken_iki_saniyede_arkaya_gecer()
        {
            var c = new FollowCam();
            Assert.AreEqual(0f, Run(c, 0f, 90f, 0.3f), 0.01f, "0,4 sn beklemeden dönmez");
            Assert.Less(Off(Run(c, 0f, 90f, 2.2f), 90f), 3f);
        }

        [Test]
        public void Kameraya_dogru_yururken_once_gorus_acilir_sonra_arkaya_doner()
        {
            var c = new FollowCam();
            var cam = Run(c, 0f, 180f, 0.6f);
            Assert.IsTrue(c.Back, "kameraya doğru: görüş açılır");
            Assert.AreEqual(0f, cam, 0.01f, "0,8 sn dolmadan dönmez");
            cam = Run(c, cam, 180f, 3.2f);
            Assert.Less(Off(cam, 180f), 3f);
        }

        [Test]
        public void Dururken_ve_yeni_dokunusun_ilk_anlarinda_donmez()
        {
            var c = new FollowCam();
            Assert.AreEqual(10f, Run(c, 10f, 100f, 2f, moving: false), 0.01f);
            Assert.AreEqual(10f, Run(c, 10f, 100f, 0.25f, age: 0f), 0.01f);
        }

        [Test]
        public void Donus_hizi_ve_ivmesi_sinirli_dokun_yuru_daha_yavas()
        {
            var c = new FollowCam();
            var cam = 0f; var lastV = 0f;
            for (var i = 0; i < 300; i++)
            {
                cam = c.Step(cam, 100f, true, true, 5f, Dt);
                Assert.LessOrEqual(System.Math.Abs(c.Velocity), FollowCam.SideSpeed + 0.01f);
                Assert.LessOrEqual(System.Math.Abs(c.Velocity) - System.Math.Abs(lastV), FollowCam.Accel * Dt + 0.01f, "hızlanma sınırlı (varışta durmak serbest)");
                lastV = c.Velocity;
            }
            var t = new FollowCam();
            var cam2 = 0f;
            for (var i = 0; i < 300; i++) { cam2 = t.Step(cam2, 100f, true, false, 99f, Dt); Assert.LessOrEqual(System.Math.Abs(t.Velocity), FollowCam.TapWalkSpeed + 0.01f); }
        }
    }
}
