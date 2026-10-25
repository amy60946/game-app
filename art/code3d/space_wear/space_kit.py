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
        # başın eteği: gövde ekseni etrafında 16 yönde en alt baş noktası; en yükseği (yaka bunun üstünde kalmalı)
        hx = head[:, 0] - self.bones['Neck'][0].x; hy = head[:, 1] - self.bones['Neck'][0].y
        ha = np.arctan2(hx, -hy); bins = ((ha + np.pi) / (2 * np.pi) * 16).astype(int) % 16
        rb = np.array([float(head[bins == b, 2].min()) if (bins == b).any() else np.nan for b in range(16)])
        if np.isnan(rb).any(): rb[np.isnan(rb)] = np.nanmax(rb)
        for _ in range(2): rb = (np.roll(rb, 1) + 2 * rb + np.roll(rb, -1)) / 4
        self.rim_bottom = rb; self.rim_bottom_max = float(rb.max())

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
        # baş kabuğu (ayrı bileşen, baş ağırlığı baskın) köşeleri: örtü itmesine katılmaz (yaka başın eteğinin altına girer)
        par = list(range(n))
        def find(i):
            while par[i] != i: par[i] = par[par[i]]; i = par[i]
            return i
        for e in me.edges:
            a, b = find(e.vertices[0]), find(e.vertices[1])
            if a != b: par[a] = b
        root = np.array([find(i) for i in range(n)])
        self.head_shell = np.zeros(n, bool)
        for r in np.unique(root):
            m = root == r
            if self.W[m, CI['head']].mean() > 0.5: self.head_shell |= m
        self._gcat = {g.index: bcat.get(g.name) for g in self.body.vertex_groups}
        self._kd = None; self._bm_dl = None

    def rim_at(self, x, y):
        """Başın eteğinin bu yöndeki alt yüksekliği (16 yön, dairesel ara değer)."""
        a = math.atan2(x - self.bones['Neck'][0].x, -(y - self.bones['Neck'][0].y))
        u = (a + math.pi) / (2 * math.pi) * 16 - 0.5; i0 = int(math.floor(u)) % 16; k = u - math.floor(u)
        return float(self.rim_bottom[i0] * (1 - k) + self.rim_bottom[(i0 + 1) % 16] * k)

    def normals(self):
        if getattr(self, '_nb', None) is None:
            mw = self.body.matrix_world.to_3x3()
            self._nb = [(mw @ v.normal).normalized() for v in self.body.data.vertices]
        return self._nb

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


def blanket(bm, B, offs, R, lap_iters=15, reach=0.07, only=None):
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
    Gb = group5(B.W); hs = B.head_shell; Nb = B.normals()
    kd = B.kd()
    h = np.zeros(n); Rq = R + reach * B.H
    todo = range(n) if only is None else [i for i, v in enumerate(vs) if v in only]
    for i in todo:
        p = V(P[i]); nn = V(N[i]); best = 0.0
        for (co, j, d) in kd.find_range(p, Rq):
            if hs[j] or Gb[j][5] > 0.5: continue
            if np.minimum(Gv[i], Gb[j]).sum() < 0.3 and Nb[j].dot(nn) < 0.5: continue    # başka uzuv: yalnız aynı yöne bakıyorsa
            r = co - p; hg = r.dot(nn)
            if hg <= 0: continue
            lat = (r - nn * hg).length
            if lat >= R: continue
            x = min(1.0, 2.0 * (1 - lat / R)); f = x * x * (3 - 2 * x)      # iç yarıda tam, dışa doğru yumuşak
            best = max(best, hg * (0.5 + 0.5 * f))
        h[i] = best
    # vantuz halkasının ortası çukur kalmasın: önce iki halka en büyük taşırma, sonra ortalama
    # dar aralık (koltuk altı: kol ile gövde arası birkaç cm): iki yanın kumaşı birbirinin içine girmesin → itme aralığın %42'si
    gapcap = np.full(n, 1e9)
    for i in range(n):
        o = V(P[i]); d = V(N[i]); acc = 0.0
        for _ in range(4):                    # kendi yüzeyinden çıkış (normal aynı yöne) atlanır; karşı parçaya giriş aranır
            hit = B.bvh.ray_cast(o + d * 0.0005, d, 0.12 * B.H - acc)
            if hit[0] is None: break
            acc += hit[3] + 0.0005
            if hit[1].dot(d) < 0: gapcap[i] = 0.42 * acc; break
            o = hit[0]
    for _ in range(2): gapcap = np.array([min([gapcap[i]] + [gapcap[j] for j in nb[i]]) for i in range(n)])
    for _ in range(1): h = np.array([max([h[i]] + [h[j] for j in nb[i]]) for i in range(n)])
    for _ in range(4): h = np.array([(2 * h[i] + sum(h[j] for j in nb[i])) / (2 + len(nb[i])) for i in range(n)])
    tot = h + offs
    capped = np.minimum(tot, np.maximum(gapcap, 0.5 * offs))       # en az yarı kalınlık: kol kalkınca koltuk altında vücut görünmesin
    # yumuşat (kesik basamak olmasın)
    for _ in range(3): capped = np.array([(2 * capped[i] + sum(capped[j] for j in nb[i])) / (2 + len(nb[i])) for i in range(n)])
    capped = np.minimum(capped, tot)
    out = P + N * capped[:, None]
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

def garment_coords(B, P):
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
    """Kıyafetin biçim ayarları (oranlar H'ye göre). Gövde parçası vücut ağından (gövde + omuz + kalça + uyluk üstü); kollar,
    eldivenler, bacaklar ve botlar vücudun kesitlerinden örülen temiz tüpler (vantuzların üstünden geçer, katlanmaz).
    disp(B, C, piece, S) → köşe başına ek dışarı itme (metre); C = garment_coords."""
    def __init__(self, **kw):
        self.collar = 0.02            # yaka: baş eteğinin en yüksek alt noktası + collar × H
        self.glove_s = 0.66           # eldiven başlangıcı (kol zinciri oranı, 0 omuz → 1 uç)
        self.sleeve_into = 0.012      # kol eldivenin içine (× H)
        self.cuff = 0.03              # eldiven ağzı bu boyda biraz geniş (kolun ucunu örter, × H)
        self.boot_k = 0.4             # bot ağzı: bilekten dize oran
        self.leg_into = 0.03          # paça botun içine (× H)
        self.off_suit = 0.010; self.off_glove = 0.015; self.off_boot = 0.020; self.gap = 0.004
        self.thick = 0.0045           # kenar kıvrımı (× H)
        self.smooth = 4               # gövde parçası düzleştirme (Laplace; az: koltuk altı gibi dar kıvrımlarda katlanma yapıyordu)
        self.blanket_r = 0.018        # örtü yanal yarıçapı (× H)
        self.seg = 20                 # tüp çevre bölümü
        self.step = 0.011             # halka aralığı (× H)
        self.boot_seg = 28; self.boot_step = 0.010
        self.gloves = True; self.boots = True
        self.disp = None
        self.boot_profile = None      # boot_profile(B, S, zf) → ek yarıçap (zf 0 taban → 1 ağız)
        self.__dict__.update(kw)


