// Yumuşak ışık lekesi / halka (URP, toplamalı, çift yüzlü): kazanım efektlerinde (XP yıldızı, Güneş Taşı, parıltı) pete akan
// ışık ve petin parlaması. Dörtgenin uv'sinden daire: _Ring 0 = ortası dolu leke, 1 = ince halka (_Radius çevresinde).
Shader "Pofi/Glow"
{
    Properties
    {
        _Color ("Renk", Color) = (1, 0.85, 0.3, 1)
        _Intensity ("Parlaklık", Float) = 1
        _Ring ("Halka (0 leke, 1 halka)", Float) = 0
        _Radius ("Halka yarıçapı (0..1)", Float) = 0.7
    }
    SubShader
    {
        Tags { "RenderType" = "Transparent" "Queue" = "Transparent" "RenderPipeline" = "UniversalPipeline" "IgnoreProjector" = "True" }
        Blend One One
        ZWrite Off
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
                float _Intensity, _Ring, _Radius;
            CBUFFER_END

            struct Attributes { float4 positionOS : POSITION; float2 uv : TEXCOORD0; };
            struct Varyings { float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; };

            Varyings vert(Attributes v)
            {
                Varyings o;
                o.positionCS = TransformObjectToHClip(v.positionOS.xyz);
                o.uv = v.uv;
                return o;
            }

            half4 frag(Varyings i) : SV_Target
            {
                float r = length(i.uv * 2.0 - 1.0);
                float blob = saturate(1.0 - r); blob *= blob;
                float d = (r - _Radius) / 0.09;
                float ring = exp(-d * d) * step(r, 1.0);
                float a = lerp(blob, ring, saturate(_Ring)) * _Intensity;
                return half4(_Color.rgb * a, 1);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
