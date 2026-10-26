# Ada v6 süsleri → oyun modelleri (22 Ekim 2026; onaylı taslağın aynı kodu, oyun bütçesiyle).
# Her model taslaktaki örnek ölçüsünde (ör. çam 1 m boyunda kurulur, yerleşim ölçeği 5–12) → bake_game.py'deki "s" doğrudan ölçektir.
# Dışa aktarma: kit.export_baked_fbx (üçgen bütçesi POFI_TARGET + pişirilmiş renk/AO) → Resources/Env/<ad>/<ad>.fbx + _basecolor.png
#   /tmp/claude-0/bpyenv/bin/python -I assets_v6_game.py -- [ad ...]
import sys, os, math, random, shutil, glob, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
ENV = os.path.join(ROOT, 'Assets', '_Pofi', 'Resources', 'Env')
PY = os.environ.get('POFI_BPY', '/tmp/claude-0/bpyenv/bin/python')
STAGE = os.environ.get('POFI_STAGE', '/tmp/pofi_v6_export')

# oyun adı: (yapıcı, üçgen bütçesi, doku boyu)
ASSETS = {
    't_round0': ('round:0', 2400, 1024), 't_round1': ('round:1', 2400, 1024), 't_round2': ('round:2', 2400, 1024), 't_round3': ('round:3', 2400, 1024),
    't_cypress': ('cypress', 1800, 1024), 't_birch': ('birch', 1600, 1024),
    't_pine0': ('pine:0', 1700, 1024), 't_pine1': ('pine:1', 1700, 1024), 't_pine2': ('pine:2', 1700, 1024), 't_pine_snow': ('pine_snow', 1700, 1024),
    't_palm_tall0': ('palm2:0', 2600, 1024), 't_palm_tall1': ('palm2:1', 2600, 1024), 't_palm_tall2': ('palm2:2', 2600, 1024),
    't_bush': ('bush', 700, 512), 't_blossom': ('blossom', 2600, 1024),
    'r_boulder': ('boulder', 900, 512), 'r_boulder_b': ('boulderB', 900, 512), 'r_pebble': ('pebW', 300, 256),
    'p_campfire': ('campfire', 2600, 512), 'p_log_v6': ('log', 900, 512), 'p_stump_v6': ('stump', 800, 512),
    'p_driftwood': ('driftwood', 1400, 512), 'p_starfish': ('starfish', 300, 256),   # p_crab: art/code3d/crab_v2.py (26 Ekim 2026, parçalı ve oynar)
    'p_pool': ('pool', 7000, 1024), 'b_temple': ('temple', 110000, 2048),   # tapınak: kendi yolu (temple_game.py), bütçe üst sınır
    'p_trail_pole': ('pole', 120, 128), 'p_snow_lump': ('snowlump', 200, 256),
    'b_cave_v6': ('cave', 7000, 1024), 'b_ski_v6': ('skiset', 3000, 512), 'b_summit_v6': ('summit', 2600, 512),
}

FRINGE = 0.07        # ağaç taçlarında hedefte kalan gerçek kenar yaprağı oranı (siluet tırtıklı kalsın)

