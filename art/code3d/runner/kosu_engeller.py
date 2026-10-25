# Piramit Koşusu — engeller, toplanabilirler ve varış kapısı (25 Ekim 2026). Hepsi gerçek boyda (m), orijin zeminde (z = 0),
# yönlü olanların ÖNÜ Blender −Y'ye bakar (oyunda yaklaşan koşucuya). Araçlar: egypt_kit.py; pişirme bld_kit tarzı (aynı ağ, parça
# içi sadeleşme, gizli yüz silme, renk × AO + normal). Kabartmalar 'dec' UV'siyle yüzeye izdüşer (CLIP: alan dışı nötr).
#   rn_block   şerit kapatan taş yığını (1,9 × 1,2 × 1,7): iki oyma blok + üstte mavi sırlı sevimli kedi heykeli + küçük küp
#   rn_block2  aynı boy: yan yatmış nilüfer başlıklı sütun gövdesi, takozlar, kum
#   rn_low     tam genişlik alçak engel (7,0 × 0,8 × 0,55): şerit başına bir taş, önünde skarabe kabartması → zıpla
#   rn_high    tam genişlik kiriş (alt 1,15, üst 1,75): iki kare ayak (x = ±3,5), önde kanatlı güneş → kay
#   rn_scarab  altın skarabe (~0,5), lapis kanat · rn_scroll papirüs tomarı (~0,7), kırmızı kurdele, mavi mühür
#   rn_gate    varış kapısı (pilon): iki eğimli kule (x = ±4,6), lento + büyük altın güneş, bayrak direkleri; açıklık x ±3,4, z 5'e dek
import os, sys, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.insert(0, HERE)
import egypt_kit as EK
from egypt_kit import np, bpy, bmesh, V, MN, TAU, smoothstep
import kit
from kit import blob, tube, cyl


# ------------------------------------------------------------------ yardımcılar

def relief(name, wm, hm, draw, ppm=300, depth=0.012, groove=0.004, fade=0.3, chips=0.3, seed=0, dark=0.1):
    """wm × hm (m) kabartma paneli → Decal (CLIP). draw(cv) tuvale çizer (metre, sol alt köşe 0,0)."""
    cv = EK.Canvas(wm, hm, ppm)
    draw(cv)
    h, over, shade = EK.finish_relief(cv, depth=depth, groove=groove, bevel=0.005, fade=fade, chips=chips, seed=seed, stone_dark=dark)
    # panel kenarında (son 2 cm) her şey nötre iner: dikiş görünmesin
    H, W = h.shape; e = int(0.02 * ppm)
    ramp = np.ones((H, W), np.float32)
    if e > 0:
        rx = np.minimum(np.arange(W), np.arange(W)[::-1]) / e; ry = np.minimum(np.arange(H), np.arange(H)[::-1]) / e
        ramp = np.clip(np.minimum(ry[:, None], rx[None, :]), 0, 1)
    h *= ramp; over[..., 3] *= ramp; shade = 1 + (shade - 1) * ramp[..., None]
    nrm = EK.normal_from_height(h, ppm, (False, False))
    return EK.Decal(name, over=over, shade=shade, normal=nrm, ext='CLIP')


def front_dec(o, x0, y, z0, w, h, face=(0, -1, 0)):
    """Önden (−Y) bakan yüzlere panel izdüşümü: u sağa (+x), v yukarı (+z)."""
    bpy.context.view_layer.update()
    if face[1] < 0: EK.planar_dec_uv(o, (x0, y, z0), (1, 0, 0), (0, 0, 1), w, h, face_dir=face)
    elif face[1] > 0: EK.planar_dec_uv(o, (x0 + w, y, z0), (-1, 0, 0), (0, 0, 1), w, h, face_dir=face)
    elif face[0] < 0: EK.planar_dec_uv(o, (x0, y + w, z0), (0, -1, 0), (0, 0, 1), w, h, face_dir=face)
    else: EK.planar_dec_uv(o, (x0, y, z0), (0, 1, 0), (0, 0, 1), w, h, face_dir=face)


def m_glaze(name, hexc, crackle=0.3):
    """Sırlı çini (fayans) heykel: canlı mavi, yukarı bakan yüz açık, dış kenar parlak, oyukta koyu; ince çatlak ağı."""
    def b(nt, bsdf):
        G = EK.EG(nt); cw = G.coords()
        col = G.mix(G.rng(G.nz(), -0.7, 0.9), EK._shade(hexc, 0.62), hexc)
        col = G.mix(G.rng(G.nz(), 0.45, 0.95, 0, 0.5), col, EK._shade(hexc, 1.45))
        col = G.mix(G.math('MULTIPLY', G.edges(0.52, 0.6), 0.45), col, EK._shade(hexc, 1.6))
        col = G.mix(G.rng(G.ao(0.06), 0.85, 0.3, 0, 0.55), col, EK._shade(hexc, 0.35))
        col = G.mix(G.rng(G.vor4(cw, 18.0, 'DISTANCE_TO_EDGE'), 0.02, 0.0, 0, crackle), col, EK._shade(hexc, 0.7))
        col = G.mix(G.rng(G.noise4(cw, 2.0, 3), 0.35, 0.7, 0, 0.25), col, '#e9d6a8')       # eskimiş sır lekesi
        G.l.new(col, bsdf.inputs['Base Color'])
    return EK.nodes_mat(name, b)


