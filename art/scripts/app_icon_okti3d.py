"""Moyo Oyun uygulama simgesi, tamamen kodla (kullanıcı, 23 Kasım 2026: "Okti'yi zemine oturt, daha oturaklı bir çalışma yap,
kollar simetrik olmak zorunda değil, kodla yap; Meshy beğenmiyorum, özgün değil").

Blender (Cycles) sahnesi: kumsalda oturan sevimli mavi ahtapot Okti. Tek parça dönel gövde (büyük yuvarlak baş + alçak etek, ek yeri
yok), parlak koyu boncuk gözler, gülümseme, al yanak; sekiz kol kuma düzensiz yayılır, kalın tabandan ince uca daralır, uçları kameraya
dönük kıvrılır, alt kenarlarında dolu pembe vantuzlar. Asimetrik duruş: sağ kol havada, ucu inciyi sarar (önünden geçer); önde kumda
yivli deniz tarağı kabuğu. Fon oyunun kendi kodla yapılmış varlıklarıyla: palmiye (Env/palm) solda, uzak adacıkta fener
(Env/b_lighthouse), sıcak gün doğumu (güneş başın arkasında, kenar ışığı), turkuaz deniz (göğü yansıtır), kıyı köpüğü.
Hiçbir görsel yapay zekâdan gelmez.

Kullanım (bpy yalnız python3.11'de):
    python3.11 -I art/scripts/app_icon_okti3d.py <çıktı.png> [örnek_sayısı] [boyut]
Rozet sonra: python3 -I art/scripts/app_icon_moyo.py <simge.png> <çıktı.png>
"""
import math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "art", "code3d")); sys.path.insert(0, os.path.join(ROOT, "art", "code3d", "v6"))
import bpy, bmesh
from mathutils import Vector as V, Matrix
import kit
import residents_v1 as R

OUT = sys.argv[1]
SAMPLES = int(sys.argv[2]) if len(sys.argv) > 2 else 96
SIZE = int(sys.argv[3]) if len(sys.argv) > 3 else 1024

SKIN = "#3f8ed8"      # Okti mavisi (önceki simgelerden biraz daha doygun)
SPOT = "#3478c4"
SUCK = "#f9cfd8"      # vantuz
SUCK_IN = "#e690a8"   # vantuz ortası
CAM = V((0, -3.72, 1.27))


def catmull(points, n):
    p = [points[0]] + list(points) + [points[-1]]
    segs = len(points) - 1; out = []
    for i in range(n):
        t = i / (n - 1) * segs; k = min(int(t), segs - 1); u = t - k
        p0, p1, p2, p3 = (V(p[k]), V(p[k + 1]), V(p[k + 2]), V(p[k + 3]))
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3))
    return out


def curl_path(base, heading_deg, ground_len, bend_deg, curl_r, turns, curl_dir_deg, r0, r1):
    """Kol yolu: gövde altından çıkar, kumda bükülerek uzanır, ucu dikey bir düzlemde sarmal kıvrılır.
    curl_dir_deg: kıvrımın ilk gittiği yatay yön (0 = +X sağ, 180 = −X sol); kıvrım düzlemi kameraya yüzünü gösterir."""
    pts = [V(base)]
    h = math.radians(heading_deg); pos = V((base[0], base[1], 0.0)); n = 10
    for i in range(1, n + 1):
        s = i / n
        a = h + math.radians(bend_deg) * s
        pos = pos + V((math.sin(a), -math.cos(a), 0.0)) * (ground_len / n)
        rad = r1 + (r0 - r1) * (1 - 0.6 * s) ** 1.1
        z = base[2] * (1 - s) ** 1.8 + rad * (1 - (1 - s) ** 1.8) + 0.004
        pts.append(V((pos.x, pos.y, z)))
    cd = math.radians(curl_dir_deg)
    c = V((math.cos(cd), math.sin(cd), 0.0))
    up = V((0, 0, 1))
    end = pts[-1]
    centre = end + up * curl_r
    m = 16
    for i in range(1, m + 1):
        f = i / m
        th = -math.pi / 2 + f * turns * math.tau
        rr = curl_r * (1 - 0.62 * f)
        pts.append(centre + c * rr * math.cos(th) + up * rr * math.sin(th))
    return pts, centre


