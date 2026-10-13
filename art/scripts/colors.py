# Renk ayrışma analizi: CIEDE2000 + renk körlüğü simülasyonu (Machado 2009, şiddet 1.0)
import numpy as np, itertools, sys, json
def hex2rgb(h): h=h.lstrip('#'); return np.array([int(h[i:i+2],16)/255 for i in (0,2,4)])
def lin(c): return np.where(c<=0.04045,c/12.92,((c+0.055)/1.055)**2.4)
def delin(c): c=np.clip(c,0,1); return np.where(c<=0.0031308,c*12.92,1.055*c**(1/2.4)-0.055)
def lab(rgb):
    M=np.array([[0.4124,0.3576,0.1805],[0.2126,0.7152,0.0722],[0.0193,0.1192,0.9505]])
    x,y,z=M@lin(rgb)/np.array([0.95047,1,1.08883])
    f=lambda t: np.where(t>0.008856,np.cbrt(t),7.787*t+16/116)
    return np.array([116*f(y)-16,500*(f(x)-f(y)),200*(f(y)-f(z))])
def de2000(l1,l2):
    L1,a1,b1=l1;L2,a2,b2=l2
    C1=np.hypot(a1,b1);C2=np.hypot(a2,b2);Cb=(C1+C2)/2
    G=0.5*(1-np.sqrt(Cb**7/(Cb**7+25**7)))
    a1p,a2p=(1+G)*a1,(1+G)*a2
    C1p,C2p=np.hypot(a1p,b1),np.hypot(a2p,b2)
    h1=np.degrees(np.arctan2(b1,a1p))%360;h2=np.degrees(np.arctan2(b2,a2p))%360
    dL=L2-L1;dC=C2p-C1p
    dh=h2-h1
    if C1p*C2p==0: dh=0
    elif dh>180: dh-=360
    elif dh<-180: dh+=360
    dH=2*np.sqrt(C1p*C2p)*np.sin(np.radians(dh/2))
    Lb=(L1+L2)/2;Cbp=(C1p+C2p)/2
    hb=(h1+h2)/2 if abs(h1-h2)<=180 else (h1+h2+360)/2
    if C1p*C2p==0: hb=h1+h2
    T=1-0.17*np.cos(np.radians(hb-30))+0.24*np.cos(np.radians(2*hb))+0.32*np.cos(np.radians(3*hb+6))-0.2*np.cos(np.radians(4*hb-63))
    dth=30*np.exp(-((hb-275)/25)**2);RC=2*np.sqrt(Cbp**7/(Cbp**7+25**7))
    SL=1+0.015*(Lb-50)**2/np.sqrt(20+(Lb-50)**2);SC=1+0.045*Cbp;SH=1+0.015*Cbp*T
    RT=-np.sin(np.radians(2*dth))*RC
    return float(np.sqrt((dL/SL)**2+(dC/SC)**2+(dH/SH)**2+RT*(dC/SC)*(dH/SH)))
CVD={'deutan':np.array([[0.367322,0.860646,-0.227968],[0.280085,0.672501,0.047413],[-0.011820,0.042940,0.968881]]),
     'protan':np.array([[0.152286,1.052583,-0.204868],[0.114503,0.786281,0.099216],[-0.003882,-0.048116,1.051998]]),
     'tritan':np.array([[1.255528,-0.076749,-0.178779],[-0.078411,0.930809,0.147602],[0.004733,0.691367,0.303900]])}
def sim(rgb,k): return delin(CVD[k]@lin(rgb))
def analyse(pal):
    rows=[]
    for (n1,h1),(n2,h2) in itertools.combinations(pal.items(),2):
        r1,r2=hex2rgb(h1),hex2rgb(h2)
        d={'normal':de2000(lab(r1),lab(r2))}
        for k in CVD: d[k]=de2000(lab(sim(r1,k)),lab(sim(r2,k)))
        rows.append((n1,n2,d))
    return rows
if __name__=='__main__':
    pal=json.load(open(sys.argv[1]))
    rows=analyse(pal)
    rows.sort(key=lambda r:min(r[2].values()))
    for n1,n2,d in rows[:14]:
        print(f"{n1:7s}-{n2:7s} " + " ".join(f"{k}={v:5.1f}" for k,v in d.items()))