def build(spec):
    """Taslaktaki modeli TAM ayrıntıyla kurar. Döndürür: (kaynak nesneler, hedef nesneler ya da None, pişirme ayarları)."""
    import bpy
    sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
    import kit_v6 as K, kit2_v6 as K2, kit3_v6 as K3, proxy_bake as PB
    col = bpy.context.scene.collection
    kind, _, k = spec.partition(':'); k = int(k or 0)
    low = []
    opts = {}
    if kind in ('round', 'birch', 'bush', 'cypress', 'blossom') and not getattr(K, '_proxy_crown', False):
        orig = K.crown
        def proxy_crown(name, clusters, center, radii, palette, leaf=0.35, density=320, seed=0, col=None, mat=None, droop=0.35, shell=0.86, flat_top=0.0, cw=0.45):
            hi = orig(name, clusters, center, radii, palette, leaf=leaf, density=density, seed=seed, col=col, mat=mat, droop=droop, shell=shell, flat_top=flat_top, cw=cw)
            vs, fs = [], []
            for j, (cc, rr) in enumerate(clusters):
                pts, f = PB.shell_cluster(tuple(cc), tuple(v * 0.97 for v in rr), sub=2, seed=seed + j)
                fs += [[i + len(vs) for i in q] for q in f]; vs += pts
            low.append(PB.mesh_from(name + '_shell', vs, fs, col=col))
            fr = orig(name + '_fr', clusters, center, radii, palette, leaf=leaf * 1.15, density=density * FRINGE, seed=seed + 101, col=col, mat=mat, droop=droop, shell=0, flat_top=flat_top, cw=cw)
            a = fr.data.attributes.new('ds', 'INT', 'FACE'); a.data.foreach_set('value', [1] * len(fr.data.polygons))
            low.append(fr)
            opts['leaf'] = max(opts.get('leaf', 0), leaf)
            return hi
        K.crown = proxy_crown; K._proxy_crown = True
    bark = K.bark_mat()
    if kind == 'round':
        pals = [K.PAL_BROAD, K.PAL_BROAD2, K.PAL_BROAD3, K.PAL_BROAD4]
        K.round_tree('rt', 1.0, 10 + k, col=col, palette=pals[k], spread=0.85 + 0.12 * k, fol=K.foliage_mat('fol_broad'), bark=bark, clumps=8 + k)
    elif kind == 'blossom':   # tapınak avlusundaki pembe çiçekli ağaç (kit3_v6.temple ile aynı)
        K.round_tree('bl', 1.0, 77, col=col, palette=K3.PAL_BLOSSOM, spread=1.2, fol=K.foliage_mat('fol_blossom', translucent=0.35), bark=bark, clumps=13)
    elif kind == 'cypress': K.cypress('cy', 1.0, 30, col=col, fol=K.foliage_mat('fol_cyp', translucent=0.15), bark=bark)
    elif kind == 'birch': K.birch('bi', 1.0, 40, col=col, fol=K.foliage_mat('fol_broad'))
    elif kind in ('pine', 'pine_snow'):
        seed = 55 if kind == 'pine_snow' else 50 + k
        pal = K.PAL_PINE_SNOW if kind == 'pine_snow' else (K.PAL_PINE, K.PAL_PINE2, K.PAL_PINE3)[k]
        K.pine('pi', 1.0, seed, col=col, fol=K.foliage_mat('fol_pine', translucent=0.18), bark=bark, palette=pal)
        low.append(pine_low('pi_low', 1.0, seed, PB, col)); opts['leaf'] = 0.04
    elif kind == 'palm2': K2.palm('pm', (9.5, 13.0, 16.0)[k], 300 + k, col=col, thick=(1.0, 0.85, 0.8)[k])
    elif kind == 'bush': K.bush('bu', 1.0, 60, col=col, fol=K.foliage_mat('fol_broad'), leaf=0.09)
    elif kind == 'boulder': K.boulder('bd', (1.0, 0.9, 0.8), 70, mat=K.rock_mat('rockA', base='#b3a8a8', dark='#7f7386', light='#d4c9c0', moss_amt=0.18), col=col)
    elif kind == 'boulderB': K.boulder('bb', (1.0, 0.85, 0.85), 80, mat=K.rock_mat('rockB', base='#a7adb8', dark='#727a8c', light='#cdd2d8', moss_amt=0.28), col=col)
    elif kind == 'pebW': K.boulder('bw', (1.0, 0.85, 0.7), 90, cuts=4, mat=K.rock_mat('rockW', base='#d6d0cc', dark='#a49ca0', light='#ece8e2', moss_amt=0.0, cracks=0.2), col=col, bevel=0.25, top_flat=0.0)
    elif kind == 'campfire':
        K2.campfire_v2('cf', col=col, seed=4, scale=1.0)
        # alevler oyunda canlı (Runtime/World/Campfire): pişirilen modelde yalnız odun + taş + kor
        for o in list(col.objects):
            if any(m and m.name.endswith('_fire') for m in getattr(o.data, 'materials', [])) or o.type == 'LIGHT':
                bpy.data.objects.remove(o)
    elif kind == 'log': K2.log_v2('lg', 3.0, 0.34, 20, col=col)
    elif kind == 'stump': K2.stump_v2('st', 0.42, 0.55, 30, col=col)
    elif kind == 'driftwood': K2.driftwood('dw', 5.8, 0.62, 5, col=col)
    elif kind == 'starfish': K2.starfish('sf', 0.15, 51, col=col)
    elif kind == 'crab': K2.crab('cr', 0.22, 60, col=col)
    elif kind == 'pool':
        rmA = K.rock_mat('rockA', base='#b3a8a8', dark='#7f7386', light='#d4c9c0', moss_amt=0.18)
        rmB = K.rock_mat('rockB', base='#a7adb8', dark='#727a8c', light='#cdd2d8', moss_amt=0.28)
        K2.swim_pool('pool', col=col, seed=3, mats=(rmA, rmB))
    elif kind == 'temple':
        K3.temple(col)
        # avludaki ot telleri (600 bin üçgen) ve çiçek öbekleri pişirilmez: hedefte yerlerine hafif 3B çim öbekleri ve çiçek
        # demetleri eklenir (temple_game.meadow). Hedef = aynı ağ (temple_game.build_low; 24 Ekim 2026: eskitme/fener ayrıntısı
        # oyunda görünmüyordu — küresel sadeleştirme ve kötü UV paketlemesi yüzünden)
        for o in list(bpy.context.scene.objects):
            if o.type == 'LIGHT' or o.name.startswith('tmp_grass') or o.name.startswith('tmp_flw'): bpy.data.objects.remove(o)
        import temple_game as TG
        low += TG.build_low([o for o in bpy.context.scene.objects if o.type == 'MESH'])
        opts['export'] = dict(target=None, cull_hidden=True, uv_weight='uvw', reserve=TG.RESERVE, paint=TG.paint_swatches,
                              extras=lambda L, H: TG.meadow(L, H), ao_dist=0.7, ao_strength=0.55, nsize=1024, dilate=16)
    elif kind == 'pole':
        v, f = K.tube_data([(0, 0, 0), (0, 0, 1.35)], [0.045, 0.04], 6, 0); K.mesh_obj('pole', v, f, K.bark_mat('pole_bark', base='#7a5536', dark='#4a3222', light='#a67c55'), col=col)
        cap = bpy.data.materials.new('pole_cap'); cap.use_nodes = True; cap.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = K.srgb('#f07a1a') + (1,)
        v, f = K.tube_data([(0, 0, 1.35), (0, 0, 1.6)], [0.06, 0.06], 6, 0); K.mesh_obj('cap', v, f, cap, col=col)
    elif kind == 'snowlump': K2.snow_lump('sl', 1.0, 70, col=col, mat=K2.snow_mat())
    elif kind == 'cave': cave_model(K, K2, col)
    elif kind == 'skiset': ski_set(K, K2, col)
    elif kind == 'summit': summit(K, K2, col)
    else: raise SystemExit('bilinmeyen ' + spec)
    high = [o for o in bpy.context.scene.objects if o.type in ('MESH', 'CURVE') and o not in low]
    if low:
        # gövde/dal ve taç dışı parçalar hedefte de kalır (kopya; bütçeye birlikte iner)
        for o in high:
            if o.name.endswith('_trunk') or o.name.endswith('_boot'):
                c = o.copy(); c.data = o.data.copy(); col.objects.link(c); low.append(c)
    return high, (low or None), opts

