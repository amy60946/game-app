// Düz renk (URP, ışıksız, çift yüzlü): uzaktaki kuş siluetleri gibi küçük süsler için. Gölge düşürmez/almaz.
Shader "Pofi/Flat"
{
    Properties
    {
        _Color ("Renk", Color) = (0.22, 0.28, 0.38, 1)
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
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            CBUFFER_START(UnityPerMaterial)
                float4 _Color;
            CBUFFER_END

            struct Attributes { float4 positionOS : POSITION; };
            struct Varyings { float4 positionCS : SV_POSITION; };

            Varyings vert(Attributes v)
            {
                Varyings o;
                o.positionCS = TransformObjectToHClip(v.positionOS.xyz);
                return o;
            }

            half4 frag(Varyings i) : SV_Target { return half4(_Color.rgb, 1); }
            ENDHLSL
        }
    }
    FallBack Off
}