def rect_sweep(name, cx, cy, w, d, prof, mats, n_side=None, r=0.04, cap=True):
    """Dikdörtgen çevresinde profil süpürme (saçak/silme): prof = [(dışa kaçıklık, z)] alttan üste. Köşeler r yarıçaplı yay."""
    pts = []
    hw, hd = w / 2 - r, d / 2 - r
    corners = [(hw, -hd, -90), (hw, hd, 0), (-hw, hd, 90), (-hw, -hd, 180)]
    sides = n_side or max(4, int(max(w, d) / 0.25))
    path = []
    for i, (qx, qy, a0) in enumerate(corners):
        for k in range(3):
            a = math.radians(a0 + 90 * k / 2); path.append((qx, qy, math.cos(a), math.sin(a)))
        nx_, ny_ = corners[(i + 1) % 4][:2]
        seg = int(max(1, math.hypot(nx_ - qx, ny_ - qy) / 2.0))
        for k in range(1, seg):
            t = k / seg; a = math.radians(a0 + 90)
            path.append((qx + (nx_ - qx) * t, qy + (ny_ - qy) * t, math.cos(a), math.sin(a)))
    path.append(path[0])
    L = np.concatenate([[0], np.cumsum([math.hypot(path[i + 1][0] - path[i][0], path[i + 1][1] - path[i][1]) for i in range(len(path) - 1)])])
    P = np.zeros((len(prof), len(path), 3)); UV = np.zeros((len(prof), len(path), 2))
    ps = np.concatenate([[0], np.cumsum([math.hypot(prof[i + 1][0] - prof[i][0], prof[i + 1][1] - prof[i][1]) for i in range(len(prof) - 1)])])
    for i, (off, z) in enumerate(prof):
        for j, (x, y, nx_, ny_) in enumerate(path):
            P[i, j] = (cx + x + nx_ * (r + off), cy + y + ny_ * (r + off), z)
            UV[i, j] = (L[j], ps[i] / max(ps[-1], 1e-6))
    o = EK.grid_obj(name, P, UV, mats)
    if cap:   # üst kapak: son satırın köşeleri (dikiş kopyası hariç), sonra kaynak
        nu = len(path); bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
        ring = [bm.verts[(len(prof) - 1) * nu + j] for j in range(nu - 1)]
        f = bm.faces.new(ring); bm.normal_update()
        if f.normal.z < 0: f.normal_flip()
        uvl = bm.loops.layers.uv.get('dec')
        if uvl is not None:
            for l in f.loops: l[uvl].uv = (-5.0, -5.0)
        bmesh.ops.triangulate(bm, faces=[f]); bm.to_mesh(o.data); bm.free()
    EK.weld(o)
    return o


def cavetto(h=0.4, out=0.32, base=0.0, z0=0.0, fillet=0.08, n=7):
    """Mısır saçağı kesiti: dik başlar, dışa açılarak yükselir, üstte düz şerit. [(kaçıklık, z)]."""
    p = [(base, z0)]
    for k in range(1, n + 1):
        a = math.radians(90 * k / n)
        p.append((base + out * (1 - math.cos(a)), z0 + h * math.sin(a)))
    p.append((base + out, z0 + h + fillet))
    return p


def sand_skirt(name, cx, cy, rx, ry, h, seed=0, mat=None, n=36, rings=5, lift=0.0):
    """Nesne dibinde kum eteği: dışta sıfır, içte h (dibe yaslanan halka)."""
    R = random.Random(seed); ph = [R.uniform(0, TAU) for _ in range(3)]
    P = np.zeros((rings + 1, n + 1, 3))
    for i in range(rings + 1):
        t = i / rings
        for j in range(n + 1):
            a = j / n * TAU
            k = 1 + 0.12 * math.sin(a * 2 + ph[0]) + 0.07 * math.sin(a * 3 + ph[1])
            rr = (1.0 + 0.35 * (1 - t)) * k
            P[i, j] = (cx + math.cos(a) * rx * rr, cy + math.sin(a) * ry * rr, lift + h * smoothstep(0, 1, t) * (0.8 + 0.2 * math.sin(a * 4 + ph[2])))
    o = EK.grid_obj(name, P, None, [mat or EK.m_sand('ssand')])
    EK.weld(o)
    return o


def rubble(name, loc, size, seed, mat, rot=None):
    R = random.Random(seed)
    return EK.rounded_box(name, size, min(size) * 0.2, max(0.015, min(size) / 6), [mat], loc=loc,
                          rot=rot or (R.uniform(-12, 12), R.uniform(-12, 12), R.uniform(0, 360)), chips=min(size) * 0.12, lump=min(size) * 0.03, seed=seed)


# ------------------------------------------------------------------ çizimler

def draw_block_front(cv):
    W, H = cv.wm, cv.H / cv.ppm
    cv.rect(0.03, 0.03, W - 0.03, H - 0.03, carve=True, col=None, layer='groove')
    cv.rect(0.05, 0.05, W - 0.05, H - 0.05, carve=False, col=None)
    inner = [(0.06, 0.06), (W - 0.06, 0.06), (W - 0.06, H - 0.06), (0.06, H - 0.06), (0.06, 0.06)]
    cv.line(inner, 0.014, col=EK.C(EK.LAPIS))
    EK.g_sun(EK.Pen(cv, W / 2 - 0.2, H / 2 - 0.2, 0.4, 0.4))
    for s in (-1, 1):
        EK.g_lotus(EK.Pen(cv, W / 2 + s * 0.38 - 0.11, 0.1, 0.22, 0.36))
        EK.g_duck(EK.Pen(cv, W / 2 + s * 0.62 - 0.15, 0.14, 0.3, 0.22, flip=s < 0))
    EK.g_waves(EK.Pen(cv, 0.1, 0.07, W - 0.2, 0.06), rows=1)


def draw_starband(cv):
    W, H = cv.wm, cv.H / cv.ppm
    cv.rect(0.02, 0.06, W - 0.02, H - 0.06, carve=False, col=EK.C('#2b5fa6'))
    n = int(W / 0.2)
    for i in range(n):
        EK.g_star(EK.Pen(cv, 0.04 + i * (W - 0.08) / n + 0.02, H / 2 - 0.08, 0.16, 0.16))


def draw_scarab_band(cv):
    W, H = cv.wm, cv.H / cv.ppm
    EK.g_scarab(EK.Pen(cv, W / 2 - 0.17, 0.02, 0.34, H - 0.04))
    for s in (-1, 1):
        EK.g_lotus(EK.Pen(cv, W / 2 + s * 0.42 - 0.12, 0.03, 0.24, H - 0.08))
        EK.g_feather(EK.Pen(cv, W / 2 + s * 0.68 - 0.06, 0.03, 0.12, H - 0.06))
    cv.rect(0.02, H - 0.035, W - 0.02, H - 0.012, carve=True, col=EK.C(EK.BLUE), val=120)


