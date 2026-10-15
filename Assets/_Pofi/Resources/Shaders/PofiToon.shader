// Pofi Toon (URP): boyalı/maket görünüm + "vinyl oyuncak" yüzeyi. Görsel stil çalışması (15 Ekim 2026).
// - Işık: iki yumuşak ton geçişi (aydınlık / gölge), gölge tarafı hafif serin-mor, alt yüzler biraz koyu (ortam ışığından).
// - Vinyl: pürüzsüzlüğe (_Smoothness) göre küçük, yumuşak kenarlı parlama + kenarda ince gökyüzü ışığı.
// - Dış çizgi: ters kabuk (SRPDefaultUnlit geçişi), ekranda sabit piksel kalınlığı, uzakta söner; rengi dokunun koyusu.
// RealAssets'teki URP Lit malzemesiyle aynı özellik adlarını kullanır (_BaseMap, _BaseColor, _BumpMap, _Smoothness):
// Look.Set ile shader değiştirilince doku/renk korunur.
Shader "Pofi/Toon"
{
    Properties
    {
        _BaseMap ("Doku", 2D) = "white" {}
        _BaseColor ("Renk", Color) = (1, 1, 1, 1)
        _BumpMap ("Normal", 2D) = "bump" {}
        _Smoothness ("Pürüzsüzlük (vinyl parlaması)", Range(0, 1)) = 0.2
        _Metallic ("(kullanılmaz)", Range(0, 1)) = 0
        _OutlineWidth ("Dış çizgi (px, 720p)", Float) = 1.4
    }

    HLSLINCLUDE
    #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
    CBUFFER_START(UnityPerMaterial)
        float4 _BaseMap_ST;
        half4 _BaseColor;
        float4 _BumpMap_ST;
        half _Smoothness;
        half _Metallic;
        float _OutlineWidth;
    CBUFFER_END
    TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);
    TEXTURE2D(_BumpMap); SAMPLER(sampler_BumpMap);
    ENDHLSL

    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" "Queue" = "Geometry" }

        Pass
        {
            Name "ToonForward"
            Tags { "LightMode" = "UniversalForward" }
            Cull Back
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            #pragma multi_compile_fog
            // malzemeler çalışma anında kurulduğu için shader_feature değil (değişken atılmasın)
            #pragma multi_compile_local _ _NORMALMAP
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                float4 tangentOS : TANGENT;
                float2 uv : TEXCOORD0;
            };
            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                float3 normalWS : TEXCOORD1;
                float4 tangentWS : TEXCOORD2;
                float2 uv : TEXCOORD3;
                float fog : TEXCOORD4;
            };

            Varyings vert(Attributes v)
            {
                Varyings o;
                o.positionWS = TransformObjectToWorld(v.positionOS.xyz);
                o.positionCS = TransformWorldToHClip(o.positionWS);
                VertexNormalInputs n = GetVertexNormalInputs(v.normalOS, v.tangentOS);
                o.normalWS = n.normalWS;
                o.tangentWS = float4(n.tangentWS, v.tangentOS.w * GetOddNegativeScale());
                o.uv = TRANSFORM_TEX(v.uv, _BaseMap);
                o.fog = ComputeFogFactor(o.positionCS.z);
                return o;
            }

            half4 frag(Varyings i) : SV_Target
            {
                half3 albedo = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, i.uv).rgb * _BaseColor.rgb;
                float3 n = normalize(i.normalWS);
            #if defined(_NORMALMAP)
                // doku ayrıntısı yarım güçte: boyalı görünümde yüzey sakin kalsın
                half3 nts = UnpackNormalScale(SAMPLE_TEXTURE2D(_BumpMap, sampler_BumpMap, i.uv), 0.5);
                float3 t = normalize(i.tangentWS.xyz);
                float3 b = cross(n, t) * i.tangentWS.w;
                n = normalize(nts.x * t + nts.y * b + nts.z * n);
            #endif
                float3 v = normalize(GetWorldSpaceViewDir(i.positionWS));

                Light light = GetMainLight(TransformWorldToShadowCoord(i.positionWS));
                float ndl = dot(n, light.direction);
                float shadow = light.shadowAttenuation;
                // iki ton: geniş yumuşak geçiş + aydınlık tarafta ikinci hafif kademe (boyalı his)
                float lit = smoothstep(-0.05, 0.18, ndl) * shadow;
                float lit2 = smoothstep(0.45, 0.75, ndl) * shadow;

                // ortam: gökyüzü/ufuk/zemin (SH); alt yüzler biraz koyu → nesne zemine oturur
                half3 amb = SampleSH(n) * lerp(0.72, 1.0, saturate(n.y * 0.5 + 0.5));
                half3 shadowTint = half3(0.36, 0.40, 0.62);             // gölge hafif serin-mor (soluk gri değil)
                half3 shadowCol = albedo * (amb * 0.82 + shadowTint * 0.16);
                half3 litCol = albedo * (amb * 0.38 + light.color * (0.78 + 0.10 * lit2));
                half3 col = lerp(shadowCol, litCol, lit);

                // vinyl parlaması: küçük, yumuşak kenarlı; pürüzsüzlük arttıkça belirginleşir
                float3 h = normalize(light.direction + v);
                float sp = pow(saturate(dot(n, h)), 24.0 + _Smoothness * 160.0);
                sp = smoothstep(0.30, 0.62, sp) * _Smoothness * 0.55 * lit;
                col += light.color * sp;

                // kenar ışığı: ince, gökyüzü renginde (yalnız silüete yakın)
                float fres = pow(1.0 - saturate(dot(n, v)), 3.0);
                col += half3(0.55, 0.75, 1.0) * smoothstep(0.45, 0.85, fres) * 0.14 * (0.35 + 0.65 * lit);

                col = MixFog(col, i.fog);
                return half4(col, 1);
            }
            ENDHLSL
        }

        Pass
        {
            // dış çizgi: ters kabuk; normal yönünde ekranda sabit piksel kadar şişir
            Name "ToonOutline"
            Tags { "LightMode" = "SRPDefaultUnlit" }
            Cull Front
            ZWrite On
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog

            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; float2 uv : TEXCOORD0; };
            struct Varyings { float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; float fog : TEXCOORD1; };

            Varyings vert(Attributes v)
            {
                Varyings o;
                float3 pws = TransformObjectToWorld(v.positionOS.xyz);
                float3 nws = normalize(TransformObjectToWorldNormal(v.normalOS));
                float4 cs = TransformWorldToHClip(pws);
                float2 ncs = mul((float3x3)UNITY_MATRIX_VP, nws).xy;
                float dist = length(_WorldSpaceCameraPos.xyz - pws);
                float fade = saturate((40.0 - dist) / 18.0);           // uzaktaki küçük süslerde çizgi söner
                float px = _OutlineWidth * fade * (_ScreenParams.y / 720.0);
                float2 dir = ncs / max(length(ncs), 1e-5);
                cs.xy += dir * px * 2.0 / _ScreenParams.xy * cs.w;
                o.positionCS = cs;
                o.uv = TRANSFORM_TEX(v.uv, _BaseMap);
                o.fog = ComputeFogFactor(cs.z);
                return o;
            }

            half4 frag(Varyings i) : SV_Target
            {
                half3 albedo = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, i.uv).rgb * _BaseColor.rgb;
                // çizgi rengi: dokunun koyu, biraz doygun hali (siyah değil → yumuşak, çocuk dostu)
                half lum = dot(albedo, half3(0.3, 0.59, 0.11));
                half3 sat = saturate(lerp(lum.xxx, albedo, 1.35));
                half3 col = sat * half3(0.30, 0.24, 0.26) + half3(0.04, 0.03, 0.05);
                col = MixFog(col, i.fog);
                return half4(col, 1);
            }
            ENDHLSL
        }

        Pass
        {
            Name "ShadowCaster"
            Tags { "LightMode" = "ShadowCaster" }
            ZWrite On
            ZTest LEqual
            ColorMask 0
            Cull Back
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_vertex _ _CASTING_PUNCTUAL_LIGHT_SHADOW
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            float3 _LightDirection;
            float3 _LightPosition;

            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; };
            struct Varyings { float4 positionCS : SV_POSITION; };

            Varyings vert(Attributes v)
            {
                Varyings o;
                float3 pws = TransformObjectToWorld(v.positionOS.xyz);
                float3 nws = TransformObjectToWorldNormal(v.normalOS);
            #if defined(_CASTING_PUNCTUAL_LIGHT_SHADOW)
                float3 ld = normalize(_LightPosition - pws);
            #else
                float3 ld = _LightDirection;
            #endif
                float4 cs = TransformWorldToHClip(ApplyShadowBias(pws, nws, ld));
            #if UNITY_REVERSED_Z
                cs.z = min(cs.z, UNITY_NEAR_CLIP_VALUE);
            #else
                cs.z = max(cs.z, UNITY_NEAR_CLIP_VALUE);
            #endif
                o.positionCS = cs;
                return o;
            }
            half4 frag(Varyings i) : SV_Target { return 0; }
            ENDHLSL
        }

        Pass
        {
            Name "DepthOnly"
            Tags { "LightMode" = "DepthOnly" }
            ZWrite On
            ColorMask R
            Cull Back
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            struct Attributes { float4 positionOS : POSITION; };
            struct Varyings { float4 positionCS : SV_POSITION; };
            Varyings vert(Attributes v) { Varyings o; o.positionCS = TransformObjectToHClip(v.positionOS.xyz); return o; }
            half frag(Varyings i) : SV_Target { return i.positionCS.z; }
            ENDHLSL
        }

        Pass
        {
            Name "DepthNormals"
            Tags { "LightMode" = "DepthNormals" }
            ZWrite On
            Cull Back
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; };
            struct Varyings { float4 positionCS : SV_POSITION; float3 normalWS : TEXCOORD0; };
            Varyings vert(Attributes v)
            {
                Varyings o;
                o.positionCS = TransformObjectToHClip(v.positionOS.xyz);
                o.normalWS = TransformObjectToWorldNormal(v.normalOS);
                return o;
            }
            half4 frag(Varyings i) : SV_Target { return half4(NormalizeNormalPerPixel(i.normalWS), 0.0); }
            ENDHLSL
        }
    }
    FallBack Off
}
