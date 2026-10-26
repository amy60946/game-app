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

// PofiQrScan: giriş ekranında QR okuma (26 Ekim 2026; ortak akislar.md §2.0). Yalnız AVFoundation (ek kütüphane yok): tam ekran
// kamera önizlemesi, ortada kılavuz kare, altta "Vazgeç". İlk QR okununca kamera kapanır, metin Unity'ye gider
// (UnitySendMessage → <alıcı>.OnQrScanned). Vazgeç / izin yok → <alıcı>.OnQrCancel("cancel" | "denied" | "nocamera").
// Görüntü hiçbir yere kaydedilmez ya da gönderilmez. ARC açık ya da kapalı derlenebilir (retain/release çağrısı yok).
#include "UnityInterface.h"

@interface PofiQrController : UIViewController <AVCaptureMetadataOutputObjectsDelegate>
@property (nonatomic, strong) AVCaptureSession *session;
@property (nonatomic, strong) AVCaptureVideoPreviewLayer *preview;
@property (nonatomic, strong) UIView *frameView;
@property (nonatomic, copy) NSString *receiver;
@property (nonatomic, copy) NSString *titleText;
@property (nonatomic, copy) NSString *cancelText;
@property (nonatomic, assign) BOOL finished;
@property (nonatomic, copy) NSString *failReason;   // viewDidLoad'da kurulamadıysa: sunum bitince (viewDidAppear) kapanır
@end

static PofiQrController *gPofiQr = nil;   // gösterilirken canlı tut

@implementation PofiQrController

- (UIInterfaceOrientationMask)supportedInterfaceOrientations { return UIInterfaceOrientationMaskLandscape; }
- (BOOL)prefersStatusBarHidden { return YES; }

- (void)viewDidLoad
{
    [super viewDidLoad];
    self.view.backgroundColor = [UIColor blackColor];
    AVCaptureDevice *dev = [AVCaptureDevice defaultDeviceWithMediaType:AVMediaTypeVideo];
    if (dev == nil) { self.failReason = @"nocamera"; return; }
    NSError *err = nil;
    AVCaptureDeviceInput *input = [AVCaptureDeviceInput deviceInputWithDevice:dev error:&err];
    if (input == nil) { self.failReason = @"denied"; return; }
    self.session = [[AVCaptureSession alloc] init];
    if ([self.session canAddInput:input]) [self.session addInput:input];
    AVCaptureMetadataOutput *output = [[AVCaptureMetadataOutput alloc] init];
    if ([self.session canAddOutput:output]) [self.session addOutput:output];
    [output setMetadataObjectsDelegate:self queue:dispatch_get_main_queue()];
    if ([[output availableMetadataObjectTypes] containsObject:AVMetadataObjectTypeQRCode])
        output.metadataObjectTypes = @[AVMetadataObjectTypeQRCode];
    self.preview = [AVCaptureVideoPreviewLayer layerWithSession:self.session];
    self.preview.videoGravity = AVLayerVideoGravityResizeAspectFill;
    [self.view.layer addSublayer:self.preview];

    // kılavuz kare (krem kenarlı, köşeleri yuvarlak) + başlık + Vazgeç
    self.frameView = [[UIView alloc] initWithFrame:CGRectZero];
    self.frameView.layer.borderColor = [UIColor colorWithRed:1.0 green:0.85 blue:0.35 alpha:1.0].CGColor;
    self.frameView.layer.borderWidth = 5.0;
    self.frameView.layer.cornerRadius = 22.0;
    [self.view addSubview:self.frameView];

    UILabel *title = [[UILabel alloc] initWithFrame:CGRectZero];
    title.tag = 11;
    title.text = self.titleText;
    title.textColor = [UIColor whiteColor];
    title.font = [UIFont boldSystemFontOfSize:24];
    title.textAlignment = NSTextAlignmentCenter;
    title.numberOfLines = 2;
    title.shadowColor = [UIColor colorWithWhite:0 alpha:0.6];
    title.shadowOffset = CGSizeMake(0, 2);
    [self.view addSubview:title];

    UIButton *cancel = [UIButton buttonWithType:UIButtonTypeSystem];
    cancel.tag = 12;
    [cancel setTitle:self.cancelText forState:UIControlStateNormal];
    [cancel setTitleColor:[UIColor colorWithRed:0.42 green:0.25 blue:0.06 alpha:1] forState:UIControlStateNormal];
    cancel.titleLabel.font = [UIFont boldSystemFontOfSize:22];
    cancel.backgroundColor = [UIColor colorWithRed:1.0 green:0.97 blue:0.88 alpha:1.0];
    cancel.layer.cornerRadius = 26.0;
    [cancel addTarget:self action:@selector(onCancel) forControlEvents:UIControlEventTouchUpInside];
    [self.view addSubview:cancel];
}