def draw_winged_sun(cv, disc=True):
    W, H = cv.wm, cv.H / cv.ppm; cx = W / 2
    rows = (EK.BLUE, EK.TURQ, EK.TERRA, EK.GOLD)
    for s in (-1, 1):
        for k, c in enumerate(rows):
            # kanat: diskten dışa uzanan, uca doğru incelen tüy sırası (alttaki sıralar daha kısa)
            y0 = H * (0.62 - k * 0.15); y1 = y0 + H * 0.13
            reach = (W / 2 - 0.05) * (1.0 - 0.13 * k)
            pts = [(cx + s * 0.18, y0), (cx + s * reach, y0 + H * 0.05 * k * 0.3), (cx + s * reach, y1), (cx + s * 0.18, y1 + H * 0.02)]
            cv.poly(pts, col=EK.C(c))
            nf = int(reach / 0.12)
            for f in range(1, nf):
                u = cx + s * (0.18 + f * (reach - 0.18) / nf); cv.line([(u, y0 + 0.01), (u, y1 - 0.01)], 0.01)
    if disc:
        cv.ell(cx, H * 0.55, H * 0.36, H * 0.36, col=EK.C(EK.GOLD)); cv.ell(cx, H * 0.55, H * 0.24, H * 0.24, col=EK.C(EK.TERRA), layer='raise')


def draw_cornice(cv):
    """Saçak yaprak çubukları (u yönünde 1 m'de tekrar; tekrar eden UV ile)."""
    W, H = cv.wm, cv.H / cv.ppm; lc = [EK.BLUE, EK.GREEN, EK.TERRA, EK.GREEN]
    for i in range(8):
        u = i * 0.125 + 0.02
        p = EK.Pen(cv, u, 0.0, 0.085, H * 0.86)
        p.poly([(0, 0), (0, 0.86)] + EK.arcpts(0.5, 0.86, 0.5, 0.14, 180, 0, 8) + [(1, 0)], EK.C(lc[i % 4]), val=140)
    cv.rect(0, H * 0.88, W, H, carve=False, col=EK.C(EK.OCHRE))


def cornice_decal(name, hm):
    cv = EK.Canvas(1.0, hm, 300, wrap_u=True)
    draw_cornice(cv)
    h, over, shade = EK.finish_relief(cv, depth=0.008, groove=0.003, fade=0.35, chips=0.35, seed=4, wrap=(False, True))
    return EK.Decal(name, over=over, shade=shade, normal=EK.normal_from_height(h, 300, (False, True)), ext='REPEAT')


# ------------------------------------------------------------------ kedi heykeli (sevimli, oturan; önü −Y)

def cat_statue(loc, s=1.0, yaw=0.0, tilt=(0, 0)):
    BL = m_glaze('catglaze', '#2f78bf'); GD = EK.m_gold('catgold'); IN = EK.m_flatc('catear', '#e08a6a')
    EYE = EK.m_flatc('cateye', '#f2d36a', 0.05, 0.2); PUP = EK.m_flatc('catpupil', '#2a2238', 0.05, 0.0); WH = EK.m_flatc('catshine', '#ffffff', 0.0, 0.0)
    parts = []
    def B(n, c, r, m, rot=(0, 0, 0), seg=24, sub=2): parts.append(blob(n, c, r, m, rot=rot, seg=seg, sub=sub))
    B('cat_body', (0, 0.03, 0.17), (0.15, 0.17, 0.19), BL)
    B('cat_chest', (0, -0.07, 0.21), (0.12, 0.09, 0.15), BL)
    for sx in (-1, 1):
        B('cat_haunch', (sx * 0.1, 0.06, 0.1), (0.07, 0.13, 0.1), BL)
        B('cat_paw', (sx * 0.055, -0.14, 0.03), (0.042, 0.06, 0.034), BL, seg=16)
        parts.append(tube('cat_leg', [(sx * 0.055, -0.08, 0.22), (sx * 0.055, -0.12, 0.12), (sx * 0.055, -0.13, 0.04)], [0.036, 0.034, 0.034], BL, res=4))
        ear = blob('cat_ear', (sx * 0.072, -0.045, 0.485), (0.045, 0.025, 0.07), BL, rot=(0, sx * -18, sx * 10), seg=16)
        parts.append(ear)
        B('cat_earin', (sx * 0.072, -0.066, 0.48), (0.026, 0.008, 0.045), IN, rot=(0, sx * -18, sx * 10), seg=12, sub=1)
        B('cat_eye', (sx * 0.048, -0.152, 0.4), (0.03, 0.012, 0.027), EYE, rot=(0, 0, sx * 12), seg=16, sub=1)
        B('cat_pupil', (sx * 0.048, -0.161, 0.4), (0.017, 0.006, 0.02), PUP, seg=12, sub=1)
        B('cat_shine', (sx * 0.044, -0.165, 0.41), (0.006, 0.003, 0.006), WH, seg=8, sub=0)
    B('cat_head', (0, -0.06, 0.39), (0.12, 0.11, 0.105), BL)
    B('cat_cheek', (0, -0.12, 0.36), (0.1, 0.06, 0.06), BL)
    B('cat_muzzle', (0, -0.165, 0.355), (0.045, 0.03, 0.03), BL, seg=16)
    B('cat_nose', (0, -0.192, 0.37), (0.014, 0.008, 0.01), IN, seg=8, sub=1)
    parts.append(tube('cat_tail', [(0.12, 0.17, 0.05), (0.19, 0.04, 0.035), (0.15, -0.1, 0.03), (0.06, -0.19, 0.03)], [0.035, 0.034, 0.03, 0.026], BL, res=6))
    bpy.ops.mesh.primitive_torus_add(major_radius=0.105, minor_radius=0.016, location=(0, -0.05, 0.29), rotation=(math.radians(-14), 0, 0))
    c = bpy.context.object; c.name = 'cat_collar'; c.data.materials.append(GD); parts.append(c)
    B('cat_tag', (0, -0.158, 0.255), (0.03, 0.012, 0.03), GD, seg=16, sub=1)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.018, minor_radius=0.005, location=(0.1, -0.06, 0.45), rotation=(0, math.radians(90), 0))
    e = bpy.context.object; e.name = 'cat_ring'; e.data.materials.append(GD); parts.append(e)
    # yerleştir: s ölçek, yaw, eğiklik
    root = bpy.data.objects.new('cat_root', None); bpy.context.scene.collection.objects.link(root)
    for p in parts: p.parent = root
    root.scale = (s, s, s); root.rotation_euler = (math.radians(tilt[0]), math.radians(tilt[1]), math.radians(yaw)); root.location = loc
    bpy.context.view_layer.update()
    for p in parts:
        mw = p.matrix_world.copy(); p.parent = None; p.matrix_world = mw
    bpy.data.objects.remove(root)
    return parts


