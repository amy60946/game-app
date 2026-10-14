// Pofi Adası denizi (URP): dalga (köşe noktasında), küçük dalgacık parıltısı, sığ turkuaz / derin lacivert,
// kıyı köpüğü. Kıyı bilgisi _ShoreMap'ten (r: sığlık, g: köpük şeridi) gelir; MapWorld arazi yüksekliğinden üretir.
// Işık ölçülü tutulur (kullanıcı uyarısı: ekran parlamasın).
Shader "Pofi/Water"
{
    Properties
    {
        _Deep ("Derin", Color) = (0.02, 0.26, 0.6, 1)
        _Shallow ("Sığ", Color) = (0.18, 0.72, 0.82, 1)
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
                float a1 = 1.0, a2 = 0.55, a3 = 0.25;
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

            half4 frag(Varyings i) : SV_Target
            {
                float t = _Time.y;
                // ince dalgacıklar (piksel başına normal)
                float2 p = i.positionWS.xz;
                float2 rip = float2(sin(p.x * 3.1 + t * 2.1) + sin(p.y * 2.3 - t * 1.7), cos(p.y * 3.7 + t * 1.5) + cos(p.x * 2.9 + p.y * 1.3 - t * 2.4)) * 0.035;
                float3 n = normalize(i.normalWS + float3(rip.x, 0, rip.y));
                float3 viewDir = normalize(GetCameraPositionWS() - i.positionWS);
                Light light = GetMainLight();

                float shallow = i.shore.r;
                float3 col = lerp(_Deep.rgb, _Shallow.rgb, shallow);
                float fres = pow(1.0 - saturate(dot(n, viewDir)), 4.0);
                col = lerp(col, _Sky.rgb, fres * 0.45);
                col *= 0.82 + 0.18 * saturate(dot(n, light.direction));

                // kıyı köpüğü: kıyıya yakın şerit, içe-dışa nefes alır
                float band = i.shore.g;
                float pulse = 0.5 + 0.5 * sin(t * 1.4 - band * 5.0);
                float noise = 0.5 + 0.5 * sin(p.x * 4.3 + sin(p.y * 3.1) * 2.0 + t * 0.7);
                float foam = saturate(band * (0.55 + 0.45 * pulse) - noise * 0.35) * 1.4;
                col = lerp(col, _Foam.rgb, saturate(foam));

                // güneş parıltısı (ölçülü)
                float3 hv = normalize(light.direction + viewDir);
                float spec = pow(saturate(dot(n, hv)), _Gloss) * _SpecStrength;
                col += spec * light.color;
                return half4(col, 1);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
