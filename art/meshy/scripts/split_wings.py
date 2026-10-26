"""
Mavi (martı postacı, Env/res_mavi) kanat çırpabilsin (26 Ekim 2026): Meshy'nin tek parça, iskeletsiz modelini gövde + iki kanada ayırır.

  python3.11 -I art/meshy/scripts/split_wings.py -- <giriş.glb> <çıkış.fbx> [ayıklama_klasörü]
  (giriş: art/meshy/out/res3d_mavi_c/res3d_mavi_c.glb, çıkış: Assets/_Pofi/Resources/Env/res_mavi/res_mavi.fbx)

Çıktı hiyerarşisi: res_mavi (kök) → body, wing_l, wing_r. Dokular ve UV'ler aynı (res_mavi_basecolor.jpg / _normal.jpg, yeniden yazılmaz).
  - Kanat bölgesi: yandan bakışta kanadın (yuvarlak omuz + koyu uçlar) çevresini saran çokgen + yüzün o yandan açıkta olması
    (yan yöne ışın atılır) + renk (kayış, mektup, gaga dışarıda). En büyük parça kalır, içindeki küçük boşluklar kanada katılır.
  - Gövdedeki delik "iki halkalı" düzgün yüzeyle kapanır (biharmonik dolgu: çevredeki gövde eğimini sürdürür), kanadın altında
    kalacak kadar içeri itilir; rengi yakındaki gövde rengi (dokuda tek renkli bir nokta). Aynı yüzey ters çevrilip kanadın iç
    yüzü olur (kanat açılınca içi boş görünmez). Dinlenme duruşunda görünüş özgün modelle aynı.
  - Kanadın orijini omuz eklemi (kanat kenarının üst-ön noktası, biraz içeride): nesneyi ileri-geri ekseni etrafında döndürmek
    kanadı yana/yukarı açar.
Dışa aktarma prepare_asset.py ile aynı (ileri −Z, yukarı Y, FBX_SCALE_UNITS).
"""
import math
import os
import sys

import bpy
import bmesh  # bpy'den sonra (PyPI bpy)
import numpy as np
from mathutils import Vector as V
from mathutils.bvhtree import BVHTree

args = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT = os.path.abspath(args[0]), os.path.abspath(args[1])
DBG = args[2] if len(args) > 2 else None
NAME = os.path.splitext(os.path.basename(OUT))[0]
OUTDIR = os.path.dirname(OUT)

# Kanadın yandan görünüşü (Blender y = arka, z = yukarı; kuş −y'ye bakar). İki yan aynı çokgeni kullanır.
POLY = [(-0.68, 0.06), (-0.66, -0.12), (-0.60, -0.26), (-0.48, -0.36), (-0.30, -0.40), (-0.10, -0.40), (0.10, -0.36),
        (0.30, -0.31), (0.50, -0.26), (0.62, -0.22), (0.64, -0.16), (0.54, -0.10), (0.35, -0.02), (0.15, 0.07),
        (0.00, 0.14), (-0.15, 0.19), (-0.35, 0.21), (-0.55, 0.17), (-0.66, 0.12)]
XMIN = 0.18          # kanat yüzü bu yanal uzaklıktan dışarıda
MARGIN = 0.03        # kapak, kanat yüzünün en az bu kadar içinde (m, model birimi)
PIVOT_IN = 0.04      # omuz noktası kanat kenarından bu kadar içeride
GROW_STEPS = 8       # görünmeyen kanat kıvrımlarına büyüme adımı
GROW_YMAX = 0.62     # kuyruk (gri) kanada katılmasın

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
src = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
me = src.data

# --- dokular: depodaki jpg'ler (prepare_asset.py çıktısı) bağlanır; yeniden yazılmaz ---
tex = {}
for mat in me.materials:
    for n in mat.node_tree.nodes:
        if n.type != "TEX_IMAGE":
            continue
        role = None
        for l in n.outputs[0].links:
            if "base color" in l.to_socket.name.lower():
                role = "basecolor"
            if l.to_node.type == "NORMAL_MAP":
                role = "normal"
        if role:
            img = bpy.data.images.load(os.path.join(OUTDIR, f"{NAME}_{role}.jpg"))
            n.image = img
            tex[role] = img
base = tex["basecolor"]
W, H = base.size
PIX = np.array(base.pixels[:], dtype=np.float32).reshape(H, W, 4)[:, :, :3]

