#!/usr/bin/env python3
"""
Meshy API istemcisi (Pofi Adası sanat hattı).
- Anahtar ortamda değil: bulut ortamının ağ vekili Authorization başlığını api.meshy.ai isteklerine kendisi ekler.
- Her iş için harcanan kredi bakiye farkıyla ölçülür ve ledger.csv'ye yazılır (kredi planlaması için).
Kullanım (örnek):
  python3 meshy.py image  <ad> <model> "<prompt>" [--ref yol.png ...]
  python3 meshy.py to3d   <ad> <görsel.png> [--polys 12000] [--model meshy-6]
  python3 meshy.py rig    <ad> <image_to_3d_task_id> [--height 0.7]
  python3 meshy.py anim   <ad> <rig_task_id> <action_id>
  python3 meshy.py balance
"""
import base64, csv, json, os, sys, time, urllib.request, urllib.error, datetime

API = "https://api.meshy.ai/openapi"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
LEDGER = os.path.join(HERE, "ledger.csv")


def req(method, path, body=None, tries=8):
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(tries):
        r = urllib.request.Request(API + path, data=data, method=method, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(r, timeout=120) as resp:
                txt = resp.read().decode()
                return json.loads(txt) if txt else {}
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:500]
            if e.code in (429, 502, 503) and attempt < tries - 1:
                time.sleep(min(60, 5 * 2 ** attempt))   # istek sınırı: bekle ve tekrar dene
                continue
            raise SystemExit(f"HTTP {e.code} {path}: {msg}")


def balance():
    return req("GET", "/v1/balance")["balance"]


def data_uri(path):
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"
    return f"data:{mime};base64," + base64.b64encode(open(path, "rb").read()).decode()


def wait(kind, task_id, every=8, limit=1800):
    t0 = time.time()
    while True:
        t = req("GET", f"/{kind}/{task_id}")
        st = t.get("status")
        print(f"  {kind} {task_id[:8]} {st} {t.get('progress', '')}", flush=True)
        if st in ("SUCCEEDED", "FAILED", "CANCELED", "EXPIRED"):
            return t
        if time.time() - t0 > limit:
            raise SystemExit("zaman aşımı")
        time.sleep(every)


def download(url, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with urllib.request.urlopen(url, timeout=300) as r, open(path, "wb") as f:
        f.write(r.read())
    return path


def log(name, kind, task_id, before, after, note=""):
    new = not os.path.exists(LEDGER)
    with open(LEDGER, "a", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        if new:
            w.writerow(["zaman", "ad", "tür", "görev", "kredi", "not"])
        w.writerow([datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), name, kind, task_id, before - after, note])
    print(f"  kredi: {before - after}  (kalan {after})")


def run(name, kind, path, body, note=""):
    before = balance()
    task_id = req("POST", path, body)["result"]
    print(f"{name}: {kind} başladı {task_id}")
    t = wait(path.lstrip("/"), task_id)
    time.sleep(2)
    after = balance()
    # Paralel işlerde bakiye farkı karışır: görevin kendi bildirdiği kredi esas alınır.
    used = t.get("consumed_credits")
    if isinstance(used, (int, float)):
        before = after + int(used)
    log(name, kind, task_id, before, after, note)
    d = os.path.join(OUT, name)
    os.makedirs(d, exist_ok=True)
    json.dump(t, open(os.path.join(d, f"{kind}_{task_id[:8]}.json"), "w"), indent=1)
    if t.get("status") != "SUCCEEDED":
        raise SystemExit(f"başarısız: {t.get('task_error')}")
    return t


def cmd_image(args):
    name, model, prompt = args[0], args[1], args[2]
    refs = [a for i, a in enumerate(args) if i > 0 and args[i - 1] == "--ref"]
    aspect = args[args.index("--aspect") + 1] if "--aspect" in args else "1:1"
    count = int(args[args.index("--n") + 1]) if "--n" in args else 1
    body = {"ai_model": model, "prompt": prompt, "aspect_ratio": aspect}
    if count > 1:
        body["generate_multi_view"] = False
    if refs:
        body["image_urls"] = [data_uri(r) for r in refs]
    t = run(name, "image", "/v1/text-to-image", body, model)
    urls = t.get("image_urls") or []
    for i, u in enumerate(urls):
        p = download(u, os.path.join(OUT, name, f"concept_{t['id'][:8]}_{i}.png"))
        print("  indirildi:", p)


def cmd_to3d(args):
    name, img = args[0], args[1]
    polys = int(args[args.index("--polys") + 1]) if "--polys" in args else 12000
    model = args[args.index("--model") + 1] if "--model" in args else "latest"
    pose = args[args.index("--pose") + 1] if "--pose" in args else None
    body = {"image_url": data_uri(img) if os.path.exists(img) else img, "ai_model": model, "topology": "triangle",
            "target_polycount": polys, "should_remesh": True, "should_texture": True, "enable_pbr": True,
            "symmetry_mode": "auto"}
    if pose:
        body["pose_mode"] = pose
    t = run(name, "to3d", "/v1/image-to-3d", body, f"{model} {polys}")
    for fmt, u in (t.get("model_urls") or {}).items():
        if u and fmt in ("glb", "fbx"):
            print("  indirildi:", download(u, os.path.join(OUT, name, f"{name}.{fmt}")))
    if t.get("thumbnail_url"):
        download(t["thumbnail_url"], os.path.join(OUT, name, "thumb.png"))


def cmd_rig(args):
    name, task = args[0], args[1]
    h = float(args[args.index("--height") + 1]) if "--height" in args else 0.7
    t = run(name, "rig", "/v1/rigging", {"input_task_id": task, "height_meters": h})
    res = t.get("result") or {}
    for k, u in res.items():
        if isinstance(u, str) and u.startswith("http") and (".glb" in u or ".fbx" in u):
            print("  indirildi:", download(u, os.path.join(OUT, name, f"rig_{k}" + (".glb" if ".glb" in u else ".fbx"))))


def cmd_anim(args):
    name, rig, action = args[0], args[1], int(args[2])
    t = run(name, f"anim{action}", "/v1/animations", {"rig_task_id": rig, "action_id": action})
    res = t.get("result") or {}
    for k, u in res.items():
        if isinstance(u, str) and u.startswith("http") and (".glb" in u or ".fbx" in u):
            print("  indirildi:", download(u, os.path.join(OUT, name, f"anim{action}_{k}" + (".glb" if ".glb" in u else ".fbx"))))


def cmd_fetchimage(args):
    """Önceden başlamış text-to-image görevini indir: fetchimage <ad> <görev_id>"""
    name, tid = args[0], args[1]
    t = wait("v1/text-to-image", tid)
    d = os.path.join(OUT, name); os.makedirs(d, exist_ok=True)
    json.dump(t, open(os.path.join(d, f"image_{tid[:8]}.json"), "w"), indent=1)
    log(name, "image", tid, int(t.get("consumed_credits") or 0), 0, "geri alındı")
    for i, u in enumerate(t.get("image_urls") or []):
        print("  indirildi:", download(u, os.path.join(d, f"concept_{tid[:8]}_{i}.png")))


if __name__ == "__main__":
    c, a = sys.argv[1], sys.argv[2:]
    if c == "balance":
        print(balance())
    else:
        {"image": cmd_image, "to3d": cmd_to3d, "rig": cmd_rig, "anim": cmd_anim, "fetchimage": cmd_fetchimage}[c](a)
