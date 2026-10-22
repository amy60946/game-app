// Pofi Adası denizi (URP): dalga (köşe noktasında), küçük dalgacık parıltısı, sığ turkuaz / derin lacivert,
// kıyı köpüğü. Kıyı bilgisi _ShoreMap'ten (r: sığlık, g: köpük şeridi) gelir; MapWorld arazi yüksekliğinden üretir.
// Renkler (22 Ekim 2026): onaylı v6 taslağındaki açık gök mavisi deniz (eski derin lacivertti).
// Işık ölçülü tutulur (kullanıcı uyarısı: ekran parlamasın).
Shader "Pofi/Water"
{
    Properties
    {
        _Deep ("Derin", Color) = (0.16, 0.52, 0.76, 1)
        _Shallow ("Sığ", Color) = (0.24, 0.78, 0.82, 1)
        _Sky ("Gökyüzü yansıması", Color) = (0.55, 0.75, 0.95, 1)
        _Foam ("Köpük", Color) = (0.97, 0.99, 1, 1)
        _ShoreMap ("Kıyı haritası", 2D) = "black" {}
        _ShoreRect ("Kıyı haritası alanı (minX, minZ, genX, genZ)", Vector) = (0, 0, 1, 1)
        _WaveAmp ("Dalga yüksekliği", Float) = 0.09
        _Gloss ("Parıltı keskinliği", Float) = 140
        _SpecStrength ("Parıltı gücü", Float) = 0.45
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
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            CBUFFER_START(UnityPerMaterial)
                float4 _Deep, _Shallow, _Sky, _Foam, _ShoreRect;
                float _WaveAmp, _Gloss, _SpecStrength;
            CBUFFER_END
            TEXTURE2D(_ShoreMap); SAMPLER(sampler_ShoreMap);

            struct Attributes { float4 positionOS : POSITION; };
            struct Varyings { float4 positionCS : SV_POSITION; float3 positionWS : TEXCOORD0; float3 normalWS : TEXCOORD1; float4 shore : TEXCOORD2; };

            float4 Shore(float2 xz)
            {
                float2 uv = (xz - _ShoreRect.xy) / _ShoreRect.zw;
                return SAMPLE_TEXTURE2D_LOD(_ShoreMap, sampler_ShoreMap, uv, 0);
            }

            // 3 yönlü sinüs dalgası; yükseklik ve eğim
            float Waves(float2 p, float t, out float2 grad)
            {
                const float2 d1 = float2(0.8, 0.6), d2 = float2(-0.5, 0.86), d3 = float2(0.2, -0.98);
                const float k1 = 0.55, k2 = 0.9, k3 = 1.6;
                // üçüncü (3,9 m) dalga kaldırıldı: büyük adada ağ adımı 2,56 m, bu dalga köşelerde örneklenince kuşbakışında
                // zikzak kırık + güneş lekesi yapıyordu (ince ayrıntı piksel başına dalgacıkta)
                float a1 = 1.0, a2 = 0.55, a3 = 0.0;
                float p1 = dot(d1, p) * k1 + t * 0.9, p2 = dot(d2, p) * k2 + t * 1.3, p3 = dot(d3, p) * k3 + t * 1.9;
                float h = a1 * sin(p1) + a2 * sin(p2) + a3 * sin(p3);
                grad = a1 * k1 * cos(p1) * d1 + a2 * k2 * cos(p2) * d2 + a3 * k3 * cos(p3) * d3;
                return h;
            }

            Varyings vert(Attributes v)
            {
                Varyings o;
                float3 w = TransformObjectToWorld(v.positionOS.xyz);
                float4 sh = Shore(w.xz);
                float calm = 1.0 - sh.r * 0.6;                       // sığda daha sakin
                float2 g;
                float h = Waves(w.xz, _Time.y, g) * _WaveAmp * calm;
                w.y += h;
                o.positionWS = w;
                o.normalWS = normalize(float3(-g.x * _WaveAmp * calm, 1.0, -g.y * _WaveAmp * calm));
                o.positionCS = TransformWorldToHClip(w);
                o.shore = sh;
                return o;
            }

            float hash21(float2 p) { p = frac(p * float2(123.34, 456.21)); p += dot(p, p + 45.32); return frac(p.x * p.y); }

            // ucuz hücre deseni (kostik / parıltı için): en yakın nokta uzaklığı, 3x3 komşu
            float Cells(float2 p, float t)
            {
                float2 c = floor(p), f = frac(p); float d = 1.0;
                [unroll] for (int y = -1; y <= 1; y++)
                [unroll] for (int x = -1; x <= 1; x++)
                {
                    float2 g = float2(x, y); float h = hash21(c + g);
                    float2 o = 0.5 + 0.4 * sin(t * (0.6 + h) + h * 6.28 + float2(0, 1.7));
                    d = min(d, length(g + o - f));
                }
                return d;
            }

            half4 frag(Varyings i) : SV_Target
            {
                float t = _Time.y;
                // ince dalgacıklar (piksel başına normal)
                float2 p = i.positionWS.xz;
                float2 rip = float2(sin(p.x * 3.1 + t * 2.1) + sin(p.y * 2.3 - t * 1.7), cos(p.y * 3.7 + t * 1.5) + cos(p.x * 2.9 + p.y * 1.3 - t * 2.4)) * 0.035;
                // uzakta ince ayrıntı söner: piksel başına dalgacık/pırıltı/kıyı çizgisi kuşbakışında zikzak hare yapıyordu
                float camDist = distance(GetCameraPositionWS(), i.positionWS);
                float nearF = saturate(1.0 - (camDist - 18.0) / 24.0);   // kuşbakışı (~60 m) tamamen sakin
                rip *= nearF;
                float3 n = normalize(i.normalWS + float3(rip.x, 0, rip.y));
                float3 viewDir = normalize(GetCameraPositionWS() - i.positionWS);
                Light light = GetMainLight();

                float shallow = i.shore.r;
                // derinlik geçişi: lacivert → turkuaz → kıyıda açık camgöbeği (kum görünür gibi)
                float3 col = lerp(_Deep.rgb, _Shallow.rgb, smoothstep(0.0, 0.8, shallow));
                col = lerp(col, float3(0.55, 0.9, 0.86), smoothstep(0.75, 1.0, shallow) * 0.55);
                // sığda kostik ışık ağı (yavaş kıpırdar), derinde kaybolur
                float cst = Cells(p * 1.3, t * 0.8);
                col += smoothstep(0.18, 0.02, cst) * 0.12 * smoothstep(0.35, 0.9, shallow);

                float fres = pow(1.0 - saturate(dot(n, viewDir)), 4.0);
                col = lerp(col, _Sky.rgb, fres * 0.45);
                // güneş tarafı / gölge tarafı: güneşe karşı bakarken dalga ayrıntısı ve parıltı belirgin, sırtı güneşe dönükken sakin
                float facingSun = saturate(dot(normalize(float3(-viewDir.x, 0, -viewDir.z)), normalize(float3(light.direction.x, 0, light.direction.z))) * 0.5 + 0.5);
                float lam = saturate(dot(n, light.direction));
                col *= 0.84 + 0.16 * lerp(0.6, 1.0, facingSun) * lam;

                // kıyı köpüğü: kıyıya koşan ince köpük şeritleri + kıyı çizgisinde yırtık köpük; içe-dışa nefes alır
                float band = i.shore.g;
                float pulse = 0.5 + 0.5 * sin(t * 1.4 - band * 5.0);
                float noise = 0.5 + 0.5 * sin(p.x * 4.3 + sin(p.y * 3.1) * 2.0 + t * 0.7);
                float lace = Cells(p * 2.6 + float2(t * 0.15, 0), t * 0.5);
                float foam = saturate(band * (0.55 + 0.45 * pulse) - noise * 0.3 - lace * 0.35) * 1.6;
                float lines = frac(shallow * 3.0 - t * 0.22);
                float wl = smoothstep(0.0, 0.05, lines) * smoothstep(0.14, 0.05, lines) * smoothstep(0.70, 0.92, shallow) * (1.0 - band) * smoothstep(0.25, 0.6, noise);   // yalnız kıyı dibinde (açıkta taban çizgisi zikzak yapıyordu)
                col = lerp(col, _Foam.rgb, saturate(foam + wl * 0.4 * nearF));

                // güneş parıltısı (ölçülü) + seyrek göz kırpan pırıltılar (yalnız güneş tarafında)
                float3 hv = normalize(light.direction + viewDir);
                float nh = saturate(dot(n, hv));
                float spec = pow(nh, _Gloss) * _SpecStrength * lerp(0.2, 1.0, nearF);   // uzakta dalga sırtı parlaması kuşbakışında zikzak beyaz leke yapıyordu
                float2 gc = floor(p * 6.0);
                float tw = hash21(gc + floor(t * 2.0));
                float glint = step(0.985, tw) * step(0.9, pow(nh, 8.0) + 0.6) * facingSun * (1.0 - shallow * 0.5) * nearF;
                col += (spec + glint * 0.35) * light.color;
                return half4(min(col, 1.0), 1);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
