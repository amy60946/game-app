# Her pet/animasyon için gerçek hareket aralığı ve en iyi döngü sonu (poz başa en yakın) → JSON
import bpy, sys, json, os, glob
root=sys.argv[sys.argv.index('--')+1]; out=sys.argv[sys.argv.index('--')+2]
res={}
for f in sorted(glob.glob(root+'/pet_*/pet_*@*.fbx')):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=f)
    arms=[o for o in bpy.data.objects if o.type=='ARMATURE']
    if not arms: continue
    arm=arms[0]; sc=bpy.context.scene
    a=bpy.data.actions[0]; f0,f1=int(a.frame_range[0]),int(a.frame_range[1])
    poses=[]
    for fr in range(f0,f1+1):
        sc.frame_set(fr)
        poses.append([v for b in arm.pose.bones for v in tuple(b.matrix_basis.to_quaternion())+tuple(b.matrix_basis.to_translation())])
    def d(p,q): return max(abs(x-y) for x,y in zip(p,q))
    last=f0
    for i in range(len(poses)-1,0,-1):
        if d(poses[i],poses[i-1])>1e-4: last=f0+i; break
    name=os.path.basename(f)[:-4]; clip=name.split('@')[1]
    start=f0
    # döngü sonu: [start+12, last] içinde başlangıç pozuna en yakın kare
    best=last; bd=1e9
    for i in range(12, last-f0+1):
        dd=d(poses[i],poses[0])
        if dd<bd: bd=dd; best=f0+i
    res[name]={'first':start,'last':last,'loopEnd':best,'loopErr':round(bd,3),'fps':sc.render.fps}
    print(name,res[name],flush=True)
json.dump(res,open(out,'w'),indent=1)
