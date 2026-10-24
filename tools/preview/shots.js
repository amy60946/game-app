// Oyun önizlemesinin (webgl-preview, pack.sh çıktısı) yerelde ekran görüntüsü: python3 -m http.server 8765 ile sunulan klasör.
// Kullanım: node tools/preview/shots.js "dbg login B2B2B2;wait 4000;dbg pick pet_13;wait 8000;dbg tp -52 18 120;wait 3000;shot magara"
// Komutlar: dbg <PofiDebug komutu> · wait ms · click x y · drag x1 y1 x2 y2 ms · down x y · move x y · up · shot ad (ad.png). Ortam: URL, W, H, LOG=1.
const { chromium } = require(process.env.PW || '/opt/node-tools/node_modules/playwright');
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROME || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--use-gl=angle'] });
  const p = await b.newPage({ viewport: { width: +(process.env.W||1000), height: +(process.env.H||462) } });
  p.on('console', m => { const t = m.text(); if (t.includes('PofiDebug') || process.env.LOG) console.log('C:', t.slice(0,300)); });
  await p.goto(process.env.URL || 'http://localhost:8765/index.html');
  await p.waitForFunction(() => window.unityInstance, null, { timeout: 180000 });
  await p.waitForTimeout(3000);
  for (const raw of process.argv[2].split(';')) {
    const s = raw.trim(); if (!s) continue; const [cmd, ...a] = s.split(/\s+/);
    if (cmd === 'dbg') await p.evaluate(x => window.unityInstance.SendMessage('Bootstrap', 'PofiDebug', x), a.join(' '));
    else if (cmd === 'wait') await p.waitForTimeout(+a[0]);
    else if (cmd === 'click') { await p.mouse.click(+a[0], +a[1]); await p.waitForTimeout(400); }
    else if (cmd === 'drag') { await p.mouse.move(+a[0], +a[1]); await p.mouse.down(); const n=20; for (let i=1;i<=n;i++){ await p.mouse.move(+a[0]+(a[2]-a[0])*i/n, +a[1]+(a[3]-a[1])*i/n); await p.waitForTimeout((+a[4]||1000)/n);} await p.mouse.up(); }
    else if (cmd === 'down') { await p.mouse.move(+a[0], +a[1]); await p.mouse.down(); }   // basılı tut (uzun bas çekimi)
    else if (cmd === 'up') await p.mouse.up();
    else if (cmd === 'move') await p.mouse.move(+a[0], +a[1]);
    else if (cmd === 'shot') { await p.screenshot({ path: a[0] + '.png', timeout: 180000 }); console.log('shot', a[0]); }
  }
  await b.close();
})();
