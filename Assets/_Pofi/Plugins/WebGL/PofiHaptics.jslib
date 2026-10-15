// Kısa hafif titreşim (kullanıcı isteği 15 Ekim 2026): Android tarayıcılarında navigator.vibrate;
// iPhone Safari'de vibrate yok — iOS 18+ "switch" onay kutusu değişince sistem hafif dokunsal his verir (gizli etiket tıklanır).
mergeInto(LibraryManager.library, {
  PofiHaptic: function (ms) {
    try {
      if (navigator.vibrate && navigator.vibrate(ms)) return;
      var l = window.__pofiHapticLabel;
      if (!l) {
        var i = document.createElement('input');
        i.type = 'checkbox'; i.setAttribute('switch', ''); i.id = '__pofi_haptic';
        var hide = 'position:fixed;left:-200px;top:-200px;width:1px;height:1px;opacity:0;pointer-events:none;';
        i.style.cssText = hide;
        l = document.createElement('label'); l.htmlFor = i.id; l.style.cssText = hide;
        document.body.appendChild(i); document.body.appendChild(l);
        window.__pofiHapticLabel = l;
      }
      l.click();
    } catch (e) { }
  }
});
