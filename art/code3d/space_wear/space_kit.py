# Uzay kıyafetleri ortak araçları (25 Ekim 2026, kullanıcı: "Okti'ye ayrıntılı, kodla 3 uzay kıyafeti": klasik astronot,
# roket pilotu, yıldız kaşifi). Tasarımlar özgün; konsept görseli yalnız yön (yapay zekâya yüklenmez, yüz kopyalanmaz).
#
# Gövde kıyafeti DERİ GİYSİ (art/meshy/scripts/base_wear.py yöntemi): her evrenin kendi vücut ağından giysi bölgesi kemik
# ağırlıkları + düz kesim düzlemleriyle kesilir (gövde + kol bileğe kadar + bacak bileğe kadar, eldiven ve bot ayrı kabuk),
# iç noktalar Taubin ile yumuşatılır (büzülmez), normal boyunca dışarı itilir (+ kabarık dilim/yastık yer değiştirmesi),
# vücuttan en az boşluk korunur, açıklıklara içe kıvrık kenar (Solidify yalnız kenar) verilir. Kemik ağırlıkları vücuttan
# gelir → oyunda vücudun kemiklerine bağlanır (CosmeticModels.BuildSkinWear), her harekette vücutla esner.
# Doku: ağın UV'si (akıllı açılım) üzerine numpy ile boyanır: her doku pikseli için 3B konum, normal ve "giysi koordinatları"
# (kol/bacak boyunca uzaklık, çevre açısı, gövde yüksekliği…) üçgen taramasıyla bulunur; dikiş, kapitone, şerit, cep,
# yama, biyeler bu koordinatlardan çizilir. Yükseklik haritası → teğet uzayı normal haritası (Unity/MikkTSpace, +Y),
# köşe başına oyuk gölgesi (AO, ışın) + dikiş oyuğu → renk × yumuşak AO. Ek parçalar (hortum, göğüs ünitesi, fular)
# evrenin gövdesine göre kurulur, en yakın gövde köşelerinin ağırlığını alır (oyundaki SkinToBody fikri) ve aynı dokuya boyanır.
# Ön = −Y, yukarı = +Z, Okti'nin solu = +X (Blender). Birim metre (evre modelleri ~1,65 m).
import os, sys, math, json, random
import bpy, bmesh
import numpy as np
from mathutils import Vector as V, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
RES = os.path.join(ROOT, 'Assets', '_Pofi', 'Resources')
CODE3D = os.path.normpath(os.path.join(HERE, '..'))
STAGES = ('yavru', 'genc', 'yetiskin')


def model_name(stage): return 'pet_13_' + stage
def stage_dir(stage): return os.path.join(RES, 'Pets', model_name(stage))
def short(n): return n.split(':')[-1]


