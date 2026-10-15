// Pofuduk bulut (URP): üstü güneşle beyaz, altı serin mavi-gri yumuşak gölge; kenarda hafif ışık. Gölge düşürmez.
Shader "Pofi/Cloud"
{
    Properties
    {
        _Lit ("Aydınlık", Color) = (1, 1, 1, 1)
        _Shade ("Gölge", Color) = (0.8, 0.87, 0.98, 1)
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

            CBUFFER_START(UnityPerMaterial)
                float4 _Lit, _Shade;
            CBUFFER_END

            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; };
            struct Varyings { float4 positionCS : SV_POSITION; float3 normalWS : TEXCOORD0; float3 positionWS : TEXCOORD1; };

            Varyings vert(Attributes v)
            {
                Varyings o;
                o.positionWS = TransformObjectToWorld(v.positionOS.xyz);
                o.normalWS = TransformObjectToWorldNormal(v.normalOS);
                o.positionCS = TransformWorldToHClip(o.positionWS);
                return o;
            }

            half4 frag(Varyings i) : SV_Target
            {
                float3 n = normalize(i.normalWS);
                float up = n.y * 0.5 + 0.5;
                float sun = dot(n, _MainLightPosition.xyz) * 0.5 + 0.5;
                // yumuşak üç ton: alt serin lavanta-mavi, orta beyaz, güneşe bakan üst sıcak krem
                float k = saturate(up * 0.6 + sun * 0.5);
                float3 col = lerp(_Shade.rgb, _Lit.rgb, smoothstep(0.15, 0.85, k));
                col = lerp(col, float3(1.0, 0.97, 0.9), smoothstep(0.75, 1.0, sun) * 0.35);
                float3 v = normalize(GetCameraPositionWS() - i.positionWS);
                float rim = pow(1.0 - saturate(dot(n, v)), 3.0);
                // güneşe karşı bakınca gümüş kenar (ışık bulutun kenarından süzülür)
                float back = saturate(dot(-v, _MainLightPosition.xyz));
                col += rim * (0.06 + 0.18 * back);
                return half4(min(col, 1.0), 1);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