def jar(name, loc, h=0.3, rot=(0, 0, 0), hexc='#c9774a', band='#2f6db5'):
    prof = [(0.0, 0.0), (0.2, 0.0), (0.42, 0.18), (0.5, 0.42), (0.42, 0.7), (0.2, 0.84), (0.17, 0.92), (0.24, 0.97), (0.2, 1.0), (0.14, 0.98),
            (0.12, 0.9), (0.0, 0.86)]
    prof = [(r * h * 0.5, z * h) for r, z in prof]
    m = EK.m_clay('clay_' + name, hexc, band=[(0.55 * h, 0.62 * h, band), (0.66 * h, 0.69 * h, EK.CREAM)])
    o = EK.lathe_grid(name, prof, 20, [m], uv=False)
    o.location = loc; o.rotation_euler = [math.radians(a) for a in rot]
    return o


# ================================================================== rn_block

def build_block():
    ST = EK.SANDSTONE
    d1 = relief('blkfront', 1.6, 0.6, draw_block_front, seed=3)
    d2 = relief('blkstars', 1.3, 0.3, draw_starband, seed=4)
    b1 = EK.rounded_box('blk1', (1.9, 1.2, 0.82), 0.05, 0.03, [EK.m_stone('blk1st', ST, dec=d1)], loc=(0, 0, 0.41), chips=0.05, lump=0.006, seed=1)
    front_dec(b1, -0.8, -0.6, 0.13, 1.6, 0.6)
    b2 = EK.rounded_box('blk2', (1.45, 0.95, 0.45), 0.045, 0.03, [EK.m_stone('blk2st', EK.SANDSTONE, dec=d2, seed=2.0)], loc=(-0.06, 0.04, 0.82 + 0.225 - 0.005), rot=(0, 0, 4), chips=0.045, lump=0.005, seed=2)
    front_dec(b2, -0.71, -0.45, 0.89, 1.3, 0.3)
    hi = [b1, b2]
    hi += cat_statue((0.12, -0.06, 1.262), s=0.8, yaw=-14, tilt=(0, 5))
    hi.append(jar('blkjar', (-0.5, 0.05, 1.265), 0.3))
    hi.append(jar('blkjar2', (-0.3, 0.3, 1.265), 0.22, hexc='#d68d5c', band=EK.TURQ))
    SD = EK.m_sand('blksand')
    hi.append(sand_skirt('blksand', 0, 0, 0.98, 0.64, 0.13, 3, SD))
    STN = EK.m_stone('blkrub', ST, seed=5.0)
    hi.append(rubble('rub', (0.82, -0.62, 0.05), (0.18, 0.14, 0.1), 11, STN))
    hi.append(rubble('rub', (-0.88, 0.55, 0.04), (0.14, 0.12, 0.09), 12, STN))
    decim = [(r'^blk[12]$', 0.012), (r'^cat_(body|head|chest|cheek)$', 0.06), (r'^cat_(haunch|muzzle)$', 0.08), (r'^cat_(paw|ear|leg|tail)$', 0.12),
             (r'^cat_(earin|eye|pupil|nose|tag)$', 0.25), (r'^cat_shine$', 0.5), (r'^cat_collar$', 0.1), (r'^cat_ring$', 0.25),
             (r'^blkjar', 0.3), (r'^blksand$', 0.5), (r'^rub$', 0.03)]
    weights = [(r'^cat_', 1.6), (r'^blkjar', 1.2), (r'^blk[12]$', 1.0), (r'sand', 0.4), (r'^rub$', 0.5)]
    return hi, None, dict(decim=decim, weights=weights, tex=512, budget=2500, ao_dist=0.3)


# ================================================================== rn_block2

