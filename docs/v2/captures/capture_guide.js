// Captures d'écran du guide utilisateur, prises sur la base de DÉMONSTRATION (données fictives).
// 1. python -m demo.build_demo <dossier>   (depuis SmartOffice/)
// 2. AFMI_DESKTOP_DB=<dossier>/database.db AFMI_DATA_DIR=<dossier>/data python -m uvicorn backend.main:app --port 8765
// 3. NODE_PATH=$(npm root -g) node docs/v2/captures/capture_guide.js docs/v2/images
const { chromium } = require('playwright');

(async () => {
  const out = process.argv[2] || 'docs/v2/images';
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  const shot = async (name, full = false) => { await page.waitForTimeout(700); await page.screenshot({ path: `${out}/${name}.png`, fullPage: full }); };
  const menu = async (label) => { await page.getByText(label, { exact: true }).first().click(); await page.waitForTimeout(800); };
  const step = async (name, fn) => { try { await fn(); console.log('ok', name); } catch (e) { console.log('ÉCHEC', name, e.message.split('\n')[0]); } };

  await page.goto('http://127.0.0.1:8765/');
  await page.getByRole('button', { name: 'FR', exact: true }).click();

  await step('releves', async () => {
    await menu('Relevés bancaires');
    const sel = page.getByLabel('Relevé à vérifier');
    const value = await sel.locator('option', { hasText: 'à vérifier' }).first().getAttribute('value');
    await sel.selectOption(value);
    await page.waitForTimeout(1500);
    await shot('01_releves_validation');
  });
  await step('ged', async () => {
    await menu('Documents & cycle de vie');
    await page.getByLabel('Projet', { exact: true }).selectOption({ index: 1 });
    await page.waitForTimeout(1200);
    await shot('02_ged_documents');
    await page.getByRole('button', { name: /Frise du cycle de vie/ }).click();
    await shot('03_ged_frise');
  });
  await step('rapports', async () => { await menu('Rapports annuels'); await shot('04_rapports_annuels'); });
  await step('editeur', async () => {
    await menu('Éditeur de documents');
    await page.getByLabel('Ouvrir un document').selectOption({ index: 1 });
    await page.waitForTimeout(2500);
    await shot('05_editeur_rapport');
  });
  await step('indicateurs', async () => {
    await menu('Indicateurs & bénéficiaires');
    const sel = page.getByLabel('Projet', { exact: true });
    if (await sel.count()) await sel.selectOption({ index: 1 });
    await shot('06_indicateurs');
  });
  await step('photos', async () => { await menu('Photos des activités'); await shot('07_photos'); });
  await step('chartes', async () => { await menu('Chartes & modèles'); await shot('08_chartes'); });
  await step('parametres', async () => {
    await menu('Paramètres');
    await shot('09_parametres');
    await page.getByRole('button', { name: /Intelligence artificielle/ }).click();
    await shot('10_parametres_ia');
    await page.getByRole('button', { name: /Sauvegardes/ }).first().click();
    await shot('11_parametres_sauvegardes');
  });
  console.log(JSON.stringify({ errors }));
  await browser.close();
})();