# --- ağ dizileri ---
nv, nf = len(me.vertices), len(me.polygons)
CO = np.zeros(nv * 3); me.vertices.foreach_get("co", CO); CO = CO.reshape(-1, 3)
FV = np.array([list(p.vertices) for p in me.polygons])          # Meshy: hep üçgen
assert FV.shape[1] == 3
LUV = np.zeros(len(me.loops) * 2); me.uv_layers[0].data.foreach_get("uv", LUV); LUV = LUV.reshape(-1, 2)
FL = np.array([list(p.loop_indices) for p in me.polygons])
FC = CO[FV].mean(1)
FN = np.cross(CO[FV[:, 1]] - CO[FV[:, 0]], CO[FV[:, 2]] - CO[FV[:, 0]])
FA = np.linalg.norm(FN, axis=1); FN = FN / np.maximum(FA, 1e-12)[:, None]


def sample(uv):
    x = np.clip((uv[..., 0] * W).astype(int), 0, W - 1)
    y = np.clip((uv[..., 1] * H).astype(int), 0, H - 1)
    return PIX[y, x]


FCOL = sample(LUV[FL].mean(1))

# UV dikişlerinde bölünmüş köşeler konumla birleştirilir (topoloji için)
_, first, WID = np.unique(np.round(CO / 1e-6).astype(np.int64), axis=0, return_index=True, return_inverse=True)
WID = WID.ravel()
P = CO[first]                       # kaynak köşe konumları
WF = WID[FV]                        # birleşik üçgenler
NW = len(P)
EDGE = {}
for f, (a, b, c) in enumerate(WF):
    for u, v in ((a, b), (b, c), (c, a)):
        EDGE.setdefault((min(u, v), max(u, v)), []).append(f)
FADJ = [[] for _ in range(nf)]
for fs in EDGE.values():
    for f in fs:
        FADJ[f].extend(g for g in fs if g != f)

bvh = BVHTree.FromPolygons([V(p) for p in CO], [list(f) for f in FV])


def in_poly(y, z):
    inside = np.zeros(len(y), bool)
    n = len(POLY)
    for i in range(n):
        y1, z1 = POLY[i]; y2, z2 = POLY[(i + 1) % n]
        hit = ((z1 > z) != (z2 > z)) & (y < (y2 - y1) * (z - z1) / (z2 - z1 + 1e-12) + y1)
        inside ^= hit
    return inside


def components(mask):
    seen = np.zeros(nf, bool); out = []
    for s in np.where(mask)[0]:
        if seen[s]:
            continue
        st = [s]; seen[s] = True; comp = []
        while st:
            f = st.pop(); comp.append(f)
            for g in FADJ[f]:
                if mask[g] and not seen[g]:
                    seen[g] = True; st.append(g)
        out.append(comp)
    return out


def select_wing(sg):
    """sg=+1: Blender +x yanı (kuşun solu, wing_l), −1: −x yanı (kuşun sağı, wing_r)."""
    cand = in_poly(FC[:, 1], FC[:, 2]) & (FC[:, 0] * sg > XMIN)
    r, g, b = FCOL[:, 0], FCOL[:, 1], FCOL[:, 2]
    cand &= ~((r - b) > 0.08)                     # kayış/çanta (kahve), mektup (krem), gaga/ayak (turuncu)
    # yandan açıkta mı: yüz merkezinden yan yöne ışın
    vis = np.zeros(nf, bool)
    d = V((sg, 0, 0))
    for f in np.where(cand)[0]:
        o = V(FC[f]) + d * 0.002
        hit = bvh.ray_cast(o, d, 2.0)
        vis[f] = hit[0] is None
    sel = cand & vis
    comps = sorted(components(sel), key=len, reverse=True)
    sel = np.zeros(nf, bool); sel[comps[0]] = True
    # yandan görünmeyen kanat kıvrımları (iç kenar, alt kenarın altı): kanat renginde (gri/koyu, gövde beyazından koyu) komşular
    bright = FCOL.mean(1)
    ok = (FC[:, 0] * sg > XMIN - 0.06) & (FC[:, 1] < GROW_YMAX) & (bright < 0.8) & ~((r - b) > 0.08)
    for _ in range(GROW_STEPS):
        add = [g for f in np.where(sel)[0] for g in FADJ[f] if not sel[g] and ok[g]]
        if not add:
            break
        sel[add] = True
    # kanadın içinde kalan seçilmemiş adacıklar (çanta arkası, ışının kaçırdığı kıvrım) kanada katılır
    for comp in components(~sel):
        if len(comp) < 0.25 * sel.sum() and all(FC[f, 0] * sg > XMIN - 0.05 for f in comp):
            touches_out = any(not sel[g] and g not in comp for f in comp for g in FADJ[f])
            if not touches_out:
                sel[comp] = True
    return sel


