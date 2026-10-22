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
                // taslaktaki kanyon duvarı: serin gri, dikey akan kıvrımlar (perde gibi oluklar) ağır basar, yatay tabaka
                // izi hafif; düzensiz genişlikte dikey sütunlar (çatlak çizgisi y boyunca kıvrılır), çatlak/oluk diplerinde koyu
                float wob = vnoise(q * 0.17) * 1.6 + vnoise(q * 0.6) * 0.4;
                float ly = y / 1.6 + wob / 6.2832;
                float layer = floor(ly), fr = ly - layer;
                float bw = lerp(1.4, 3.6, hash12(float2(floor(ly * 0.5), 7.1)));
                float u = along / bw + vnoise(float2(y * 0.55, along * 0.2)) * 0.3 + hash12(float2(floor(ly * 0.5), 3.3)) * 10.0;
                float cell = floor(u), fu = u - cell;
                float rnd = hash12(float2(cell, floor(ly * 0.5)));
                float crack = smoothstep(0.05, 0.0, fu) + smoothstep(0.95, 1.0, fu);
                float under = smoothstep(0.10, 0.0, fr) * 0.8;                            // tabaka altı oyuğu
                float lip = smoothstep(0.88, 0.97, fr) * (1.0 - smoothstep(0.97, 1.0, fr));
                // dikey perde oluklar: geniş (ince kıvrık çizgi gibi okunmasın), dikeyde çok düşük frekans
                float drape = vnoise(float2(along * 0.9, y * 0.10)) * 0.65 + vnoise(float2(along * 3.2, y * 0.3)) * 0.35;
                float fold = smoothstep(0.30, 0.80, drape);
                groove = saturate(max(crack * 0.95, under) + smoothstep(0.34, 0.16, drape) * 0.35);
                // taslaktaki yar: orta-koyu serin gri bloklar, tabaka üstü açık pah, altı koyu (oyunda açık ton soluk/pembe okunuyordu)
                // güneş sıcak (1, .95, .86) + renk süzgeci: albedo serine kaydırılır ki yar ekranda pembe-bej değil gri okunsun (ölçüm: 167,153,146)
                float3 dark = Lin(float3(0.26, 0.28, 0.33)), mid = Lin(float3(0.43, 0.45, 0.51)), light = Lin(float3(0.58, 0.60, 0.65));
                float3 rk = lerp(mid, light, saturate(fold * 0.75 + (rnd - 0.5) * 0.5));
                rk = lerp(rk, dark, smoothstep(0.32, 0.14, drape) * 0.5);
                rk = lerp(rk, Lin(float3(0.74, 0.75, 0.78)), lip * 0.5);
                rk = lerp(rk, Lin(float3(0.30, 0.30, 0.33)), smoothstep(1.6, 0.0, y) * 0.55);
                rk = lerp(rk, Lin(float3(0.16, 0.16, 0.20)), groove * 0.8);
                tilt = float2((fold - 0.5) * 0.7 + (rnd - 0.5) * 0.6, (hash12(float2(floor(ly * 0.5), cell + 9.0)) - 0.5) * 0.35 + 0.1);
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

            // kanyon kaldırımı: dünya koordinatlı Voronoi taşları (~0,15 m), aralarda kahve toprak; uzakta söner (titreme olmasın)
            float3 Cobbles(float2 p, out float edge)
            {
                float2 g = p / 0.13; float2 c = floor(g), f = g - c;
                float d1 = 8.0, d2 = 8.0; float2 id = 0;
                [unroll] for (int y = -1; y <= 1; y++)
                [unroll] for (int x = -1; x <= 1; x++)
                {
                    float2 o = float2(x, y); float2 r = o + hash22(c + o) * 0.85 - f;
                    float d = dot(r, r);
                    if (d < d1) { d2 = d1; d1 = d; id = c + o; } else if (d < d2) d2 = d;
                }
                edge = smoothstep(0.16, 0.04, sqrt(d2) - sqrt(d1));
                float h = hash12(id);
                // taslaktaki kaldırım: orta-koyu gri taşlar (açık bej değil), arada koyu toprak derzi
                float3 stone = lerp(Lin(float3(0.36, 0.37, 0.40)), Lin(float3(0.60, 0.60, 0.61)), h * h);
                stone = lerp(stone, Lin(float3(0.52, 0.46, 0.40)), step(0.8, hash12(id + 5.0)) * 0.5);
                float3 dirt = Lin(float3(0.27, 0.22, 0.17));
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
                    n = normalize(n + (bend * 1.3 - float3(0, 0.6, 0) * groove) * steep);
                }
                // kanyon tabanı kaldırım taşı (maske dokusu r), kameraya yakınken
                float4 mk = SAMPLE_TEXTURE2D(_MaskMap, sampler_MaskMap, i.uv);
                float cob = mk.r * _Cobble * (1.0 - steep);
                float camd = distance(GetCameraPositionWS(), i.positionWS);
                // çiçek tarlası (maske g: çan çiçeği, b: turuncu): yakında 3B öbekler (GrassField) var, uzakta zemin rengi olarak
                float farF = smoothstep(7.0, 13.0, camd) * _Cobble * (1.0 - steep);
                float speck = smoothstep(0.35, 0.75, vnoise(p * 2.3) * 0.6 + vnoise(p * 7.0) * 0.4);
                albedo = lerp(albedo, lerp(Lin(float3(0.26, 0.29, 0.72)), Lin(float3(0.40, 0.37, 0.82)), speck), saturate(mk.g * 1.4) * lerp(0.55, 0.9, speck) * farF);
                albedo = lerp(albedo, Lin(float3(0.90, 0.56, 0.26)), saturate(mk.b * 1.2) * speck * 0.6 * farF);
                cob *= smoothstep(38.0, 18.0, camd);
                if (cob > 0.001)
                {
                    float edge;
                    float3 cb = Cobbles(p, edge);
                    albedo = lerp(albedo, cb * lerp(0.9, 1.1, tex.g), cob * 0.95);
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