def srgb2lin(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin2srgb(c):
    c = np.clip(np.asarray(c, np.float32), 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def hexc(h):
    """'#rrggbb' → sRGB üçlü (0..1)."""
    h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy.context.scene


def import_fbx(p):
    before = set(bpy.data.objects); bpy.ops.import_scene.fbx(filepath=p)
    return [o for o in bpy.data.objects if o not in before]


# ------------------------------------------------------------------ evre gövdesi: kemikler, bölgeler, uzuv eksenleri

CATS = ('head', 'torso', 'hips', 'armL', 'armR', 'handL', 'handR', 'legL', 'legR', 'footL', 'footR')
CI = {c: i for i, c in enumerate(CATS)}


def _bone_cat(b):
    n = short(b.name)
    if n in ('Head', 'HeadTop_End', 'headfront'): return 'head'
    if n == 'Hips': return 'hips'
    if n in ('Spine', 'Spine1', 'Spine2', 'Neck', 'LeftShoulder', 'RightShoulder'): return 'torso'
    for side, S in (('Left', 'L'), ('Right', 'R')):
        if n in (side + 'Arm', side + 'ForeArm'): return 'arm' + S
        if n == side + 'Hand': return 'hand' + S
        if n in (side + 'UpLeg', side + 'Leg'): return 'leg' + S
        if n in (side + 'Foot', side + 'ToeBase', side + 'Toe_End'): return 'foot' + S
    p = b.parent                      # Meshy dokunaç uç kemikleri (Bone_0xx): önkol/el altında → el
    while p is not None:
        c = _bone_cat(p)
        if c[:-1] in ('arm', 'hand'): return 'hand' + c[-1]
        if c[:-1] in ('leg', 'foot'): return 'foot' + c[-1]
        if c != 'torso': return c
        p = p.parent
    return 'torso'


def catmull(pts, per=12):
    """Uzuv zinciri için yumuşak çizgi (Catmull-Rom, uçlar uzatılmış)."""
    P = [pts[0] + (pts[0] - pts[1])] + list(pts) + [pts[-1] + (pts[-1] - pts[-2])]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(per):
            t = k / per; t2 = t * t; t3 = t2 * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(pts[-1].copy())
    return out


class Chain:
    """Uzuv ekseni (yumuşak çizgi). project(p) → (t metre, toplam boy, eksen noktası, yön, ön, dış)."""
    def __init__(self, pts, outward_x):
        self.pts = catmull(pts)
        self.cum = [0.0]
        for a, b in zip(self.pts, self.pts[1:]): self.cum.append(self.cum[-1] + (b - a).length)
        self.L = self.cum[-1]; self.sx = outward_x
        self.A = np.array([tuple(p) for p in self.pts], np.float64)

    def frame(self, d):
        f = V((0, -1, 0)); f = (f - d * d.dot(f)).normalized()
        o = d.cross(f)
        if o.x * self.sx < 0: o = -o
        return f, o

    def project_np(self, P):
        """P: (n,3) → t (n), foot (n,3), dir (n,3), dist (n)."""
        A = self.A[:-1]; B = self.A[1:]; S = B - A; L = np.linalg.norm(S, axis=1); D = S / L[:, None]
        best_d = np.full(len(P), 1e9); best_t = np.zeros(len(P)); foot = np.zeros((len(P), 3)); dirs = np.zeros((len(P), 3))
        cum = np.array(self.cum[:-1])
        for i in range(len(A)):
            u = np.clip(((P - A[i]) * D[i]).sum(1), 0, L[i])
            q = A[i] + u[:, None] * D[i]
            dist = np.linalg.norm(P - q, axis=1)
            m = dist < best_d
            best_d[m] = dist[m]; best_t[m] = cum[i] + u[m]; foot[m] = q[m]; dirs[m] = D[i]
        return best_t, foot, dirs, best_d

    def point(self, t):
        t = max(0.0, min(self.L, t))
        for i in range(len(self.pts) - 1):
            if self.cum[i + 1] >= t:
                k = (t - self.cum[i]) / max(1e-9, self.cum[i + 1] - self.cum[i])
                return self.pts[i].lerp(self.pts[i + 1], k), (self.pts[i + 1] - self.pts[i]).normalized()
        return self.pts[-1].copy(), (self.pts[-1] - self.pts[-2]).normalized()


class Body:
    """Bir evrenin dinlenme duruşundaki gövdesi (sahneye yükler)."""
    def __init__(self, stage):
        self.stage = stage; self.name = model_name(stage); self.dir = stage_dir(stage)
        objs = import_fbx(os.path.join(self.dir, self.name + '.fbx'))
        self.arm = next(o for o in objs if o.type == 'ARMATURE'); self.body = next(o for o in objs if o.type == 'MESH')
        self.objs = objs
        for pb in self.arm.pose.bones: pb.matrix_basis.identity()
        bpy.context.view_layer.update()
        mw = self.arm.matrix_world
        self.bones = {short(b.name): (mw @ b.head_local, mw @ b.tail_local) for b in self.arm.data.bones}
        self.bone_full = {short(b.name): b.name for b in self.arm.data.bones}
        bcat = {b.name: _bone_cat(b) for b in self.arm.data.bones}
        me = self.body.data; bw = self.body.matrix_world
        n = len(me.vertices)
        self.P = np.array([tuple(bw @ v.co) for v in me.vertices], np.float64)
        self.W = np.zeros((n, len(CATS)), np.float32)
        gname = {g.index: g.name for g in self.body.vertex_groups}
        for v in me.vertices:
            for g in v.groups:
                c = bcat.get(gname[g.group])
                if c: self.W[v.index, CI[c]] += g.weight
        s = self.W.sum(1, keepdims=True); s[s == 0] = 1; self.W /= s
        self.minz = self.P[:, 2].min(); self.maxz = self.P[:, 2].max(); self.H = self.maxz - self.minz
        head = self.P[self.W[:, CI['head']] > 0.5]
        front = head[(np.abs(head[:, 0]) < 0.08 * self.H) & (head[:, 1] < 0)]
        self.rim_z = float(front[:, 2].min()) if len(front) else float(head[:, 2].min())      # başın eteği (önde en alt)
        self.rim_z_min = float(head[:, 2].min())
        self.head_top = float(head[:, 2].max())
        # uzuv zincirleri
        self.arms = {}; self.legs = {}
        for side, S, sx in (('Left', 'L', 1), ('Right', 'R', -1)):
            a0 = self.bones[side + 'Arm'][0]; a1 = self.bones[side + 'ForeArm'][0]; a2 = self.bones[side + 'Hand'][0]
            m = (self.W[:, CI['arm' + S]] + self.W[:, CI['hand' + S]]) > 0.5
            d = (a2 - a1).normalized(); pr = (self.P[m] - np.array(a2)) @ np.array(d)
            tipm = pr > pr.max() - 0.012 * self.H
            tip = V(self.P[m][tipm].mean(0))
            self.arms[S] = Chain([a0, a1, a2, tip], sx)
            l0 = self.bones[side + 'UpLeg'][0]; l1 = self.bones[side + 'Leg'][0]; l2 = self.bones[side + 'Foot'][0]
            mf = self.W[:, CI['foot' + S]] > 0.5
            ft = self.P[mf]
            toe = V((ft[:, 0].mean(), ft[:, 1].min() + 0.25 * (ft[:, 1].max() - ft[:, 1].min()), self.minz + 0.02 * self.H)) if len(ft) else l2 - V((0, 0, 0.08))
            self.legs[S] = Chain([l0, l1, l2, toe], sx)
            # bacak zinciri: diz ve bilek t'si
        self.knee_t = {S: self.legs[S].project_np(np.array([tuple(self.bones[('Left' if S == 'L' else 'Right') + 'Leg'][0])]))[0][0] for S in 'LR'}
        self.ankle_t = {S: self.legs[S].project_np(np.array([tuple(self.bones[('Left' if S == 'L' else 'Right') + 'Foot'][0])]))[0][0] for S in 'LR'}
        self.hand_t = {S: self.arms[S].project_np(np.array([tuple(self.bones[('Left' if S == 'L' else 'Right') + 'Hand'][0])]))[0][0] for S in 'LR'}
        self.elbow_t = {S: self.arms[S].project_np(np.array([tuple(self.bones[('Left' if S == 'L' else 'Right') + 'ForeArm'][0])]))[0][0] for S in 'LR'}
        sp = [self.bones[n][0] for n in ('Hips', 'Spine', 'Spine1', 'Spine2', 'Neck')]
        self.spine = sp
        self.neck_z = self.bones['Neck'][0].z
        self.hips_z = self.bones['Hips'][0].z
        self.bvh = self.body_bvh()
        self._gcat = {g.index: bcat.get(g.name) for g in self.body.vertex_groups}
        self._kd = None; self._bm_dl = None

    def kd(self):
        if self._kd is None:
            self._kd = KDTree(len(self.P))
            for i, p in enumerate(self.P): self._kd.insert(V(p), i)
            self._kd.balance()
        return self._kd

    def body_bvh(self):
        dg = bpy.context.evaluated_depsgraph_get(); e = self.body.evaluated_get(dg); me = e.to_mesh()
        bm = bmesh.new(); bm.from_mesh(me); bm.transform(self.body.matrix_world); bm.normal_update()
        t = BVHTree.FromBMesh(bm); bm.free(); e.to_mesh_clear(); return t

    def spine_xy(self, z):
        """Gövde ekseninin bu yükseklikteki (x, y) noktası (omurga kemik başları arasında)."""
        sp = self.spine
        if z <= sp[0].z: return sp[0].x, sp[0].y
        for a, b in zip(sp, sp[1:]):
            if z <= b.z:
                k = (z - a.z) / max(1e-6, b.z - a.z); return a.x + (b.x - a.x) * k, a.y + (b.y - a.y) * k
        return sp[-1].x, sp[-1].y

    def report(self):
        return {'H': round(self.H, 3), 'rim_z': round(self.rim_z, 3), 'neck_z': round(self.neck_z, 3), 'hips_z': round(self.hips_z, 3),
                'arm_L': round(self.arms['L'].L, 3), 'leg_L': round(self.legs['L'].L, 3)}


# ------------------------------------------------------------------ bmesh yardımcıları (base_wear.py ile aynı fikir)

def _face_w(f, VW):
    return sum(VW[v.index] for v in f.verts) / len(f.verts)


def delete_faces(bm, faces):
    faces = [f for f in set(faces) if f.is_valid]
    if faces: bmesh.ops.delete(bm, geom=faces, context='FACES')


def bisect(bm, faces, co, no):
    faces = [f for f in faces if f.is_valid]
    if not faces: return
    geom = list({e for f in faces for e in f.edges}) + list({v for f in faces for v in f.verts}) + faces
    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-6, plane_co=co, plane_no=no)


def keep_big(bm, frac=0.03):
    faces = set(bm.faces); comps = []
    while faces:
        f0 = faces.pop(); comp = {f0}; stack = [f0]
        while stack:
            f = stack.pop()
            for e in f.edges:
                for g in e.link_faces:
                    if g in faces: faces.discard(g); comp.add(g); stack.append(g)
        comps.append(comp)
    big = max((len(c) for c in comps), default=0)
    for c in comps:     # vantuzlar ayrı küçük kabuklar (eldiven/bot parçasında %3'ten büyük kalıyordu): en büyüğe oranla
        if len(c) < frac * 10 * big: delete_faces(bm, c)


def vert_cats(bm, B):
    """bmesh köşeleri için bölge ağırlıkları (deform katmanından)."""
    dl = bm.verts.layers.deform.active
    gname = {g.index: g.name for g in B.body.vertex_groups}
    bcat = {b.name: _bone_cat(b) for b in B.arm.data.bones}
    out = {}
    for v in bm.verts:
        w = np.zeros(len(CATS), np.float32)
        for gi, x in v[dl].items():
            c = bcat.get(gname.get(gi, ''))
            if c: w[CI[c]] += x
        s = w.sum(); out[v] = w / s if s > 0 else w
    return out


def taubin(bm, verts, iters=6, lam=0.5, mu=-0.53):
    """Büzülmeyen yumuşatma (λ/μ): Meshy yüzey pürüzü ve vantuzlar düzleşir, ince dokunaç incelmez."""
    verts = [v for v in verts if v.is_valid]
    idx = {v: i for i, v in enumerate(verts)}
    nb = [[e.other_vert(v) for e in v.link_edges] for v in verts]
    for _ in range(iters):
        for k in (lam, mu):
            new = []
            for v, ns in zip(verts, nb):
                if not ns: new.append(v.co.copy()); continue
                c = sum((x.co for x in ns), V()) / len(ns)
                new.append(v.co + (c - v.co) * k)
            for v, c in zip(verts, new): v.co = c


def push_dirs(bm):
    bm.normal_update(); push = {}
    for v in bm.verts:
        if not v.is_boundary: push[v] = v.normal.copy()
    for v in bm.verts:
        if v.is_boundary:
            ns = [e.other_vert(v).normal for e in v.link_edges if not e.other_vert(v).is_boundary]
            n = sum(ns, V()) if ns else v.normal.copy()
            push[v] = n.normalized() if n.length > 1e-6 else v.normal.copy()
    return push


def smooth_ring(bm, iters=3):
    ring = [v for v in bm.verts if v.is_boundary]
    for _ in range(iters):
        new = {}
        for v in ring:
            nb = [e.other_vert(v) for e in v.link_edges if e.is_boundary]
            if len(nb) == 2: new[v] = v.co * 0.5 + (nb[0].co + nb[1].co) * 0.25
        for v, c in new.items(): v.co = c


GROUP5 = {'head': 5, 'torso': 0, 'hips': 0, 'armL': 1, 'handL': 1, 'armR': 2, 'handR': 2, 'legL': 3, 'footL': 3, 'legR': 4, 'footR': 4}


def group5(W):
    """11 bölge ağırlığı → 6 grup (gövde, sol kol, sağ kol, sol bacak, sağ bacak, baş). Baş eteği yakanın üstünde: örtüye katılmaz."""
    G = np.zeros((len(W), 6), np.float32)
    for c, g in GROUP5.items(): G[:, g] += W[:, CI[c]]
    return G


def blanket(bm, B, offs, R, lap_iters=15, reach=0.07):
    """Örtü itmesi (vantuzlar, 25 Ekim 2026): parça önce Laplace ile düzleştirilir (vantuz halkaları, çukurlar kaybolur),
    sonra her köşe düz yüzeyin normali boyunca, yanal R içindeki AYNI uzvun tüm vücut noktalarının üstüne çıkacak kadar
    (yanal uzaklıkla yumuşak azalan) + offs kadar itilir → kumaş çıkıntıların üstünden yumuşak bir örtü gibi geçer.
    Kol-gövde, bacak-bacak arası köprü kurmaz (yalnız aynı gruptaki vücut noktaları)."""
    vs = list(bm.verts); n = len(vs); idx = {v: i for i, v in enumerate(vs)}
    P = np.array([tuple(v.co) for v in vs]); bnd = np.array([v.is_boundary for v in vs])
    nb = [[idx[e.other_vert(v)] for e in v.link_edges] for v in vs]
    for _ in range(lap_iters):
        M = np.array([P[js].mean(0) if js else P[i] for i, js in enumerate(nb)])
        P[~bnd] += 0.5 * (M[~bnd] - P[~bnd])
    # düz yüzeyin köşe normalleri (alan ağırlıklı)
    N = np.zeros((n, 3))
    for f in bm.faces:
        ids = [idx[v] for v in f.verts]
        for k in range(1, len(ids) - 1):
            a, b, c = P[ids[0]], P[ids[k]], P[ids[k + 1]]; fn = np.cross(b - a, c - a)
            for j in (ids[0], ids[k], ids[k + 1]): N[j] += fn
    N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-12
    for i in np.nonzero(bnd)[0]:                      # kenarda: iç komşuların normali (base_wear gibi; kenar normali dağınık)
        js = [j for j in nb[i] if not bnd[j]]
        if js:
            m = N[js].mean(0); N[i] = m / (np.linalg.norm(m) + 1e-12)
    Gv = group5(np.array([vert_cats_one(v, B) for v in vs]))
    Gb = group5(B.W)
    kd = B.kd()
    h = np.zeros(n); Rq = R + reach * B.H
    for i in range(n):
        p = V(P[i]); nn = V(N[i]); best = 0.0
        for (co, j, d) in kd.find_range(p, Rq):
            if Gb[j][5] > 0.5 or np.minimum(Gv[i], Gb[j]).sum() < 0.3: continue
            r = co - p; hg = r.dot(nn)
            if hg <= 0: continue
            lat = (r - nn * hg).length
            if lat >= R: continue
            x = min(1.0, 2.0 * (1 - lat / R)); f = x * x * (3 - 2 * x)      # iç yarıda tam, dışa doğru yumuşak
            best = max(best, hg * (0.5 + 0.5 * f))
        h[i] = best
    # vantuz halkasının ortası çukur kalmasın: önce iki halka en büyük taşırma, sonra ortalama
    for _ in range(1): h = np.array([max([h[i]] + [h[j] for j in nb[i]]) for i in range(n)])
    for _ in range(4): h = np.array([(2 * h[i] + sum(h[j] for j in nb[i])) / (2 + len(nb[i])) for i in range(n)])
    out = P + N * (h + offs)[:, None]
    for i, v in enumerate(vs): v.co = V(out[i])
    return P, N


def vert_cats_one(v, B):
    w = np.zeros(len(CATS), np.float32)
    lay = B._bm_dl
    for gi, x in v[lay].items():
        c = B._gcat.get(gi)
        if c: w[CI[c]] += x
    s = w.sum(); return w / s if s > 0 else w


def clearance(bm, B, gap, iters=3, verts=None):
    """Her köşe vücut yüzeyinin en az gap dışında kalsın (en yakın yüz normaline göre)."""
    vs = verts if verts is not None else list(bm.verts)
    bm.normal_update(); moved = 0
    for _ in range(iters):
        for v in vs:
            loc, nor, _, d = B.bvh.find_nearest(v.co)
            if loc is None: continue
            s = (v.co - loc).dot(nor)
            if s < gap:
                n = v.normal if v.normal.length > 0.5 else nor
                if n.dot(nor) < 0.2: n = nor
                v.co += n * (gap - s) / max(0.3, n.dot(nor)); moved += 1
    return moved


# ------------------------------------------------------------------ giysi koordinatları (köşe başına; boyama + şekil için)

def garment_coords(B, P, faces_piece=None):
    """P: (n,3) dinlenme konumları → sözlük: gövde z/açı/yarıçap, her uzuv için t, çevre ön/dış bileşenleri, eksene uzaklık."""
    C = {'P': P}
    # gövde: dikey eksen omurga noktasından
    ax = np.array([B.spine_xy(z) for z in P[:, 2]])
    rx = P[:, 0] - ax[:, 0]; ry = P[:, 1] - ax[:, 1]; rr = np.sqrt(rx * rx + ry * ry) + 1e-9
    C['tz'] = P[:, 2]; C['ta'] = np.arctan2(rx, -ry)            # 0 önde, +π/2 Okti'nin solu (+X), ±π arkada
    C['tr'] = rr; C['tx'] = rx; C['ty'] = ry
    for kind, chains in (('arm', B.arms), ('leg', B.legs)):
        for S, ch in chains.items():
            t, foot, dirs, dist = ch.project_np(P)
            r = P - foot
            f = np.tile([0.0, -1.0, 0.0], (len(P), 1)); f = f - dirs * (dirs * f).sum(1, keepdims=True); f /= np.linalg.norm(f, axis=1, keepdims=True) + 1e-9
            o = np.cross(dirs, f); flip = (o[:, 0] * ch.sx) < 0; o[flip] *= -1
            rn = np.linalg.norm(r, axis=1) + 1e-9
            C[kind + S + '_t'] = t; C[kind + S + '_d'] = dist
            C[kind + S + '_cf'] = (r * f).sum(1) / rn; C[kind + S + '_co'] = (r * o).sum(1) / rn
            C[kind + S + '_up'] = (r[:, 2]) / rn
            C[kind + S + '_tn'] = t / ch.L
    return C


# ------------------------------------------------------------------ deri giysi kurma

class SuitSpec:
    """Kıyafetin biçim ayarları (boya oranları H'ye göre). disp(C, piece) → metre (köşe başına ek dışarı itme)."""
    def __init__(self, **kw):
        self.collar = 0.02            # yaka: Neck + collar × H
        self.glove_s = 0.66           # eldiven başlangıcı (kol zinciri oranı, 0 omuz → 1 uç)
        self.sleeve_into = 0.05       # kol eldivenin içine bu oran kadar uzar (boşluk kalmaz)
        self.boot_k = 0.4             # bot ağzı: bilekten dize oran
        self.leg_into = 0.025         # paça botun içine (× H)
        self.off_suit = 0.010; self.off_glove = 0.015; self.off_boot = 0.020; self.gap = 0.004
        self.thick = 0.0045           # kenar kıvrımı (× H)
        self.smooth = 8               # düzleştirme (Laplace) adımı: gövde; eldiven/bot smooth_end (vantuz bölgesi ayrıca zar)
        self.smooth_end = 10
        self.blanket_r = 0.018        # örtü yanal yarıçapı (× H)
        self.subdiv = 0               # 1: ağ bir kez bölünür (kabarık dilimler için), sonra bütçeye sadeleşir
        self.target = 0               # üçgen bütçesi (yalnız subdiv)
        self.gloves = True; self.boots = True
        self.disp = None              # disp(B, C, piece) → (n,) metre
        self.boot_shape = None        # boot_shape(B, bm, verts, C) → köşe konumlarına bot biçimi (taban, burun)
        self.__dict__.update(kw)


def _bm_from_body(B):
    me = B.body.data.copy(); bm = bmesh.new(); bm.from_mesh(me); bpy.data.meshes.remove(me)
    bm.transform(B.body.matrix_world)
    return bm


def _cut_piece(B, spec, piece, S=None):
    """piece: 'suit' | 'glove' | 'boot'. Dinlenme duruşunda vücut ağından bölge kesilir."""
    bm = _bm_from_body(B); H = B.H
    tag_suckers(bm, B)
    W = vert_cats(bm, B)
    ci = lambda *ks: (lambda v: sum(W[v][CI[k]] for k in ks))
    head = ci('head')
    delete_faces(bm, [f for f in bm.faces if sum(head(v) for v in f.verts) / len(f.verts) > 0.5])
    z_neck = B.neck_z + spec.collar * H
    bisect(bm, list(bm.faces), V((0, 0, z_neck)), V((0, 0, 1)))
    delete_faces(bm, [f for f in bm.faces if f.calc_center_median().z > z_neck])
    W = vert_cats(bm, B)
    def fw(f, *ks): return sum(sum(W[v][CI[k]] for k in ks) for v in f.verts) / len(f.verts)
    sides = 'LR'
    if piece == 'suit':
        for s in sides:
            ch = B.arms[s]
            if spec.gloves:
                tcut = ch.L * min(0.98, spec.glove_s + spec.sleeve_into)
                co, d = ch.point(tcut)
                faces = [f for f in bm.faces if fw(f, 'arm' + s, 'hand' + s) > 0.4]
                bisect(bm, faces, co, d)
                W = vert_cats(bm, B)
                delete_faces(bm, [f for f in bm.faces if fw(f, 'arm' + s, 'hand' + s) > 0.4 and (f.calc_center_median() - co).dot(d) > 0])
            if spec.boots:
                lz = _boot_z(B, spec, s) - spec.leg_into * H
                faces = [f for f in bm.faces if fw(f, 'leg' + s, 'foot' + s) > 0.4]
                bisect(bm, faces, V((0, 0, lz)), V((0, 0, -1)))
                W = vert_cats(bm, B)
                delete_faces(bm, [f for f in bm.faces if fw(f, 'leg' + s, 'foot' + s) > 0.4 and f.calc_center_median().z < lz])
    elif piece == 'glove':
        ch = B.arms[S]
        tcut = ch.L * spec.glove_s; co, d = ch.point(tcut)
        delete_faces(bm, [f for f in bm.faces if fw(f, 'arm' + S, 'hand' + S) < 0.4])
        bisect(bm, list(bm.faces), co, d)
        delete_faces(bm, [f for f in bm.faces if (f.calc_center_median() - co).dot(d) < 0])
    elif piece == 'boot':
        delete_faces(bm, [f for f in bm.faces if fw(f, 'leg' + S, 'foot' + S) < 0.4])
        bz = _boot_z(B, spec, S)
        bisect(bm, list(bm.faces), V((0, 0, bz)), V((0, 0, 1)))
        delete_faces(bm, [f for f in bm.faces if f.calc_center_median().z > bz])
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    keep_big(bm)
    # vantuz çukurlarındaki küçük delikler (vücut ağında açık): kapat, yoksa kenar köşeleri sabit kalıp çukur iz bırakıyor
    bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=12)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    return bm