def _bm_from_body(B):
    me = B.body.data.copy(); bm = bmesh.new(); bm.from_mesh(me); bpy.data.meshes.remove(me)
    bm.transform(B.body.matrix_world)
    return bm


def _cut_torso(B, spec):
    """Gövde parçası (tulum): baş ve yaka üstü silinir; kollar eldivenin, bacaklar botun içinde biter."""
    bm = _bm_from_body(B); H = B.H
    tag_suckers(bm, B)
    W = vert_cats(bm, B)
    # baş ayrı bir kabuk (prepare_stages yalnız başı yeniden örüyor): baş ağırlığı baskın bileşen tümüyle silinir
    faces = set(bm.faces)
    while faces:
        f0 = faces.pop(); comp = {f0}; st = [f0]
        while st:
            f = st.pop()
            for e in f.edges:
                for g in e.link_faces:
                    if g in faces: faces.discard(g); comp.add(g); st.append(g)
        hv = {v for f in comp for v in f.verts}
        if np.mean([W[v][CI['head']] for v in hv]) > 0.5: delete_faces(bm, comp)
    W = vert_cats(bm, B)
    delete_faces(bm, [f for f in bm.faces if sum(W[v][CI['head']] for v in f.verts) / len(f.verts) > 0.5])
    # yaka: her yönde başın eteğinin alt kenarının biraz üstünde (boyun görünmez; eteğin içindeki katlanmış alt yüzey alınmaz)
    z_neck = min(B.rim_bottom_max + spec.collar * H, B.bones['Head'][0].z - 0.005 * H)
    bisect(bm, list(bm.faces), V((0, 0, z_neck)), V((0, 0, 1)))
    delete_faces(bm, [f for f in bm.faces if f.calc_center_median().z > z_neck])
    def above(f, k=0.0):
        return any(v.co.z > B.rim_at(v.co.x, v.co.y) + (spec.collar + k) * H for v in f.verts)
    delete_faces(bm, [f for f in bm.faces if above(f)])
    bm.normal_update()
    # eteğin iç alt yüzeyi (aşağı bakan, yakaya yakın) katlanma yapıyor: alınmaz
    delete_faces(bm, [f for f in bm.faces if f.normal.z < -0.35 and above(f, -0.05)])
    for S in 'LR':
        # kol: eldivenin içine kadar (zincire dik düzlem), bacak: botun içine kadar (yatay düzlem). Kesim yalnız o uzvun yüzlerinde.
        ch = B.arms[S]
        tcut = ch.L * spec.glove_s + spec.sleeve_into * H if spec.gloves else ch.L + 1.0
        if tcut < ch.L:
            co, d = ch.point(tcut)
            W = vert_cats(bm, B); fw = lambda f: sum(W[v][CI['arm' + S]] + W[v][CI['hand' + S]] for v in f.verts) / len(f.verts)
            bisect(bm, [f for f in bm.faces if fw(f) > 0.4], co, d)
            W = vert_cats(bm, B)
            delete_faces(bm, [f for f in bm.faces if fw(f) > 0.4 and (f.calc_center_median() - co).dot(d) > 0])
        if spec.boots:
            lz = _boot_z(B, spec, S) - spec.leg_into * H
            W = vert_cats(bm, B); fw = lambda f: sum(W[v][CI['leg' + S]] + W[v][CI['foot' + S]] for v in f.verts) / len(f.verts)
            bisect(bm, [f for f in bm.faces if fw(f) > 0.4], V((0, 0, lz)), V((0, 0, -1)))
            W = vert_cats(bm, B)
            delete_faces(bm, [f for f in bm.faces if fw(f) > 0.4 and f.calc_center_median().z < lz])
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    keep_big(bm)
    bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=12)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    return bm


def build_torso(B, spec):
    H = B.H
    bm = _cut_torso(B, spec)
    B._bm_dl = bm.verts.layers.deform.active
    verts = list(bm.verts)
    P0 = np.array([tuple(v.co) for v in verts])
    C = garment_coords(B, P0)
    C['g5'] = group5(np.array([vert_cats_one(v, B) for v in verts]))
    extra = spec.disp(B, C, 'torso', None) if spec.disp else np.zeros(len(verts))
    offs = spec.off_suit * H + extra + np.array([0.2 * spec.off_suit * H if v.is_boundary else 0.0 for v in verts])
    zone = membrane(bm)
    # örtü itmesi yalnız vantuz bölgesi ve çevresinde (yetişkinin önkol/baldırı); başka yerde düz kalınlık (base_wear gibi).
    # Her yerde örtü, çocuğun koltuk altı ve omuzunda kolu gövdenin üstüne kaldırıp buruşturuyordu
    for _ in range(3): zone |= {e.other_vert(v) for v in list(zone) for e in v.link_edges}
    zone0 = set(zone)
    blanket(bm, B, offs, spec.blanket_r * H, lap_iters=spec.smooth, only=zone)
    # zarla gerilen köşeler yüzey boyunca kaydı: eski ağırlıkları yeni yerlerine uymuyor (diz bükülünce katlanıyordu) →
    # bulundukları yerin en yakın vücut köşelerinden (aynı uzuv) ağırlık al
    if zone0:
        g5 = group5(B.W); vg = {}
        for v in zone0:
            if v.is_valid: vg.setdefault(int(np.argmax(group5(vert_cats_one(v, B)[None])[0])), []).append(v)
        for gi, vs in vg.items():
            kd = _weights_kd(B, (g5[:, gi] > 0.5) & ~B.head_shell)
            assign_weights(bm, B, kd, verts=vs)
    clearance(bm, B, spec.gap * H * 0.5, iters=2)
    smooth_ring(bm, iters=8)
    bm.normal_update()
    lay = bm.faces.layers.int.get('piece') or bm.faces.layers.int.new('piece')
    for f in bm.faces: f[lay] = PIECE['torso']
    return bm