def pine_low(name, h, seed, PB, col):
    """Katmanlı çamın hedefi: her kat için sarkan, kenarı tırtıklı koni yüzeyi (üst) + koyu iç koni (alt).
    Kat ölçüleri kit_v6.pine ile aynı rastgele sırayla hesaplanır (R.uniform → L, R.randint → yumru)."""
    import random
    R = random.Random(seed); tiers = 7; vs, fs = [], []
    seg = 28
    for t in range(tiers):
        k = t / (tiers - 1); z0 = h * (0.16 + 0.74 * k); L = h * (0.33 - 0.27 * k) * R.uniform(0.9, 1.1)
        lumpn = R.randint(5, 8)
        def zf(s): return z0 - (h * 0.12 * (s ** 1.6) * (1 - 0.4 * k) + h * 0.015)
        rings = [0.0, 0.3, 0.62, 0.86, 1.0]
        base = len(vs)
        vs.append((0.0, 0.0, z0 + h * 0.02))
        for s in rings[1:]:
            for q in range(seg):
                a = q / seg * math.tau; lump = 1 + 0.18 * math.sin(a * lumpn + t)
                rr = L * s * lump * ((1.08 if q % 2 == 0 else 0.9) if s == 1.0 else 1.0)
                vs.append((math.cos(a) * rr, math.sin(a) * rr, zf(s) - (h * 0.012 if (s == 1.0 and q % 2 == 0) else 0.0)))
        for q in range(seg):
            fs.append([base, base + 1 + q, base + 1 + (q + 1) % seg])
        for r_ in range(len(rings) - 2):
            o0 = base + 1 + r_ * seg; o1 = o0 + seg
            for q in range(seg):
                q1 = (q + 1) % seg; fs.append([o0 + q, o1 + q, o1 + q1, o0 + q1])
        # alt: dış halkadan gövdeye koyu iç koni
        outer = base + 1 + (len(rings) - 2) * seg; c = len(vs); vs.append((0.0, 0.0, z0 - h * 0.09))
        for q in range(seg):
            fs.append([c, outer + (q + 1) % seg, outer + q])
    return PB.mesh_from(name, vs, fs, col=col)