def tag_suckers(bm, B):
    """Vantuz bölgesi yüzleri (vücut dokusunda mor/lila: ton 0,64–0,9, parlaklık > 0,45): 'suck' = 1."""
    import colorsys
    from PIL import Image
    if getattr(B, '_tex', None) is None:
        B._tex = np.asarray(Image.open(os.path.join(B.dir, B.name + '_basecolor.jpg')).convert('RGB'), np.float32) / 255
    img = B._tex; h, w, _ = img.shape
    uvl = bm.loops.layers.uv.active; lay = bm.faces.layers.int.get('suck') or bm.faces.layers.int.new('suck')
    for f in bm.faces:
        u = sum(l[uvl].uv[0] for l in f.loops) / len(f.loops); v = sum(l[uvl].uv[1] for l in f.loops) / len(f.loops)
        c = img[min(h - 1, max(0, int((1 - v) * h))), min(w - 1, max(0, int(u * w)))]
        hh, ss, vv = colorsys.rgb_to_hsv(*c)
        f[lay] = 1 if (0.64 < hh < 0.9 and vv > 0.45) else 0


def membrane(bm, rings=1, iters=160):
    """Vantuz bölgesini zar gibi ger: bölgedeki köşeler (1 halka genişletilmiş) çevredeki sabit köşeler arasında Laplace ile
    yeniden dağılır (Tutte gibi; katlanmış vantuz halkası düz, katlanmasız bir yamaya döner)."""
    lay = bm.faces.layers.int.get('suck')
    if lay is None: return 0
    free = {v for f in bm.faces if f[lay] for v in f.verts}
    for _ in range(rings): free |= {e.other_vert(v) for v in list(free) for e in v.link_edges}
    free = [v for v in free if not v.is_boundary]
    if not free: return 0
    nb = {v: [e.other_vert(v) for e in v.link_edges] for v in free}
    for _ in range(iters):
        new = {v: sum((x.co for x in ns), V()) / len(ns) for v, ns in nb.items() if ns}
        for v, c in new.items(): v.co = v.co.lerp(c, 0.8)
    return len(free)