def boundary_verts(sel):
    bv = set()
    for (u, v), fs in EDGE.items():
        k = sum(sel[f] for f in fs)
        if 0 < k < len(fs):
            bv.add(u); bv.add(v)
    return bv


def vnormals(X, faces):
    fn = np.cross(X[faces[:, 1]] - X[faces[:, 0]], X[faces[:, 2]] - X[faces[:, 0]])
    N = np.zeros_like(X)
    for k in range(3):
        np.add.at(N, faces[:, k], fn)
    return N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)


NP = vnormals(P, WF)
NBR = [set() for _ in range(NW)]
for (u, v) in EDGE:
    NBR[u].add(v); NBR[v].add(u)


def cap_positions(sel):
    """Kanat yüzlerinin birleşik köşeleri için kapak konumları (sınır sabit)."""
    wv = np.unique(WF[sel])
    bv = boundary_verts(sel)
    U = np.array([v for v in wv if v not in bv])
    idx = {v: i for i, v in enumerate(U)}
    # tekdüze Laplace: L x = x − ortalama(komşular); biharmonik: L² x = 0 (bilinmeyenler U, gerisi sabit)
    ring = set(U)
    for v in U:
        ring |= NBR[v]
    ring2 = set(ring)
    for v in list(ring):
        ring2 |= NBR[v]
    R = np.array(sorted(ring)); ri = {v: i for i, v in enumerate(R)}
    A = np.array(sorted(ring2)); ai = {v: i for i, v in enumerate(A)}
    Lr = np.zeros((len(R), len(A)))
    for v in R:
        Lr[ri[v], ai[v]] = 1.0
        nb = NBR[v]
        for w in nb:
            Lr[ri[v], ai[w]] -= 1.0 / len(nb)
    Lu = Lr[[ri[v] for v in U]]          # U satırları, R sütunlarına göre aşağıda
    # L²[U, :] = L[U, R] · L[R, A]
    LuR = np.zeros((len(U), len(R)))
    for v in U:
        nb = NBR[v]
        LuR[idx[v], ri[v]] = 1.0
        for w in nb:
            LuR[idx[v], ri[w]] -= 1.0 / len(nb)
    L2 = LuR @ Lr                          # (U, A)
    ucols = [ai[v] for v in U]
    kmask = np.ones(len(A), bool); kmask[ucols] = False
    X = np.linalg.solve(L2[:, ucols], -L2[:, kmask] @ P[A[kmask]])
    C = P.copy(); C[U] = X
    # sınırdan uzaklık (adım): içe itme payı sınıra doğru sıfıra iner
    hop = {v: 0 for v in bv}
    front = list(bv)
    while front:
        nxt = []
        for v in front:
            for w in NBR[v]:
                if w in idx and w not in hop:
                    hop[w] = hop[v] + 1; nxt.append(w)
        front = nxt
    for it in range(6):
        for v in U:
            m = MARGIN * min(1.0, hop.get(v, 3) / 3.0)
            dd = np.dot(C[v] - P[v], NP[v])
            if dd > -m:
                C[v] -= (dd + m) * NP[v]
        if it < 5:  # hafif yumuşatma (sınır sabit)
            C2 = C.copy()
            for v in U:
                C2[v] = 0.5 * C[v] + 0.5 * np.mean([C[w] for w in NBR[v]], axis=0)
            C = C2
    return C, bv


def flat_uv(sel, want):
    """Dokuda kapağa uygun renkte, düzgün bir nokta: seçili bölgenin yakınındaki yüzlerden renk ortancası."""
    cols = FCOL[want]
    med = np.median(cols, axis=0)
    best, bd = None, 9
    nrm = np.array(tex["normal"].pixels[:], dtype=np.float32).reshape(tex["normal"].size[1], tex["normal"].size[0], 4)
    for f in np.where(want)[0]:
        uv = LUV[FL[f]].mean(0)
        c = sample(uv)
        x = int(uv[0] * (nrm.shape[1] - 1)); y = int(uv[1] * (nrm.shape[0] - 1))
        flat = np.abs(nrm[y, x, :3] - np.array([0.5, 0.5, 1.0])).sum()
        # çevresi aynı renkte mi (3×3 doku pikseli)
        px = int(uv[0] * (W - 1)); py = int(uv[1] * (H - 1))
        patch = PIX[max(0, py - 3):py + 4, max(0, px - 3):px + 4].reshape(-1, 3)
        score = np.abs(c - med).sum() + flat + 3 * patch.std(0).sum()
        if score < bd:
            bd, best = score, uv
    return best, med