def tentacle(name, pts, r0, r1, skin, suck_m, cup_m, centre=None, suck_from=0.42):
    dense = catmull(pts, 90)
    arc = [0.0]
    for i in range(1, len(dense)): arc.append(arc[-1] + (dense[i] - dense[i - 1]).length)
    L = arc[-1]
    rad = [r1 + (r0 - r1) * (1 - a / L) ** 1.1 for a in arc]
    kit.tube(name, [tuple(p) for p in dense], rad, skin, res=6)
    tip = dense[-1] + (dense[-1] - dense[-2]).normalized() * rad[-1] * 0.2
    kit.blob(name + "_uc", tuple(tip), (rad[-1] * 1.08,) * 3, skin, seg=16)    # yuvarlak uç (düz kesik olmasın)
    # vantuzlar: uçtan geriye küçükten büyüğe; kumdaki kısımda kolun alt-ön kenarında, kıvrımda içe ve kameraya yarı dönük
    s = L - 0.035
    while s > L * suck_from:
        k = min(range(len(arc)), key=lambda q: abs(arc[q] - s))
        p = dense[k]; r = rad[k]
        t = (dense[min(k + 1, len(dense) - 1)] - dense[max(k - 1, 0)]).normalized()
        tocam = CAM - p; tocam = (tocam - t * tocam.dot(t)).normalized()
        on_ground = p.z < r * 1.6 + 0.02
        if on_ground or centre is None:
            down = V((0, 0, -1)); down = (down - t * down.dot(t)).normalized()
            nrm = (down * 0.55 + tocam * 0.85).normalized()
        else:
            inward = centre - p; inward = (inward - t * inward.dot(t)).normalized()
            nrm = (inward * 0.6 + tocam * 0.8).normalized()
        size = max(0.011, min(0.042, r * 0.5))
        if nrm.dot(tocam) > 0.15 and p.z + nrm.z * r > 0.006:
            q = R.frame(nrm)
            pos = p + nrm * (r * 0.93)
            R.blob_q(name + "_v", pos, (size, size, size * 0.30), suck_m, q, sub=1, seg=16)
            R.blob_q(name + "_c", pos + nrm * size * 0.22, (size * 0.48, size * 0.48, size * 0.12), cup_m, q, sub=1, seg=12)
        s -= size * 2.0 + 0.014
    return dense


def body(skin):
    """Baş (yumurta) + etek tek dönel gövde: iki elipsin yumuşak birleşimi, hafif bel, basamaksız. Ön −Y, hafif geriye yatık."""
    ZH, A, BU, BL = 1.0, 0.61, 0.50, 0.66        # baş: merkez, yatay yarıçap, üst/alt düşey yarıçap
    ZS, AS, BS = 0.44, 0.55, 0.44                  # etek (kuma değer; bel başın %91i)
    Z0, Z1 = ZS - BS + 0.004, ZH + BU
    def ell(z, zc, a, bu, bl):
        b = bu if z >= zc else bl
        q = 1 - ((z - zc) / b) ** 2
        return a * math.sqrt(q) if q > 0 else 0.0
    def smax(a, b, k=0.18):
        h = max(k - abs(a - b), 0.0) / k
        return max(a, b) + h * h * k * 0.25
    def r_of(z):
        return smax(ell(z, ZH, A, BU, BL), ell(z, ZS, AS, BS, BS))
    zt = lambda t: Z0 + (Z1 - Z0) * (0.5 - 0.5 * math.cos(math.pi * t))   # uçlarda sık satır: tepe sivrilmez
    path = lambda t: (0.0, 0.05 * ((zt(t) - Z0) / (Z1 - Z0)) ** 2, zt(t))
    def rad(t, a):
        k = 1.0 / math.sqrt((math.cos(a) / 0.9) ** 2 + math.sin(a) ** 2)
        return max(r_of(zt(t)), 0.0015) * k
    o, _, _ = R.lathe("govde", path, rad, 110, 72, skin, cap_bottom=True, cap_top=True, sub=1)
    waist = min(r_of(z / 100) for z in range(50, 80))
    print("gövde: baş", round(r_of(ZH), 3), "bel", round(waist, 3), "oran", round(waist / r_of(ZH), 3))
    return o


