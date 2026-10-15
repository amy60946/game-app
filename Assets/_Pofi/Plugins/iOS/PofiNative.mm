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