SIDES = {"wing_l": 1, "wing_r": -1}
SEL, CAPS, PIV = {}, {}, {}
for name, sg in SIDES.items():
    sel = select_wing(sg)
    SEL[name] = sel
    C, bv = cap_positions(sel)
    # kapak renkleri: gövde = sınırın hemen dışındaki gövde yüzleri, kanat içi = kanat yüzleri
    ring_out = np.zeros(nf, bool)
    for f in np.where(sel)[0]:
        for g in FADJ[f]:
            if not sel[g]:
                ring_out[g] = True
    ring_out &= ~((FCOL[:, 0] - FCOL[:, 2]) > 0.08)
    body_uv, bc = flat_uv(sel, ring_out)
    wing_uv, wc = flat_uv(sel, sel)
    # omuz: sınırın üst-ön noktası (en yüksek z − 0,5·y), biraz içeride
    bvl = np.array(sorted(bv))
    s = P[bvl, 2] - 0.5 * P[bvl, 1]
    top = P[bvl[np.argmax(s)]].copy()
    top[0] -= sg * PIVOT_IN
    PIV[name] = top
    CAPS[name] = (C, body_uv, wing_uv)
    print(name, "yüz", int(sel.sum()), "sınır köşe", len(bv), "omuz", np.round(top, 4), "gövde rengi", np.round(bc, 3),
          "kanat rengi", np.round(wc, 3))


# --- nesneleri kur ---
def part(name, keep):
    ob = src.copy(); ob.data = src.data.copy(); ob.name = name; ob.data.name = name
    bpy.context.scene.collection.objects.link(ob)
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in range(nf) if not keep[i]], context="FACES")
    bm.to_mesh(ob.data); bm.free()
    return ob


def add_cap(ob, sel, C, uv, flip):
    """sel yüzlerinin birleşik topolojisiyle kapak ekler (C konumları), tek UV noktası."""
    faces = WF[sel]
    used = np.unique(faces)
    remap = {v: i for i, v in enumerate(used)}
    cm = bpy.data.meshes.new("cap")
    tris = [[remap[a], remap[b], remap[c]] if not flip else [remap[a], remap[c], remap[b]] for a, b, c in faces]
    cm.from_pydata([tuple(C[v]) for v in used], [], tris)
    cm.materials.append(ob.data.materials[0])
    uvl = cm.uv_layers.new(name=ob.data.uv_layers[0].name)
    uvl.data.foreach_set("uv", np.tile(uv, len(cm.loops)).astype(np.float32))
    for p in cm.polygons:
        p.use_smooth = True
    co = bpy.data.objects.new("cap", cm)
    bpy.context.scene.collection.objects.link(co)
    co.matrix_world = ob.matrix_world
    bpy.ops.object.select_all(action="DESELECT")
    co.select_set(True); ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.join()


wing_any = SEL["wing_l"] | SEL["wing_r"]
body = part("body", ~wing_any)
for name in SIDES:
    C, buv, wuv = CAPS[name]
    add_cap(body, SEL[name], C, buv, flip=False)
wings = {}
for name in SIDES:
    C, buv, wuv = CAPS[name]
    w = part(name, SEL[name])
    add_cap(w, SEL[name], C, wuv, flip=True)
    wings[name] = w

root = bpy.data.objects.new(NAME, None)
bpy.context.scene.collection.objects.link(root)
for ob in [body] + list(wings.values()):
    ob.parent = root
for name, w in wings.items():
    p = V(PIV[name])
    w.data.transform(__import__("mathutils").Matrix.Translation(-p))
    w.location = p
bpy.data.objects.remove(src, do_unlink=True)

if DBG:
    os.makedirs(DBG, exist_ok=True)
    np.save(os.path.join(DBG, "pivots.npy"), np.array([PIV["wing_l"], PIV["wing_r"]]))

bpy.ops.export_scene.fbx(filepath=OUT, use_selection=False, path_mode="RELATIVE", embed_textures=False,
                         apply_scale_options="FBX_SCALE_UNITS", axis_forward="-Z", axis_up="Y",
                         add_leaf_bones=False, bake_anim=False, object_types={"EMPTY", "MESH"})
print("YAZILDI", OUT, os.path.getsize(OUT))
