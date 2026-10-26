// Yer sisi (URP, yarı saydam, çift yüzlü; kullanıcı GB18-6: "sisler buluttan çok sise benzesin"). Tek ağda iki tür parça:
// - örtü (TEXCOORD1.x = 0): araziye yapışık, kenara doğru sönen yatay katman; gürültü yerin xz'sinden, rüzgârla kayar.
// - perde (TEXCOORD1 = (genişlik, yükseklik)): köşeleri gölgelendiricide kameraya dönen (yalnız y ekseni) dikey tül; alttan ve
//   üstten söner, gürültüyle yırtık tutamlar. Köşe rengi: rgb ton, a katman saydamlığı. Derinlik dokusu kullanmaz: kesişme çizgisi
//   olmasın diye örtü araziye göre kurulur, perdenin altı söner. Kameraya çok yakın sis silinir (içinden geçerken ekran dolmasın).
Shader "Pofi/Fog"
{
    Properties
    {
        _Lit ("Aydınlık", Color) = (0.97, 0.97, 0.95, 1)
        _Shade ("Gölge", Color) = (0.78, 0.84, 0.93, 1)
        _Alpha ("Yoğunluk", Float) = 1
        _Fade ("Dağılma (0..1)", Float) = 0
        _Wind ("Rüzgâr (xz)", Vector) = (0.35, 0.12, 0, 0)
    }
    SubShader
    {
        Tags { "RenderType" = "Transparent" "Queue" = "Transparent+10" "RenderPipeline" = "UniversalPipeline" "IgnoreProjector" = "True" }
        Blend SrcAlpha OneMinusSrcAlpha
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
                float4 _Lit, _Shade, _Wind;
                float _Alpha, _Fade;
            CBUFFER_END

            struct Attributes { float4 positionOS : POSITION; float4 color : COLOR; float2 uv : TEXCOORD0; float2 size : TEXCOORD1; };
            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float4 color : COLOR;
                float2 uv : TEXCOORD0;
                float3 positionWS : TEXCOORD1;
                float3 info : TEXCOORD2;   // x: perde mi, y: perde boyunca konum (m), z: tohum
            };

            Varyings vert(Attributes v)
            {
                Varyings o;
                float3 c = TransformObjectToWorld(v.positionOS.xyz);
                float veil = step(0.001, v.size.x);
                if (veil > 0.5)
                {
                    float3 toCam = GetCameraPositionWS() - c; toCam.y = 0;
                    float3 right = normalize(cross(float3(0, 1, 0), toCam + float3(1e-4, 0, 0)));
                    c += right * (v.uv.x - 0.5) * v.size.x + float3(0, 1, 0) * v.uv.y * v.size.y;
                }
                o.positionWS = c;
                o.positionCS = TransformWorldToHClip(c);
                o.color = v.color;
                o.uv = v.uv;
                float seed = frac(sin(dot(TransformObjectToWorld(v.positionOS.xyz).xz, float2(12.9898, 78.233))) * 43758.5453) * 40.0;
                o.info = float3(veil, v.uv.x * v.size.x, seed);
                return o;
            }

            float hash(float2 p) { return frac(sin(dot(p, float2(127.1, 311.7))) * 43758.5453); }
            float vnoise(float2 p)
            {
                float2 i = floor(p), f = frac(p);
                float2 u = f * f * (3.0 - 2.0 * f);
                return lerp(lerp(hash(i), hash(i + float2(1, 0)), u.x), lerp(hash(i + float2(0, 1)), hash(i + float2(1, 1)), u.x), u.y);
            }
            float fbm(float2 p)
            {
                float a = 0.55, s = 0;
                for (int k = 0; k < 4; k++) { s += vnoise(p) * a; p = p * 2.03 + float2(17.1, 9.2); a *= 0.5; }
                return s / 1.03125;   // 4 kat: ince tutam ayrıntısı (26 Ekim 2026)
            }

            half4 frag(Varyings i) : SV_Target
            {
                float t = _Time.y;
                float alpha, n, lit;
                if (i.info.x > 0.5)
                {
                    // perde: yatayda kenar, dikeyde alt/üst sönümü; tutamlar yukarı doğru süzülür
                    float2 q = float2(i.info.y * 0.32 + i.info.z, i.positionWS.y * 0.42 - t * 0.12);
                    n = fbm(q + _Wind.xy * t * 0.25);
                    float h = i.uv.y;
                    float vert = smoothstep(0.0, 0.22, h) * (1.0 - smoothstep(0.35, 1.0, h));
                    float side = 1.0 - pow(abs(i.uv.x * 2.0 - 1.0), 2.2);
                    // ince ayrıntı: hızlı küçük kıvrımlar perdenin kenarını yırtık, içini dolu yapar
                    float fine = vnoise(q * 3.7 + float2(t * 0.21, -t * 0.17));
                    alpha = vert * side * smoothstep(0.2, 0.68, n + (fine - 0.5) * 0.22);
                    lit = saturate(h * 0.8 + n * 0.4 + (fine - 0.5) * 0.15);
                }
                else
                {
                    // örtü: merkezden kenara söner, kalın-ince öbekler halinde kayar
                    float2 p = i.positionWS.xz * 0.16 + _Wind.xy * t * 0.18;
                    n = fbm(p) * 0.7 + fbm(p * 2.7 - _Wind.yx * t * 0.3) * 0.3;
                    float r = length(i.uv);
                    float fine = vnoise(i.positionWS.xz * 1.3 - _Wind.xy * t * 0.5);
                    alpha = (1.0 - smoothstep(0.5, 1.0, r)) * lerp(0.55, 1.0, smoothstep(0.22, 0.72, n)) * lerp(0.85, 1.05, fine);
                    lit = saturate(0.42 + n * 0.5 + (fine - 0.5) * 0.2);
                }
                float3 col = lerp(_Shade.rgb, _Lit.rgb, lit) * i.color.rgb;
                float sun = saturate(_MainLightPosition.y) * 0.08;
                col += sun;
                float d = distance(GetCameraPositionWS(), i.positionWS);
                alpha *= saturate((d - 1.5) / 4.0);            // kameraya çok yakınsa sil
                alpha *= i.color.a * _Alpha * (1.0 - _Fade);
                return half4(min(col, 1.0), saturate(alpha));
            }
            ENDHLSL
        }
    }
    FallBack Off
}