def _flat_mat(K, name, hexc, rough=0.7):
    import bpy
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = K.srgb(hexc) + (1,); b.inputs['Roughness'].default_value = rough
    return m

def ski_set(K, K2, col):
    """Kayak tepesi (taslak island_v6_near.ski ile aynı öğeler): +Y boyunca sırayla kırmızı/mavi kapı bayrakları,
    kardan adam (havuç burun), kızak — patikanın iki yanında (ortası yürüyüş için açık)."""
    import bpy
    bark = K.bark_mat('ski_bark', base='#7a5536', dark='#4a3222', light='#a67c55')
    red, blu, wh, org = _flat_mat(K, 'ski_red', '#e8423a'), _flat_mat(K, 'ski_blu', '#2f7be8'), _flat_mat(K, 'ski_wh', '#f4f7fb', 0.9), _flat_mat(K, 'ski_org', '#f07a1a')
    # öğeler patikanın iki yanında (bölge merkezi = karlı patikanın başı; ortası açık kalır, kapı yok)
    for k in range(5):
        y = 1.0 + k * 2.6; x = 4.6 + (-0.9 if k % 2 else 0.9) + math.sin(k) * 0.3; m = red if k % 2 else blu
        v, f = K.tube_data([(x, y, -0.1), (x, y, 1.35)], [0.03, 0.025], 6, 0); K.mesh_obj('flag_pole', v, f, m, col=col)
        K.mesh_obj('flag', [(x, y, 1.35), (x + (0.55 if x < 0 else -0.55), y, 1.15), (x, y, 0.95), (x, y + 0.01, 1.35), (x, y + 0.01, 0.95), (x + (0.55 if x < 0 else -0.55), y + 0.01, 1.15)], [(0, 1, 2), (3, 4, 5)], m, col=col)
    ico = K._ico(2); sx_, sy_ = -4.6, 1.2
    for (r, hgt) in ((0.5, 0.42), (0.37, 1.1), (0.27, 1.6)):
        K.mesh_obj('snowman', [(sx_ + q[0] * r, sy_ + q[1] * r, hgt + q[2] * r) for q in ico], K._ICO_F[2], wh, col=col)
    K.mesh_obj('nose', [(sx_ - 0.04, sy_ - 0.26, 1.6), (sx_ + 0.04, sy_ - 0.26, 1.6), (sx_, sy_ - 0.26, 1.66), (sx_, sy_ - 0.55, 1.61)], [(0, 1, 3), (1, 2, 3), (2, 0, 3)], org, col=col)
    blk = _flat_mat(K, 'ski_coal', '#2a2a30')
    for (dx, dz) in ((-0.1, 1.7), (0.1, 1.7), (0.0, 1.15), (0.0, 0.95)):
        K.mesh_obj('coal', [(sx_ + dx + q[0] * 0.045, sy_ - 0.25 + q[1] * 0.045, dz + q[2] * 0.045) for q in K._ico(1)], K._ICO_F[1], blk, col=col)
    # kızak: iki kızak demiri + tahta oturak
    wood = K.bark_mat('sled', base='#b5713a', dark='#7a4a26', light='#d89a5c')
    for sx in (-0.28, 0.28):
        v, f = K.tube_data([(-5.2 + sx, 3.0, 0.06), (-5.2 + sx, 4.2, 0.06), (-5.2 + sx, 4.4, 0.22)], [0.03, 0.03, 0.03], 6, 0); K.mesh_obj('runner', v, f, red, col=col)
    v, f = K.tube_data([(-5.5, 3.6, 0.25), (-4.9, 3.6, 0.25)], [0.32, 0.32], 4, 0); K.mesh_obj('seat', v, f, wood, col=col)