def _boot_z(B, spec, S):
    side = 'Left' if S == 'L' else 'Right'
    a = B.bones[side + 'Foot'][0].z; k = B.bones[side + 'Leg'][0].z
    return a + spec.boot_k * (k - a)


def build_piece(B, spec, piece, S=None):
    H = B.H
    bm = _cut_piece(B, spec, piece, S)
    B._bm_dl = bm.verts.layers.deform.active
    if spec.subdiv:
        bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=1, use_grid_fill=True, smooth=0.0)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    off = {'suit': spec.off_suit, 'glove': spec.off_glove, 'boot': spec.off_boot}[piece] * H
    verts = list(bm.verts)
    # biçim için koordinatlar: düzleştirilmiş yüzeyden (blanket önce düzleştirir; burada kabaca ham konum yeter)
    P0 = np.array([tuple(v.co) for v in verts])
    C = garment_coords(B, P0)
    extra = spec.disp(B, C, piece, S) if spec.disp else np.zeros(len(verts))
    offs = off + extra + np.array([0.2 * off if v.is_boundary else 0.0 for v in verts])
    membrane(bm)
    blanket(bm, B, offs, spec.blanket_r * H, lap_iters=spec.smooth if piece == 'suit' else spec.smooth_end)
    if piece == 'boot' and spec.boot_shape: spec.boot_shape(B, bm, S)
    clearance(bm, B, spec.gap * H * 0.5, iters=2)
    smooth_ring(bm)
    bm.normal_update()
    lay = bm.faces.layers.int.get('piece') or bm.faces.layers.int.new('piece')
    code = {'suit': 0, 'glove': 1, 'boot': 2}[piece] + (0 if S in (None, 'L') else 10)
    for f in bm.faces: f[lay] = code
    return bm


