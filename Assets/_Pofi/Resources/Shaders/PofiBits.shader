// Patika ayrıntıları (URP): çakıl taşları ve toprak/kum lekeleri (World.GrassField). Renk köşe renginden, yumuşak ışık + gölge alır.
// Lekeler (uv.x = 1) kenara doğru saydamlaşarak zemine karışır; taşlar (uv.x = 0) tam opak. Zeminden sonra çizilir.
Shader "Pofi/Bits"
{
    SubShader
    {
        Tags { "RenderType" = "Transparent" "RenderPipeline" = "UniversalPipeline" "Queue" = "Transparent-20" }
        Blend SrcAlpha OneMinusSrcAlpha
        ZWrite On
        Cull Back
        Pass
        {
            Name "Forward"
            Tags { "LightMode" = "UniversalForward" }
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; float2 uv : TEXCOORD0; float4 color : COLOR; };
            struct Varyings { float4 positionCS : SV_POSITION; float3 positionWS : TEXCOORD0; float3 normalWS : TEXCOORD1; float2 uv : TEXCOORD2; float4 color : TEXCOORD3; };

            Varyings vert(Attributes v)
            {
                Varyings o;
                o.positionWS = TransformObjectToWorld(v.positionOS.xyz);
                o.positionCS = TransformWorldToHClip(o.positionWS);
                o.normalWS = TransformObjectToWorldNormal(v.normalOS);
                o.uv = v.uv;
                o.color = v.color;
                return o;
            }

            half4 frag(Varyings i) : SV_Target
            {
                Light light = GetMainLight(TransformWorldToShadowCoord(i.positionWS));
                float3 n = normalize(i.normalWS);
                float wrap = saturate(dot(n, light.direction) * 0.5 + 0.5);   // yumuşak (toon benzeri) ışık
                float3 col = i.color.rgb * (SampleSH(n) + light.color * 0.8 * wrap * light.shadowAttenuation);
                float a = i.color.a;
                if (i.uv.x > 0.5) a *= 1.0 - i.uv.y * i.uv.y;   // leke: kenara doğru solar
                return half4(col, a);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
