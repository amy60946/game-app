using System;
using System.Collections.Generic;
using Pofi.Logic.Story;
using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// Gerçek takvimle mevsim görünüşü (H6, 23 Ekim 2026). Sonbaharda yapraklı ağaçlar ağaç ağaç altın/kızıla döner ve yaprak
    /// süzülür, kışın süslerin ve çatıların üstü karlanır ve kar yağar, ilkbaharda çiçek yaprakları uçuşur, 20 Aralık – 5 Ocak arası
    /// meydanda yılbaşı ışıkları yanar. Kaçırılırsa kaybolan bir şey yok. Toon/Grass gölgelendiricileri _PofiAutumn, _PofiSnow okur.
    /// </summary>
    public static class SeasonLook
    {
        /// <summary>Görsel deneme (PofiDebug "season ..."): autumn, winter, spring, summer, holiday; boş = takvim.</summary>
        public static string Override;
        private static readonly HashSet<Material> Marked = new HashSet<Material>();

        public static Season Current(DateTime local) =>
            Override == "autumn" ? Season.Autumn : Override == "winter" || Override == "holiday" ? Season.Winter :
            Override == "spring" ? Season.Spring : Override == "summer" ? Season.Summer : Seasons.For(local);

        public static bool Holiday(DateTime local) => Override == "holiday" || (string.IsNullOrEmpty(Override) && Seasons.HolidayLights(local));

        public static void Apply(MapWorld world, DateTime local)
        {
            var s = Current(local);
            Shader.SetGlobalFloat("_PofiAutumn", s == Season.Autumn ? 1f : 0f);
            Shader.SetGlobalFloat("_PofiSnow", s == Season.Winter ? 0.85f : 0f);
            if (s != Season.Summer) SeasonFall.Create(world.transform, s);
            if (Holiday(local)) HolidayLights.Build(world);
        }

        /// <summary>Ada süsü/yapısı malzemelerini işaretle: kışın karlanır; yapraklıysa sonbaharda renk değiştirir.</summary>
        public static void Mark(Transform t, bool foliage)
        {
            if (t == null) return;
            foreach (var r in t.GetComponentsInChildren<Renderer>(true))
                foreach (var m in r.sharedMaterials)
                {
                    if (m == null || !m.HasProperty("_Env")) continue;
                    if (!Marked.Add(m) && !foliage) continue;
                    m.SetFloat("_Env", 1f);
                    if (foliage) m.SetFloat("_Foliage", 1f);
                }
        }
    }

    /// <summary>Kameranın çevresinde süzülen yaprak (sonbahar), kar (kış) ya da çiçek yaprağı (ilkbahar). Az ve yavaş.</summary>
    public sealed class SeasonFall : MonoBehaviour
    {
        private ParticleSystem _ps;
        private static readonly Dictionary<Season, Material> Mats = new Dictionary<Season, Material>();

        public static SeasonFall Create(Transform parent, Season s)
        {
            var go = new GameObject("season_" + s);
            go.transform.SetParent(parent, false);
            var f = go.AddComponent<SeasonFall>();
            var ps = f._ps = go.AddComponent<ParticleSystem>();
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = ps.main;
            main.loop = true; main.playOnAwake = true;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.startLifetime = s == Season.Winter ? 9f : 7f;
            main.startSpeed = 0f;
            main.startSize = new ParticleSystem.MinMaxCurve(s == Season.Winter ? 0.08f : 0.16f, s == Season.Winter ? 0.16f : 0.28f);
            main.startRotation = new ParticleSystem.MinMaxCurve(0f, Mathf.PI * 2f);
            main.gravityModifier = 0f;
            main.maxParticles = s == Season.Winter ? 260 : 90;
            var em = ps.emission; em.rateOverTime = s == Season.Winter ? 30f : 9f;
            var sh = ps.shape; sh.shapeType = ParticleSystemShapeType.Box; sh.scale = new Vector3(34f, 1f, 34f);
            var vel = ps.velocityOverLifetime; vel.enabled = true; vel.space = ParticleSystemSimulationSpace.World;
            vel.x = new ParticleSystem.MinMaxCurve(-0.4f, 0.6f); vel.y = new ParticleSystem.MinMaxCurve(s == Season.Winter ? -1.1f : -0.8f, s == Season.Winter ? -0.7f : -0.45f); vel.z = new ParticleSystem.MinMaxCurve(-0.3f, 0.3f);
            var noise = ps.noise; noise.enabled = true; noise.strength = s == Season.Winter ? 0.3f : 0.6f; noise.frequency = 0.4f;
            var rot = ps.rotationOverLifetime; rot.enabled = s != Season.Winter; rot.z = new ParticleSystem.MinMaxCurve(-2f, 2f);
            var r = go.GetComponent<ParticleSystemRenderer>();
            r.renderMode = ParticleSystemRenderMode.Billboard;
            r.sharedMaterial = Mat(s);
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
            ps.Play();
            return f;
        }

        private void LateUpdate()
        {
            var cam = Camera.main;
            if (cam == null) return;
            // kameranın önünde ve üstünde: düşen parçalar kadrajdan geçer
            var f = cam.transform.forward; f.y = 0f;
            transform.position = cam.transform.position + f.normalized * 9f + Vector3.up * 9f;
        }

        private static Material Mat(Season s)
        {
            if (Mats.TryGetValue(s, out var m) && m != null) return m;
            m = InkHeart.SpriteMat(Tex(s));
            return Mats[s] = m;
        }

        /// <summary>Kodla çizilen tek parça: kar = yumuşak nokta, yaprak = turuncu/kızıl damla yaprak, çiçek = pembe yaprak.</summary>
        private static Texture2D Tex(Season s)
        {
            const int n = 48;
            var t = new Texture2D(n, n, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, name = "season_" + s };
            var px = new Color32[n * n];
            for (var y = 0; y < n; y++)
                for (var x = 0; x < n; x++)
                {
                    var u = (x - n * 0.5f) / (n * 0.5f); var v = (y - n * 0.5f) / (n * 0.5f);
                    Color c;
                    if (s == Season.Winter)
                    {
                        var d = Mathf.Sqrt(u * u + v * v);
                        c = new Color(1f, 1f, 1f, Mathf.Clamp01((1f - d) * 2.2f));
                    }
                    else
                    {
                        // damla yaprak: |u| ≤ (1 − v²)·0.55
                        var w = (1f - v * v) * 0.55f;
                        var a = Mathf.Clamp01((w - Mathf.Abs(u)) * 14f) * (Mathf.Abs(v) < 0.95f ? 1f : 0f);
                        var vein = Mathf.Abs(u) < 0.04f ? 0.8f : 1f;
                        c = s == Season.Autumn
                            ? Color.Lerp(new Color(0.95f, 0.55f, 0.15f), new Color(0.85f, 0.25f, 0.15f), (v + 1f) * 0.5f) * vein
                            : Color.Lerp(new Color(1f, 0.8f, 0.88f), new Color(1f, 0.62f, 0.76f), (v + 1f) * 0.5f);
                        c.a = a;
                    }
                    px[y * n + x] = c;
                }
            t.SetPixels32(px); t.Apply();
            return t;
        }
    }

    /// <summary>Yılbaşı ışıkları: meydanın çevresinde direkler arasında sarkık ışık dizisi; ampuller sırayla yavaşça yanıp söner.</summary>
    public sealed class HolidayLights : MonoBehaviour
    {
        private readonly List<(Renderer R, Material M, int Group)> _bulbs = new List<(Renderer, Material, int)>();
        private static readonly Color[] Colors = { new Color(1f, 0.35f, 0.35f), new Color(1f, 0.85f, 0.3f), new Color(0.4f, 0.85f, 0.5f), new Color(0.45f, 0.7f, 1f) };

        public static void Build(MapWorld world)
        {
            var root = new GameObject("holiday_lights").transform;
            root.SetParent(world.transform, false);
            var h = root.gameObject.AddComponent<HolidayLights>();
            var cx = world.Terrain.PlazaX; var cz = world.Terrain.PlazaZ;
            const int poles = 10; const float rad = 7.5f, top = 2.7f;
            var pole = PetModels.NewMaterial(new Color(0.35f, 0.25f, 0.2f), 0.3f);
            var tops = new Vector3[poles];
            for (var i = 0; i < poles; i++)
            {
                var a = i * Mathf.PI * 2f / poles;
                var x = cx + Mathf.Cos(a) * rad; var z = cz + Mathf.Sin(a) * rad;
                var y = world.Terrain.Height(x, z);
                var p = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                Destroy(p.GetComponent<Collider>());
                p.transform.SetParent(root, false);
                p.transform.localPosition = new Vector3(x, y + top * 0.5f, z); p.transform.localScale = new Vector3(0.09f, top * 0.5f, 0.09f);
                p.GetComponent<MeshRenderer>().sharedMaterial = pole;
                tops[i] = new Vector3(x, y + top, z);
            }
            var k = 0;
            for (var i = 0; i < poles; i++)
            {
                var a = tops[i]; var b = tops[(i + 1) % poles];
                for (var j = 1; j < 8; j++)
                {
                    var t = j / 8f;
                    var at = Vector3.Lerp(a, b, t) + Vector3.down * Mathf.Sin(t * Mathf.PI) * 0.55f;
                    var bulb = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                    Destroy(bulb.GetComponent<Collider>());
                    bulb.transform.SetParent(root, false);
                    bulb.transform.localPosition = at; bulb.transform.localScale = Vector3.one * 0.16f;
                    var m = PetModels.NewMaterial(Colors[k % Colors.Length], 0.9f);
                    var r = bulb.GetComponent<MeshRenderer>(); r.sharedMaterial = m;
                    r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                    h._bulbs.Add((r, m, k % 3));
                    k++;
                }
            }
        }

        private void Update()
        {
            // üç grup sırayla parlar: ampul hafifçe büyür, kenar ışığı güçlenir (parlama yok)
            var t = Time.time;
            foreach (var (r, m, g) in _bulbs)
            {
                if (r == null) continue;
                var on = 0.65f + 0.35f * Mathf.Sin(t * 1.6f + g * 2.1f);
                r.transform.localScale = Vector3.one * (0.14f + 0.04f * on);
                if (m.HasProperty("_Rim")) m.SetFloat("_Rim", 1f + on * 3f);
            }
        }
    }
}