def scallop(loc, yaw_deg, R0):
    """Deniz tarağı kabuğu: yelpaze, ışınsal yivler, dalgalı kenar, menteşe kulakları. Kameraya ~50° eğik, alt kenarı kumda."""
    N = 13
    me = bpy.data.meshes.new("kabuk"); bm = bmesh.new()
    rows, cols = 14, 66
    grid = []
    for i in range(rows + 1):
        r = i / rows
        row = []
        for j in range(cols + 1):
            th = math.radians(-68 + 136 * j / cols)
            edge = 1.0 + 0.035 * math.cos(N * th * 180 / 136 * 2)
            rr = R0 * r * edge
            x, y = rr * math.sin(th), rr * math.cos(th)
            z = 0.32 * R0 * (1 - r * r) ** 0.5 * (1 - 0.25 * abs(th) / 1.19) + 0.05 * R0 * r ** 0.8 * math.cos(N * th * 180 / 136 * 2)
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)
    for i in range(rows):
        for j in range(cols):
            bm.faces.new((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]))
    for sx in (-1, 1):   # menteşe kulakları
        e = [bm.verts.new((sx * 0.03 * R0, -0.02 * R0, 0.03 * R0)), bm.verts.new((sx * 0.36 * R0, -0.04 * R0, 0.02 * R0)),
             bm.verts.new((sx * 0.33 * R0, 0.20 * R0, 0.05 * R0)), bm.verts.new((sx * 0.06 * R0, 0.22 * R0, 0.09 * R0))]
        bm.faces.new(e if sx < 0 else list(reversed(e)))
    bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    o = bpy.data.objects.new("kabuk", me); bpy.context.scene.collection.objects.link(o)
    s = o.modifiers.new("kal", "SOLIDIFY"); s.thickness = 0.012; s.offset = -1
    sub = o.modifiers.new("sub", "SUBSURF"); sub.levels = sub.render_levels = 1
    o.data.materials.append(kit.nodes_mat("kabuk_m", _shell_nodes))
    yaw = math.radians(yaw_deg); tilt = math.radians(50)
    ly = V((math.sin(yaw) * math.cos(tilt), math.cos(yaw) * math.cos(tilt), math.sin(tilt)))   # menteşeden kenara: yukarı ve geriye
    lx = V((math.cos(yaw), -math.sin(yaw), 0.0))
    lz = lx.cross(ly).normalized()
    if lz.y > 0: lz = -lz; lx = -lx
    M = Matrix((lx, ly, lz)).transposed().to_4x4(); M.translation = V(loc)
    o.matrix_world = M
    return o


