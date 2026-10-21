// Pofi Adası — iOS yerel yardımcıları (TestFlight / App Store derlemesi).
// PofiHapticIOS: hafif/orta dokunsal darbe (UIImpactFeedbackGenerator); WebGL'deki PofiHaptics.jslib'in iOS karşılığı.
// PofiAudioPlayback: ses oturumu "playback" — iPhone sessiz düğmesi açıkken de müzik/efekt duyulur (WebGL'deki audioSession ile aynı karar).
#import <UIKit/UIKit.h>
#import <AVFoundation/AVFoundation.h>

extern "C" void PofiHapticIOS(int strength)
{
    dispatch_async(dispatch_get_main_queue(), ^{
        UIImpactFeedbackStyle style = strength > 15 ? UIImpactFeedbackStyleMedium : UIImpactFeedbackStyleLight;
        UIImpactFeedbackGenerator *g = [[UIImpactFeedbackGenerator alloc] initWithStyle:style];
        [g prepare];
        [g impactOccurred];
    });
}

extern "C" void PofiAudioPlayback()
{
    NSError *err = nil;
    [[AVAudioSession sharedInstance] setCategory:AVAudioSessionCategoryPlayback
                                     withOptions:AVAudioSessionCategoryOptionMixWithOthers
                                           error:&err];
    [[AVAudioSession sharedInstance] setActive:YES error:&err];
}

// PofiKeychain*: oturum yenileme belirteci iOS Keychain'de (güvenlik denetimi M4; PlayerPrefs yedeklere düz yazı düşer).
// Erişim: cihaz ilk açıldıktan sonra, YALNIZ BU CİHAZ (yedekle başka cihaza taşınmaz). Saf CoreFoundation (ARC'den bağımsız).
#import <Security/Security.h>
#include <string.h>
#include <stdlib.h>

static CFMutableDictionaryRef PofiKcQuery(const char *key)
{
    CFMutableDictionaryRef q = CFDictionaryCreateMutable(kCFAllocatorDefault, 0, &kCFTypeDictionaryKeyCallBacks, &kCFTypeDictionaryValueCallBacks);
    CFStringRef account = CFStringCreateWithCString(kCFAllocatorDefault, key, kCFStringEncodingUTF8);
    CFDictionarySetValue(q, kSecClass, kSecClassGenericPassword);
    CFDictionarySetValue(q, kSecAttrService, CFSTR("pofi.session"));
    CFDictionarySetValue(q, kSecAttrAccount, account);
    CFRelease(account);
    return q;
}

extern "C" int PofiKeychainSet(const char *key, const char *value)
{
    if (key == NULL || value == NULL) return 0;
    CFMutableDictionaryRef q = PofiKcQuery(key);
    SecItemDelete(q);
    CFDataRef data = CFDataCreate(kCFAllocatorDefault, (const UInt8 *)value, (CFIndex)strlen(value));
    CFDictionarySetValue(q, kSecValueData, data);
    CFDictionarySetValue(q, kSecAttrAccessible, kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly);
    OSStatus st = SecItemAdd(q, NULL);
    CFRelease(data);
    CFRelease(q);
    return st == errSecSuccess ? 1 : 0;
}

// Unity dönen char* dizgisini kendisi free() eder: malloc ile kopyalanır.
extern "C" char *PofiKeychainGet(const char *key)
{
    if (key == NULL) return NULL;
    CFMutableDictionaryRef q = PofiKcQuery(key);
    CFDictionarySetValue(q, kSecReturnData, kCFBooleanTrue);
    CFDictionarySetValue(q, kSecMatchLimit, kSecMatchLimitOne);
    CFTypeRef result = NULL;
    OSStatus st = SecItemCopyMatching(q, &result);
    CFRelease(q);
    if (st != errSecSuccess || result == NULL) return NULL;
    CFDataRef data = (CFDataRef)result;
    CFIndex len = CFDataGetLength(data);
    char *out = (char *)malloc((size_t)len + 1);
    if (out != NULL)
    {
        memcpy(out, CFDataGetBytePtr(data), (size_t)len);
        out[len] = 0;
    }
    CFRelease(result);
    return out;
}

extern "C" void PofiKeychainDelete(const char *key)
{
    if (key == NULL) return;
    CFMutableDictionaryRef q = PofiKcQuery(key);
    SecItemDelete(q);
    CFRelease(q);
}