def summit(K, K2, col):
    """Dağ zirvesi işareti: üst üste taş kulesi (gri kaya, yosunsuz) + ahşap direkte kırmızı bayrak + dipte birkaç taş."""
    import bpy, random
    R = random.Random(9)
    rm = K.rock_mat('summit_rock', base='#a7adb8', dark='#727a8c', light='#cdd2d8', moss_amt=0.05)
    z = 0.0
    for k, s in enumerate((0.95, 0.75, 0.6, 0.45, 0.32)):
        o = K.boulder('cairn%d' % k, (s, s * 0.9, s * 0.55), 120 + k, cuts=8, mat=rm, col=col, bevel=0.12)
        o.location = (R.uniform(-0.08, 0.08), R.uniform(-0.08, 0.08), z + s * 0.45); o.rotation_euler = (0, 0, R.uniform(0, 6.3)); z += s * 0.95
    for k in range(6):
        a = k / 6 * math.tau + R.uniform(-0.3, 0.3); r = R.uniform(1.4, 2.2); s = R.uniform(0.25, 0.5)
        o = K.boulder('cs%d' % k, (s, s * 0.85, s * 0.6), 140 + k, cuts=7, mat=rm, col=col, bevel=0.12); o.location = (math.cos(a) * r, math.sin(a) * r, s * 0.25)
    bark = K.bark_mat('summit_pole', base='#7a5536', dark='#4a3222', light='#a67c55')
    v, f = K.tube_data([(0, 0, z - 0.4), (0, 0, z + 2.4)], [0.06, 0.05], 8, 0); K.mesh_obj('pole', v, f, bark, col=col)
    red = _flat_mat(K, 'summit_flag', '#e8423a')
    fv = []; ff = []
    for i in range(7):
        t = i / 6; x = 0.05 + t * 1.3; dz = 0.12 * math.sin(t * 3.0)
        fv += [(x, 0.0 + dz * 0.3, z + 2.35 - t * 0.12), (x, 0.0 + dz * 0.3, z + 1.65 + t * 0.12)]
    for i in range(6): ff.append((i * 2, i * 2 + 2, i * 2 + 3, i * 2 + 1))
    fo = K.mesh_obj('flag', fv, ff, red, col=col)
    a = fo.data.attributes.new('ds', 'INT', 'FACE'); a.data.foreach_set('value', [1] * len(fo.data.polygons))

def cave_model(K, K2, col):
    """v6 mağarası (island_v6.cave ile aynı yapı, bölge merkezinde, ağız +Y yönüne): iri kaya kemeri + höyük + karanlık tünel."""
    import bpy, random
    from mathutils import Vector as V, noise as MN
    import island_v6 as IV
    rr = random.Random(5)
    rmB = K.rock_mat('rockB', base='#a7adb8', dark='#727a8c', light='#cdd2d8', moss_amt=0.28)
    protos = [K.boulder('cb%d' % j, (1.0, 0.85, 0.85), 80 + j, mat=rmB, col=bpy.data.collections.new('C_cb%d' % j)) for j in range(4)]
    placed = []
    def inst(proto, x, z, y, rot, s, sxyz=None):
        e = bpy.data.objects.new('cave_b', proto.data.copy()); e.location = (x, z, y); e.rotation_euler = (0, 0, rot)
        e.scale = sxyz if sxyz else (s, s, s)
        for md in proto.modifiers:
            m2 = e.modifiers.new(md.name, md.type); m2.subdivision_type = md.subdivision_type; m2.levels = md.levels; m2.render_levels = md.render_levels
        col.objects.link(e); placed.append(e); return e
    class _L:
        def height(self, x, z): return 0.0
        lay = {'regions': [{'id': 'region_cave', 'pos': [0.0, 0.0], 'yaw': 0.0}]}
    IV.inst = inst
    P = {'boulderB': [p.users_collection[0] for p in protos]}
    def inst_col(c, x, z, y, rot=0.0, s=1.0, sxyz=None):
        proto = c.objects[0]
        return inst(proto, x, z, y, rot, s, sxyz)
    IV.inst = inst_col
    IV.cave(_L(), P, 0.0, 0.0, rr)
    for p in protos: bpy.data.objects.remove(p)

