// Pofi Adası zemini (URP): boyanmış doku (_BaseMap; alfa = kum ağırlığı) + kumda rüzgâr çizgileri ve ıslak kum,
// çimende ince ton dalgası. Ana ışık + gölge + ortam ışığı. Işık dengeli (parlama yok).
Shader "Pofi/Ground"
{
    Properties
    {
        _BaseMap ("Doku", 2D) = "white" {}
        _RippleStrength ("Kum çizgisi gücü", Float) = 0.35
        _WetLevel ("Islak kum yüksekliği", Float) = 0.28
        _RockStrata ("Dik yüzde kaya tabakası (v6)", Float) = 0
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
                float _RippleStrength, _WetLevel, _RockStrata;
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

            float hash12(float2 p) { float3 p3 = frac(p.xyx * 0.1031); p3 += dot(p3, p3.yzx + 33.33); return frac((p3.x + p3.y) * p3.z); }
            float vnoise(float2 x)
            {
                float2 i = floor(x), f = x - i, u = f * f * (3.0 - 2.0 * f);
                float a = hash12(i), b = hash12(i + float2(1, 0)), c = hash12(i + float2(0, 1)), d = hash12(i + float2(1, 1));
                return a + (b - a) * u.x + (c - a) * u.y + (a - b - c + d) * u.x * u.y;
            }
            float3 Lin(float3 c) { return c * c * (c * 0.305306011 + 0.682171111) + 0.012522878; }   // sRGB → doğrusal (yaklaşık)

            // v6 kaya (taslaktaki kaya malzemesiyle aynı fikir): 1,6 m'lik yatay tabaka bantları, bant altında koyu oyuk,
            // dikey ince oluklar (yatay yüksek, dikey düşük frekanslı gürültü), açık kenar; deniz kıyısında ıslak koyu.
            float3 Strata(float3 w, out float groove)
            {
                float2 q = w.xz;
                float wob = vnoise(q * 0.17) * 2.0 + vnoise(q * 0.6) * 0.5;
                float band = sin(w.y * (6.2832 / 1.6) + wob) * 0.5 + 0.5;
                float fr = frac(w.y / 1.6 + wob / 6.2832);
                groove = smoothstep(0.10, 0.0, fr) + smoothstep(0.9, 1.0, fr) * 0.6;           // tabaka arası oyuk
                float along = (q.x + q.y) * 0.7071;
                float streak = vnoise(float2(along * 3.0, w.y * 0.45)) * 0.7 + vnoise(float2(along * 9.0, w.y * 1.4)) * 0.3;
                float3 rk = lerp(Lin(float3(0.639, 0.573, 0.604)), Lin(float3(0.816, 0.761, 0.722)), band * 0.7 + 0.15);
                rk = lerp(rk, Lin(float3(0.431, 0.373, 0.463)), smoothstep(0.52, 0.78, streak) * 0.7);
                rk = lerp(rk, Lin(float3(0.878, 0.831, 0.784)), smoothstep(0.3, 0.12, streak) * 0.5);
                rk = lerp(rk, Lin(float3(0.435, 0.408, 0.447)), smoothstep(1.6, 0.0, w.y) * 0.55);
                rk *= 1.0 - groove * 0.45;
                return rk;
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
                // dik yüz: üstten pişmiş doku burada sıkışık; yerine dünya koordinatlı tabaka (yar yüzü gerçek derinlik hissi)
                float steep = smoothstep(0.78, 0.55, n.y) * _RockStrata;
                if (steep > 0.001)
                {
                    float groove;
                    float3 rk = Strata(i.positionWS, groove);
                    albedo = lerp(albedo, rk, steep);
                    // oyuk gölgesi normali hafif aşağı büker: tabaka altları ışık almaz
                    n = normalize(n - float3(0, 0.35, 0) * groove * steep);
                }
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