def bm_to_object(bm, name, B):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    for g in B.body.vertex_groups:
        if g.name not in ob.vertex_groups: ob.vertex_groups.new(name=g.name)
    # bm deform katmanı grup dizinleri vücudunkiyle aynı sırada (vücut ağı kopyası)
    return ob


def join(objs, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1: bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active; ob.name = name; ob.data.name = name
    return ob


def apply_mods(ob):
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    for m in list(ob.modifiers):
        if m.type == 'ARMATURE': continue
        bpy.ops.object.modifier_apply(modifier=m.name)


def add_rim(ob, thick):
    """Açıklıklara içe dönük kenar (Solidify yalnız kenar): iç kabuk yok → üçgen bütçesi yarıda."""
    s = ob.modifiers.new('rim', 'SOLIDIFY'); s.thickness = thick; s.offset = -1.0; s.use_rim = True; s.use_rim_only = True
    s.use_even_offset = False; s.use_quality_normals = True
    apply_mods(ob)


def decimate(ob, target):
    cur = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    if target and cur > target:
        d = ob.modifiers.new('dec', 'DECIMATE'); d.ratio = target / cur; d.use_collapse_triangulate = True
        d.use_symmetry = False
        apply_mods(ob)


def tri_count(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def skin_like_nearest(obj, ref_obj, k=4, torso_only=False, B=None):
    """Ek parçaya (hortum, ünite, fular) referans ağın en yakın k köşesinin ağırlıklarını ver (uzaklığın karesiyle ters orantılı)."""
    rme = ref_obj.data
    names = [g.name for g in ref_obj.vertex_groups]
    for vg in list(obj.vertex_groups): obj.vertex_groups.remove(vg)
    groups = [obj.vertex_groups.new(name=n) for n in names]
    pts = []; wts = []
    leg = [any(x in short(n) for x in ('UpLeg', 'Leg', 'Foot', 'Toe')) for n in names]
    hips_i = next((i for i, n in enumerate(names) if short(n) == 'Hips'), None)
    torso_names = {'Hips', 'Spine', 'Spine1', 'Spine2', 'Neck', 'Head', 'LeftShoulder', 'RightShoulder'}
    for v in rme.vertices:
        w = {}
        for g in v.groups:
            gi = g.group
            if hips_i is not None and leg[gi]: gi = hips_i
            w[gi] = w.get(gi, 0.0) + g.weight
        if not w: continue
        if torso_only and short(names[max(w, key=w.get)]) not in torso_names: continue
        pts.append(ref_obj.matrix_world @ v.co); wts.append(w)
    kd = KDTree(len(pts))
    for i, p in enumerate(pts): kd.insert(p, i)
    kd.balance()
    mw = obj.matrix_world
    for v in obj.data.vertices:
        acc = {}
        for (_, idx, d) in kd.find_n(mw @ v.co, k):
            iw = 1.0 / (d * d + 1e-8)
            for gi, gw in wts[idx].items(): acc[gi] = acc.get(gi, 0.0) + gw * iw
        top = sorted(acc.items(), key=lambda kv: -kv[1])[:4]; tot = sum(x for _, x in top) or 1.0
        for gi, x in top: groups[gi].add([v.index], x / tot, 'REPLACE')


def surface_point(B, suit_bvh, z, ang, out=0.0):
    """Gövde ekseninden (z yüksekliğinde) ang yönüne ışın → giysi yüzeyi; out kadar dışarı."""
    cx, cy = B.spine_xy(z)
    d = V((math.sin(ang), -math.cos(ang), 0.0))
    o = V((cx, cy, z))
    loc, nor, _, _ = suit_bvh.ray_cast(o + d * 2.0, -d, 4.0)
    if loc is None: return o + d * 0.1, d
    return loc + nor * out, nor


def object_bvh(objs):
    bm = bmesh.new(); dg = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        e = o.evaluated_get(dg); me = e.to_mesh(); tmp = bmesh.new(); tmp.from_mesh(me); tmp.transform(o.matrix_world)
        m2 = bpy.data.meshes.new('tmp'); tmp.to_mesh(m2); tmp.free(); bm.from_mesh(m2); bpy.data.meshes.remove(m2); e.to_mesh_clear()
    bm.normal_update(); t = BVHTree.FromBMesh(bm); bm.free(); return t


# ------------------------------------------------------------------ UV + tarama + boyama

def smart_uv(ob, angle=62, margin=0.004):
    me = ob.data
    for l in list(me.uv_layers): me.uv_layers.remove(l)
    uv = me.uv_layers.new(name='UVMap'); me.uv_layers.active = uv
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(rotate=True, scale=True, margin_method='FRACTION', margin=margin)
    bpy.ops.object.mode_set(mode='OBJECT')


def raster(ob, size):
    """UV üçgen taraması → piksel başına üçgen no (−1 boş), ağırlıklar (3), üçgen köşe dizinleri."""
    me = ob.data; me.calc_loop_triangles()
    uvd = np.empty(len(me.loops) * 2, np.float32); me.uv_layers.active.data.foreach_get('uv', uvd); uvd = uvd.reshape(-1, 2)
    nt = len(me.loop_triangles)
    lt = np.empty(nt * 3, np.int32); me.loop_triangles.foreach_get('loops', lt); lt = lt.reshape(-1, 3)
    vt = np.empty(nt * 3, np.int32); me.loop_triangles.foreach_get('vertices', vt); vt = vt.reshape(-1, 3)
    pt = np.empty(nt, np.int32); me.loop_triangles.foreach_get('polygon_index', pt)
    tri = np.full((size, size), -1, np.int32); bary = np.zeros((size, size, 3), np.float32)
    UV = uvd[lt] * size - 0.5          # piksel merkezi koordinatı
    eps = 0.02
    for i in range(nt):
        a, b, c = UV[i]
        x0 = int(max(0, math.floor(min(a[0], b[0], c[0])))); x1 = int(min(size - 1, math.ceil(max(a[0], b[0], c[0]))))
        y0 = int(max(0, math.floor(min(a[1], b[1], c[1])))); y1 = int(min(size - 1, math.ceil(max(a[1], b[1], c[1]))))
        if x1 < x0 or y1 < y0: continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
        det = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(det) < 1e-12: continue
        w0 = ((b[1] - c[1]) * (xs - c[0]) + (c[0] - b[0]) * (ys - c[1])) / det
        w1 = ((c[1] - a[1]) * (xs - c[0]) + (a[0] - c[0]) * (ys - c[1])) / det
        w2 = 1 - w0 - w1
        m = (w0 >= -eps) & (w1 >= -eps) & (w2 >= -eps)
        if not m.any(): continue
        yy = ys[m]; xx = xs[m]
        tri[yy, xx] = i
        bw = np.stack([w0[m], w1[m], w2[m]], 1); bw = np.clip(bw, 0, None); bw /= bw.sum(1, keepdims=True)
        bary[yy, xx] = bw
    return tri, bary, vt, pt, uvd, lt


class Texels:
    """Dolu piksellerin verisi: 3B konum, normal, köşe nitelikleri (ağırlıkla), yüz nitelikleri, UV → 3B türev."""
    def __init__(self, ob, size, vattr, fattr):
        self.size = size
        tri, bary, vt, pt, uvd, lt = raster(ob, size)
        self.tri = tri; self.mask = tri >= 0
        ys, xs = np.nonzero(self.mask); self.ys, self.xs = ys, xs
        t = tri[ys, xs]; w = bary[ys, xs]; self.t = t; self.w = w
        vi = vt[t]; self.vi = vi
        me = ob.data
        co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
        no = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('normal', no); no = no.reshape(-1, 3)
        self.P = (co[vi] * w[..., None]).sum(1)
        n = (no[vi] * w[..., None]).sum(1); self.N = n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-9)
        self.a = {}
        for k, arr in vattr.items():
            arr = np.asarray(arr)
            if arr.ndim == 1: self.a[k] = (arr[vi] * w).sum(1)
            else: self.a[k] = (arr[vi] * w[..., None]).sum(1)
        self.f = {k: np.asarray(arr)[pt[t]] for k, arr in fattr.items()}
        # UV → 3B türev (üçgen başına): dP/du, dP/dv (metre / UV birimi)
        U = uvd[lt]; Pt = co[vt]
        e1 = Pt[:, 1] - Pt[:, 0]; e2 = Pt[:, 2] - Pt[:, 0]
        d1 = U[:, 1] - U[:, 0]; d2 = U[:, 2] - U[:, 0]
        det = d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]; det[np.abs(det) < 1e-12] = 1e-12
        dPu = (e1 * d2[:, 1:2] - e2 * d1[:, 1:2]) / det[:, None]
        dPv = (e2 * d1[:, 0:1] - e1 * d2[:, 0:1]) / det[:, None]
        self.dPu = dPu[t]; self.dPv = dPv[t]
        self.island = _islands(ob, len(lt), lt, uvd)[t]

    def img(self, vals, fill=0.0):
        """Piksel dizisinden görüntü (size, size[, k])."""
        vals = np.asarray(vals)
        sh = (self.size, self.size) + vals.shape[1:]
        im = np.full(sh, fill, np.float32); im[self.ys, self.xs] = vals; return im


