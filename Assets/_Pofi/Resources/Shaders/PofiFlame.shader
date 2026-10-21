// Kamp ateşi alev dili (URP): toplamalı, çift yüzlü; biçim ve kıvrım gürültüyle, yukarı akar. Dibinde sıcak sarı çekirdek, uçta koyu turuncu.
Shader "Pofi/Flame"
{
    Properties
    {
        _Seed ("Tohum", Float) = 0
        _Intensity ("Parlaklık", Float) = 1.1
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
                float _Seed, _Intensity;
            CBUFFER_END

            struct Attributes { float4 positionOS : POSITION; float2 uv : TEXCOORD0; };
            struct Varyings { float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; };

            float hash12(float2 p) { float3 p3 = frac(p.xyx * 0.1031); p3 += dot(p3, p3.yzx + 33.33); return frac((p3.x + p3.y) * p3.z); }
            float vnoise(float2 x)
            {
                float2 i = floor(x), f = x - i, u = f * f * (3.0 - 2.0 * f);
                float a = hash12(i), b = hash12(i + float2(1, 0)), c = hash12(i + float2(0, 1)), d = hash12(i + float2(1, 1));
                return a + (b - a) * u.x + (c - a) * u.y + (a - b - c + d) * u.x * u.y;
            }

            Varyings vert(Attributes v)
            {
                Varyings o;
                float3 p = v.positionOS.xyz;
                float t = _Time.y * 2.2 + _Seed;
                p.x += sin(t * 1.7 + p.y * 3.0) * 0.06 * p.y;            // tepe sallanır
                p.z += cos(t * 1.3 + p.y * 2.5) * 0.06 * p.y;
                o.positionCS = TransformObjectToHClip(p);
                o.uv = v.uv;
                return o;
            }

            half4 frag(Varyings i) : SV_Target
            {
                float t = _Time.y + _Seed;
                float2 uv = i.uv;
                float n = vnoise(float2(uv.x * 4.0 + _Seed, uv.y * 3.5 - t * 3.2)) * 0.65 + vnoise(float2(uv.x * 9.0, uv.y * 7.0 - t * 5.0)) * 0.35;
                float x = abs(uv.x - 0.5 + (n - 0.5) * 0.32 * uv.y) * 2.0;
                float width = pow(saturate(1.0 - uv.y), 0.75) * (0.85 + 0.15 * sin(t * 6.0));
                float shape = smoothstep(width, width * 0.35, x) * smoothstep(1.0, 0.55, uv.y + (n - 0.5) * 0.35) * smoothstep(0.0, 0.06, uv.y);
                float core = smoothstep(0.55, 0.0, x / max(width, 0.01)) * smoothstep(0.7, 0.1, uv.y);
                float3 col = lerp(float3(0.95, 0.25, 0.04), float3(1.0, 0.62, 0.15), saturate(shape * 1.2));
                col = lerp(col, float3(1.0, 0.9, 0.55), core);
                return half4(col * shape * _Intensity, 1);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
