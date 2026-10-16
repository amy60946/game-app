# Takımda kayıtlı iOS cihazı yoksa bir yer tutucu cihaz kaydeder (App Store Connect API).
# Neden: Xcode otomatik imzası arşivi geliştirme profiliyle imzalar; bu profil en az bir kayıtlı cihaz ister.
# TestFlight/App Store dağıtımı bu cihazı kullanmaz (dışa aktarma dağıtım imzasıyla yeniden imzalar).
# Kullanım: python3 asc_device.py <p8_dosyası>   (ortam: ASC_KEY_ID, ASC_ISSUER_ID)
import json, os, secrets, sys, time, urllib.request
import jwt  # pyjwt[crypto]

key = open(sys.argv[1]).read()
now = int(time.time())
tok = jwt.encode({'iss': os.environ['ASC_ISSUER_ID'], 'iat': now, 'exp': now + 900, 'aud': 'appstoreconnect-v1'},
                 key, algorithm='ES256', headers={'kid': os.environ['ASC_KEY_ID'], 'typ': 'JWT'})
API = 'https://api.appstoreconnect.apple.com/v1/devices'

def call(url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
                                 headers={'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as r: return json.load(r)
    except urllib.error.HTTPError as e:
        print('::error::App Store Connect API', e.code, e.read().decode()[:500]); sys.exit(1)

have = call(API + '?filter[platform]=IOS&filter[status]=ENABLED&limit=1')['data']
if have:
    print('Kayıtlı cihaz var (%d+), yeni kayıt gerekmez.' % len(have)); sys.exit(0)
udid = '00008110-' + secrets.token_hex(8).upper()
call(API, {'data': {'type': 'devices', 'attributes': {'name': 'CI yer tutucu', 'udid': udid, 'platform': 'IOS'}}})
print('Yer tutucu cihaz kaydedildi.')
