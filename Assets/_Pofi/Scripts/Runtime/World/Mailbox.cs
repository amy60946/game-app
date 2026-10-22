using UnityEngine;

namespace Pofi.World
{
    /// <summary>
    /// Evim'in önündeki posta kutusu (H2, 23 Ekim 2026): kodla (kredisiz) ahşap direk, kırmızı oval kutu, kapak ve bayrak.
    /// Okunmamış ebeveyn mesajı varsa bayrak kalkık ve kutu ara sıra hafifçe zıplar; dokunma için "mailbox" collider.
    /// </summary>
    public sealed class Mailbox : MonoBehaviour
    {
        private Transform _flag, _box;
        private bool _unread;
        private float _t, _flagA;

        public static Mailbox Create(Transform parent, Vector3 local, float yaw)
        {
            var root = new GameObject("mailbox").transform;
            root.SetParent(parent, false);
            root.localPosition = local;
            root.localRotation = Quaternion.Euler(0f, yaw, 0f);
            var m = root.gameObject.AddComponent<Mailbox>();
            var wood = PetModels.NewMaterial(new Color(0.6f, 0.4f, 0.24f), 0.3f);
            var red = PetModels.NewMaterial(new Color(0.9f, 0.3f, 0.3f), 0.75f);
            var cream = PetModels.NewMaterial(new Color(1f, 0.93f, 0.78f), 0.5f);
            var gold = PetModels.NewMaterial(new Color(1f, 0.8f, 0.3f), 0.85f);
            Part(root, PrimitiveType.Cylinder, new Vector3(0f, 0.55f, 0f), new Vector3(0.12f, 0.55f, 0.12f), wood);
            m._box = new GameObject("box").transform; m._box.SetParent(root, false); m._box.localPosition = new Vector3(0f, 1.18f, 0f);
            Part(m._box, PrimitiveType.Capsule, Vector3.zero, new Vector3(0.42f, 0.36f, 0.42f), red, Quaternion.Euler(90f, 0f, 0f));
            Part(m._box, PrimitiveType.Cylinder, new Vector3(0f, 0f, 0.37f), new Vector3(0.4f, 0.02f, 0.4f), cream, Quaternion.Euler(90f, 0f, 0f));
            Part(m._box, PrimitiveType.Sphere, new Vector3(0f, -0.05f, 0.39f), Vector3.one * 0.07f, gold);
            var hinge = new GameObject("flag").transform; hinge.SetParent(m._box, false); hinge.localPosition = new Vector3(0.23f, 0f, -0.15f);
            Part(hinge, PrimitiveType.Cube, new Vector3(0f, 0.22f, 0f), new Vector3(0.04f, 0.44f, 0.04f), gold);
            Part(hinge, PrimitiveType.Cube, new Vector3(0f, 0.4f, 0.1f), new Vector3(0.04f, 0.16f, 0.2f), red);
            m._flag = hinge;
            var col = root.gameObject.AddComponent<CapsuleCollider>();
            col.center = new Vector3(0f, 0.9f, 0f); col.height = 1.8f; col.radius = 0.6f;
            return m;
        }

        private static void Part(Transform parent, PrimitiveType t, Vector3 at, Vector3 scale, Material m, Quaternion? rot = null)
        {
            var go = GameObject.CreatePrimitive(t);
            Destroy(go.GetComponent<Collider>());
            go.transform.SetParent(parent, false);
            go.transform.localPosition = at; go.transform.localScale = scale;
            if (rot.HasValue) go.transform.localRotation = rot.Value;
            go.GetComponent<MeshRenderer>().sharedMaterial = m;
        }

        public bool Unread { set => _unread = value; }

        private void Update()
        {
            _t += Time.deltaTime;
            _flagA = Mathf.MoveTowards(_flagA, _unread ? 0f : -90f, Time.deltaTime * 240f);   // kalkık 0°, inik −90°
            _flag.localRotation = Quaternion.Euler(0f, 0f, _flagA);
            var hop = _unread ? Mathf.Max(0f, Mathf.Sin(_t * 3f)) * Mathf.Max(0f, Mathf.Sin(_t * 0.8f)) * 0.08f : 0f;
            _box.localPosition = new Vector3(0f, 1.18f + hop, 0f);
            _box.localRotation = Quaternion.Euler(0f, 0f, _unread ? Mathf.Sin(_t * 9f) * hop * 30f : 0f);
        }
    }
}
