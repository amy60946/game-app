// Pofi Adası gökyüzü (URP skybox), stilize — oyunun çizgi film 3B tarzına uygun (kullanıcı, 14 Ekim 2026: "açık mavi, oyunla bütünleşik").
// v4 (22 Ekim 2026, kullanıcının gökyüzü fotoğraflarından esinle): doğal kümülüs — düz taban, yuvarlak loblu karnabahar tepe,
// lob başına ışık, saçaklı kenar, uzaktakiler ufuk pusuna karışır; üstte ince tül (cirrus). Bulutlar rüzgârla kayar, loblar yavaşça
// kaynar (yakın sıra daha hızlı: derinlik). Işık dengeli (ekran parlamasın, renkler solmasın).
// Önizleme kopyası: art/scripts/sky_v4_preview.py (aynı matematik, numpy).
Shader "Pofi/Sky"
{
    Properties
    {
        _Zenith ("Tepe", Color) = (0.33, 0.66, 0.97, 1)
        _Mid ("Orta", Color) = (0.52, 0.8, 1, 1)
        _Horizon ("Ufuk", Color) = (0.76, 0.92, 1, 1)
        _Ground ("Ufuk altı", Color) = (0.45, 0.75, 0.95, 1)
        _CloudLit ("Bulut aydınlık", Color) = (1, 1, 1, 1)
        _CloudShade ("Bulut gölge", Color) = (0.66, 0.75, 0.89, 1)
        _Clouds ("Bulut miktarı", Range(0, 1)) = 0.62
        _Sun ("Güneş", Range(0, 1)) = 1
    }
    SubShader
    {
        Tags { "Queue" = "Background" "RenderType" = "Background" "PreviewType" = "Skybox" "RenderPipeline" = "UniversalPipeline" }
        Cull Off ZWrite Off
        Pass
        {
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            CBUFFER_START(UnityPerMaterial)
                float4 _Zenith, _Mid, _Horizon, _Ground, _CloudLit, _CloudShade;
                float _Clouds, _Sun;
            CBUFFER_END

            struct Attributes { float4 positionOS : POSITION; };
            struct Varyings { float4 positionCS : SV_POSITION; float3 dir : TEXCOORD0; };

            Varyings vert(Attributes v)
            {
                Varyings o;
                o.positionCS = TransformObjectToHClip(v.positionOS.xyz);
                o.dir = v.positionOS.xyz;
                return o;
            }

            #define TAU 6.2831853
            // sin'siz karma (Dave Hoskins hash12): mobil GPU'da büyük sayılarda bozulmaz
            float hash12(float2 p) { float3 p3 = frac(p.xyx * 0.1031); p3 += dot(p3, p3.yzx + 33.33); return frac((p3.x + p3.y) * p3.z); }
            float vnoise(float2 x)
            {
                float2 i = floor(x), f = x - i, u = f * f * (3.0 - 2.0 * f);
                float a = hash12(i), b = hash12(i + float2(1, 0)), c = hash12(i + float2(0, 1)), d = hash12(i + float2(1, 1));
                return a + (b - a) * u.x + (c - a) * u.y + (a - b - c + d) * u.x * u.y;
            }
            float fbm4(float2 p, float fade)
            {
                float s = 0, a = 0.5, f = 1, norm = 0;
                [unroll] for (int o = 0; o < 4; o++)
                {
                    s += vnoise(p * f) * a * saturate(1.5 - fade * f * 2.0); norm += a;
                    p = float2(p.x * 0.8 - p.y * 0.6 + 1.7, p.x * 0.6 + p.y * 0.8 + 9.2);
                    f *= 2.03; a *= 0.5;
                }
                return s / norm;
            }

            // Bir kümülüs sırası (yandan görünüş; art/scripts/sky_v4_preview.py ile aynı): azimut hücresi başına en çok bir bulut.
            // Düz taban, yan yana yuvarlak loblar (karnabahar tepe; loblar yavaşça "kaynar"), lob başına ışık, saçaklı kenar.
            // a: örtme, tone: 0 gölge .. 1 aydınlık
            void Cumulus(float az, float el, float sunAz, float cells, float el0, float el1, float size, float seed, float T, float pw,
                         inout float alpha, inout float tone)
            {
                if (el < el0 - size * 0.5 || el > el1 + size * 3.0) return;
                float drift = T * 0.006 * (1.0 + seed * 0.25);                 // yakın sıra biraz hızlı (derinlik)
                float x = az / TAU * cells + drift;
                float churn = T * 0.02;
                for (int dc = -1; dc <= 1; dc++)
                {
                    float c = floor(x) + dc;
                    float cw = c - cells * floor(c / cells);                    // ±180°'de dikişsiz
                    #define R(k) hash12(float2(cw * 13.1 + (k) * 1.7, seed * 7.7 + (k) * 3.1))
                    if (R(0) >= _Clouds) continue;
                    float cxp = c + 0.25 + R(1) * 0.5;
                    float ce = lerp(el0, el1, R(2));
                    float s = size * (0.6 + R(3) * 0.9);
                    float lx = (x - cxp) * (TAU / cells) * cos(el) / s;
                    float ly = (el - ce) / s;
                    float W = 0.9 + R(5) * 1.4, Hh = 0.45 + pow(R(6), 1.3) * 1.1;
                    if (abs(lx) > W * 1.7 || ly < -0.35 || ly > Hh * 1.6 + 0.3) continue;
                    float k0 = R(9) * 50.0;
                    float b3 = vnoise(float2(lx * 9.0 + k0 + 3.0, ly * 9.0 + churn * 2.3));   // saçak dokusu
                    float sx = 0.45 * sign(sin(sunAz - (cxp - drift) / cells * TAU));
                    float top = -1.0;
                    float lt = saturate(0.3 + ly * 0.9);                                       // gövde: aşağı serin
                    [unroll] for (int j = 0; j < 10; j++)
                    {
                        bool big = j < 6;
                        float n = big ? 6.0 : 4.0, jj = big ? j : j - 6;
                        float uj = (jj + 0.5) / n * 2.0 - 1.0 + (R(20 + j) - 0.5) * (big ? 0.3 : 0.5);
                        float ox = uj * W * (big ? 0.85 : 0.55);
                        float rj = (0.26 + 0.28 * R(30 + j)) * (0.6 + Hh * 0.5) * (1.0 - 0.35 * abs(uj)) * (big ? 1.0 : 0.62) + 0.025 * sin(churn * 3.0 + j);
                        float cy = Hh * (1.0 - uj * uj) * (big ? (0.3 + 0.4 * R(40 + j)) : (0.75 + 0.3 * R(40 + j)));
                        float dx = lx - ox, dy = ly - cy;
                        float q = rj * rj - dx * dx;
                        float hj = q > 0 ? cy + sqrt(q) : -1.0;
                        float hm = max(top, hj);
                        top = hm + 0.06 * log(exp((top - hm) / 0.06) + exp((hj - hm) / 0.06));   // yumuşak birleşim
                        float lj = saturate(0.6 + 0.38 * clamp(dy / rj, -1, 1) + sx * clamp(dx / rj, -1, 1) * 0.8);
                        lt = lerp(lt, lj, smoothstep(rj * 1.05, rj * 0.45, length(float2(dx, dy))));  // ressam sırası
                    }
                    #undef R
                    if (abs(lx) < W * 0.95) top = max(top, 0.18 * (1.0 - (lx / W) * (lx / W)));     // loblar arası gövde
                    top += (b3 - 0.5) * 0.06;
                    float inside = top - ly;
                    float base = ly + 0.04 + (b3 - 0.5) * 0.04;                                    // düz taban
                    float sdf = min(inside, base * 2.2);
                    float a = smoothstep(0.0, max(0.05 + 0.05 * b3, pw / s), sdf);
                    float hgt = saturate(ly / max(top, 0.05));
                    float lit = 0.25 + 0.4 * smoothstep(0.0, 0.9, hgt) + 0.45 * lt + 0.12 * clamp(lx * sign(sx) / W, -1, 1);
                    lit = lit - 0.3 * smoothstep(0.14, 0.0, ly) - 0.16 * (0.5 - b3);
                    lit += 0.25 * smoothstep(0.12, 0.0, inside) * smoothstep(0.0, 0.1, ly);         // gümüş kenar
                    if (a > alpha) tone = saturate(lit);
                    alpha = max(alpha, a);
                }
            }

            half4 frag(Varyings i) : SV_Target
            {
                float3 d = normalize(i.dir);
                float h = d.y, hp = saturate(h);
                float el = asin(clamp(h, -1.0, 1.0)), az = atan2(d.x, d.z);

                // renk geçişi: ufuk → orta → tepe (beyaz pus yok)
                float3 col = lerp(_Horizon.rgb, _Mid.rgb, smoothstep(0.0, 0.3, hp));
                col = lerp(col, _Zenith.rgb, smoothstep(0.2, 1.0, hp));
                float3 L = _MainLightPosition.xyz;
                float mu = dot(d, L);
                col *= 0.95 + 0.08 * pow(mu * 0.5 + 0.5, 2.0);                       // güneş tarafı bir tık açık
                if (h < 0) col = lerp(_Ground.rgb, _Horizon.rgb, exp(h * 8.0));

                // güneş: yumuşak kenarlı küçük disk + hafif hale
                float ang = acos(clamp(mu, -1.0, 1.0));
                col += float3(1.0, 0.95, 0.82) * _Sun * ((1.0 - smoothstep(0.022, 0.03, ang)) * 0.9 + exp(-ang * 9.0) * 0.12);

                // yüksek tül (cirrus): rüzgâr yönünde uzamış ince, yarı saydam çizgiler (yatay düzleme izdüşüm)
                float t = _Time.y, sunAz = atan2(L.x, L.z);
                float hh = max(h, 0.0) + 0.035;
                float2 pp = d.xz / hh;
                float2 cq = float2((pp.x * 0.9 + pp.y * 0.4) * 0.16 + t * 0.003, (pp.y * 0.9 - pp.x * 0.4) * 0.7);
                float ci = smoothstep(0.55, 0.85, fbm4(cq, 0.004 / hh)) * smoothstep(0.45, 0.7, vnoise(float2(cq.x * 0.3 + 3.0, cq.y * 0.12)));
                ci *= 0.32 * smoothstep(0.05, 0.3, h) * _Clouds / 0.62;
                col = lerp(col, _CloudLit.rgb, ci);

                // kümülüs sıraları: uzak/alçak küçükler ufuk pusuna karışır, yakın/yüksek büyükler
                float pw = fwidth(el) * 1.2;
                float a, tone; float3 cc;
                a = 0; tone = 1; Cumulus(az, el, sunAz, 22, 0.02, 0.045, 0.028, 1, t, pw, a, tone);
                cc = lerp(lerp(_CloudShade.rgb, _CloudLit.rgb, tone), _Horizon.rgb, 0.42); col = lerp(col, cc, a);
                a = 0; tone = 1; Cumulus(az, el, sunAz, 12, 0.045, 0.1, 0.06, 2, t, pw, a, tone);
                cc = lerp(lerp(_CloudShade.rgb, _CloudLit.rgb, tone), _Horizon.rgb, 0.18); col = lerp(col, cc, a);
                a = 0; tone = 1; Cumulus(az, el, sunAz, 7, 0.11, 0.3, 0.1, 3, t, pw, a, tone);
                cc = lerp(_CloudShade.rgb, _CloudLit.rgb, tone); col = lerp(col, cc, a);
                return half4(col, 1);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
