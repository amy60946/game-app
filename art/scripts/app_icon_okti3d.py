"""Moyo Oyun uygulama simgesi, tamamen kodla (kullanıcı, 23 Kasım 2026: "Okti'yi zemine oturt, daha oturaklı bir çalışma yap,
kollar simetrik olmak zorunda değil, kodla yap; Meshy beğenmiyorum, özgün değil").

Blender (Cycles) sahnesi: kumsalda oturan sevimli mavi ahtapot Okti. Büyük yuvarlak baş, parlak boncuk gözler, gülümseme, al yanak;
sekiz kol kuma yayılır, uçları kıvrık ve vantuzlu. Asimetrik duruş: sağ kol havada, ucu bir inciyi sarar; sol kol kumda büyük bir
kıvrım yapar; önde açık istiridye. Fon oyunun kendi kodla yapılmış varlıklarıyla: palmiye (Env/palm) solda, uzak adacıkta fener
(Env/b_lighthouse) sağda, sıcak gün doğumu göğü (R2 paleti), turkuaz deniz, kıyı köpüğü. Hiçbir görsel yapay zekâdan gelmez.

Kullanım (bpy yalnız python3.11'de):
    python3.11 -I art/scripts/app_icon_okti3d.py <çıktı.png> [örnek_sayısı] [boyut]
Rozet sonra: python3 -I art/scripts/app_icon_moyo.py <simge.png> <çıktı.png>
"""
import math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "art", "code3d")); sys.path.insert(0, os.path.join(ROOT, "art", "code3d", "v6"))
import bpy
from mathutils import Vector as V
import kit
import residents_v1 as R

OUT = sys.argv[1]
SAMPLES = int(sys.argv[2]) if len(sys.argv) > 2 else 96
SIZE = int(sys.argv[3]) if len(sys.argv) > 3 else 1024

SKIN = "#4a92ca"      # Okti mavisi (oyun ve önceki simgelerle aynı)
SPOT = "#3b7fbc"
BELLY = "#f6c3cf"     # vantuz halkası
CUP = "#e48fa6"       # vantuz çukuru


def catmull(points, n):
    p = [points[0]] + list(points) + [points[-1]]
    segs = len(points) - 1; out = []
    for i in range(n):
        t = i / (n - 1) * segs; k = min(int(t), segs - 1); u = t - k
        p0, p1, p2, p3 = (V(p[k]), V(p[k + 1]), V(p[k + 2]), V(p[k + 3]))
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3))
    return out


def curl_path(base, heading_deg, ground_len, bend_deg, curl_r, turns, curl_yaw_deg, r0, r1, rise=0.0):
    """Kol yolu: gövde altından çıkar, kumda (bükülerek) uzanır, ucu dikey bir düzlemde dışa-yukarı-geri sarmal kıvrılır.
    curl_yaw_deg: kıvrım düzleminin kolun gidiş yönüne göre dönüşü (öne bakan kollarda kameraya yüzünü göstersin)."""
    pts = [V(base)]
    h = math.radians(heading_deg); pos = V((base[0], base[1], 0.0)); n = 10
    for i in range(1, n + 1):
        s = i / n
        a = h + math.radians(bend_deg) * s
        d = V((math.sin(a), -math.cos(a), 0.0))
        pos = pos + d * (ground_len / n)
        rad = r0 + (r1 - r0) * (0.55 * s) ** 0.8
        z = base[2] * (1 - s) ** 1.8 + rad + rise * math.sin(math.pi * s)
        pts.append(V((pos.x, pos.y, z)))
    a = h + math.radians(bend_deg)
    d = V((math.sin(a), -math.cos(a), 0.0))
    cy = math.radians(curl_yaw_deg)
    c = V((d.x * math.cos(cy) - d.y * math.sin(cy), d.x * math.sin(cy) + d.y * math.cos(cy), 0.0)).normalized()
    up = V((0, 0, 1))
    end = pts[-1]
    centre = end + up * curl_r
    m = 16
    for i in range(1, m + 1):
        f = i / m
        th = -math.pi / 2 + f * turns * math.tau
        rr = curl_r * (1 - 0.62 * f)
        pts.append(centre + c * rr * math.cos(th) + up * rr * math.sin(th))
    return pts, centre, c