def build_block2():
    import piramit_kosusu as PK
    C_ = PK.column_maps(seed=41)
    dec = EK.Decal('drum', over=C_['over'], shade=C_['shade'], normal=C_['nrm'], ext='REPEAT')
    MAT = EK.m_stone('drumst', EK.SANDSTONE, dec=dec, bands=0.0, seed=3.0)
    # sütun ekseni x boyunca: z' = eksen boyu (0 kırık uç, x = −0,95 · 1,9 başlık tepesi, x = +0,95); yarıçap ×2 (ince sütun haritası)
    th = np.linspace(0, TAU, 129); ax = np.linspace(0, 1.9, 120)
    def colz(a):            # gövde boyu → ince sütun haritasındaki z (gövde 0..1,1 → 1,2..1,95; bilezik/çanak birebir)
        return np.where(a < 1.1, 1.25 + (a / 1.1) * 0.7, a + 0.85)
    TH, AX = np.meshgrid(th, ax)
    CZ = colz(AX)
    def drum_r(TH, CZ):
        cr = PK.col_radius(TH, CZ)
        return np.where(CZ < 2.12, cr * 1.8, 0.43 + (cr - 0.235) * 0.85)
    RR = drum_r(TH, CZ)
    cy0, cz0 = 0.0, 1.0
    P = np.stack([-0.95 + AX, cy0 + RR * np.cos(TH), cz0 + RR * np.sin(TH)], -1)
    UV = np.stack([TH / TAU, CZ / C_['Hm']], -1)
    drum = EK.grid_obj('drum', P, UV, [MAT], flip=False)
    # kırık uç (−x): pürüzlü disk
    R = random.Random(5); n = 40; verts = [(-0.95 - 0.02, cy0, cz0)]
    for i in range(n):
        a = i / n * TAU; r0 = float(drum_r(np.array(a), np.array(colz(np.array(0.0)))))
        for k in (0.35, 0.7, 1.0):
            jag = (0.06 * MN.noise(V((math.cos(a) * 3 * k, math.sin(a) * 3 * k, 1.7))) + 0.035) if k < 1 else 0.0
            verts.append((-0.95 + jag, cy0 + math.cos(a) * r0 * k, cz0 + math.sin(a) * r0 * k))
    faces = []
    for i in range(n):
        i2 = (i + 1) % n; a0, a1 = 1 + i * 3, 1 + i2 * 3
        faces.append((0, a1, a0))
        for k in range(2): faces.append((a0 + k, a1 + k, a1 + k + 1, a0 + k + 1))
    brk = EK.mesh_obj('break', verts, faces, [EK.m_stone('brkst', ('#cfa776', '#e6c595', '#f2dcb0'), bands=0, pits=0.8, seed=6.0)])
    bm = bmesh.new(); bm.from_mesh(brk.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(brk.data); bm.free()
    bm = bmesh.new(); bm.from_mesh(brk.data); bm.normal_update()
    if sum(f.normal.x for f in bm.faces) > 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:]); bm.to_mesh(brk.data)
    bm.free()
    # başlık tepesi (x = +0,95): kapak disk (abaküs kırığı)
    top_r = float(drum_r(np.array(0.3), np.array(colz(np.array(1.9)))))
    cap = EK.mesh_obj('capt', [(0.95, cy0 + math.cos(i / 40 * TAU) * top_r * 0.98, cz0 + math.sin(i / 40 * TAU) * top_r * 0.98) for i in range(40)], [list(range(40))],
                      [EK.m_stone('captst', EK.SANDSTONE, bands=0, seed=7.0)])
    ST = EK.m_stone('chockst', EK.SANDSTONE, seed=8.0)
    hi = [drum, brk, cap]
    hi.append(EK.rounded_box('chock', (0.42, 1.0, 0.56), 0.05, 0.03, [ST], loc=(-0.6, 0.0, 0.28), rot=(0, 0, 3), chips=0.04, lump=0.006, seed=21))
    hi.append(EK.rounded_box('chock', (0.4, 0.95, 0.56), 0.05, 0.03, [ST], loc=(-0.05, 0.02, 0.28), rot=(0, 0, -5), chips=0.04, lump=0.006, seed=22))
    SD = EK.m_sand('dsand')
    hi.append(sand_skirt('dsand', -0.2, 0.0, 0.85, 0.52, 0.34, 7, SD))
    hi.append(sand_skirt('dsand', 0.62, 0.0, 0.36, 0.42, 0.5, 8, SD))
    hi.append(rubble('rub', (-0.75, -0.55, 0.06), (0.22, 0.16, 0.12), 31, ST))
    hi.append(rubble('rub', (0.8, 0.5, 0.05), (0.16, 0.14, 0.1), 32, ST))
    decim = [(r'^drum$', 0.035), (r'^break$', 0.6), (r'^chock$', 0.012), (r'^dsand$', 0.6), (r'^rub$', 0.03)]
    weights = [(r'^drum$', 1.3), (r'^break$', 0.9), (r'sand', 0.4), (r'^rub$', 0.5)]
    return hi, None, dict(decim=decim, weights=weights, tex=512, budget=2500, ao_dist=0.3)


# ================================================================== rn_low

def build_low():
    dec = relief('lowfront', 1.9, 0.36, draw_scarab_band, seed=6)
    hi = []
    for i, (cx, hz, rz, dy) in enumerate(((-2.33, 0.49, 1.2, 0.02), (0.0, 0.52, -0.6, -0.015), (2.33, 0.47, 0.8, 0.01))):
        m = EK.m_stone('lowst%d' % i, EK.SANDSTONE, dec=dec, seed=float(i))
        b = EK.rounded_box('lowblk', (2.27, 0.8, hz), 0.045, 0.03, [m], loc=(cx, dy, hz / 2), rot=(0, 0, rz), chips=0.045, lump=0.005, seed=40 + i)
        front_dec(b, cx - 0.95, -0.4 + dy, 0.07, 1.9, 0.36)
        hi.append(b)
    SD = EK.m_sand('lowsand')
    for i, cx in enumerate((-2.33, 0.0, 2.33)):
        for sy in (-1, 1):
            R = random.Random(60 + i * 2 + sy)
            xs = np.linspace(cx - 1.05, cx + 1.05, 22); ts = np.linspace(0, 1, 5)
            X, T = np.meshgrid(xs, ts)
            hgt = 0.1 + 0.04 * np.sin(X * 2.1 + R.uniform(0, 6))
            Y = sy * (0.36 + 0.3 * T); Z = hgt * (1 - T) ** 1.4
            hi.append(EK.grid_obj('lsand', np.stack([X, Y, Z], -1), None, [SD], flip=sy < 0))
    STN = EK.m_stone('lowrub', EK.SANDSTONE, seed=9.0)
    hi.append(rubble('rub', (-3.3, -0.5, 0.05), (0.18, 0.14, 0.1), 51, STN))
    hi.append(rubble('rub', (1.2, -0.62, 0.04), (0.12, 0.1, 0.08), 52, STN))
    hi.append(rubble('rub', (3.35, 0.5, 0.05), (0.16, 0.12, 0.09), 53, STN))
    decim = [(r'^lowblk$', 0.01), (r'^lsand$', 0.5), (r'^rub$', 0.03)]
    weights = [(r'^lowblk$', 1.0), (r'sand', 0.35), (r'^rub$', 0.4)]
    return hi, None, dict(decim=decim, weights=weights, tex=512, budget=2500, ao_dist=0.3)


# ================================================================== rn_high