- (void)viewDidAppear:(BOOL)animated
{
    [super viewDidAppear:animated];
    if (self.failReason != nil) { [self finish:nil reason:self.failReason]; return; }
    if (self.finished || self.session == nil) return;
    AVAuthorizationStatus st = [AVCaptureDevice authorizationStatusForMediaType:AVMediaTypeVideo];
    if (st == AVAuthorizationStatusDenied || st == AVAuthorizationStatusRestricted) { [self finish:nil reason:@"denied"]; return; }
    AVCaptureSession *s = self.session;
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), ^{ [s startRunning]; });
}

- (void)viewDidLayoutSubviews
{
    [super viewDidLayoutSubviews];
    CGRect b = self.view.bounds;
    self.preview.frame = b;
    UIInterfaceOrientation o = self.view.window.windowScene.interfaceOrientation;
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
    if (self.preview.connection.isVideoOrientationSupported)
        self.preview.connection.videoOrientation = o == UIInterfaceOrientationLandscapeLeft ? AVCaptureVideoOrientationLandscapeLeft
                                                 : o == UIInterfaceOrientationLandscapeRight ? AVCaptureVideoOrientationLandscapeRight
                                                 : AVCaptureVideoOrientationPortrait;
#pragma clang diagnostic pop
    CGFloat side = MIN(b.size.width, b.size.height) * 0.56;
    self.frameView.frame = CGRectMake((b.size.width - side) / 2, (b.size.height - side) / 2 - 10, side, side);
    UIView *title = [self.view viewWithTag:11];
    title.frame = CGRectMake(40, 18, b.size.width - 80, 64);
    UIView *cancel = [self.view viewWithTag:12];
    cancel.frame = CGRectMake((b.size.width - 220) / 2, b.size.height - 70, 220, 52);
}

- (void)captureOutput:(AVCaptureOutput *)output didOutputMetadataObjects:(NSArray<__kindof AVMetadataObject *> *)objects fromConnection:(AVCaptureConnection *)connection
{
    if (self.finished) return;
    for (AVMetadataObject *o in objects)
    {
        if (![o isKindOfClass:[AVMetadataMachineReadableCodeObject class]]) continue;
        NSString *text = ((AVMetadataMachineReadableCodeObject *)o).stringValue;
        if (text.length == 0) continue;
        UINotificationFeedbackGenerator *g = [[UINotificationFeedbackGenerator alloc] init];
        [g notificationOccurred:UINotificationFeedbackTypeSuccess];
        [self finish:text reason:nil];
        return;
    }
}

- (void)onCancel { [self finish:nil reason:@"cancel"]; }

- (void)finish:(NSString *)text reason:(NSString *)reason
{
    if (self.finished) return;
    self.finished = YES;
    AVCaptureSession *s = self.session;
    if (s != nil) dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), ^{ [s stopRunning]; });
    NSString *recv = self.receiver;
    void (^send)(void) = ^{
        if (text != nil) UnitySendMessage([recv UTF8String], "OnQrScanned", [text UTF8String]);
        else UnitySendMessage([recv UTF8String], "OnQrCancel", [reason UTF8String]);
        gPofiQr = nil;
    };
    if (self.presentingViewController != nil) [self dismissViewControllerAnimated:YES completion:send];
    else dispatch_async(dispatch_get_main_queue(), send);
}

@end

extern "C" int PofiQrAvailable()
{
    return [AVCaptureDevice defaultDeviceWithMediaType:AVMediaTypeVideo] != nil ? 1 : 0;
}

extern "C" void PofiQrScan(const char *receiver, const char *title, const char *cancel)
{
    NSString *recv = [NSString stringWithUTF8String:receiver ? receiver : "PofiQr"];
    NSString *t = [NSString stringWithUTF8String:title ? title : ""];
    NSString *c = [NSString stringWithUTF8String:cancel ? cancel : "Vazgeç"];
    dispatch_async(dispatch_get_main_queue(), ^{
        if (gPofiQr != nil) return;
        void (^open)(void) = ^{
            PofiQrController *vc = [[PofiQrController alloc] init];
            vc.receiver = recv; vc.titleText = t; vc.cancelText = c;
            vc.modalPresentationStyle = UIModalPresentationFullScreen;
            gPofiQr = vc;
            [UnityGetGLViewController() presentViewController:vc animated:YES completion:nil];
        };
        AVAuthorizationStatus st = [AVCaptureDevice authorizationStatusForMediaType:AVMediaTypeVideo];
        if (st == AVAuthorizationStatusNotDetermined)
        {
            [AVCaptureDevice requestAccessForMediaType:AVMediaTypeVideo completionHandler:^(BOOL granted) {
                dispatch_async(dispatch_get_main_queue(), ^{
                    if (granted) open();
                    else UnitySendMessage([recv UTF8String], "OnQrCancel", "denied");
                });
            }];
        }
        else if (st == AVAuthorizationStatusAuthorized) open();
        else UnitySendMessage([recv UTF8String], "OnQrCancel", "denied");
    });
}