def radii_for(pts, r0, r1):
    arc = [0.0]
    for i in range(1, len(pts)): arc.append(arc[-1] + (pts[i] - pts[i - 1]).length)
    L = arc[-1]
    return [r0 + (r1 - r0) * (a / L) ** 0.75 for a in arc], arc


def tentacle(name, pts, r0, r1, skin, ring_m, cup_m, centre=None, cam=V((0, -3.7, 1.25)), suck_from=0.45):
    dense = catmull(pts, 90)
    rad, arc = radii_for(dense, r0, r1)
    kit.tube(name, [tuple(p) for p in dense], rad, skin, res=6)
    # vantuzlar: kolun alt yüzü (kumdaki kısımda görünmez) → kıvrımın içine ve kameraya yarı dönük, uçtan geriye
    L = arc[-1]; s = L - 0.03; d = 0.022
    while s > L * suck_from:
        k = min(range(len(arc)), key=lambda q: abs(arc[q] - s))
        p = dense[k]; r = rad[k]
        t = (dense[min(k + 1, len(dense) - 1)] - dense[max(k - 1, 0)]).normalized()
        inward = (centre - p) if centre is not None else V((0, 0, -1))
        inward = (inward - t * inward.dot(t)).normalized()
        tocam = (cam - p); tocam = (tocam - t * tocam.dot(t)).normalized()
        nrm = (inward * 0.62 + tocam * 0.78).normalized()
        if nrm.z < -0.35: s -= 0.04; continue          # kuma bakan vantuz görünmez
        size = max(0.012, min(0.05, r * 0.55))
        pos = p + nrm * (r * 0.9)
        q = R.frame(nrm)
        R.ring_mesh(name + "_v", pos, q @ V((1, 0, 0)), q @ V((0, 1, 0)), size, size, size * 0.34, ring_m, n=20, nm=8, sub=1)
        R.blob_q(name + "_c", pos - nrm * size * 0.08, (size * 0.72, size * 0.72, size * 0.18), cup_m, q, sub=1, seg=14)
        s -= size * 2.0 + 0.012
    return dense


def shell_and_pearl(loc, yaw_deg, scale, pearl_m):
    """Açık istiridye (yivli iki yarım, arka menteşe) + içinde inci. Döndürür: inci konumu."""
    sh = kit.nodes_mat("kabuk", lambda nt, b: _shell_nodes(nt, b))
    inner = kit.mat("kabuk_ic", "#fbe3dc", rough=0.18, coat=0.8, sheen=0.3)
    yaw = math.radians(yaw_deg); x, y, z = loc
    lo = kit.blob("kabuk_alt", (x, y, z + 0.05 * scale), (0.24 * scale, 0.20 * scale, 0.07 * scale), sh, rot=(0, 0, yaw_deg))
    li = kit.blob("kabuk_alt_ic", (x, y, z + 0.075 * scale), (0.215 * scale, 0.175 * scale, 0.04 * scale), inner, rot=(0, 0, yaw_deg))
    back = V((math.sin(yaw) * 0.18 * scale, math.cos(yaw) * 0.18 * scale, 0))
    up = kit.blob("kabuk_ust", (x + back.x * 0.9, y + back.y * 0.9, z + 0.2 * scale), (0.24 * scale, 0.07 * scale, 0.2 * scale), sh,
                  rot=(-12, 0, yaw_deg))
    pz = z + 0.075 * scale + 0.085 * scale
    # istiridye boş: inci Okti'nin havadaki kolunda (tek inci, net okunsun)
    return V((x, y, pz))