def _islands(ob, nt, lt, uvd):
    """Üçgen başına UV adası no (UV'si eşleşen ortak kenar)."""
    me = ob.data
    vt = np.empty(nt * 3, np.int32); me.loop_triangles.foreach_get('vertices', vt); vt = vt.reshape(-1, 3)
    par = list(range(nt))
    def find(i):
        while par[i] != i: par[i] = par[par[i]]; i = par[i]
        return i
    edge = {}
    for i in range(nt):
        for k in range(3):
            a, b = vt[i, k], vt[i, (k + 1) % 3]; la, lb = lt[i, k], lt[i, (k + 1) % 3]
            key = (min(a, b), max(a, b))
            uva = tuple(np.round(uvd[la], 5)); uvb = tuple(np.round(uvd[lb], 5))
            ent = (uva, uvb) if a < b else (uvb, uva)
            if key in edge:
                j, e2 = edge[key]
                if e2 == ent:
                    ra, rb = find(i), find(j)
                    if ra != rb: par[ra] = rb
            else: edge[key] = (i, ent)
    return np.array([find(i) for i in range(nt)], np.int32)


def vertex_ao(ob, others, dist, rays=24, seed=1):
    """Köşe başına oyuk gölgesi: normal yarıküresinde ışın (kendisi + diğer nesneler)."""
    bvh = object_bvh([ob] + list(others))
    me = ob.data; R = random.Random(seed)
    dirs = []
    for i in range(rays):
        u = (i + 0.5) / rays; a = i * 2.39996323
        r = math.sqrt(u); dirs.append((r * math.cos(a), r * math.sin(a), math.sqrt(max(0.0, 1 - u))))
    out = np.ones(len(me.vertices), np.float32)
    mw = ob.matrix_world
    for v in me.vertices:
        n = (mw.to_3x3() @ v.normal).normalized(); p = mw @ v.co
        t = n.orthogonal().normalized(); b = n.cross(t); hit = 0
        o = p + n * 0.002
        for (x, y, z) in dirs:
            d = t * x + b * y + n * z
            loc, _, _, dd = bvh.ray_cast(o, d, dist)
            if loc is not None: hit += 1 - (dd / dist) ** 2 * 0.5
        out[v.index] = 1.0 - hit / rays
    # komşu ortalaması (yumuşak)
    nb = [[] for _ in me.vertices]
    for e in me.edges:
        a, b = e.vertices; nb[a].append(b); nb[b].append(a)
    for _ in range(2):
        out = np.array([(out[i] + sum(out[j] for j in nb[i])) / (1 + len(nb[i])) for i in range(len(out))], np.float32)
    return out