def build_high():
    ST = EK.SANDSTONE
    dsun = relief('wingsun', 5.2, 0.4, draw_winged_sun, ppm=220, seed=8)
    def pillar_draw(cv):
        W, H = cv.wm, cv.H / cv.ppm
        for k, g in enumerate(('eye', 'star', 'lotus', 'duck')):
            EK.GLYPHS[g](EK.Pen(cv, 0.04, H - 0.06 - (k + 1) * 0.22 + 0.02, W - 0.08, 0.18))
        cv.line([(0.02, 0.05), (0.02, H - 0.04)], 0.012, col=EK.C(EK.LAPIS)); cv.line([(W - 0.02, 0.05), (W - 0.02, H - 0.04)], 0.012, col=EK.C(EK.LAPIS))
    dp = relief('pilglyph', 0.3, 1.0, pillar_draw, seed=9)
    hi = []
    for sx in (-1, 1):
        p = EK.rounded_box('pillar', (0.44, 0.5, 1.16), 0.035, 0.03, [EK.m_stone('pilst', ST, dec=dp, seed=sx * 1.0)], loc=(sx * 3.5, 0, 0.58), chips=0.035, lump=0.004, seed=70 + sx)
        front_dec(p, sx * 3.5 - 0.15, -0.25, 0.08, 0.3, 1.0)
        hi.append(p)
    beam = EK.rounded_box('beam', (7.8, 0.6, 0.44), 0.04, 0.035, [EK.m_stone('beamst', ST, dec=dsun, seed=4.0)], loc=(0, 0, 1.16 + 0.22), chips=0.035, lump=0.0, seed=80)
    front_dec(beam, -2.6, -0.3, 1.18, 5.2, 0.4)
    hi.append(beam)
    dc = cornice_decal('hcorn', 0.15)
    hi.append(rect_sweep('hcornice', 0, 0, 7.82, 0.62, cavetto(0.1, 0.07, -0.01, 1.595, 0.045), [EK.m_stone('hcst', ST, dec=dc, seed=5.0)], r=0.03))
    SD = EK.m_sand('hsand')
    for sx in (-1, 1): hi.append(sand_skirt('hsand', sx * 3.5, 0, 0.3, 0.33, 0.14, 81 + sx, SD))
    decim = [(r'^pillar$', 0.015), (r'^beam$', 0.006), (r'^hcornice$', 0.5), (r'^hsand$', 0.5)]
    weights = [(r'^beam$', 1.25), (r'^pillar$', 1.0), (r'^hcornice', 0.8), (r'sand', 0.35)]
    return hi, None, dict(decim=decim, weights=weights, tex=512, budget=3000, ao_dist=0.3)


# ================================================================== rn_scarab

def build_scarab():
    GD = EK.m_gold('scgold'); LP = m_glaze('sclapis', '#2350a8', crackle=0.0)
    TQ = m_glaze('scturq', '#2fb3a6', crackle=0.0); RED = m_glaze('scred', '#d0472f', crackle=0.0)
    hi = []
    hi.append(blob('sc_base', (0, 0.03, 0.1), (0.2, 0.23, 0.085), GD))
    for sx in (-1, 1):
        hi.append(blob('sc_wing', (sx * 0.098, 0.06, 0.135), (0.1, 0.19, 0.085), LP, rot=(0, sx * 6, sx * -4)))
        hi.append(blob('sc_wingdot', (sx * 0.1, 0.1, 0.205), (0.035, 0.05, 0.016), TQ, rot=(0, sx * 10, 0), seg=16, sub=1))
        for k, (ya, yb, z) in enumerate(((-0.08, -0.18, 0.06), (0.0, 0.0, 0.055), (0.1, 0.2, 0.05))):
            hi.append(tube('sc_leg', [(sx * 0.15, ya, z + 0.02), (sx * 0.24, (ya + yb) / 2, 0.05), (sx * 0.28, yb, 0.015)], [0.024, 0.02, 0.022], GD, res=4))
    hi.append(blob('sc_seam', (0, 0.06, 0.2), (0.012, 0.18, 0.03), GD, seg=12, sub=1))
    hi.append(blob('sc_thorax', (0, -0.14, 0.12), (0.15, 0.08, 0.07), GD))
    hi.append(blob('sc_head', (0, -0.22, 0.09), (0.1, 0.06, 0.05), GD))
    for k in range(4):
        a = math.radians(-50 + k * 33.3)
        hi.append(blob('sc_rake', (math.sin(a) * 0.09, -0.26 - math.cos(a) * 0.025, 0.08), (0.025, 0.025, 0.02), GD, seg=12, sub=1))
    hi.append(blob('sc_gem', (0, -0.15, 0.185), (0.045, 0.035, 0.022), RED, seg=16, sub=1))
    decim = [(r'^sc_(base|wing|thorax|head)$', 0.05), (r'^sc_(wingdot|seam|gem|rake)$', 0.18), (r'^sc_leg$', 0.25)]
    weights = [(r'^sc_(wing|thorax|head|gem)', 1.4)]
    return hi, None, dict(decim=decim, weights=weights, tex=512, budget=800, ao_dist=0.12, cage=0.01, ray=0.04)


# ================================================================== rn_scroll

def m_papyrus(name='papyrus'):
    """Papirüs: krem-saman, iki yönlü lif şeritleri (enine/boyuna), kenara doğru koyulaşan, eski lekeler."""
    def b(nt, bsdf):
        G = EK.EG(nt); o = G.obj(); x, y, z = G.sep(G.pos())
        col = G.mix(G.rng(G.noise(o, 3.0, 3), 0.3, 0.7), '#e9d29a', '#f6e6bb')
        f1 = G.noise(G.mapping(o, (2.0, 60.0, 60.0)), 4.0, 2); f2 = G.noise(G.mapping(o, (60.0, 2.0, 2.0)), 4.0, 2)
        col = G.mix(G.rng(f1, 0.45, 0.6, 0, 0.28), col, '#c9a865'); col = G.mix(G.rng(f2, 0.48, 0.62, 0, 0.2), col, '#c9a865')
        col = G.mix(G.rng(G.math('ABSOLUTE', x), 0.28, 0.35, 0, 0.5), col, '#b98d4c')
        col = G.mix(G.rng(G.ao(0.03), 0.85, 0.3, 0, 0.6), col, '#7a5a2c')
        G.l.new(col, bsdf.inputs['Base Color'])
    return EK.nodes_mat(name, b)