def _shell_nodes(nt, b):
    n = nt.nodes; l = nt.links
    tc = n.new("ShaderNodeTexCoord")
    wv = n.new("ShaderNodeTexWave"); wv.wave_type = "RINGS"; wv.inputs["Scale"].default_value = 7.0; wv.inputs["Distortion"].default_value = 0.0
    sep = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Object"], sep.inputs[0])
    # yivler: nesne x'ine göre ışınsal (yelpaze) dalga
    at = n.new("ShaderNodeMath"); at.operation = "ARCTAN2"; l.new(sep.outputs[0], at.inputs[0]); l.new(sep.outputs[1], at.inputs[1])
    mul = n.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = 14.0; l.new(at.outputs[0], mul.inputs[0])
    sn = n.new("ShaderNodeMath"); sn.operation = "SINE"; l.new(mul.outputs[0], sn.inputs[0])
    bump = n.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.35; l.new(sn.outputs[0], bump.inputs["Height"])
    l.new(bump.outputs[0], b.inputs["Normal"])
    mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.inputs[6].default_value = kit.srgb("#f7a98d"); mx.inputs[7].default_value = kit.srgb("#ffd9c2")
    mr = n.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = -1.0; mr.inputs["From Max"].default_value = 1.0
    l.new(sn.outputs[0], mr.inputs["Value"]); l.new(mr.outputs[0], mx.inputs["Factor"]); l.new(mx.outputs[2], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.4; b.inputs["Coat Weight"].default_value = 0.35


def pearl_material():
    def b(nt, bsdf):
        bsdf.inputs["Base Color"].default_value = kit.srgb("#f7f3ee")
        bsdf.inputs["Roughness"].default_value = 0.12
        bsdf.inputs["Coat Weight"].default_value = 1.0
        bsdf.inputs["Coat Roughness"].default_value = 0.05
        if "Sheen Weight" in bsdf.inputs:
            bsdf.inputs["Sheen Weight"].default_value = 0.6; bsdf.inputs["Sheen Tint"].default_value = kit.srgb("#ffd6e8")
        if "Thin Film Thickness" in bsdf.inputs:
            bsdf.inputs["Thin Film Thickness"].default_value = 420.0
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = kit.srgb("#fff6ea"); bsdf.inputs["Emission Strength"].default_value = 0.12
    return kit.nodes_mat("inci", b)


def sand_material():
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links
        tc = n.new("ShaderNodeTexCoord")
        big = n.new("ShaderNodeTexNoise"); big.inputs["Scale"].default_value = 0.9; big.inputs["Detail"].default_value = 3
        l.new(tc.outputs["Object"], big.inputs["Vector"])
        fine = n.new("ShaderNodeTexNoise"); fine.inputs["Scale"].default_value = 260.0; fine.inputs["Detail"].default_value = 2
        l.new(tc.outputs["Object"], fine.inputs["Vector"])
        cr = kit.ramp(nt, [(0.35, "#e9c58a"), (0.65, "#f6dcaa")]); l.new(big.outputs["Fac"], cr.inputs[0])
        # ıslak kum: kıyıya yakın (y büyük) koyulaşır
        sep = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Object"], sep.inputs[0])
        wet = n.new("ShaderNodeMapRange"); wet.inputs["From Min"].default_value = 1.9; wet.inputs["From Max"].default_value = 2.75
        l.new(sep.outputs[1], wet.inputs["Value"])
        mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.inputs[7].default_value = kit.srgb("#d7ad74")
        l.new(wet.outputs[0], mx.inputs["Factor"]); l.new(cr.outputs[0], mx.inputs[6]); l.new(mx.outputs[2], bsdf.inputs["Base Color"])
        bump = n.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.18; l.new(fine.outputs["Fac"], bump.inputs["Height"])
        l.new(bump.outputs[0], bsdf.inputs["Normal"])
        bsdf.inputs["Roughness"].default_value = 0.85; bsdf.inputs["Coat Weight"].default_value = 0.0
    return kit.nodes_mat("kum", b)


def sea_material():
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links
        geo = n.new("ShaderNodeNewGeometry")
        sep = n.new("ShaderNodeSeparateXYZ"); l.new(geo.outputs["Position"], sep.inputs[0])
        depth = n.new("ShaderNodeMapRange"); depth.inputs["From Min"].default_value = 2.9; depth.inputs["From Max"].default_value = 14.0
        l.new(sep.outputs[1], depth.inputs["Value"])
        cr = kit.ramp(nt, [(0.0, "#7fe3d6"), (0.25, "#3fc4cf"), (1.0, "#1f8fbd")]); l.new(depth.outputs[0], cr.inputs[0])
        # kıyı köpüğü: su çizgisinin hemen önünde, gürültülü beyaz şerit
        fo = n.new("ShaderNodeMapRange"); fo.inputs["From Min"].default_value = 2.86; fo.inputs["From Max"].default_value = 3.02
        fo.inputs["To Min"].default_value = 1.0; fo.inputs["To Max"].default_value = 0.0; l.new(sep.outputs[1], fo.inputs["Value"])
        nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 9.0; l.new(geo.outputs["Position"], nz.inputs["Vector"])
        fm = n.new("ShaderNodeMath"); fm.operation = "MULTIPLY"; l.new(fo.outputs[0], fm.inputs[0]); l.new(nz.outputs["Fac"], fm.inputs[1])
        fm2 = n.new("ShaderNodeMath"); fm2.operation = "MULTIPLY"; fm2.inputs[1].default_value = 2.2; fm2.use_clamp = True
        l.new(fm.outputs[0], fm2.inputs[0])
        mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.inputs[7].default_value = kit.srgb("#fbfff8")
        l.new(fm2.outputs[0], mx.inputs["Factor"]); l.new(cr.outputs[0], mx.inputs[6]); l.new(mx.outputs[2], bsdf.inputs["Base Color"])
        wv = n.new("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = 1.4; wv.inputs["Distortion"].default_value = 6.0
        wv.bands_direction = "Y"; l.new(geo.outputs["Position"], wv.inputs["Vector"])
        bump = n.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.08; l.new(wv.outputs["Fac"], bump.inputs["Height"])
        l.new(bump.outputs[0], bsdf.inputs["Normal"])
        bsdf.inputs["Roughness"].default_value = 0.1; bsdf.inputs["Coat Weight"].default_value = 0.0
    return kit.nodes_mat("deniz", b)


def sky_world(sun_dir):
    """Kamera ışınında sıcak gün doğumu (R2 paleti, güneş ışıması); aydınlatmada yumuşak nötr gök."""
    w = bpy.data.worlds.new("gok"); bpy.context.scene.world = w; w.use_nodes = True
    nt = w.node_tree; n = nt.nodes; l = nt.links
    for x in list(n): n.remove(x)
    out = n.new("ShaderNodeOutputWorld")
    tc = n.new("ShaderNodeTexCoord")
    sep = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Generated"], sep.inputs[0])
    grad = kit.ramp(nt, [(0.0, "#ffe3a0"), (0.10, "#ffc76f"), (0.32, "#fba04e"), (0.6, "#f58b48")])
    l.new(sep.outputs[2], grad.inputs[0])
    dot = n.new("ShaderNodeVectorMath"); dot.operation = "DOT_PRODUCT"; dot.inputs[1].default_value = tuple(sun_dir)
    l.new(tc.outputs["Generated"], dot.inputs[0])
    pw = n.new("ShaderNodeMath"); pw.operation = "POWER"; pw.inputs[1].default_value = 9.0; pw.use_clamp = True
    cl = n.new("ShaderNodeMath"); cl.operation = "MAXIMUM"; cl.inputs[1].default_value = 0.0
    l.new(dot.outputs["Value"], cl.inputs[0]); l.new(cl.outputs[0], pw.inputs[0])
    mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.inputs[7].default_value = kit.srgb("#fff6d6")
    l.new(pw.outputs[0], mx.inputs["Factor"]); l.new(grad.outputs[0], mx.inputs[6])
    cam_bg = n.new("ShaderNodeBackground"); l.new(mx.outputs[2], cam_bg.inputs["Color"]); cam_bg.inputs["Strength"].default_value = 1.0
    lit_bg = n.new("ShaderNodeBackground"); lit_bg.inputs["Color"].default_value = kit.srgb("#e6eef6"); lit_bg.inputs["Strength"].default_value = 0.75
    lp = n.new("ShaderNodeLightPath"); mix = n.new("ShaderNodeMixShader")
    l.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"]); l.new(lit_bg.outputs[0], mix.inputs[1]); l.new(cam_bg.outputs[0], mix.inputs[2])
    l.new(mix.outputs[0], out.inputs["Surface"])


def ground_and_sea(sand, sea):
    import bmesh
    me = bpy.data.meshes.new("kum"); bm = bmesh.new()
    nx, ny = 120, 120; x0, x1, y0, y1 = -14.0, 14.0, -8.0, 4.2
    vs = []
    from mathutils import noise
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            x = x0 + (x1 - x0) * i / nx; y = y0 + (y1 - y0) * j / ny
            z = 0.025 * noise.noise(V((x * 0.6, y * 0.6, 0.3))) + 0.012 * noise.noise(V((x * 2.1, y * 2.1, 1.7)))
            if y > 2.55: z -= 0.15 * (y - 2.55)
            if abs(x) < 1.6 and -1.6 < y < 1.0: z *= 0.3            # Okti'nin oturduğu yer düz
            row.append(bm.verts.new((x, y, z)))
        vs.append(row)
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    g = bpy.data.objects.new("kum", me); bpy.context.scene.collection.objects.link(g); g.data.materials.append(sand)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 60, -0.045))
    s = bpy.context.object; s.name = "deniz"; s.scale = (400, 116, 1); s.data.materials.append(sea)