def dilate(im, mask, iters=12):
    out = im.copy(); valid = mask.copy()
    for _ in range(iters):
        if valid.all(): break
        acc = np.zeros_like(out); cnt = np.zeros(valid.shape, np.float32)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0: continue
                v = np.roll(np.roll(valid, dy, 0), dx, 1)
                acc += np.roll(np.roll(out, dy, 0), dx, 1) * (v[..., None] if out.ndim == 3 else v)
                cnt += v
        new = (~valid) & (cnt > 0)
        if out.ndim == 3: out[new] = acc[new] / cnt[new][:, None]
        else: out[new] = acc[new] / cnt[new]
        valid |= new
    return out


def blur(im, r=2):
    """Basit kutu bulanıklığı (ayrık, r yarıçap, 2 geçiş)."""
    out = im.astype(np.float32)
    for _ in range(2):
        for ax in (0, 1):
            acc = np.zeros_like(out)
            for k in range(-r, r + 1): acc += np.roll(out, k, ax)
            out = acc / (2 * r + 1)
    return out


def height_to_normal(T, h, strength=1.0):
    """Piksel yüksekliklerinden (metre) teğet uzayı normal (Unity: x = T, y = B = (n × T)·w, z = n)."""
    size = T.size
    Hm = T.img(h); M = T.mask; I = T.img(T.island.astype(np.float32), -1)
    def diff(ax):
        p = np.roll(Hm, -1, ax); m = np.roll(Hm, 1, ax)
        pv = np.roll(M, -1, ax) & (np.roll(I, -1, ax) == I); mv = np.roll(M, 1, ax) & (np.roll(I, 1, ax) == I)
        d = np.where(pv & mv, (p - m) * 0.5, np.where(pv, p - Hm, np.where(mv, Hm - m, 0.0)))
        return d
    dhu = diff(1)[T.ys, T.xs] * size        # yükseklik / UV birimi
    dhv = diff(0)[T.ys, T.xs] * size
    Pu, Pv, n = T.dPu.astype(np.float64), T.dPv.astype(np.float64), T.N.astype(np.float64)
    # yüzey gradyanı: J (JᵀJ)⁻¹ g
    a = (Pu * Pu).sum(1); b = (Pu * Pv).sum(1); c = (Pv * Pv).sum(1); det = a * c - b * b; det[np.abs(det) < 1e-20] = 1e-20
    gu = (c * dhu - b * dhv) / det; gv = (-b * dhu + a * dhv) / det
    grad = Pu * gu[:, None] + Pv * gv[:, None]
    grad -= n * (grad * n).sum(1, keepdims=True)
    nn = n - grad * strength; nn /= np.linalg.norm(nn, axis=1, keepdims=True) + 1e-12
    Tt = Pu - n * (Pu * n).sum(1, keepdims=True); Tt /= np.linalg.norm(Tt, axis=1, keepdims=True) + 1e-12
    Bt = np.cross(n, Tt); w = np.sign((Bt * Pv).sum(1)); w[w == 0] = 1; Bt *= w[:, None]
    out = np.stack([(nn * Tt).sum(1), (nn * Bt).sum(1), (nn * n).sum(1)], 1)
    return out