def child(name, out):
    """bpy alt süreci: tam modeli kur, oyun hedefine pişir (renk + AO + normal), dışa aktar."""
    import bpy
    sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
    import proxy_bake as PB
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import kit_v6; kit_v6.BAKE_LOOK = True
    high, low, opts = build(ASSETS[name][0])
    bpy.ops.object.select_all(action='SELECT')
    try: bpy.ops.object.duplicates_make_real()
    except Exception: pass
    for o in list(bpy.context.scene.objects):
        if o.type == 'CURVE':
            bpy.context.view_layer.objects.active = o; o.select_set(True)
            try: bpy.ops.object.convert(target='MESH')
            except Exception: pass
    high = [o for o in bpy.context.scene.objects if o.type == 'MESH' and (low is None or o not in low)]
    if low is None:
        # hedef = taslağın görünüm (alt bölmesiz) ağı; kaynak = alt bölme + yer değiştirme ile kabartmalı kopya.
        # (Hedef kaynağın kendisinden sadeleşince çok parçalı modeller — tapınak — dağılıyordu.)
        dg = bpy.context.evaluated_depsgraph_get(); low = []
        for o in high:
            me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), depsgraph=dg)
            c = bpy.data.objects.new(o.name + '_low', me); c.matrix_world = o.matrix_world.copy(); bpy.context.scene.collection.objects.link(c); low.append(c)
    # kabartma: alt bölme + gerçek yer değiştirme yalnız kaynağa (kaya çatlakları normal haritasına geçer); tapınak gibi
    # çok parçalı yapılarda alt bölme kapalı kalır (kaynak zaten ayrıntılı)
    if ASSETS[name][0].split(':')[0] in ('boulder', 'boulderB', 'pebW', 'cave', 'summit', 'pool', 'stump', 'log', 'driftwood'):
        for o in high:
            for md in getattr(o, 'modifiers', []):
                if md.type == 'SUBSURF' and md.render_levels > md.levels: md.levels = min(md.render_levels, 2)
    _, target, tex = ASSETS[name]
    leaf = opts.get('leaf')
    # ışın: ağaçta yaprak katmanı kalınlığı; katı modellerde kabartma kadar (model 1 m'lik örnek ölçüsünde)
    cage, ray = (leaf * 0.9, leaf * 2.2) if leaf else (0.02, 0.08)
    kw = dict(target=target, size=tex, nsize=max(256, tex // 2), cage=cage, ray=ray, ao_strength=0.5 if leaf is None else 0.7, ds_low=True,
              tone=1.2 if ASSETS[name][0].split(':')[0] in ('boulder', 'boulderB', 'pebW', 'cave', 'pool') else 1.0,
              fix_normals=ASSETS[name][0].split(':')[0] in ('stump', 'log', 'driftwood', 'boulder', 'boulderB', 'pebW'))
    kw.update(opts.get('export', {}))
    tris = PB.export_proxy(os.path.join(out, name), high, low, **kw)
    print('üçgen', tris, flush=True)

def export(name):
    out = os.path.join(STAGE, name); os.makedirs(out, exist_ok=True)
    _, target, tex = ASSETS[name]
    env = dict(os.environ, POFI_TARGET=str(target), POFI_TEX=str(tex))
    r = subprocess.run([PY, '-I', os.path.abspath(__file__), '--child', name, out], env=env, capture_output=True, text=True, cwd=HERE)
    fbx = os.path.join(out, name + '.fbx')
    if r.returncode != 0 or not os.path.exists(fbx):
        print('HATA', name, r.stdout[-1200:], r.stderr[-1500:], flush=True); return False
    dst = os.path.join(ENV, name)
    if os.path.isdir(dst):
        for f in glob.glob(os.path.join(dst, '*')): os.remove(f)
    os.makedirs(dst, exist_ok=True)
    shutil.copy(fbx, os.path.join(dst, name + '.fbx'))
    for suf in ('_basecolor.png', '_normal.png'):
        if os.path.exists(os.path.join(out, name + suf)): shutil.copy(os.path.join(out, name + suf), os.path.join(dst, name + suf))
    print('OK', name, [l for l in r.stdout.splitlines() if 'üçgen' in l][-1:], flush=True)
    return True

if __name__ == '__main__':
    if '--child' in sys.argv:
        i = sys.argv.index('--child'); child(sys.argv[i + 1], sys.argv[i + 2])
    else:
        args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
        names = args or list(ASSETS)
        bad = [n for n in names if not export(n)]
        print('bitti', len(names) - len(bad), 'hatalı:', bad)