def build_scroll():
    PY = m_papyrus(); RB = m_glaze('scrred', '#d23f34', crackle=0.0); SL = m_glaze('scrseal', '#2f63b8', crackle=0.05); GD = EK.m_gold('scrgold')
    hi = []
    L = 0.62; r = 0.085
    prof = [(0.0, -L / 2), (r * 0.92, -L / 2), (r * 1.06, -L / 2 + 0.012), (r, -L / 2 + 0.05), (r * 0.97, 0.0), (r, L / 2 - 0.05), (r * 1.06, L / 2 - 0.012), (r * 0.92, L / 2), (0.0, L / 2)]
    roll = EK.lathe_grid('scr_roll', prof, 28, [PY], uv=False)
    roll.rotation_euler = (0, math.radians(90), 0); roll.location = (0, 0, r * 1.06)
    hi.append(roll)
    # uçlarda sarmal: koyu spiral çizgi (ince tüp) — kâğıt katmanları
    for sx in (-1, 1):
        pts = []
        for k in range(40):
            t = k / 39; a = t * TAU * 3.2; rr = r * (0.12 + 0.85 * t)
            pts.append((sx * (L / 2 + 0.002), math.cos(a) * rr, r * 1.06 + math.sin(a) * rr))
        hi.append(tube('scr_spiral', pts, [0.006] * 40, EK.m_flatc('scrline', '#9a7440', 0.05, 0.0), res=2))
    # dışa açılmış kat (kıvrık dil): ince yaprak
    th = np.linspace(-0.4, 1.1, 12); xs = np.linspace(-L / 2 + 0.03, L / 2 - 0.03, 10)
    TH, X = np.meshgrid(th, xs)
    RR = r * 1.01 + 0.03 * np.clip(TH, 0, None) ** 1.5
    P = np.stack([X, RR * np.cos(-TH - 1.2), r * 1.06 + RR * np.sin(-TH - 1.2)], -1)
    flap = EK.grid_obj('scr_flap', P, None, [PY]); flap.data.attributes.new('ds', 'INT', 'FACE').data.foreach_set('value', [1] * len(flap.data.polygons))
    s = flap.modifiers.new('sol', 'SOLIDIFY'); s.thickness = 0.004; hi.append(flap)
    # kurdele + fiyonk + mühür
    bpy.ops.mesh.primitive_torus_add(major_radius=r * 1.04, minor_radius=0.012, location=(0, 0, r * 1.06), rotation=(0, math.radians(90), 0))
    t = bpy.context.object; t.name = 'scr_ribbon'; t.scale = (1, 1, 1); t.data.materials.append(RB); hi.append(t)
    for sy in (-1, 1):
        hi.append(blob('scr_bow', (0, sy * 0.05, r * 2.2), (0.018, 0.045, 0.03), RB, rot=(sy * 25, 0, 0), seg=16))
        hi.append(tube('scr_tail', [(0, sy * 0.01, r * 2.1), (0.01, sy * 0.05, r * 1.6), (0.02, sy * 0.07, r * 1.1)], [0.012, 0.011, 0.01], RB, res=3))
    hi.append(blob('scr_knot', (0, 0, r * 2.15), (0.022, 0.022, 0.02), RB, seg=16))
    hi.append(cyl('scr_seal', (0, -r * 1.02, r * 1.06), 0.038, 0.016, SL, rot=(90, 0, 0), verts=20, bevel=0.004))
    hi.append(blob('scr_sealsun', (0, -r * 1.02 - 0.01, r * 1.06), (0.017, 0.006, 0.017), GD, seg=12, sub=1))
    for a in range(5):
        aa = math.radians(a * 72 + 20)
        hi.append(blob('scr_sealdrop', (math.cos(aa) * 0.04, -r * 1.02 - 0.002, r * 1.06 + math.sin(aa) * 0.04), (0.012, 0.008, 0.01), SL, seg=8, sub=1))
    decim = [(r'^scr_roll$', 0.35), (r'^scr_spiral$', 0.3), (r'^scr_flap$', 0.5), (r'^scr_ribbon$', 0.15), (r'^scr_(bow|knot|tail)$', 0.12),
             (r'^scr_seal$', 0.4), (r'^scr_(sealsun|sealdrop)$', 0.3)]
    weights = [(r'^scr_roll', 1.2), (r'^scr_(seal|bow|knot)', 1.4)]
    return hi, None, dict(decim=decim, weights=weights, tex=512, budget=800, ao_dist=0.06, cage=0.008, ray=0.03, ds_low=True)


# ================================================================== rn_gate

