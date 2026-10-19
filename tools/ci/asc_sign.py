# App Store dağıtım imzası (elle, yerelde): API anahtarıyla geçici bir "Apple Distribution" sertifikası + IOS_APP_STORE
# profili oluşturur. Neden: Xcode'un bulut imzası App Store doğrulamasından geçmeyen imza üretti ("Invalid Signature").
# Sertifika işin sonunda iptal edilir (cleanup); yüklenmiş TestFlight/App Store derlemeleri bundan etkilenmez.
# Kullanım:
#   python3 asc_sign.py create <p8> <bundle_id> <çıkış_klasörü>   → key.pem, cert.der, profile.mobileprovision, info.json
#   python3 asc_sign.py cleanup <p8> <info.json>
# Ortam: ASC_KEY_ID, ASC_ISSUER_ID. Gizli bilgiler loga yazılmaz.
import base64, json, os, sys, time, urllib.error, urllib.request
import jwt
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

API = 'https://api.appstoreconnect.apple.com/v1'

def token(p8):
    now = int(time.time())
    return jwt.encode({'iss': os.environ['ASC_ISSUER_ID'], 'iat': now, 'exp': now + 900, 'aud': 'appstoreconnect-v1'},
                      open(p8).read(), algorithm='ES256', headers={'kid': os.environ['ASC_KEY_ID'], 'typ': 'JWT'})

def call(tok, method, path, body=None, ok_missing=False):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        msg = e.read().decode()[:600]
        if ok_missing and e.code == 404: return {}
        raise RuntimeError('%s %s → %d %s' % (method, path.split('?')[0], e.code, msg))

def create(p8, bundle, out):
    tok = token(p8)
    os.makedirs(out, exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, 'CI Distribution'), x509.NameAttribute(NameOID.COUNTRY_NAME, 'TR')])
    ).sign(key, hashes.SHA256())
    body = {'data': {'type': 'certificates', 'attributes': {
        'certificateType': 'DISTRIBUTION', 'csrContent': csr.public_bytes(serialization.Encoding.PEM).decode()}}}
    try:
        cert = call(tok, 'POST', '/certificates', body)
    except RuntimeError as e:
        # sınır dolduysa (önceki yarım kalmış işlerden) en eski dağıtım sertifikasını iptal edip bir kez daha dene
        if '409' not in str(e) and 'maximum' not in str(e).lower(): raise
        olds = call(tok, 'GET', '/certificates?filter[certificateType]=DISTRIBUTION,IOS_DISTRIBUTION&limit=50')['data']
        olds.sort(key=lambda c: c['attributes'].get('expirationDate', ''))
        if not olds: raise
        print('Sertifika sınırı dolu; en eski dağıtım sertifikası iptal ediliyor.')
        call(tok, 'DELETE', '/certificates/' + olds[0]['id'])
        cert = call(tok, 'POST', '/certificates', body)
    cid = cert['data']['id']
    open(os.path.join(out, 'cert.der'), 'wb').write(base64.b64decode(cert['data']['attributes']['certificateContent']))
    open(os.path.join(out, 'key.pem'), 'wb').write(key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()))
    os.chmod(os.path.join(out, 'key.pem'), 0o600)
    info = {'cert_id': cid}
    open(os.path.join(out, 'info.json'), 'w').write(json.dumps(info))   # profil hatasında da sertifika iptal edilebilsin
    bids = call(tok, 'GET', '/bundleIds?filter[identifier]=%s&limit=20' % bundle)['data']
    bids = [b for b in bids if b['attributes']['identifier'] == bundle]
    if not bids: raise RuntimeError('Bundle ID kayıtlı değil: ' + bundle)
    name = 'CI %s %d' % (bundle, int(time.time()))
    prof = call(tok, 'POST', '/profiles', {'data': {'type': 'profiles', 'attributes': {'name': name, 'profileType': 'IOS_APP_STORE'},
        'relationships': {'bundleId': {'data': {'type': 'bundleIds', 'id': bids[0]['id']}},
                          'certificates': {'data': [{'type': 'certificates', 'id': cid}]}}}})
    open(os.path.join(out, 'profile.mobileprovision'), 'wb').write(base64.b64decode(prof['data']['attributes']['profileContent']))
    info.update(profile_id=prof['data']['id'], profile_uuid=prof['data']['attributes']['uuid'], profile_name=name)
    open(os.path.join(out, 'info.json'), 'w').write(json.dumps(info))
    print('Dağıtım sertifikası ve App Store profili hazır:', name)

def cleanup(p8, info_path):
    if not os.path.exists(info_path): return
    info = json.load(open(info_path)); tok = token(p8)
    if info.get('profile_id'): call(tok, 'DELETE', '/profiles/' + info['profile_id'], ok_missing=True)
    if info.get('cert_id'): call(tok, 'DELETE', '/certificates/' + info['cert_id'], ok_missing=True)
    print('Geçici sertifika ve profil kaldırıldı.')

if __name__ == '__main__':
    {'create': lambda: create(*sys.argv[2:5]), 'cleanup': lambda: cleanup(*sys.argv[2:4])}[sys.argv[1]]()