def okti(skin, ring_m, cup_m, pearl_m):
    mantle = kit.blob("bas", (0, 0.02, 1.0), (0.56, 0.5, 0.62), skin, rot=(-6, 0, 0), seg=48)
    skirt = kit.blob("etek", (0, 0, 0.42), (0.47, 0.43, 0.27), skin, seg=40)
    surf = R.Surf([mantle])
    c = V((0, 0.02, 1.0))
    parts = []
    for sx in (-1, 1):
        R.bead_eye("g%d" % sx, surf, c, V((sx * 0.37, -1, -0.30)), 0.105, 0.135, 0.05, glint_at=(0.30 * -sx * -1, 0.36))
    R.stroke("agiz", surf, c, [V((-0.15, -1, -0.50)), V((-0.07, -1, -0.58)), V((0.0, -1, -0.60)), V((0.07, -1, -0.58)), V((0.15, -1, -0.50))],
             [0.014, 0.016, 0.017, 0.016, 0.014], kit.mat("agiz", "#4a2230", rough=0.4, coat=0.2), lift=0.004)
    blush = kit.mat("yanak", "#f48da6", rough=0.6, coat=0.0)
    for sx in (-1, 1):
        R.decal("yanak%d" % sx, surf, c, V((sx * 0.56, -1, -0.47)), (0.075, 0.048, 0.008), blush, lift=0.003)
    # sekiz kol: tabanı gövdenin altında halka; her biri farklı (asimetrik), uçları kıvrık
    B = lambda ang, rr=0.27, z=0.3: (math.sin(math.radians(ang)) * rr, -math.cos(math.radians(ang)) * rr, z)
    specs = [
        # (taban açısı, gidiş, kumdaki boy, bükülme, kıvrım yarıçapı, tur, kıvrım düzlemi dönüşü, r0, r1)
        (-28, -30, 0.62, -34, 0.15, 0.95, 78, 0.12, 0.028),    # ön sol: sola kıvrılır
        (24, 22, 0.52, 40, 0.13, 0.9, -82, 0.12, 0.028),        # ön sağ: kısa, içe kıvrılır (rozetten uzak)
        (-74, -78, 0.80, -20, 0.21, 1.05, 18, 0.13, 0.03),      # sol: uzun, büyük kıvrım
        (72, 76, 0.55, 26, 0.12, 0.85, -14, 0.12, 0.028),       # sağ: kumda
        (-125, -128, 0.42, -18, 0.11, 0.8, 8, 0.11, 0.026),     # arka sol: kıvrık uç başın yanında
        (130, 132, 0.40, 22, 0.10, 0.8, -8, 0.11, 0.026),       # arka sağ
        (-4, 2, 0.58, 30, 0.12, 0.85, 72, 0.12, 0.028),         # ön orta: istiridyeye uzanır
    ]
    for i, (ba, hd, gl, bd, cr, tu, cyaw, r0, r1) in enumerate(specs):
        pts, cen, _ = curl_path(B(ba), hd, gl, bd, cr, tu, cyaw, r0, r1)
        tentacle("kol%d" % i, pts, r0, r1, skin, ring_m, cup_m, centre=cen)
    # sağ kol havada, ucu inciyi sarar
    P = V((0.86, -0.46, 1.06)); pr = 0.10
    kit.blob("inci", tuple(P), (pr, pr, pr), pearl_m, seg=40)
    wrap = []
    k0 = math.radians(-110); k1 = math.radians(205)
    for i in range(12):
        t = k0 + (k1 - k0) * i / 11
        rr = pr + 0.05 - 0.012 * i / 11
        wrap.append(V((P.x + math.cos(t) * rr, P.y + 0.06, P.z + math.sin(t) * rr)))
    arm = [V(B(84, 0.3, 0.42)), V((0.62, -0.12, 0.36)), V((0.86, -0.26, 0.48)), V((0.97, -0.38, 0.72)), V((0.98, -0.44, 0.88))] + wrap
    tentacle("kol_inci", arm, 0.12, 0.03, skin, ring_m, cup_m, centre=P, suck_from=0.55)
    return mantle


