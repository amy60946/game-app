// Arayüz "çıkartma" gölgelendiricisi (24 Ekim 2026, kullanıcı: göstergelerin etrafına ince beyaz çerçeve).
// UI/Default ile aynı (maske, kırpma, saydamlık); tek fark: köşenin TEXCOORD1.x'i 1,5'ten büyükse kopya köşesidir: doku rengi
// yerine düz köşe rengi çizilir (dokunun saydamlığı kalır). UI.Sticker bu bayrakla simgenin kopyalarını beyaz kontur ve
// gölge olarak çizer; TEXCOORD1.xy − 2 = kopyanın o noktasının asıl simgedeki doku konumu. _HoleOn açıksa o konumda
// _HoleTex (Icons/Holes, art/scripts/icon_holes.py) delik diyorsa kopya silinir: simgenin içindeki kapalı boşluklar
// (çanta sapının içi) beyazla dolmaz, arkadaki harita görünür.
Shader "Pofi/UISticker"
{
    Properties
    {
        [PerRendererData] _MainTex ("Sprite Texture", 2D) = "white" {}
        _Color ("Tint", Color) = (1,1,1,1)
        _StencilComp ("Stencil Comparison", Float) = 8
        _Stencil ("Stencil ID", Float) = 0
        _StencilOp ("Stencil Operation", Float) = 0
        _StencilWriteMask ("Stencil Write Mask", Float) = 255
        _StencilReadMask ("Stencil Read Mask", Float) = 255
        _ColorMask ("Color Mask", Float) = 15
        _HoleTex ("Hole Mask", 2D) = "white" {}
        _HoleOn ("Hole Mask On", Float) = 0
        [Toggle(UNITY_UI_ALPHACLIP)] _UseUIAlphaClip ("Use Alpha Clip", Float) = 0
    }

    SubShader
    {
        Tags { "Queue"="Transparent" "IgnoreProjector"="True" "RenderType"="Transparent" "PreviewType"="Plane" "CanUseSpriteAtlas"="True" }
        Stencil
        {
            Ref [_Stencil]
            Comp [_StencilComp]
            Pass [_StencilOp]
            ReadMask [_StencilReadMask]
            WriteMask [_StencilWriteMask]
        }
        Cull Off
        Lighting Off
        ZWrite Off
        ZTest [unity_GUIZTestMode]
        Blend SrcAlpha OneMinusSrcAlpha
        ColorMask [_ColorMask]

        Pass
        {
            Name "Default"
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma target 2.0
            #include "UnityCG.cginc"
            #include "UnityUI.cginc"
            #pragma multi_compile_local _ UNITY_UI_CLIP_RECT
            #pragma multi_compile_local _ UNITY_UI_ALPHACLIP

            struct appdata_t
            {
                float4 vertex : POSITION;
                float4 color : COLOR;
                float2 texcoord : TEXCOORD0;
                float2 texcoord1 : TEXCOORD1;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct v2f
            {
                float4 vertex : SV_POSITION;
                fixed4 color : COLOR;
                float2 texcoord : TEXCOORD0;
                float4 worldPosition : TEXCOORD1;
                float3 flat : TEXCOORD2;   // x: kopya mı, yz: asıl simgedeki doku konumu
                UNITY_VERTEX_OUTPUT_STEREO
            };

            sampler2D _MainTex;
            sampler2D _HoleTex;
            float _HoleOn;
            fixed4 _Color;
            fixed4 _TextureSampleAdd;
            float4 _ClipRect;
            float4 _MainTex_ST;

            v2f vert(appdata_t v)
            {
                v2f OUT;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(OUT);
                OUT.worldPosition = v.vertex;
                OUT.vertex = UnityObjectToClipPos(OUT.worldPosition);
                OUT.texcoord = TRANSFORM_TEX(v.texcoord, _MainTex);
                OUT.color = v.color * _Color;
                OUT.flat = float3(step(1.5, v.texcoord1.x), v.texcoord1 - 2.0);
                return OUT;
            }

            fixed4 frag(v2f IN) : SV_Target
            {
                half4 tex = tex2D(_MainTex, IN.texcoord) + _TextureSampleAdd;
                half4 color;
                color.rgb = lerp(tex.rgb * IN.color.rgb, IN.color.rgb, IN.flat.x);
                color.a = tex.a * IN.color.a;
                if (_HoleOn > 0.5)
                {
                    float2 b = IN.flat.yz;
                    float inside = step(0.0, b.x) * step(b.x, 1.0) * step(0.0, b.y) * step(b.y, 1.0);
                    color.a *= 1.0 - tex2D(_HoleTex, saturate(b)).a * inside * IN.flat.x;
                }
                #ifdef UNITY_UI_CLIP_RECT
                color.a *= UnityGet2DClipping(IN.worldPosition.xy, _ClipRect);
                #endif
                #ifdef UNITY_UI_ALPHACLIP
                clip(color.a - 0.001);
                #endif
                return color;
            }
            ENDCG
        }
    }
}
