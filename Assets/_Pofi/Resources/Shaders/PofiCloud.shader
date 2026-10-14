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
                float3 col = lerp(_Shade.rgb, _Lit.rgb, saturate(up * 0.65 + sun * 0.45));
                float3 v = normalize(GetCameraPositionWS() - i.positionWS);
                col += pow(1.0 - saturate(dot(n, v)), 3.0) * 0.08;   // yumuşak kenar
                return half4(min(col, 1.0), 1);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