PIECE = {'torso': 0, 'sleeveL': 1, 'sleeveR': 2, 'gloveL': 3, 'gloveR': 4, 'legL': 5, 'legR': 6, 'bootL': 7, 'bootR': 8, 'extra': 9}


def hull2d(pts):
    """Andrew monotone zinciri: (n,2) → saat yönü tersine dışbükey çokgen."""
    P = sorted(set(map(tuple, np.round(pts, 6))))
    if len(P) < 3: return np.array(P)
    def cross(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo = []; hi = []
    for p in P:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(P):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0: hi.pop()
        hi.append(p)
    return np.array(lo[:-1] + hi[:-1])


def ray_poly(c, u, poly):
    """Dışbükey çokgende c'den u yönünde çıkış uzaklığı."""
    best = None
    n = len(poly)
    for i in range(n):
        a = poly[i]; b = poly[(i + 1) % n]; e = b - a
        den = u[0] * (-e[1]) - u[1] * (-e[0])
        if abs(den) < 1e-12: continue
        r = a - c
        s_ = (r[0] * (-e[1]) - r[1] * (-e[0])) / den
        w = (u[0] * r[1] - u[1] * r[0]) / den
        if s_ > 0 and -1e-6 <= w <= 1 + 1e-6:
            best = s_ if best is None else max(best, s_)
    return best if best is not None else 0.0


def _grid_smooth(R, it_t=2, it_a=2, maxf=True):
    """Halka × açı yarıçap ızgarası: önce komşu en büyük (çıkıntıyı örter), sonra ortalama. Açı ekseni dairesel."""
    R = R.copy()
    if maxf:
        P = np.pad(R, ((1, 1), (0, 0)), mode='edge'); M = R.copy()
        for dt in (0, 1, 2):
            row = P[dt:dt + len(R)]
            for da in (-1, 0, 1): M = np.maximum(M, np.roll(row, da, 1))
        R = M
    for _ in range(it_a): R = (np.roll(R, 1, 1) + 2 * R + np.roll(R, -1, 1)) / 4
    for _ in range(it_t):
        Q = R.copy(); Q[1:-1] = (R[:-2] + 2 * R[1:-1] + R[2:]) / 4; R = Q
    return R


def tag_suckers(bm, B):
    """Vantuz bölgesi yüzleri (vücut dokusunda mor/lila: ton 0,64–0,9, parlaklık > 0,45): 'suck' = 1."""
    import colorsys
    from PIL import Image
    if getattr(B, '_tex', None) is None:
        B._tex = np.asarray(Image.open(os.path.join(B.dir, B.name + '_basecolor.jpg')).convert('RGB'), np.float32) / 255
    img = B._tex; h, w, _ = img.shape
    uvl = bm.loops.layers.uv.active; lay = bm.faces.layers.int.get('suck') or bm.faces.layers.int.new('suck')
    W = vert_cats(bm, B)
    # yalnız dirsek/diz ötesindeki uzuv yüzleri (koltuk altı mor gölgesi vantuz sayılıp zara çekilince kol ile gövde arasında perde oluşuyordu)
    lim = {}
    for kind, chains, lim_t in (('arm', B.arms, B.elbow_t), ('leg', B.legs, B.knee_t)):
        for S, ch in chains.items():
            ks = (kind + S, ('hand' if kind == 'arm' else 'foot') + S)
            lim[(kind, S)] = (ch, ks, lim_t[S] * 0.9)
    for f in bm.faces:
        f[lay] = 0
        u = sum(l[uvl].uv[0] for l in f.loops) / len(f.loops); v = sum(l[uvl].uv[1] for l in f.loops) / len(f.loops)
        c = img[min(h - 1, max(0, int((1 - v) * h))), min(w - 1, max(0, int(u * w)))]
        hh, ss, vv = colorsys.rgb_to_hsv(*c)
        if not (0.64 < hh < 0.9 and vv > 0.45): continue
        for (ch, ks, tmin) in lim.values():
            wl = sum(W[x][CI[ks[0]]] + W[x][CI[ks[1]]] for x in f.verts) / len(f.verts)
            if wl > 0.7 and ch.project_np(np.array([tuple(f.calc_center_median())]))[0][0] > tmin:
                f[lay] = 1; break


def membrane(bm, rings=1, iters=160):
    """Vantuz bölgesini zar gibi ger: bölgedeki köşeler (1 halka genişletilmiş) çevredeki sabit köşeler arasında Laplace ile
    yeniden dağılır (katlanmış vantuz halkası düz, katlanmasız bir yamaya döner)."""
    lay = bm.faces.layers.int.get('suck')
    if lay is None: return set()
    free = {v for f in bm.faces if f[lay] for v in f.verts}
    for _ in range(rings): free |= {e.other_vert(v) for v in list(free) for e in v.link_edges}
    free = [v for v in free if not v.is_boundary]
    if not free: return set()
    nb = {v: [e.other_vert(v) for e in v.link_edges] for v in free}
    for _ in range(iters):
        new = {v: sum((x.co for x in ns), V()) / len(ns) for v, ns in nb.items() if ns}
        for v, c in new.items(): v.co = v.co.lerp(c, 0.8)
    return set(free)


def _boot_z(B, spec, S):
    side = 'Left' if S == 'L' else 'Right'
    a = B.bones[side + 'Foot'][0].z; k = B.bones[side + 'Leg'][0].z
    return a + spec.boot_k * (k - a)


def _limb_points(B, kind, S):
    ks = ('arm' + S, 'hand' + S) if kind == 'arm' else ('leg' + S, 'foot' + S)
    m = B.W[:, [CI[k] for k in ks]].sum(1) > 0.5
    return B.P[m]


def _weights_kd(B, mask=None):
    """Vücut köşelerinin kemik ağırlıkları (grup dizini → ağırlık) + KD ağacı (mask: yalnız bu köşeler)."""
    me = B.body.data
    if getattr(B, '_vw', None) is None:
        B._vw = [{g.group: g.weight for g in v.groups} for v in me.vertices]
    idx = np.nonzero(mask)[0] if mask is not None else np.arange(len(B.P))
    kd = KDTree(len(idx))
    for k, i in enumerate(idx): kd.insert(V(B.P[i]), int(i))
    kd.balance()
    return kd


def assign_weights(bm, B, kd, k=4, verts=None):
    dl = bm.verts.layers.deform.verify()
    for v in (verts if verts is not None else bm.verts):
        acc = {}
        for (_, i, d) in kd.find_n(v.co, k):
            iw = 1.0 / (d * d + 1e-8)
            for gi, w in B._vw[i].items(): acc[gi] = acc.get(gi, 0.0) + w * iw
        top = sorted(acc.items(), key=lambda kv: -kv[1])[:4]; tot = sum(x for _, x in top) or 1.0
        dv = v[dl]; dv.clear()
        for gi, x in top: dv[gi] = x / tot


def tube_piece(B, spec, S, kind, t0, t1, off, cap=False, piece=None):
    """Uzuv tüpü: t0 → t1 halkalar (zincire dik), her halkada yarıçap = o dilimdeki vücut noktalarının 2B dışbükey zarfı
    (vantuzlar dahil) + off (+ disp). cap: uçta yarım küre kapak (uç noktalarının 3B zarfına)."""
    H = B.H; ch = B.arms[S] if kind == 'arm' else B.legs[S]
    pts = _limb_points(B, kind, S)
    tp, foot, dirs, dist = ch.project_np(pts)
    nseg = spec.seg; step = spec.step * H
    n = max(3, int(round((t1 - t0) / step)) + 1)
    ts = np.linspace(t0, t1, n)
    slab = max(step * 1.5, 0.016 * H)
    ang = np.arange(nseg) / nseg * 2 * math.pi
    rings = []; R = np.zeros((n, nseg)); centers = []
    for i, t in enumerate(ts):
        c, d = ch.point(t); f, o = ch.frame(d)
        m = np.abs(tp - t) < slab
        if m.sum() < 14: m = np.abs(tp - t) < slab * 2.0
        q = pts[m] - np.array(c)
        q = q - np.outer(q @ np.array(d), np.array(d))
        xy = np.stack([q @ np.array(f), q @ np.array(o)], 1)
        hull = hull2d(xy) if len(xy) >= 3 else np.array([[0.01, 0], [0, 0.01], [-0.01, 0], [0, -0.01]])
        cc = np.zeros(2)
        if len(hull) >= 3 and not _inside(cc, hull): cc = hull.mean(0)
        for k, a in enumerate(ang):
            R[i, k] = ray_poly(cc, np.array([math.cos(a), math.sin(a)]), hull)
        centers.append((c + f * cc[0] + o * cc[1], d, f, o))
    R = _grid_smooth(R)
    # kapak: uç noktalarının 3B zarfı, yarım küre doğrultuları
    cap_rows = []
    if cap:
        tip = pts[tp > ts[-1] - 2 * step]
        hb = bmesh.new()
        for p in tip: hb.verts.new(V(p))
        bmesh.ops.convex_hull(hb, input=list(hb.verts)); hb.normal_update()
        hbvh = BVHTree.FromBMesh(hb); hb.free()
        c, d, f, o = centers[-1]
        nphi = 4
        for j in range(1, nphi + 1):
            phi = j / (nphi + 0.0) * math.pi / 2
            row = []
            for k, a in enumerate(ang):
                u = (f * math.cos(a) + o * math.sin(a)) * math.cos(phi) + d * math.sin(phi)
                hit = hbvh.ray_cast(c, u, 2.0)
                r = (hit[0] - c).length if hit[0] is not None else R[-1, k] * math.cos(phi)
                row.append((u, max(r, 0.004 * H)))
            cap_rows.append(row)
    # köşe konumları + ek yer değiştirme
    bm = bmesh.new(); grid = []
    allP = []
    for i in range(n):
        c, d, f, o = centers[i]
        for k, a in enumerate(ang):
            u = f * math.cos(a) + o * math.sin(a); allP.append(c + u * R[i, k])
    for row in cap_rows:
        for (u, r) in row: allP.append(centers[-1][0] + u * r)
    P = np.array([tuple(p) for p in allP])
    C = garment_coords(B, P)
    extra = spec.disp(B, C, piece, S) if spec.disp else np.zeros(len(P))
    if piece and piece.startswith('glove'):          # eldiven ağzı: kolun ucunun üstüne genişçe otursun
        tt = C['arm' + S + '_t']
        extra = extra + 0.006 * H * np.clip(1 - (tt - t0) / (spec.cuff * H), 0, 1) ** 0.7
    idx = 0
    for i in range(n):
        c, d, f, o = centers[i]; row = []
        for k, a in enumerate(ang):
            u = f * math.cos(a) + o * math.sin(a)
            row.append(bm.verts.new(c + u * (R[i, k] + off + extra[idx]))); idx += 1
        grid.append(row)
    for row in cap_rows:
        r2 = []
        for (u, r) in row:
            r2.append(bm.verts.new(centers[-1][0] + u * (r + off + extra[idx]))); idx += 1
        grid.append(r2)
    for i in range(len(grid) - 1):
        A_, B_ = grid[i], grid[i + 1]
        for k in range(nseg):
            k2 = (k + 1) % nseg
            bm.faces.new((A_[k], A_[k2], B_[k2], B_[k]))
    if cap:
        pole = bm.verts.new(centers[-1][0] + centers[-1][1] * 0.0)
        # kutup: son kapak halkasının ortalaması biraz ileride
        last = grid[-1]
        pc = sum((v.co for v in last), V()) / len(last)
        pole.co = pc + centers[-1][1] * (0.15 * (sum(((v.co - pc).length for v in last)) / len(last)))
        for k in range(nseg):
            bm.faces.new((last[k], last[(k + 1) % nseg], pole))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    # yüzler dışa baksın (ilk halkadan eksene göre)
    bm.normal_update()
    c0 = centers[len(centers) // 2][0]
    out_votes = sum(1 if (f.calc_center_median() - _axis_near(centers, f.calc_center_median())).dot(f.normal) > 0 else -1 for f in bm.faces)
    if out_votes < 0: bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    lay = bm.faces.layers.int.new('piece')
    for fc in bm.faces: fc[lay] = PIECE[piece]
    return bm


def _axis_near(centers, p):
    best = min(centers, key=lambda c: (c[0] - p).length); return best[0]


def _inside(c, poly):
    n = len(poly)
    for i in range(n):
        a = poly[i]; b = poly[(i + 1) % n]
        if (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) < 0: return False
    return True


def boot_piece(B, spec, S, off):
    """Bot: ağızdan tabana yatay dilimler; her dilim bacak/ayak noktalarının 2B dışbükey zarfı (vantuzlar, bilek boşluğu dahil)
    + off; dilim merkezleri yumuşatılır; altta düz taban."""
    H = B.H
    pts = _limb_points(B, 'leg', S)
    ztop = _boot_z(B, spec, S); zb = B.minz
    nseg = spec.boot_seg; step = spec.boot_step * H
    n = max(4, int(round((ztop - zb) / step)) + 1)
    zs = np.linspace(ztop, zb + 0.002 * H, n)
    ang = np.arange(nseg) / nseg * 2 * math.pi
    dz = max(step * 1.4, 0.014 * H)
    hulls = []; cents = []
    for z in zs:
        m = np.abs(pts[:, 2] - z) < dz
        if m.sum() < 14: m = np.abs(pts[:, 2] - z) < dz * 2.0
        xy = pts[m][:, :2]
        hl = hull2d(xy); hulls.append(hl); cents.append(hl.mean(0))
    cents = np.array(cents)
    for _ in range(3): cents[1:-1] = (cents[:-2] + 2 * cents[1:-1] + cents[2:]) / 4
    R = np.zeros((n, nseg))
    for i in range(n):
        cc = cents[i] if _inside(cents[i], hulls[i]) else hulls[i].mean(0)
        cents[i] = cc
        for k, a in enumerate(ang):
            R[i, k] = ray_poly(cc, np.array([math.sin(a), -math.cos(a)]), hulls[i])
    R = _grid_smooth(R, it_t=2, it_a=2)
    P = []
    for i in range(n):
        for k, a in enumerate(ang):
            P.append((cents[i][0] + math.sin(a) * R[i, k], cents[i][1] - math.cos(a) * R[i, k], zs[i]))
    P = np.array(P)
    C = garment_coords(B, P)
    extra = spec.disp(B, C, 'boot' + S, S) if spec.disp else np.zeros(len(P))
    bm = bmesh.new(); grid = []; idx = 0
    for i in range(n):
        zf = (zs[i] - zb) / max(1e-6, ztop - zb)
        add = spec.boot_profile(B, S, zf) * H if spec.boot_profile else 0.0
        row = []
        for k, a in enumerate(ang):
            r = R[i, k] + off + add + extra[idx]; idx += 1
            row.append(bm.verts.new((cents[i][0] + math.sin(a) * r, cents[i][1] - math.cos(a) * r, zs[i] if i < n - 1 else zb - 0.004 * H)))
        grid.append(row)
    for i in range(n - 1):
        A_, B_ = grid[i], grid[i + 1]
        for k in range(nseg):
            k2 = (k + 1) % nseg; bm.faces.new((A_[k], A_[k2], B_[k2], B_[k]))
    # taban: iç halka + merkez
    last = grid[-1]; cz = zb - 0.004 * H
    inner = [bm.verts.new((cents[-1][0] + (v.co.x - cents[-1][0]) * 0.8, cents[-1][1] + (v.co.y - cents[-1][1]) * 0.8, cz)) for v in last]
    for k in range(nseg):
        k2 = (k + 1) % nseg; bm.faces.new((last[k], last[k2], inner[k2], inner[k]))
    ctr = bm.verts.new((cents[-1][0], cents[-1][1], cz))
    for k in range(nseg): bm.faces.new((inner[k], inner[(k + 1) % nseg], ctr))
    bm.normal_update()
    ctr3 = V((cents[len(cents) // 2][0], cents[len(cents) // 2][1], (ztop + zb) / 2))
    if sum(1 if (f.calc_center_median() - ctr3).dot(f.normal) > 0 else -1 for f in bm.faces) < 0:
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    lay = bm.faces.layers.int.new('piece')
    for fc in bm.faces: fc[lay] = PIECE['boot' + S]
    return bm


def build_suit(B, spec, name):
    """Tulum (vücut ağından) + eldivenler (uç tüpü) + botlar (dilim) → tek nesne (vücut grupları + ağırlıklar)."""
    H = B.H; parts = []
    bm = build_torso(B, spec); parts.append(bm_to_object(bm, 'torso', B))
    g5 = group5(B.W)
    for S in 'LR':
        ch = B.arms[S]
        limb_arm = g5[:, 1 if S == 'L' else 2] > 0.5; limb_leg = g5[:, 3 if S == 'L' else 4] > 0.5
        if spec.gloves:
            kd_arm = _weights_kd(B, limb_arm)
            bm = tube_piece(B, spec, S, 'arm', ch.L * spec.glove_s, ch.L - 0.045 * H, spec.off_glove * H, cap=True, piece='glove' + S)
            assign_weights(bm, B, kd_arm); clearance(bm, B, spec.gap * H, iters=2); parts.append(bm_to_object(bm, 'glove' + S, B))
        if spec.boots:
            kd_leg = _weights_kd(B, limb_leg)
            bm = boot_piece(B, spec, S, spec.off_boot * H)
            assign_weights(bm, B, kd_leg); clearance(bm, B, spec.gap * H, iters=2); parts.append(bm_to_object(bm, 'boot' + S, B))
    ob = join(parts, name)
    return ob


def bm_to_object(bm, name, B):
    for f in bm.faces: f.smooth = True
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


# ------------------------------------------------------------------ doku boyama yardımcıları (piksel konumundan)

def _hash3(ix, iy, iz, seed):
    h = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (seed * 2654435761)
    h = (h ^ (h >> 13)) * 1274126177
    return ((h ^ (h >> 16)) & 0xFFFFFF).astype(np.float32) / float(0xFFFFFF)


def vnoise(P, scale, seed=0):
    """Vektörel 3B değer gürültüsü (0..1)."""
    X = np.asarray(P, np.float64) * scale
    i = np.floor(X).astype(np.int64); f = (X - i).astype(np.float32); u = f * f * (3 - 2 * f)
    out = np.zeros(len(X), np.float32)
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (u[:, 0] if dx else 1 - u[:, 0]) * (u[:, 1] if dy else 1 - u[:, 1]) * (u[:, 2] if dz else 1 - u[:, 2])
                out += w * _hash3(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz, seed)
    return out


def fbm(P, scale, oct=4, seed=0):
    a = 0.5; s = scale; out = np.zeros(len(P), np.float32); tot = 0
    for k in range(oct):
        out += a * vnoise(P, s, seed + k * 17); tot += a; a *= 0.5; s *= 2.03
    return out / tot


class Paint:
    """Bir giysinin piksel verisi + desen araçları. col: sRGB (n,3), h: yükseklik (metre, n)."""
    def __init__(self, B, T, ob):
        self.B = B; self.T = T; self.P = T.P.astype(np.float64); self.N = T.N; self.n = len(T.P); H = B.H; self.H = H
        self.piece = T.f['piece']
        self.col = np.ones((self.n, 3), np.float32) * 0.8; self.h = np.zeros(self.n, np.float32)
        self.ao = T.a.get('ao', np.ones(self.n))
        g = T.a.get('g5')
        dom = np.argmax(g, 1) if g is not None else np.zeros(self.n, int)
        # bölge: 0 gövde, 1/2 kol L/R, 3/4 bacak L/R, 5 eldiven L, 6 eldiven R, 7/8 bot L/R, 9 ek parça
        reg = np.where(dom == 5, 0, dom)
        pc = self.piece
        reg = np.where(pc == PIECE['gloveL'], 5, np.where(pc == PIECE['gloveR'], 6, reg))
        reg = np.where(pc == PIECE['bootL'], 7, np.where(pc == PIECE['bootR'], 8, reg))
        reg = np.where(pc >= PIECE['extra'], 9, reg)
        self.reg = reg
        # gövde koordinatları
        ax = np.array([B.spine_xy(z) for z in np.linspace(B.minz, B.maxz, 200)])
        zi = np.clip(((self.P[:, 2] - B.minz) / (B.maxz - B.minz) * 199).astype(int), 0, 199)
        rx = self.P[:, 0] - ax[zi, 0]; ry = self.P[:, 1] - ax[zi, 1]
        self.ta = np.arctan2(rx, -ry); self.tr = np.sqrt(rx * rx + ry * ry); self.tz = self.P[:, 2]
        self.lim = {}
        for kind, chains in (('arm', B.arms), ('leg', B.legs)):
            for S, ch in chains.items():
                t, foot, dirs, dist = ch.project_np(self.P)
                r = self.P - foot
                f = np.tile([0.0, -1.0, 0.0], (self.n, 1)); f -= dirs * (dirs * f).sum(1, keepdims=True); f /= np.linalg.norm(f, axis=1, keepdims=True) + 1e-9
                o = np.cross(dirs, f); o[(o[:, 0] * ch.sx) < 0] *= -1
                a = np.arctan2((r * o).sum(1), (r * f).sum(1))        # 0 önde, +π/2 dışta, ±π arkada, −π/2 içte
                self.lim[kind + S] = dict(t=t, a=a, r=dist, L=ch.L, ch=ch)

    # --- bölge maskeleri
    def m_reg(self, *rs): return np.isin(self.reg, rs).astype(np.float32)

    def limb_of(self, kind, S):
        """Bu uzuvdaki pikseller (gövde parçasındaki kol/bacak + eldiven/bot)."""
        if kind == 'arm': return self.m_reg(1 if S == 'L' else 2, 5 if S == 'L' else 6)
        return self.m_reg(3 if S == 'L' else 4, 7 if S == 'L' else 8)

    # --- yüzey noktası ve çıkartma (yama) koordinatı
    def decal(self, c, n, up=(0, 0, 1), reach=None):
        """c merkezli, n yönlü teğet düzlemde (x, y) koordinatı + bu yüzde mi maskesi."""
        c = np.asarray(c, np.float64); n = np.asarray(n, np.float64); n /= np.linalg.norm(n)
        u = np.asarray(up, np.float64); u = u - n * (u @ n); u /= np.linalg.norm(u) + 1e-9
        x_ = np.cross(u, n)
        d = self.P - c
        X = d @ x_; Y = d @ u; Z = d @ n
        m = (self.N @ n > 0.25) & (np.abs(Z) < (reach or 0.06 * self.H))
        return X, Y, m.astype(np.float32)

    # --- boyama
    def fill(self, mask, hexcol, k=1.0):
        c = hexc(hexcol) if isinstance(hexcol, str) else np.asarray(hexcol, np.float32)
        m = np.clip(np.asarray(mask, np.float32) * k, 0, 1)[:, None]
        self.col = self.col * (1 - m) + c[None, :] * m

    def fill_arr(self, mask, cols):
        m = np.clip(np.asarray(mask, np.float32), 0, 1)[:, None]
        self.col = self.col * (1 - m) + cols * m

    def shade(self, mask, k):
        """Rengi k ile çarp (k<1 koyulaşır) — maske oranında."""
        m = np.clip(np.asarray(mask, np.float32), 0, 1)[:, None]
        self.col = self.col * (1 - m) + self.col * k * m

    def bump(self, amount):
        self.h += np.asarray(amount, np.float32)

    def fabric(self, scale=1.0, amt=0.05, seed=3):
        """Kumaş: geniş ton dalgası + ince dokuma gürültüsü (renk ve yükseklik)."""
        w = fbm(self.P, 9 / self.H * scale, 3, seed) - 0.5
        f = vnoise(self.P, 260 / self.H * scale, seed + 5) - 0.5
        self.col = np.clip(self.col * (1 + (w * 0.10 + f * 0.05)[:, None] * amt / 0.05), 0, 1)
        self.h += (f * 0.00025 * self.H).astype(np.float32)

    def wear(self, amt=0.06, seed=9):
        """Hafif eskime: geniş açık/soluk lekeler + kenar/dip kiri (AO'yla)."""
        n1 = fbm(self.P, 5 / self.H, 4, seed)
        self.col = np.clip(self.col * (1 + ((n1 - 0.5) * amt)[:, None]), 0, 1)
        dirt = sstep(0.55, 0.85, 1 - self.ao) * amt * 2
        self.col = self.col * (1 - dirt[:, None] * 0.35)

    def stitches(self, d, offset, width=None, period=None, depth=None, col='#ffffff', alpha=0.7, along=None):
        """d: işaretli uzaklık alanı (metre, dikiş çizgisinden). Çizginin offset kadar yanında kesik dikiş (along: çizgi boyunca metre)."""
        H = self.H; width = width or 0.0016 * H; period = period or 0.012 * H; depth = depth or 0.0004 * H
        m = line_mask(d - offset, width, width * 0.6)
        if along is not None: m = m * dashes(along, period, 0.6)
        self.fill(m * alpha, col)
        self.h -= m * depth

    def seam(self, d, width=None, depth=None, dark=0.78):
        """Dikiş oyuğu (koyu, girintili) d = 0'da."""
        H = self.H; width = width or 0.003 * H; depth = depth or 0.0018 * H
        g = groove(d, width)
        self.h += g * depth
        self.shade(-g, dark)


def surf_point(B, bvh, kind, S=None, t=None, a=0.0, z=None, out=0.0):
    """Giysi yüzeyinde nokta + normal. kind 'torso': z yüksekliği, a açısı (0 ön, +π/2 sol/+X). 'arm'/'leg': t (m), a (0 ön, +π/2 dış)."""
    if kind == 'torso':
        cx, cy = B.spine_xy(z); o = V((cx, cy, z)); d = V((math.sin(a), -math.cos(a), 0.0))
    else:
        ch = (B.arms if kind == 'arm' else B.legs)[S]; c, dd = ch.point(t); f, oo = ch.frame(dd)
        o = c; d = f * math.cos(a) + oo * math.sin(a)
    loc, nor, _, _ = bvh.ray_cast(o, d, 3.0)            # eksenden dışa: ilk yüzey giysinin kendisi (sarkan kol değil)
    if loc is None: return np.array(o + d * 0.1), np.array(d)
    if nor.dot(d) < 0: nor = -nor
    return np.array(loc + nor * out), np.array(nor)


# ------------------------------------------------------------------ ek parçalar (hortum, ünite, fular): kur, ağırlıkla, nesneye çevir

SPINE = ('Hips', 'Spine', 'Spine1', 'Spine2', 'Neck')


def spine_weight(B):
    if getattr(B, '_spw', None) is None:
        gname = {g.index: short(g.name) for g in B.body.vertex_groups}
        B._spw = np.array([sum(g.weight for g in v.groups if gname[g.group] in SPINE) for v in B.body.data.vertices])
    return B._spw


def torso_kd(B):
    """Ek parçalar için: yalnız omurga zinciri (kalça…boyun) köşeleri. 'Gövde' kategorisi omuz kemiklerini de içeriyor:
    kollar öne gelince (çömelme) hortum omuza bağlı halkalardan 10 kat geriliyordu."""
    return _weights_kd(B, (spine_weight(B) > 0.6) & ~B.head_shell)


def keep_spine(bm, B):
    dl = bm.verts.layers.deform.verify()
    keep = {g.index for g in B.body.vertex_groups if short(g.name) in SPINE}
    for v in bm.verts:
        d = {gi: w for gi, w in v[dl].items() if gi in keep}; tot = sum(d.values())
        dv = v[dl]; dv.clear()
        for gi, w in d.items(): dv[gi] = w / tot if tot > 0 else w


def extra_object(bm, B, code, name, kd=None, labels=None, smooth=0):
    """Ek parça bmesh'i: yüz kodu (piece), en yakın gövde köşelerinden ağırlık (labels verilirse küme ortalaması) → nesne."""
    lay = bm.faces.layers.int.get('piece') or bm.faces.layers.int.new('piece')
    for f in bm.faces:
        if f[lay] < PIECE['extra']: f[lay] = code
    assign_weights(bm, B, kd or torso_kd(B))
    if kd is None: keep_spine(bm, B)
    if labels is not None: cluster_weights(bm, labels(bm) if callable(labels) else labels, smooth)
    return bm_to_object(bm, name, B)


def tube_along(bm, pts, radius, seg=8, rib=None, cap=True, code=None):
    """Nokta dizisi boyunca tüp (paralel taşınan çerçeve). radius: sabit ya da fonksiyon(s 0..1, uzunluk m). rib: (dönem m, derinlik oranı)."""
    pts = [V(p) for p in pts]
    L = [0.0]
    for a, b in zip(pts, pts[1:]): L.append(L[-1] + (b - a).length)
    tot = L[-1]
    d0 = (pts[1] - pts[0]).normalized(); ref = V((0, 0, 1)) if abs(d0.z) < 0.9 else V((1, 0, 0))
    u = (ref - d0 * d0.dot(ref)).normalized()
    rings = []; lay = bm.faces.layers.int.get('piece') or bm.faces.layers.int.new('piece')
    for i, p in enumerate(pts):
        d = ((pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)])).normalized()
        u = (u - d * d.dot(u)).normalized(); w = d.cross(u)
        r = radius(L[i] / tot, L[i]) if callable(radius) else radius
        if rib: r *= 1.0 - rib[1] * (0.5 - 0.5 * math.cos(2 * math.pi * L[i] / rib[0]))
        rings.append([bm.verts.new(p + (u * math.cos(2 * math.pi * k / seg) + w * math.sin(2 * math.pi * k / seg)) * r) for k in range(seg)])
    faces = []
    for A_, B_ in zip(rings, rings[1:]):
        for k in range(seg):
            faces.append(bm.faces.new((A_[k], A_[(k + 1) % seg], B_[(k + 1) % seg], B_[k])))
    if cap:
        for ring, rev in ((rings[0], True), (rings[-1], False)):
            c = bm.verts.new(sum((v.co for v in ring), V()) / seg)
            for k in range(seg):
                faces.append(bm.faces.new((ring[(k + 1) % seg], ring[k], c) if rev else (ring[k], ring[(k + 1) % seg], c)))
    if code is not None:
        for f in faces: f[lay] = code
    return faces


def obj_to_bm(ob, code=None):
    """Blender nesnesi (değiştiriciler uygulanmış, dünya konumunda) → bmesh; yüz kodu."""
    dg = bpy.context.evaluated_depsgraph_get(); e = ob.evaluated_get(dg); me = e.to_mesh()
    bm = bmesh.new(); bm.from_mesh(me); bm.transform(ob.matrix_world); e.to_mesh_clear()
    lay = bm.faces.layers.int.get('piece') or bm.faces.layers.int.new('piece')
    if code is not None:
        for f in bm.faces: f[lay] = code
    bpy.data.objects.remove(ob)
    return bm


def merge_bm(dst, src):
    me = bpy.data.meshes.new('tmp'); src.to_mesh(me); src.free(); dst.from_mesh(me); bpy.data.meshes.remove(me)


# ------------------------------------------------------------------ deri giysi üretimi (evre × kıyafet)

def make_suit(stage, O, out_dir, size=1024, keep=False):
    """O: kıyafet modülü (ID, spec(B), extras(B, ob, bvh), paint(Pt)). Çıktı: <out>/<ID>_<evre>.fbx (iskelet + ağ)
    ve <out>/<ID>_<evre>_basecolor.png / _normal.png. keep: sahne açık kalır (önizleme için) → (B, ob) döner."""
    import time
    t0 = time.time()
    reset_scene(); B = Body(stage); H = B.H
    spec = O.spec(B)
    ob = build_suit(B, spec, O.ID)
    if hasattr(O, 'extras'):
        bvh = object_bvh([ob])
        ex = [e for e in O.extras(B, ob, bvh) if e is not None]
        if ex: ob = join([ob] + ex, O.ID)
    # n-gen (ünite kutusunun yuvarlatılmış köşeleri) üçgenlenir: FBX'te teğet uzayı yazılabilsin (normal haritası için)
    bmt = bmesh.new(); bmt.from_mesh(ob.data)
    ng = [f for f in bmt.faces if len(f.verts) > 4]
    if ng: bmesh.ops.triangulate(bmt, faces=ng)
    bmt.to_mesh(ob.data); bmt.free()
    add_rim(ob, spec.thick * H)
    for p in ob.data.polygons: p.use_smooth = True
    smart_uv(ob)
    me = ob.data
    piece = np.zeros(len(me.polygons), np.int32); me.attributes['piece'].data.foreach_get('value', piece)
    # köşe nitelikleri: 6 grup ağırlığı (bölge), AO
    gname = {g.index: g.name for g in ob.vertex_groups}
    bcat = {b.name: _bone_cat(b) for b in B.arm.data.bones}
    Wv = np.zeros((len(me.vertices), len(CATS)), np.float32)
    for v in me.vertices:
        for g in v.groups:
            c = bcat.get(gname[g.group])
            if c: Wv[v.index, CI[c]] += g.weight
    s = Wv.sum(1, keepdims=True); s[s == 0] = 1; Wv /= s
    ao = vertex_ao(ob, [B.body], 0.07 * H, rays=20)
    T = Texels(ob, size, {'g5': group5(Wv), 'ao': ao}, {'piece': piece})
    Pt = Paint(B, T, ob)
    O.paint(Pt)
    nrm = height_to_normal(T, Pt.h, 1.0)
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, '%s_%s' % (O.ID, stage))
    save_maps(T, Pt.col, nrm, base, ao=Pt.ao, ao_strength=getattr(O, 'AO', 0.5))
    mod = ob.modifiers.new('Armature', 'ARMATURE'); mod.object = B.arm
    ob.parent = B.arm
    for o in list(bpy.context.scene.objects):
        if o.type == 'MESH' and o not in (ob, B.body): bpy.data.objects.remove(o)
    export_skin_fbx(base + '.fbx', B.arm, [ob])
    info = dict(stage=stage, tris=tri_count(ob), verts=len(me.vertices), tex=size, sec=round(time.time() - t0, 1))
    print('KIYAFET', O.ID, info, flush=True)
    if keep: return B, ob, base, info
    return info


# ------------------------------------------------------------------ çapa noktaları (yama/pad merkezleri, vücut yüzeyinden)

def anchor_limb(B, kind, S, t, a=0.0, win=0.25):
    """Uzvun t (m) kesitinde a açısındaki (0 ön, +π/2 dış) vücut yüzeyi noktası ve dışa yön."""
    ch = (B.arms if kind == 'arm' else B.legs)[S]
    pts = _limb_points(B, kind, S)
    tp, foot, dirs, dist = ch.project_np(pts)
    c, d = ch.point(t); f, o = ch.frame(d)
    m = np.abs(tp - t) < 0.02 * B.H
    q = pts[m] - np.array(c); q = q - np.outer(q @ np.array(d), np.array(d))
    ang = np.arctan2(q @ np.array(o), q @ np.array(f))
    dd = np.abs((ang - a + np.pi) % (2 * np.pi) - np.pi)
    k = dd < win
    r = np.linalg.norm(q[k], axis=1).max() if k.any() else 0.05 * B.H
    u = f * math.cos(a) + o * math.sin(a)
    return np.array(c + u * r), np.array(u)


def anchor_torso(B, z, a=0.0, win=0.22):
    """Gövdenin z yüksekliğinde a yönündeki (0 ön, +π/2 Okti'nin solu) en dış vücut noktası ve yatay dışa yön."""
    g5 = group5(B.W); m = (g5[:, 0] > 0.5) & ~B.head_shell & (np.abs(B.P[:, 2] - z) < 0.015 * B.H)
    cx, cy = B.spine_xy(z)
    q = B.P[m]; rx = q[:, 0] - cx; ry = q[:, 1] - cy
    ang = np.arctan2(rx, -ry); dd = np.abs((ang - a + np.pi) % (2 * np.pi) - np.pi)
    k = dd < win
    r = np.sqrt(rx[k] ** 2 + ry[k] ** 2).max() if k.any() else 0.08 * B.H
    u = np.array([math.sin(a), -math.cos(a), 0.0])
    return np.array([cx, cy, z]) + u * r, u


def torso_z(B, frac):
    """Kalça kemiği (0) ile önde başın eteği (1) arasında yükseklik."""
    front = B.rim_at(B.spine_xy(B.hips_z)[0], -1.0)
    return B.hips_z + frac * (front - B.hips_z)


# ------------------------------------------------------------------ 2B şekil işaretli uzaklıkları (yama çizimi)

def sd_circle(x, y, r): return np.sqrt(x * x + y * y) - r


def sd_ellipse(x, y, rx, ry):
    k = np.sqrt((x / rx) ** 2 + (y / ry) ** 2); return (k - 1) * min(rx, ry)


def sd_rrect(x, y, w, h, r):
    qx = np.abs(x) - w / 2 + r; qy = np.abs(y) - h / 2 + r
    return np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2) + np.minimum(np.maximum(qx, qy), 0) - r


def inside(sd, soft): return 1.0 - sstep(-soft, soft, sd)


def cluster_weights(bm, labels, smooth=0):
    """Küme başına ortak ağırlık (kümenin ortalaması): kutu tek parça, hortum halka halka esner (yanyana köşeler farklı
    kemik karışımı alınca hortum koşuda gerilip kıvrılıyordu). labels: köşe → tamsayı küme; smooth: ardışık kümeler arasında
    pencere (hortum boyunca yumuşak geçiş)."""
    dl = bm.verts.layers.deform.verify()
    acc = {}; cnt = {}
    for v, lab in labels.items():
        d = acc.setdefault(lab, {}); cnt[lab] = cnt.get(lab, 0) + 1
        for gi, w in v[dl].items(): d[gi] = d.get(gi, 0.0) + w
    mean = {lab: {gi: w / cnt[lab] for gi, w in d.items()} for lab, d in acc.items()}
    if smooth:
        keys = sorted(mean); sm = {}
        for i, k in enumerate(keys):
            d = {}
            for j in range(max(0, i - smooth), min(len(keys), i + smooth + 1)):
                for gi, w in mean[keys[j]].items(): d[gi] = d.get(gi, 0.0) + w
            sm[k] = d
        mean = sm
    for v, lab in labels.items():
        top = sorted(mean[lab].items(), key=lambda kv: -kv[1])[:4]; tot = sum(x for _, x in top) or 1.0
        dv = v[dl]; dv.clear()
        for gi, x in top: dv[gi] = x / tot
