// Çim telleri (URP): kökten uca koyudan açığa, öbek tonu köşe renginden, rüzgârda sallanma (uca doğru artar).
// Çiçek öbekleri (22 Ekim 2026, GrassField): uv.x 0..1 çim teli (ton = köşe rengi), 2 sap (ton = köşe alfası), 3 çiçek (renk = köşe rengi).
Shader "Pofi/Grass"
{
    Properties
    {
        _Root ("Kök", Color) = (0.2, 0.35, 0.13, 1)
        _Tip ("Uç", Color) = (0.54, 0.67, 0.31, 1)
        _Wind ("Rüzgâr", Float) = 0.12
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" "Queue" = "Geometry" }
        Cull Off
        Pass
        {
            Name "Forward"
            Tags { "LightMode" = "UniversalForward" }
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_instancing
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            CBUFFER_START(UnityPerMaterial)
                float4 _Root, _Tip;
                float _Wind;
            CBUFFER_END
            half _PofiAutumn;   // mevsim (H6): çimen biraz kurur, altın tona kayar
            half _PofiSnow;

            struct Attributes { float4 positionOS : POSITION; float2 uv : TEXCOORD0; float4 color : COLOR; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct Varyings { float4 positionCS : SV_POSITION; float3 positionWS : TEXCOORD0; float h : TEXCOORD1; float3 tint : TEXCOORD2; float bloom : TEXCOORD3; };

            Varyings vert(Attributes v)
            {
                UNITY_SETUP_INSTANCE_ID(v);
                Varyings o;
                float3 w = TransformObjectToWorld(v.positionOS.xyz);
                float h = v.uv.y;
                float sway = sin(_Time.y * 1.8 + w.x * 0.6 + w.z * 0.4) + 0.4 * sin(_Time.y * 3.1 + w.z * 1.3);
                w.xz += float2(0.8, 0.5) * sway * _Wind * h * h;
                o.positionWS = w;
                o.positionCS = TransformWorldToHClip(w);
                o.h = h;
                float mode = v.uv.x;
                o.tint = mode >= 2.5 ? v.color.rgb : (mode >= 1.5 ? v.color.aaa : v.color.rgb);   // öbek başına ton (GrassField köşe rengi)
                o.bloom = mode >= 2.5 ? 1.0 : 0.0;
                return o;
            }

            half4 frag(Varyings i) : SV_Target
            {
                float3 albedo = i.bloom > 0.5 ? i.tint * (0.8 + 0.2 * i.h) : lerp(_Root.rgb, _Tip.rgb, i.h) * i.tint;
                if (i.bloom < 0.5)
                {
                    albedo = lerp(albedo, albedo.ggg * float3(1.05, 0.88, 0.45), 0.28 * _PofiAutumn);
                    albedo = lerp(albedo, float3(0.9, 0.94, 1.0), 0.45 * _PofiSnow * i.h);
                }
                Light light = GetMainLight(TransformWorldToShadowCoord(i.positionWS));
                float3 col = albedo * (SampleSH(float3(0, 1, 0)) + light.color * 0.75 * light.shadowAttenuation);
                return half4(col, 1);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
