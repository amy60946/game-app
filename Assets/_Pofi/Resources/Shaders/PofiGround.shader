// Pofi Adası zemini (URP): boyanmış doku (_BaseMap; alfa = kum ağırlığı) + kumda rüzgâr çizgileri ve ıslak kum,
// çimende ince ton dalgası. Ana ışık + gölge + ortam ışığı. Işık dengeli (parlama yok).
Shader "Pofi/Ground"
{
    Properties
    {
        _BaseMap ("Doku", 2D) = "white" {}
        _RippleStrength ("Kum çizgisi gücü", Float) = 0.35
        _WetLevel ("Islak kum yüksekliği", Float) = 0.28
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" "Queue" = "Geometry" }
        Pass
        {
            Name "Forward"
            Tags { "LightMode" = "UniversalForward" }
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile_fragment _ _SHADOWS_SOFT
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            CBUFFER_START(UnityPerMaterial)
                float4 _BaseMap_ST;
                float _RippleStrength, _WetLevel;
            CBUFFER_END
            TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);

            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; float2 uv : TEXCOORD0; };
            struct Varyings { float4 positionCS : SV_POSITION; float3 positionWS : TEXCOORD0; float3 normalWS : TEXCOORD1; float2 uv : TEXCOORD2; };

            Varyings vert(Attributes v)
            {
                Varyings o;
                o.positionWS = TransformObjectToWorld(v.positionOS.xyz);
                o.normalWS = TransformObjectToWorldNormal(v.normalOS);
                o.positionCS = TransformWorldToHClip(o.positionWS);
                o.uv = v.uv;
                return o;
            }

            half4 frag(Varyings i) : SV_Target
            {
                float4 tex = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, i.uv);
                float sand = tex.a;
                float2 p = i.positionWS.xz;
                float3 n = normalize(i.normalWS);

                // kum: rüzgâr çizgileri (normal bükme) — dalgalı, hafif kıvrımlı
                float warp = sin(p.y * 0.35 + sin(p.x * 0.21) * 2.0) * 1.5;
                float ph = (p.x * 0.85 + p.y * 0.45 + warp) * 6.2832 / 0.55;
                float rip = cos(ph);
                n = normalize(n + float3(0.8, 0, 0.42) * rip * _RippleStrength * 0.25 * sand);

                float3 albedo = tex.rgb;
                // ıslak kum: suya yakın alçak kum koyulaşır
                float wet = saturate((_WetLevel - i.positionWS.y) / _WetLevel) * sand;
                albedo *= lerp(1.0, 0.72, wet);
                // çimen: ince ton dalgası
                float tint = sin(p.x * 1.7 + sin(p.y * 1.3) * 1.5) * sin(p.y * 2.1 - p.x * 0.6);
                albedo *= 1.0 + tint * 0.05 * (1.0 - sand);

                float4 sc = TransformWorldToShadowCoord(i.positionWS);
                Light light = GetMainLight(sc);
                float ndl = saturate(dot(n, light.direction));
                float3 diffuse = light.color * ndl * light.shadowAttenuation;
                float3 ambient = SampleSH(n);
                float3 col = albedo * (ambient + diffuse);
                return half4(col, 1);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