def main():
    kit.reset()
    sc = bpy.context.scene
    for nm in ("sun", "fill"):                       # kit.reset'in stüdyo ışıkları bu sahnede yok
        o = bpy.data.objects.get(nm)
        if o: bpy.data.objects.remove(o, do_unlink=True)
    R.render_cfg(sc, SIZE, SIZE, SAMPLES)
    sc.view_settings.exposure = -0.15
    skin = R.m_skin("deri", SKIN, SPOT, spot_amt=0.28, scale=6.0)
    ring_m = kit.mat("vantuz", BELLY, rough=0.4, coat=0.3)
    cup_m = kit.mat("vantuz_ic", CUP, rough=0.55, coat=0.0)
    pearl_m = pearl_material()
    sun_dir = V((0.0, 1.0, 0.11)).normalized()
    sky_world(sun_dir)
    ground_and_sea(sand_material(), sea_material())
    okti(skin, ring_m, cup_m, pearl_m)
    shell_and_pearl((-0.42, -1.02, 0.0), -24, 1.0, pearl_m)
    # oyunun kodla yapılmış varlıkları: palmiye solda, uzak adacıkta fener sağda
    try:
        palm, _, ph = R.load_game("palm", height=4.2)
        palm.location = (-2.35, 1.5, 0.0); palm.rotation_euler = (0, math.radians(4), math.radians(35))
        lh, _, lhh = R.load_game("b_lighthouse", height=7.0)
        lh.location = (17.5, 70.0, 0.6)
        rock = kit.blob("adacik", (17.5, 70.0, -0.4), (6.5, 4.0, 1.6), kit.mat("kaya", "#8c8a6a", rough=0.8, coat=0.0), seg=32)
        grass = kit.blob("adacik_cim", (17.5, 70.0, 0.55), (5.0, 3.2, 0.5), kit.mat("cim", "#7fb35a", rough=0.8, coat=0.0), seg=32)
    except Exception as e:
        print("varlık yüklenemedi:", e)
    # ışık: ön sağ üstten sıcak beyaz ana ışık + arkadan turuncu kenar ışığı (gün doğumu)
    key = bpy.data.lights.new("ana", "SUN"); key.energy = 3.4; key.angle = math.radians(8); key.color = (1.0, 0.95, 0.88)
    ko = bpy.data.objects.new("ana", key); sc.collection.objects.link(ko)
    ko.rotation_euler = V((-0.42, 0.78, -0.62)).normalized().to_track_quat("-Z", "Y").to_euler()
    rim = bpy.data.lights.new("kenar", "SUN"); rim.energy = 2.6; rim.angle = math.radians(5); rim.color = (1.0, 0.72, 0.42)
    ro = bpy.data.objects.new("kenar", rim); sc.collection.objects.link(ro)
    ro.rotation_euler = V((0.12, -0.95, -0.28)).normalized().to_track_quat("-Z", "Y").to_euler()
    R.cam_shot(sc, OUT, (0, 0, 0.8), 3.75, 0, 7.2, lens=50)
    print("yazıldı", OUT)


main()
