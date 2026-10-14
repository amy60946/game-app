// Pofi Adası gökyüzü (URP skybox): ufuktan tepeye renk geçişi, ufukta hafif pus, güneş ışıması, yüksekte çok hafif bulut tülü.
// Işık dengeli (kullanıcı uyarısı: ekran parlamasın, renkler solmasın).
Shader "Pofi/Sky"
{
    Properties
    {
        _Zenith ("Tepe", Color) = (0.13, 0.38, 0.86, 1)
        _Horizon ("Ufuk", Color) = (0.62, 0.8, 0.98, 1)
        _Ground ("Ufuk altı", Color) = (0.42, 0.66, 0.86, 1)
        _SunGlow ("Güneş ışıması", Float) = 0.35
        _Wisps ("Bulut tülü", Float) = 0.4
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
                float4 _Zenith, _Horizon, _Ground;
                float _SunGlow, _Wisps;
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

            float hash(float2 p) { return frac(sin(dot(p, float2(127.1, 311.7))) * 43758.5453); }
            float vnoise(float2 p)
            {
                float2 i = floor(p), f = frac(p);
                float2 u = f * f * (3.0 - 2.0 * f);
                return lerp(lerp(hash(i), hash(i + float2(1, 0)), u.x), lerp(hash(i + float2(0, 1)), hash(i + float2(1, 1)), u.x), u.y);
            }
            float fbm(float2 p) { float a = 0.5, s = 0; for (int k = 0; k < 4; k++) { s += a * vnoise(p); p *= 2.03; a *= 0.5; } return s; }

            half4 frag(Varyings i) : SV_Target
            {
                float3 d = normalize(i.dir);
                float h = d.y;
                float3 col = h > 0 ? lerp(_Horizon.rgb, _Zenith.rgb, pow(saturate(h), 0.55)) : lerp(_Horizon.rgb, _Ground.rgb, saturate(-h * 4.0));
                col = lerp(col, float3(0.9, 0.95, 1.0), exp(-abs(h) * 16.0) * 0.22);           // ufuk pusu
                float s = saturate(dot(d, _MainLightPosition.xyz));
                col += _MainLightColor.rgb * (pow(s, 48.0) * _SunGlow * 0.3 + pow(s, 900.0) * 0.5); // ölçülü güneş
                if (h > 0.02)
                {
                    float2 uv = d.xz / (h + 0.2) * 0.9 + float2(_Time.y * 0.004, _Time.y * 0.002);
                    float c = smoothstep(0.58, 0.85, fbm(uv * 2.2)) * saturate(h * 3.0);
                    col = lerp(col, float3(0.96, 0.97, 1.0), c * _Wisps);
                }
                return half4(col, 1);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