def save_maps(T, col_srgb, nrm, path_base, ao=None, ao_strength=0.55):
    """renk (sRGB 0..1) × yumuşak AO → <yol>_basecolor.png, normal → <yol>_normal.png (dolgu taşırmalı)."""
    from PIL import Image
    lin = srgb2lin(col_srgb)
    if ao is not None: lin = lin * (1.0 - ao_strength * (1.0 - ao[:, None]))
    cimg = T.img(lin2srgb(lin)); nimg = T.img(nrm * 0.5 + 0.5)
    cimg = dilate(cimg, T.mask, 16); nimg = dilate(nimg, T.mask, 16)
    empty = cimg.sum(-1) == 0
    nimg[empty] = (0.5, 0.5, 1.0)
    Image.fromarray((np.clip(cimg, 0, 1) * 255).astype(np.uint8)[::-1]).save(path_base + '_basecolor.png', optimize=True)
    Image.fromarray((np.clip(nimg, 0, 1) * 255).astype(np.uint8)[::-1]).save(path_base + '_normal.png', optimize=True)


# ------------------------------------------------------------------ desen yardımcıları (numpy, piksel dizileri)

def sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0 + 1e-12), 0, 1); return t * t * (3 - 2 * t)


def line_mask(d, w, soft):
    """|d| < w çizgisi (yumuşak kenar)."""
    return 1.0 - sstep(w, w + soft, np.abs(d))


def groove(d, w):
    """Dikiş oyuğu yükseklik profili: merkezde −1, w dışında 0 (yuvarlak)."""
    x = np.clip(np.abs(d) / w, 0, 1); return -(1 - x * x) ** 2


def puff(frac):
    """Kapitone dilim kabarıklığı: frac 0..1 (dilim içi) → 0 kenarda, 1 ortada (yumuşak)."""
    x = np.clip(frac, 0, 1); return np.sin(np.pi * x) ** 0.6


def dashes(s, period, duty=0.55):
    return (np.mod(s, period) / period < duty).astype(np.float32)


def star_sdf(x, y, r, inner=0.45, n=5, rot=0.0):
    """Yuvarlatılmış yıldız: < 0 içeride (yaklaşık uzaklık)."""
    a = np.arctan2(x, y) + rot; d = np.sqrt(x * x + y * y)
    k = np.pi / n; m = np.abs(np.mod(a, 2 * k) - k) / k          # 0 sivri uçta, 1 içte
    rr = r * (inner + (1 - inner) * (1 - m) ** 1.6)
    return d - rr


def mix(a, b, t):
    t = np.asarray(t, np.float32)
    if t.ndim == 1 and np.ndim(a) == 2: t = t[:, None]
    return a * (1 - t) + b * t


# ------------------------------------------------------------------ deri giysiyi dışa aktarma

def export_skin_fbx(path, arm, objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in [arm] + list(objs): o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, path_mode='RELATIVE', embed_textures=False,
                             apply_scale_options='FBX_SCALE_UNITS', axis_forward='-Z', axis_up='Y',
                             add_leaf_bones=False, bake_anim=False, object_types={'ARMATURE', 'MESH'}, use_tspace=True)


def export_static_fbx(path, ob):
    """Kemiksiz kopya (dükkân simgesi, RealAssets.HasItem): dinlenme duruşunda tek ağ."""
    me = ob.data.copy(); st = bpy.data.objects.new('model', me); bpy.context.scene.collection.objects.link(st)
    st.matrix_world = ob.matrix_world.copy()
    for vg in list(st.vertex_groups): st.vertex_groups.remove(vg)
    st.modifiers.clear()
    bpy.ops.object.select_all(action='DESELECT'); st.select_set(True); bpy.context.view_layer.objects.active = st
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y',
                             bake_space_transform=True, mesh_smooth_type='FACE', add_leaf_bones=False, use_tspace=True)
    bpy.data.objects.remove(st)
