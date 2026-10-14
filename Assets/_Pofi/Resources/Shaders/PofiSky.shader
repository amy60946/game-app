// Pofi Adası gökyüzü (URP skybox), stilize — oyunun çizgi film 3B tarzına uygun (kullanıcı, 14 Ekim 2026: "açık mavi, oyunla bütünleşik").
// Açık mavi geçiş; net kenarlı, iki tonlu "pamuk şeker" bulutlar, her biri özgün biçimde (yayvan / kule / küçük tutam;
// açısal hücrelerde gövde + tümsek birleşimi), üç sıra: uzak/orta/yakın; küçük yumuşak güneş. Bulutlar yavaşça kayar. Işık dengeli (ekran parlamasın, renkler solmasın).
// Önizleme kopyası: art/scripts/sky_preview.py (aynı matematik, numpy).
Shader "Pofi/Sky"
{
    Properties
    {
        _Zenith ("Tepe", Color) = (0.33, 0.66, 0.97, 1)
        _Mid ("Orta", Color) = (0.52, 0.8, 1, 1)
        _Horizon ("Ufuk", Color) = (0.76, 0.92, 1, 1)
        _Ground ("Ufuk altı", Color) = (0.45, 0.75, 0.95, 1)
        _CloudLit ("Bulut aydınlık", Color) = (1, 1, 1, 1)
        _CloudShade ("Bulut gölge", Color) = (0.8, 0.87, 0.98, 1)
        _Clouds ("Bulut miktarı", Range(0, 1)) = 0.65
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
            float h1(float n) { return frac(sin(n * 91.345 + 47.0) * 43758.5453); }
            float smin(float a, float b, float k) { float h = saturate(0.5 + 0.5 * (b - a) / k); return lerp(b, a, h) - k * h * (1.0 - h); }

            // Bir bulut sırası: azimut hücreleri, hücre başına en çok bir bulut. a: örtme, t: ton (0 gölge .. 1 aydınlık)
            void Layer(float az, float el, float sunAz, float cells, float el0, float el1, float size, float seed, float drift, float pw,
                       inout float alpha, inout float tone)
            {
                if (el < el0 - size * 2.0 || el > el1 + size * 2.5) return;
                float x = az / TAU * cells + drift;
                for (int dc = -1; dc <= 1; dc++)
                {
                    float c = floor(x) + dc;
                    float k0 = (c - cells * floor(c / cells)) * 13.1 + seed * 7.7;   // azimut ±180°'de dikişsiz (hücre sarar)
                    if (h1(k0) >= _Clouds) continue;
                    float cx = c + 0.2 + h1(k0 + 1) * 0.6;
                    float ce = lerp(el0, el1, h1(k0 + 2));
                    float s = size * (0.5 + h1(k0 + 3) * 1.0);
                    float px = (x - cx) * (TAU / cells) * cos(el) / s;
                    float py = (el - ce) / s;
                    float cloudAz = (cx - drift) / cells * TAU;
                    float sunx = sin(sunAz - cloudAz) > 0 ? 0.35 : -0.35;
                    // her bulut özgün: yarı genişlik, kabarıklık ve tümsek sayısı buluttan buluta değişir (yayvan / kule / küçük tutam)
                    float W = 0.45 + h1(k0 + 5) * 1.2;
                    float H = 0.12 + pow(h1(k0 + 6), 1.5) * 0.9;
                    float n = min(8.0, max(3.0 + floor(h1(k0 + 7) * 4.0), ceil(W * 3.2)));
                    float sp = 2.0 * W / n;
                    // gövde: tümsekleri birleştiren yatay kapsül (düz tabanlı)
                    float rb = 0.2 + 0.12 * H;
                    float body = length(float2(px - clamp(px, -W * 0.8, W * 0.8), py - 0.06)) - rb;
                    float dist = body, lt = 1.0;
                    // ressam sırası: ortadaki (yüksek, arkadaki) tümsekten kenarlara (alçak, öndeki); öndekinin aydınlık tepesi
                    // arkadakinin gölgeli altına biner → çizgi film bulut kıvrımları
                    float mid = floor(n * 0.5);
                    [unroll] for (int k = 0; k < 8; k++)
                    {
                        float on = k < n ? 0.0 : 9.0;                               // kullanılmayan tümsek uzakta
                        float i = mid + ((k & 1) == 1 ? -(float)((k + 1) / 2) : (float)(k / 2));
                        float u = (i + 0.5) / n * 2.0 - 1.0 + (h1(k0 + 20 + i) - 0.5) * 0.6 / n;
                        float ox = u * W;
                        float rr = max(sp * 0.72, (0.24 + 0.2 * h1(k0 + 40 + i)) * (0.7 + H * 0.6)) * (1.0 - 0.3 * abs(u));
                        float oy = min(H * (1.0 - u * u) * (0.55 + 0.7 * h1(k0 + 30 + i)), rb + rr * (0.5 + H * 0.9));
                        float dd = length(float2(px - ox, py - oy)) - rr + on;
                        dist = smin(dist, dd, 0.22);                                   // geniş yumuşak birleşim (tekil toplar seçilmesin)
                        float cov = smoothstep(0.06, -0.22, dd) * 0.85;               // yumuşak geçişli kıvrım
                        lt = lerp(lt, smoothstep(-0.9, 0.55, (py - oy) / rr + (px - ox) / rr * sunx), cov);
                    }
                    // gövdenin alt yarısı en önde
                    lt = lerp(lt, smoothstep(-1.0, 0.7, (py - 0.06) / rb), smoothstep(0.06, -0.22, body) * smoothstep(0.0, -0.15, py - 0.06));
                    dist = max(dist, -(py + 0.1));                                      // düz taban
                    float w = max(pw / s, 0.002);                                    // bir piksel (kenar yumuşatma)
                    float a = 1.0 - smoothstep(-w, w, dist);
                    if (a > alpha) tone = lt * smoothstep(-0.1, 0.05, py);
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

                // bulut sıraları: uzak/alçak küçük (havaya karışır), orta, yakın/yüksek büyük
                float sunAz = atan2(L.x, L.z), t = _Time.y;
                float pw = fwidth(el) * 1.2;                                            // piksel açısı (döngü dışında)
                float a, tone; float3 cc;
                a = 0; tone = 1; Layer(az, el, sunAz, 20, 0.025, 0.05, 0.03, 1, t * 0.0016, pw, a, tone);
                cc = lerp(lerp(_CloudShade.rgb, _CloudLit.rgb, tone), _Horizon.rgb, 0.35); col = lerp(col, cc, a);
                a = 0; tone = 1; Layer(az, el, sunAz, 11, 0.05, 0.11, 0.065, 2, t * 0.0022, pw, a, tone);
                cc = lerp(lerp(_CloudShade.rgb, _CloudLit.rgb, tone), _Horizon.rgb, 0.12); col = lerp(col, cc, a);
                a = 0; tone = 1; Layer(az, el, sunAz, 7, 0.13, 0.35, 0.1, 3, t * 0.003, pw, a, tone);
                cc = lerp(_CloudShade.rgb, _CloudLit.rgb, tone); col = lerp(col, cc, a);
                return half4(col, 1);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
