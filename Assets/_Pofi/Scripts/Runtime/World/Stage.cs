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
            Camera.clearFlags = CameraClearFlags.SolidColor;
            Camera.backgroundColor = sky;
            Camera.fieldOfView = 34f;
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
            var water = Cylinder("Water", new Vector3(0f, -0.12f, 0f), new Vector3(9f, 0.02f, 9f), _waterMat);
            var island = Cylinder("Island", new Vector3(0f, -0.05f, 0f), new Vector3(2.8f, 0.06f, 2.8f), _islandMat);
            water.GetComponent<Renderer>().shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            island.GetComponent<Renderer>().shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;

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
        public void SetCamera(Vector3 position, float pitch)
        {
            Camera.transform.SetPositionAndRotation(position, Quaternion.Euler(pitch, 0f, 0f));
        }

        public void SetSky(Color sky) => Camera.backgroundColor = sky;

        public void ShowPet(PetSpeciesDef def, GrowthStage stage, IEnumerable<string> equipped = null, bool resetYaw = true)
        {
            ClearPet();
            _petDef = def;
            Pet = PetModels.Build(def, _holder);
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
            CosmeticModels.Apply(Pet, _petDef, items);
        }

        public void SetPetVisible(bool visible) => _holder.gameObject.SetActive(visible);

        public void ClearPet()
        {
            if (Pet == null) return;
            foreach (var r in Pet.GetComponentsInChildren<Renderer>())
                foreach (var m in r.sharedMaterials) if (m != null) Destroy(m);
            Destroy(Pet.gameObject);
            Pet = null;
        }

        public void Hop() => _hop = 1f;

        /// <summary>Petin kafa üstünün ekran konumu (konuşma balonu için).</summary>
        public Vector2 PetHeadScreenPoint()
        {
            var top = _holder.position + Vector3.up * (1.75f * _baseScale);
            return (Vector2)Camera.WorldToScreenPoint(top);
        }

        private void Update()
        {
            var dt = Time.deltaTime;
            HandleDrag(dt);

            if (!_dragging)
            {
                _yaw += _yawVelocity * dt;
                _yawVelocity = Mathf.Lerp(_yawVelocity, 0f, 1f - Mathf.Exp(-3f * dt));
            }

            _appear = Mathf.Min(1f, _appear + dt * 3.5f);
            var pop = 1f + Mathf.Sin(_appear * Mathf.PI) * 0.12f * (1f - _appear * 0.3f);
            _breath += dt * 2.2f;
            var breath = 1f + Mathf.Sin(_breath) * 0.015f;
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
