// Yalnız yerel derleme kontrolü için URP/Core taslakları (oyuna girmez). İmzalar Unity Graphics 6000.3 kaynağından.
namespace UnityEngine.Rendering
{
    public class VolumeParameter<T> { public T value; public bool overrideState; public virtual void Override(T x) { value = x; overrideState = true; } }
    public class FloatParameter : VolumeParameter<float> { }
    public class ClampedFloatParameter : FloatParameter { }
    public class ColorParameter : VolumeParameter<Color> { }
    public abstract class VolumeComponent : ScriptableObject { }
    public sealed class VolumeProfile : ScriptableObject { public T Add<T>(bool overrides = false) where T : VolumeComponent => null; }
    public class Volume : MonoBehaviour { public bool isGlobal { get; set; } public float priority; public float weight = 1f; public VolumeProfile sharedProfile; }
}
namespace UnityEngine.Rendering.Universal
{
    public sealed class ColorAdjustments : VolumeComponent { public FloatParameter postExposure; public ClampedFloatParameter contrast; public ColorParameter colorFilter; public ClampedFloatParameter hueShift; public ClampedFloatParameter saturation; }
    public sealed class Vignette : VolumeComponent { public ColorParameter color; public ClampedFloatParameter intensity; public ClampedFloatParameter smoothness; }
    public class UniversalAdditionalCameraData : MonoBehaviour { public bool renderPostProcessing { get; set; } }
    public static class CameraExtensions { public static UniversalAdditionalCameraData GetUniversalAdditionalCameraData(this Camera camera) => null; }
}