def build_gate():
    ST = EK.SANDSTONE
    def pylon_draw(cv, big):
        W, H = cv.wm, cv.H / cv.ppm
        cv.rect(0.04, H - 0.5, W - 0.04, H - 0.06, carve=False, col=EK.C('#2b5fa6'))
        for i in range(5): EK.g_star(EK.Pen(cv, 0.12 + i * (W - 0.24) / 5 + 0.05, H - 0.44, 0.28, 0.32))
        cv.line([(0.04, H - 0.56), (W - 0.04, H - 0.56)], 0.03, col=EK.C(EK.TERRA))
        EK.GLYPHS[big](EK.Pen(cv, W * 0.14, 1.25, W * 0.72, 2.0, flip=big in ('ibis',)))
        for k in range(3):
            EK.g_lotus(EK.Pen(cv, 0.2 + k * (W - 0.4) / 3 + 0.04, 0.32, (W - 0.4) / 3 - 0.08, 0.75))
        EK.g_waves(EK.Pen(cv, 0.08, 0.08, W - 0.16, 0.18), rows=2)
        frame = [(0.03, 0.03), (W - 0.03, 0.03), (W - 0.03, H - 0.03), (0.03, H - 0.03), (0.03, 0.03)]
        cv.line(frame, 0.03, col=EK.C(EK.OCHRE))
    hi = []
    H, BW, BD, TOP = 6.0, 2.4, 1.6, 0.84
    for sx, big in ((-1, 'cat'), (1, 'ibis')):
        d = relief('pyl%d' % sx, 1.7, 4.6, lambda cv, b=big: pylon_draw(cv, b), ppm=120, depth=0.02, groove=0.006, seed=12 + sx)
        p = EK.rounded_box('pylon', (BW, BD, H), 0.06, 0.08, [EK.m_stone('pylst%d' % sx, ST, dec=d, seed=sx * 2.0)], loc=(0, 0, H / 2), chips=0.07, lump=0.01, seed=90 + sx)
        # eğim (batter): tepede 0,84 kat; sonra yerine
        for v in p.data.vertices:
            t = (v.co.z + H / 2) / H; k = 1 - (1 - TOP) * t
            v.co.x *= k; v.co.y *= k
        p.location = (sx * 4.6, 0, H / 2)
        bpy.context.view_layer.update()
        # yüz paneli: eğik yüze izdüşüm (yaklaşık; panel ortası)
        front_dec(p, sx * 4.6 - 0.85, -BD / 2, 0.45, 1.7, 4.6)
        hi.append(p)
        dc = cornice_decal('pcorn%d' % sx, 0.5)
        hi.append(rect_sweep('pcornice', sx * 4.6, 0, BW * TOP + 0.02, BD * TOP + 0.02, cavetto(0.38, 0.26, -0.02, H - 0.02, 0.1),
                             [EK.m_stone('pcst%d' % sx, ST, dec=dc, seed=sx * 3.0)], r=0.05))
        # bayrak direği + flama (iç ön köşe)
        px, py = sx * 3.72, -1.0
        hi.append(cyl('pole', (px, py, 3.9), 0.07, 7.8, EK.m_paint('polepaint', '#b8763c', 0.2, 0.2, base='#8a5a30'), verts=12, bevel=0.0))
        hi.append(blob('polecap', (px, py, 7.86), (0.13, 0.13, 0.13), EK.m_gold('polegold'), seg=16))
        hi.append(cyl('polering', (px, py, 0.9), 0.1, 0.12, EK.m_gold('polegold2'), verts=12, bevel=0.01))
        FL = EK.m_cloth('flag%d' % sx, EK.BLUE if sx < 0 else EK.TERRA, EK.CREAM, stripes=2.4, axis='Z')
        us = np.linspace(0, 1, 16); vs = np.linspace(0, 1, 4)
        U, Vv = np.meshgrid(us, vs)
        Lf = 1.9
        X = px + sx * (0.06 + U * Lf * (0.95 - 0.1 * U)); Y = py + 0.12 * np.sin(U * 5.0 + 0.6) * U - 0.03 * Vv
        Z = 7.65 - 0.55 * Vv * (1 - 0.82 * U) - 0.08 * U - 0.06 * np.sin(U * 3.1)
        f = EK.grid_obj('flag', np.stack([X, Y, Z], -1), None, [FL], flip=sx < 0)
        f.data.attributes.new('ds', 'INT', 'FACE').data.foreach_set('value', [1] * len(f.data.polygons))
        hi.append(f)
        SD = EK.m_sand('gsand%d' % sx)
        hi.append(sand_skirt('gsand', sx * 4.6, 0, 1.3, 0.9, 0.22, 95 + sx, SD))
        hi.append(jar('gjar', (sx * 5.55, -1.05, 0.0), 0.55, rot=(0, 0, 20 * sx), hexc='#c9774a', band=EK.BLUE if sx > 0 else EK.TURQ))
    # lento (açıklık z 5'e dek boş) + saçak + kanatlı süs + güneş diski
    dl = relief('lintel', 5.6, 0.7, lambda cv: draw_winged_sun(cv, disc=False), ppm=140, seed=17)
    lin = EK.rounded_box('lintel', (7.7, 1.2, 0.85), 0.05, 0.08, [EK.m_stone('linst', ST, dec=dl, seed=6.0)], loc=(0, 0, 5.0 + 0.425), chips=0.05, lump=0.0, seed=99)
    front_dec(lin, -2.8, -0.6, 5.08, 5.6, 0.7)
    hi.append(lin)
    dc = cornice_decal('lcorn', 0.4)
    hi.append(rect_sweep('lcornice', 0, 0, 7.72, 1.22, cavetto(0.3, 0.2, -0.01, 5.84, 0.08), [EK.m_stone('lcst', ST, dec=dc, seed=7.0)], r=0.04))
    GD = EK.m_gold('sungold'); LP = m_glaze('sunlapis', '#2350a8', crackle=0.0); RD = m_glaze('sunred', '#d0472f', crackle=0.0)
    hi.append(cyl('sun_disc', (0, -0.62, 6.55), 0.92, 0.24, GD, rot=(90, 0, 0), verts=48, bevel=0.06))
    bpy.ops.mesh.primitive_torus_add(major_radius=0.7, minor_radius=0.07, location=(0, -0.76, 6.55), rotation=(math.radians(90), 0, 0), major_segments=48, minor_segments=10)
    t = bpy.context.object; t.name = 'sun_ring'; t.data.materials.append(LP); hi.append(t)
    hi.append(cyl('sun_core', (0, -0.75, 6.55), 0.42, 0.06, RD, rot=(90, 0, 0), verts=32, bevel=0.02))
    for k in range(16):
        a = k / 16 * TAU
        hi.append(blob('sun_ray', (math.cos(a) * 1.05, -0.62, 6.55 + math.sin(a) * 1.05), (0.12, 0.05, 0.05), GD, rot=(0, -math.degrees(a), 0), seg=12, sub=1))
    decim = [(r'^pylon$', 0.008), (r'^pcornice$', 0.45), (r'^lintel$', 0.006), (r'^lcornice$', 0.45), (r'^pole$', 1.0), (r'^polecap$', 0.1),
             (r'^polering$', 0.6), (r'^flag$', 1.0), (r'^gsand$', 0.5), (r'^gjar$', 0.3), (r'^sun_disc$', 0.6), (r'^sun_ring$', 0.4),
             (r'^sun_core$', 0.6), (r'^sun_ray$', 0.4)]
    weights = [(r'^pylon$', 1.0), (r'^lintel$', 1.1), (r'^sun_', 1.4), (r'cornice', 0.7), (r'^flag$', 0.8), (r'sand', 0.3), (r'^pole', 0.5)]
    return hi, None, dict(decim=decim, weights=weights, tex=1024, budget=6000, ao_dist=0.6, ds_low=True)


BUILD = {'rn_block': build_block, 'rn_block2': build_block2, 'rn_low': build_low, 'rn_high': build_high, 'rn_scarab': build_scarab,
         'rn_scroll': build_scroll, 'rn_gate': build_gate}
