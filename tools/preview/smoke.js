// Pofi Adası WebGL duman testi: PofiDebug komutlarıyla her ekranı açıp ekran görüntüsü alır.
// Kullanım: node smoke.js <url> <çıktı klasörü>
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [url, out] = [process.argv[2], process.argv[3]];
  fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
  const logs = [];
  p.on('pageerror', e => logs.push('PAGEERROR ' + e.message));
  p.on('console', m => {
    const t = m.text();
    if (t.includes('[PofiDebug]') || m.type() === 'error' || t.includes('Exception')) logs.push(m.type() + ': ' + t.slice(0, 400));
  });
  await p.goto(url);
  await p.waitForFunction(() => window.unityInstance, null, { timeout: 120000 });
  await p.waitForTimeout(4000);
  let n = 0;
  const shot = async (name) => { n++; await p.screenshot({ path: `${out}/${String(n).padStart(2, '0')}_${name}.png` }); };
  const cmd = async (c, wait = 2500) => { await p.evaluate(c => window.unityInstance.SendMessage('Bootstrap', 'PofiDebug', c), c); await p.waitForTimeout(wait); };
  await shot('login');
  const steps = (process.argv[4] || 'A1A1A1').split(',');
  for (const code of steps) {
    await cmd('login ' + code); await shot('select_' + code);
    await cmd('pick pet_03'); await shot('name');
    await cmd('name Limon', 4000); await shot('home');
    for (const page of ['Map', 'Tasks']) { await cmd('open ' + page, 3000); await shot(page.toLowerCase()); }
    await cmd('approve', 3500); await shot('tasks_approved');
    for (const page of ['Shop', 'Wardrobe']) { await cmd('open ' + page, 3000); await shot(page.toLowerCase()); }
    await cmd('xp 6000', 3000); await shot('levelup'); await cmd('dismiss', 800);
    for (const page of ['Home', 'Map', 'Cards', 'Garden', 'Album', 'Settings', 'Decorate', 'Festival', 'Lighthouse'])
    { await cmd('open ' + page, 3000); await shot(page.toLowerCase()); }
    for (const g of ['coconut', 'help_pet', 'swim', 'fishing', 'cave', 'hike'])
    { await cmd('minigame ' + g, 2500); await shot('mg_' + g); }
  }
  fs.writeFileSync(`${out}/log.txt`, logs.join('\n'));
  console.log(logs.filter(l => !l.includes('[PofiDebug] ok')).slice(-30).join('\n') || 'hata yok');
  console.log(logs.filter(l => l.includes('[PofiDebug]')).length + ' komut');
  await b.close();
})();