def _shell_nodes(nt, b):
    n = nt.nodes; l = nt.links
    tc = n.new("ShaderNodeTexCoord")
    sep = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Object"], sep.inputs[0])
    at = n.new("ShaderNodeMath"); at.operation = "ARCTAN2"; l.new(sep.outputs[0], at.inputs[0]); l.new(sep.outputs[1], at.inputs[1])
    mul = n.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = 13 * 180 / 136 * 2; l.new(at.outputs[0], mul.inputs[0])
    cs = n.new("ShaderNodeMath"); cs.operation = "COSINE"; l.new(mul.outputs[0], cs.inputs[0])
    mr = n.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = -1.0; mr.inputs["From Max"].default_value = 1.0
    l.new(cs.outputs[0], mr.inputs["Value"])
    mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.inputs[6].default_value = kit.srgb("#ffe2cf"); mx.inputs[7].default_value = kit.srgb("#ff9a72")
    l.new(mr.outputs[0], mx.inputs["Factor"]); l.new(mx.outputs[2], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.42; b.inputs["Coat Weight"].default_value = 0.3


def pearl_material():
    def b(nt, bsdf):
        bsdf.inputs["Base Color"].default_value = kit.srgb("#e4d2cc")
        bsdf.inputs["Roughness"].default_value = 0.2
        bsdf.inputs["Coat Weight"].default_value = 0.55
        bsdf.inputs["Coat Roughness"].default_value = 0.08
        if "Specular IOR Level" in bsdf.inputs: bsdf.inputs["Specular IOR Level"].default_value = 0.3
        if "Sheen Weight" in bsdf.inputs:
            bsdf.inputs["Sheen Weight"].default_value = 0.3; bsdf.inputs["Sheen Tint"].default_value = kit.srgb("#ffc9e0")
        if "Thin Film Thickness" in bsdf.inputs:
            bsdf.inputs["Thin Film Thickness"].default_value = 300.0
    return kit.nodes_mat("inci", b)


def sand_material():
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links
        tc = n.new("ShaderNodeTexCoord")
        big = n.new("ShaderNodeTexNoise"); big.inputs["Scale"].default_value = 0.9; big.inputs["Detail"].default_value = 3
        l.new(tc.outputs["Object"], big.inputs["Vector"])
        fine = n.new("ShaderNodeTexNoise"); fine.inputs["Scale"].default_value = 260.0; fine.inputs["Detail"].default_value = 2
        l.new(tc.outputs["Object"], fine.inputs["Vector"])
        cr = kit.ramp(nt, [(0.35, "#efc98a"), (0.65, "#f8dcaa")]); l.new(big.outputs["Fac"], cr.inputs[0])
        sep = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Object"], sep.inputs[0])
        wet = n.new("ShaderNodeMapRange"); wet.inputs["From Min"].default_value = 1.9; wet.inputs["From Max"].default_value = 2.75
        l.new(sep.outputs[1], wet.inputs["Value"])
        mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.inputs[7].default_value = kit.srgb("#d9aa70")
        l.new(wet.outputs[0], mx.inputs["Factor"]); l.new(cr.outputs[0], mx.inputs[6]); l.new(mx.outputs[2], bsdf.inputs["Base Color"])
        bump = n.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.18; l.new(fine.outputs["Fac"], bump.inputs["Height"])
        l.new(bump.outputs[0], bsdf.inputs["Normal"])
        bsdf.inputs["Roughness"].default_value = 0.88; bsdf.inputs["Coat Weight"].default_value = 0.0
    return kit.nodes_mat("kum", b)


def sea_material():
    def b(nt, bsdf):
        n = nt.nodes; l = nt.links
        geo = n.new("ShaderNodeNewGeometry")
        sep = n.new("ShaderNodeSeparateXYZ"); l.new(geo.outputs["Position"], sep.inputs[0])
        depth = n.new("ShaderNodeMapRange"); depth.inputs["From Min"].default_value = 2.9; depth.inputs["From Max"].default_value = 16.0
        l.new(sep.outputs[1], depth.inputs["Value"])
        cr = kit.ramp(nt, [(0.0, "#59d9cf"), (0.22, "#22b0cc"), (1.0, "#137bb4")]); l.new(depth.outputs[0], cr.inputs[0])
        fo = n.new("ShaderNodeMapRange"); fo.inputs["From Min"].default_value = 2.86; fo.inputs["From Max"].default_value = 3.05
        fo.inputs["To Min"].default_value = 1.0; fo.inputs["To Max"].default_value = 0.0; l.new(sep.outputs[1], fo.inputs["Value"])
        nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 9.0; l.new(geo.outputs["Position"], nz.inputs["Vector"])
        fm = n.new("ShaderNodeMath"); fm.operation = "MULTIPLY"; l.new(fo.outputs[0], fm.inputs[0]); l.new(nz.outputs["Fac"], fm.inputs[1])
        fm2 = n.new("ShaderNodeMath"); fm2.operation = "MULTIPLY"; fm2.inputs[1].default_value = 2.6; fm2.use_clamp = True
        l.new(fm.outputs[0], fm2.inputs[0])
        mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.inputs[7].default_value = kit.srgb("#fdfff9")
        l.new(fm2.outputs[0], mx.inputs["Factor"]); l.new(cr.outputs[0], mx.inputs[6]); l.new(mx.outputs[2], bsdf.inputs["Base Color"])
        wv = n.new("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = 1.4; wv.inputs["Distortion"].default_value = 6.0
        wv.bands_direction = "Y"; l.new(geo.outputs["Position"], wv.inputs["Vector"])
        bump = n.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.07; l.new(wv.outputs["Fac"], bump.inputs["Height"])
        l.new(bump.outputs[0], bsdf.inputs["Normal"])
        bsdf.inputs["Roughness"].default_value = 0.12; bsdf.inputs["Coat Weight"].default_value = 0.0
        if "Specular IOR Level" in bsdf.inputs: bsdf.inputs["Specular IOR Level"].default_value = 0.35
    return kit.nodes_mat("deniz", b)


def sky_world(sun_dir):
    """Kamerada ve yansımada sıcak gün doğumu (güneş başın arkasında, dar ışıma); dağınık aydınlatmada yumuşak nötr gök."""
    w = bpy.data.worlds.new("gok"); bpy.context.scene.world = w; w.use_nodes = True
    nt = w.node_tree; n = nt.nodes; l = nt.links
    for x in list(n): n.remove(x)
    out = n.new("ShaderNodeOutputWorld")
    tc = n.new("ShaderNodeTexCoord")
    sep = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Generated"], sep.inputs[0])
    grad = kit.ramp(nt, [(0.0, "#ffd27c"), (0.06, "#ffb664"), (0.2, "#fb9b58"), (0.42, "#f38a63")])
    l.new(sep.outputs[2], grad.inputs[0])
    dot = n.new("ShaderNodeVectorMath"); dot.operation = "DOT_PRODUCT"; dot.inputs[1].default_value = tuple(sun_dir)
    l.new(tc.outputs["Generated"], dot.inputs[0])
    cl = n.new("ShaderNodeMath"); cl.operation = "MAXIMUM"; cl.inputs[1].default_value = 0.0
    l.new(dot.outputs["Value"], cl.inputs[0])
    p1 = n.new("ShaderNodeMath"); p1.operation = "POWER"; p1.inputs[1].default_value = 900.0; l.new(cl.outputs[0], p1.inputs[0])
    p2 = n.new("ShaderNodeMath"); p2.operation = "POWER"; p2.inputs[1].default_value = 70.0; l.new(cl.outputs[0], p2.inputs[0])
    m2 = n.new("ShaderNodeMath"); m2.operation = "MULTIPLY"; m2.inputs[1].default_value = 0.5; l.new(p2.outputs[0], m2.inputs[0])
    ad = n.new("ShaderNodeMath"); ad.operation = "ADD"; ad.use_clamp = True; l.new(p1.outputs[0], ad.inputs[0]); l.new(m2.outputs[0], ad.inputs[1])
    mx = n.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.inputs[7].default_value = kit.srgb("#fff2cc")
    l.new(ad.outputs[0], mx.inputs["Factor"]); l.new(grad.outputs[0], mx.inputs[6])
    cam_bg = n.new("ShaderNodeBackground"); l.new(mx.outputs[2], cam_bg.inputs["Color"]); cam_bg.inputs["Strength"].default_value = 1.0
    lit_bg = n.new("ShaderNodeBackground"); lit_bg.inputs["Color"].default_value = kit.srgb("#e6eef6"); lit_bg.inputs["Strength"].default_value = 0.85
    lp = n.new("ShaderNodeLightPath")
    mxf = n.new("ShaderNodeMath"); mxf.operation = "MAXIMUM"
    l.new(lp.outputs["Is Camera Ray"], mxf.inputs[0]); l.new(lp.outputs["Is Glossy Ray"], mxf.inputs[1])
    mix = n.new("ShaderNodeMixShader")
    l.new(mxf.outputs[0], mix.inputs["Fac"]); l.new(lit_bg.outputs[0], mix.inputs[1]); l.new(cam_bg.outputs[0], mix.inputs[2])
    l.new(mix.outputs[0], out.inputs["Surface"])


def ground_and_sea(sand, sea):
    from mathutils import noise
    me = bpy.data.meshes.new("kum"); bm = bmesh.new()
    nx, ny = 120, 120; x0, x1, y0, y1 = -14.0, 14.0, -8.0, 4.2
    vs = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            x = x0 + (x1 - x0) * i / nx; y = y0 + (y1 - y0) * j / ny
            z = 0.025 * noise.noise(V((x * 0.6, y * 0.6, 0.3))) + 0.012 * noise.noise(V((x * 2.1, y * 2.1, 1.7)))
            if y > 2.55: z -= 0.15 * (y - 2.55)
            if abs(x) < 1.7 and -1.7 < y < 1.0: z *= 0.15          # Okti'nin oturduğu yer düz
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


def contact_shadow(loc, rx, ry, strength):
    """Gövdenin altında boyalı temas gölgesi (gölge ışınlarında görünmez)."""
    def b(nt, bsdf):
        pass
    m = bpy.data.materials.new("temas"); m.use_nodes = True; nt = m.node_tree; n = nt.nodes; l = nt.links
    for x in list(n): n.remove(x)
    out = n.new("ShaderNodeOutputMaterial"); tr = n.new("ShaderNodeBsdfTransparent"); df = n.new("ShaderNodeBsdfDiffuse")
    df.inputs["Color"].default_value = kit.srgb("#6b4a2a")
    tc = n.new("ShaderNodeTexCoord"); gr = n.new("ShaderNodeTexGradient"); gr.gradient_type = "SPHERICAL"
    l.new(tc.outputs["Object"], gr.inputs["Vector"])
    pw = n.new("ShaderNodeMath"); pw.operation = "POWER"; pw.inputs[1].default_value = 1.6; l.new(gr.outputs["Fac"], pw.inputs[0])
    ml = n.new("ShaderNodeMath"); ml.operation = "MULTIPLY"; ml.inputs[1].default_value = strength; l.new(pw.outputs[0], ml.inputs[0])
    mix = n.new("ShaderNodeMixShader"); l.new(ml.outputs[0], mix.inputs["Fac"]); l.new(tr.outputs[0], mix.inputs[1]); l.new(df.outputs[0], mix.inputs[2])
    l.new(mix.outputs[0], out.inputs["Surface"])
    m.blend_method = "BLEND" if hasattr(m, "blend_method") else None
    bpy.ops.mesh.primitive_plane_add(size=2, location=loc)
    o = bpy.context.object; o.name = "temas"; o.scale = (rx, ry, 1); o.data.materials.append(m)
    o.visible_shadow = False
    return o


def okti(skin, suck_m, cup_m, pearl_m):
    g = body(skin)
    surf = R.Surf([g])
    c = V((0, 0.05, 1.0))
    eye_m = kit.mat("goz", "#161c3e", rough=0.3, coat=0.3)
    for sx in (-1, 1):
        forms, dets, _ = R.bead_eye("g%d" % sx, surf, c, V((sx * 0.36, -1, -0.25)), 0.112, 0.142, 0.05, glint_at=(0.30 * sx, 0.36))
        for o in forms:
            o.data.materials.clear(); o.data.materials.append(eye_m)
    R.stroke("agiz", surf, c, [V((-0.17, -1, -0.50)), V((-0.085, -1, -0.585)), V((0.0, -1, -0.61)), V((0.085, -1, -0.585)), V((0.17, -1, -0.50))],
             [0.017, 0.019, 0.02, 0.019, 0.017], kit.mat("agiz", "#4a2230", rough=0.4, coat=0.2), lift=0.004)
    blush = kit.mat("yanak", "#f48aa5", rough=0.6, coat=0.0)
    for sx in (-1, 1):
        R.decal("yanak%d" % sx, surf, c, V((sx * 0.46, -1, -0.50)), (0.105, 0.068, 0.008), blush, lift=0.003)
    B = lambda ang, rr=0.2, z=0.14: (math.sin(math.radians(ang)) * rr, -math.cos(math.radians(ang)) * rr, z)
    specs = [
        # (taban açısı, gidiş, kumdaki boy, bükülme, kıvrım yarıçapı, tur, kıvrım yönü, r0, r1)
        (-75, -84, 0.56, -10, 0.19, 1.0, 180, 0.15, 0.03),     # sol: uzun, büyük kıvrım (sol kenardan içeride)
        (-34, -40, 0.50, -24, 0.14, 0.95, 180, 0.15, 0.03),    # ön sol
        (6, 2, 0.36, 22, 0.12, 0.9, 0, 0.145, 0.028),           # ön orta: kısa
        (40, 50, 0.30, 6, 0.07, 0.6, 0, 0.14, 0.026),           # ön sağ: kumda uzanır, ucu küçük kıvrık (rozetin solunda)
        (118, 135, 0.90, 6, 0.15, 0.95, 0, 0.14, 0.03),         # sağ arka: gövdenin arkasından sağa, ucu rozetin üstünde kıvrılır
        (-128, -134, 0.40, -14, 0.12, 0.9, 180, 0.13, 0.028),   # arka sol: başın yanında kıvrık uç
        (152, 156, 0.30, 10, 0.10, 0.8, 0, 0.12, 0.026),        # arka sağ: kısa
    ]
    for i, (ba, hd, gl, bd, cr, tu, cdir, r0, r1) in enumerate(specs):
        pts, cen = curl_path(B(ba), hd, gl, bd, cr, tu, cdir, r0, r1)
        tentacle("kol%d" % i, pts, r0, r1, skin, suck_m, cup_m, centre=cen)
    # sağ kol havada, ucu inciyi sarar ve önünden geçer
    P = V((0.80, -0.46, 0.86)); pr = 0.10
    kit.blob("inci", tuple(P), (pr, pr, pr), pearl_m, seg=40)
    wrap = []
    a0, a1 = math.radians(-62), math.radians(262)
    for i in range(16):
        f = i / 15; a = a0 + (a1 - a0) * f
        rr = pr + 0.045 - 0.012 * f
        dy = 0.075 if f < 0.55 else 0.075 - (f - 0.55) / 0.45 * 0.2
        wrap.append(V((P.x + math.cos(a) * rr, P.y + dy, P.z + math.sin(a) * rr)))
    arm = [V(B(84, 0.24, 0.3)), V((0.6, -0.14, 0.36)), V((0.84, -0.26, 0.44)), V((0.93, -0.36, 0.60))] + wrap
    tentacle("kol_inci", arm, 0.13, 0.03, skin, suck_m, cup_m, centre=P, suck_from=0.6)
    return g


def main():
    kit.reset()
    sc = bpy.context.scene
    for nm in ("sun", "fill"):                       # kit.reset'in stüdyo ışıkları bu sahnede yok
        o = bpy.data.objects.get(nm)
        if o: bpy.data.objects.remove(o, do_unlink=True)
    R.render_cfg(sc, SIZE, SIZE, SAMPLES)
    sc.view_settings.exposure = -0.1
    skin = R.m_skin("deri", SKIN, SPOT, spot_amt=0.22, scale=6.0)
    pb = skin.node_tree.nodes.get("Principled BSDF")
    if pb: pb.inputs["Roughness"].default_value = 0.5; pb.inputs["Coat Weight"].default_value = 0.16
    suck_m = kit.mat("vantuz", SUCK, rough=0.45, coat=0.25)
    cup_m = kit.mat("vantuz_ic", SUCK_IN, rough=0.55, coat=0.0)
    pearl_m = pearl_material()
    sun_dir = V((0.158, 0.987, 0.031)).normalized()
    sky_world(sun_dir)
    ground_and_sea(sand_material(), sea_material())
    okti(skin, suck_m, cup_m, pearl_m)
    contact_shadow((0, 0.02, 0.006), 0.78, 0.66, 0.55)
    scallop((-0.68, -0.62, 0.01), -18, 0.17)
    try:
        palm, _, _ = R.load_game("palm", height=2.5)
        palm.name = "palmiye"; palm.location = (-2.54, 2.6, -0.1); palm.rotation_euler = (0, 0, math.radians(180))   # gövde kumdan sola eğik çıkar, tepe sol kenarda
        pm = palm.data.materials[0]; nt = pm.node_tree
        tex = next(x for x in nt.nodes if x.type == "TEX_IMAGE" and x.image and "basecolor" in x.image.name)
        hs = nt.nodes.new("ShaderNodeHueSaturation"); hs.inputs["Saturation"].default_value = 0.85; hs.inputs["Value"].default_value = 0.97
        nt.links.new(tex.outputs[0], hs.inputs["Color"]); nt.links.new(hs.outputs[0], nt.nodes["Principled BSDF"].inputs["Base Color"])
        nt.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.75; nt.nodes["Principled BSDF"].inputs["Coat Weight"].default_value = 0.0
        lh, _, _ = R.load_game("b_lighthouse", height=4.6)
        lh.name = "fener"; lh.location = (22.2, 72.0, 0.45)
        kit.blob("adacik", (22.2, 72.0, -0.4), (4.0, 2.8, 1.25), kit.mat("kaya", "#8c8a6a", rough=0.8, coat=0.0), seg=32)
        kit.blob("adacik_cim", (22.2, 72.0, 0.45), (3.0, 2.0, 0.4), kit.mat("cim", "#7fb35a", rough=0.8, coat=0.0), seg=32)
    except Exception as e:
        print("varlık yüklenemedi:", e)
    key = bpy.data.lights.new("ana", "SUN"); key.energy = 3.0; key.angle = math.radians(8); key.color = (1.0, 0.95, 0.88)
    ko = bpy.data.objects.new("ana", key); sc.collection.objects.link(ko)
    ko.rotation_euler = V((-0.45, 0.72, -0.53)).normalized().to_track_quat("-Z", "Y").to_euler()
    rim = bpy.data.lights.new("kenar", "SUN"); rim.energy = 3.2; rim.angle = math.radians(4); rim.color = (1.0, 0.76, 0.48)
    ro = bpy.data.objects.new("kenar", rim); sc.collection.objects.link(ro)
    ro.rotation_euler = V((-0.16, -0.98, -0.11)).normalized().to_track_quat("-Z", "Y").to_euler()
    fl = bpy.data.lights.new("dolgu", "SUN"); fl.energy = 1.1; fl.angle = math.radians(20); fl.color = (1.0, 0.86, 0.72)
    fo = bpy.data.objects.new("dolgu", fl); sc.collection.objects.link(fo)
    fo.rotation_euler = V((0.85, 0.42, -0.32)).normalized().to_track_quat("-Z", "Y").to_euler()
    if os.environ.get("ICON_PROBE"):
        probe(sc)
        return
    R.cam_shot(sc, OUT, (0, 0, 0.8), 3.75, 0, 7.2, lens=50)
    print("yazıldı", OUT)


def probe(sc):
    """ICON_PROBE=1: her parçanın 1024'lük ekrandaki kutusunu yazar (render yok)."""
    from bpy_extras.object_utils import world_to_camera_view
    c = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", c); sc.collection.objects.link(cam); sc.camera = cam
    c.lens = 50; t = V((0, 0, 0.8)); p = math.radians(7.2)
    cam.location = t + V((0, -math.cos(p), math.sin(p))) * 3.75
    cam.rotation_euler = (t - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    groups = {}
    for o in sc.objects:
        if o.type not in ("MESH", "CURVE"): continue
        key = o.name.split("_")[0].split(".")[0]
        if key in ("kum", "deniz", "temas"): continue
        e = o.evaluated_get(dg)
        try: me = e.to_mesh()
        except Exception: continue
        for v in list(me.vertices)[::7]:
            q = world_to_camera_view(sc, cam, o.matrix_world @ v.co)
            x, y = q.x * 1024, (1 - q.y) * 1024
            g = groups.setdefault(key, [1e9, 1e9, -1e9, -1e9])
            g[0] = min(g[0], x); g[1] = min(g[1], y); g[2] = max(g[2], x); g[3] = max(g[3], y)
        e.to_mesh_clear()
    for k in sorted(groups):
        g = groups[k]; print("%-12s x %5d–%5d  y %5d–%5d" % (k, g[0], g[2], g[1], g[3]))


main()
