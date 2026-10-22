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
        _MaskMap ("Maske (r: kanyon kaldırımı)", 2D) = "black" {}
        _Cobble ("Kaldırım taşı gücü", Float) = 0
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
                float _RippleStrength, _WetLevel, _RockStrata, _Cobble;
            CBUFFER_END
            TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);
            TEXTURE2D(_MaskMap); SAMPLER(sampler_MaskMap);

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

            float2 hash22(float2 p) { float3 p3 = frac(p.xyx * float3(0.1031, 0.1030, 0.0973)); p3 += dot(p3, p3.yzx + 33.33); return frac((p3.xx + p3.yz) * p3.zy); }

            // v6 kaya (22 Ekim 2026, taslaktaki kanyon/yar görünümü): soğuk açık gri levhalar, 1,6 m'lik yatay tabakalar;
            // her tabakada kaydırılmış dikey çatlaklarla bölünmüş bloklar (blok başına ton ve hafif eğim), çatlak ve tabaka
            // altında koyu oyuk, üst kenarda açık pah; deniz kıyısında ıslak koyu. along: yüzeyin yatay yönü (iki izdüşüm karışımı).
            float3 StrataAt(float y, float along, float2 q, out float groove, out float2 tilt)
            {
                float wob = vnoise(q * 0.17) * 1.6 + vnoise(q * 0.6) * 0.4;
                float ly = y / 1.6 + wob / 6.2832;
                float layer = floor(ly), fr = ly - layer;
                // dikey çatlaklar: tabaka başına kaydırılmış, genişliği 0,9–2,2 m bloklar
                float bw = lerp(0.9, 2.2, hash12(float2(layer, 7.1)));
                float u = along / bw + hash12(float2(layer, 3.3)) * 10.0 + vnoise(float2(y * 1.3, along * 0.3)) * 0.35;
                float cell = floor(u), fu = u - cell;
                float rnd = hash12(float2(cell, layer));
                float crack = smoothstep(0.06, 0.0, fu) + smoothstep(0.94, 1.0, fu);
                float under = smoothstep(0.10, 0.0, fr);                                   // tabaka altı oyuk
                float lip = smoothstep(0.86, 0.97, fr) * (1.0 - smoothstep(0.97, 1.0, fr)); // üst pah (açık)
                groove = saturate(max(crack * 0.85, under));
                float streak = vnoise(float2(along * 3.0, y * 0.45)) * 0.7 + vnoise(float2(along * 9.0, y * 1.4)) * 0.3;
                float3 rk = lerp(Lin(float3(0.60, 0.60, 0.62)), Lin(float3(0.83, 0.82, 0.80)), saturate(0.35 + rnd * 0.45 + (streak - 0.5) * 0.5));
                rk = lerp(rk, Lin(float3(0.47, 0.45, 0.50)), smoothstep(0.62, 0.85, streak) * 0.55);
                rk = lerp(rk, Lin(float3(0.92, 0.90, 0.87)), lip * 0.6);
                rk = lerp(rk, Lin(float3(0.40, 0.39, 0.42)), smoothstep(1.6, 0.0, y) * 0.55);
                rk = lerp(rk, Lin(float3(0.24, 0.23, 0.27)), groove * 0.8);
                // blok yüzeyi hafif eğik (yontulmuş levha hissi) + çatlağa doğru kavis
                tilt = float2((rnd - 0.5) * 0.5 + (fu - 0.5) * 0.25 * (1.0 - crack), (hash12(float2(layer, cell + 9.0)) - 0.5) * 0.35);
                return rk;
            }

            float3 Strata(float3 w, float3 n, out float groove, out float3 bend)
            {
                // yüzey x'e bakıyorsa z boyunca, z'ye bakıyorsa x boyunca ilerle; ikisini yönle karıştır (dikiş görünmesin)
                float wx = abs(n.x), wz = abs(n.z); float s = wx + wz + 1e-4; wx /= s; wz /= s;
                float g1, g2; float2 t1, t2;
                float3 a = StrataAt(w.y, w.z, w.xz, g1, t1);
                float3 b = StrataAt(w.y, w.x, w.xz + 31.0, g2, t2);
                groove = g1 * wx + g2 * wz;
                float2 t = t1 * wx + t2 * wz;
                // eğim: yatay bileşen yüzeyin yatay teğetine, dikey bileşen yukarı
                float3 side = normalize(float3(-n.z, 0, n.x) + 1e-4);
                bend = side * t.x + float3(0, 1, 0) * t.y;
                return a * wx + b * wz;
            }

            // kanyon kaldırımı: dünya koordinatlı Voronoi taşları (0,22 m), aralarda kahve toprak; uzakta söner (titreme olmasın)
            float3 Cobbles(float2 p, float3 base, out float edge)
            {
                float2 g = p / 0.22; float2 c = floor(g), f = g - c;
                float d1 = 8.0, d2 = 8.0; float2 id = 0;
                [unroll] for (int y = -1; y <= 1; y++)
                [unroll] for (int x = -1; x <= 1; x++)
                {
                    float2 o = float2(x, y); float2 r = o + hash22(c + o) * 0.85 - f;
                    float d = dot(r, r);
                    if (d < d1) { d2 = d1; d1 = d; id = c + o; } else if (d < d2) d2 = d;
                }
                edge = smoothstep(0.10, 0.02, sqrt(d2) - sqrt(d1));
                float h = hash12(id);
                float3 stone = lerp(Lin(float3(0.62, 0.62, 0.63)), Lin(float3(0.86, 0.85, 0.83)), h);
                stone = lerp(stone, Lin(float3(0.70, 0.60, 0.50)), step(0.78, hash12(id + 5.0)) * 0.6);
                float3 dirt = Lin(float3(0.44, 0.34, 0.24));
                return lerp(stone, dirt, edge);
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
                float steep = smoothstep(0.80, 0.55, n.y) * _RockStrata;
                if (steep > 0.001)
                {
                    float groove; float3 bend;
                    float3 rk = Strata(i.positionWS, n, groove, bend);
                    albedo = lerp(albedo, rk, steep);
                    // blok eğimi + oyuk gölgesi (normal aşağı/içe bükülür): tabaka altları ve çatlaklar ışık almaz
                    n = normalize(n + (bend * 0.55 - float3(0, 0.45, 0) * groove) * steep);
                }
                // kanyon tabanı kaldırım taşı (maske dokusu r), kameraya yakınken
                float cob = SAMPLE_TEXTURE2D(_MaskMap, sampler_MaskMap, i.uv).r * _Cobble * (1.0 - steep);
                float camd = distance(GetCameraPositionWS(), i.positionWS);
                cob *= smoothstep(38.0, 18.0, camd);
                if (cob > 0.001)
                {
                    float edge;
                    float3 cb = Cobbles(p, albedo, edge);
                    albedo = lerp(albedo, cb * lerp(0.9, 1.1, tex.g), cob * 0.9);
                    n = normalize(n + float3(0, -0.25, 0) * edge * cob);
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
