// Test de fumée de l'interface Smart Office servie par le backend compilé (lancé par smoke_test.ps1).
const { chromium } = require('playwright');
(async () => {
  const [url, out] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  page.on('response', (r) => { if (r.status() >= 400) errors.push(`HTTP ${r.status()} ${r.url()}`); });
  await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(3000);
  const rootChildren = await page.evaluate(() => document.getElementById('root')?.children.length ?? -1);
  const text = (await page.evaluate(() => document.body.innerText)).slice(0, 300);
  await page.screenshot({ path: `${out}/smart_office.png` });
  let settingsOk = false;
  try {
    await page.goto(url.replace(/#.*$/, '') + '#settings', { waitUntil: 'networkidle' });
    await page.waitForSelector('text=Paramètres', { timeout: 15000 });
    await page.screenshot({ path: `${out}/parametres.png` });
    settingsOk = true;
  } catch (e) { errors.push('paramètres : ' + e.message.split('\n')[0]); }
  console.log(JSON.stringify({ rootChildren, text, settingsOk, errors }, null, 1));
  await browser.close();
  process.exit(rootChildren > 0 && settingsOk ? 0 : 1);
})();
