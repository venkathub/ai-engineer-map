// Optional: serve ./run.sh, then NODE_PATH=<playwright modules> node tests/lab-browser.cjs
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const { readFile, mkdir } = require('node:fs/promises');
const path = require('node:path');

(async () => {
  const root = path.join(__dirname, '..');
  const catalog = JSON.parse(await readFile(path.join(root, 'curriculum/hoe.json'), 'utf8'));
  const curriculum = JSON.parse(await readFile(path.join(root, 'curriculum/concepts.json'), 'utf8'));
  const browser = await chromium.launch({executablePath:process.env.CHROME_PATH || '/usr/bin/google-chrome', headless:true, args:['--no-sandbox']});
  try {
    const page = await browser.newPage({viewport:{width:1440, height:1050}, reducedMotion:'reduce'});
    const errors = [];
    const requests = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => requests.push(request.url()));
    const base = process.env.BASE_URL || 'http://127.0.0.1:8000';
    async function open(id) {
      await page.goto(`${base}/lab.html?id=${id}`);
      await page.waitForSelector('#lab-execution[aria-busy="false"]');
    }
    await mkdir(path.join(root, 'outputs'), {recursive:true});
    for (const id of ['python-ai', 'embeddings', 'model-apis', 'peft']) {
      await open(id);
      const profile = catalog.profiles[catalog.topics[id]];
      const panel = page.locator('#lab-execution');
      const text = await panel.textContent();
      assert.equal(await page.locator('[data-execution-status]').getAttribute('data-execution-status'), profile.status);
      for (const field of ['requirements', 'artifacts', 'cleanup']) {
        for (const value of profile[field]) assert.ok(text.includes(value), `${id}: missing ${value}`);
      }
      assert.ok(text.includes(profile.estimatedCost));
      assert.ok(text.includes(`${profile.estimatedMinutes} minutes`));
      for (const key of ['setup', 'run', 'verify']) {
        if (profile[key]) assert.ok(text.includes(profile[key].join(' ')));
      }
      for (const prereq of curriculum.concepts.find(c => c.id === id).prerequisites) {
        assert.equal(await panel.locator(`a[href="concept.html?id=${prereq}"]`).count(), 1);
      }
      if (profile.status === 'setup-ready') assert.match(text, /topic experiment is not automated/);
      if (id === 'peft') {
        assert.match(text, /Environment verification only/);
        assert.match(text, /--allow-billable/);
        assert.match(text, /paused instances can retain billable storage/);
      }
      const progress = await page.evaluate(() => localStorage.getItem('ai-map-progress-v2'));
      await page.locator('#code-editor').fill('TODO: deliberately unfinished artifact');
      await page.locator('#run-tests').focus();
      await page.keyboard.press('Enter');
      assert.match(await page.locator('#terminal').textContent(), /No code was executed or verified/);
      assert.equal(await page.evaluate(() => localStorage.getItem('ai-map-progress-v2')), progress);
      assert.equal(await page.locator('#test-list .pass').count(), 0);
      assert.equal(await page.evaluate(() => document.activeElement.id), 'run-tests');
      await page.evaluate(() => scrollTo(0, 0));
      await page.screenshot({path:path.join(root, `outputs/lab-${id}-desktop.png`)});
      for (const width of [320, 720, 1050]) {
        await page.setViewportSize({width, height:900});
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `${id}: overflow at ${width}`);
        assert.equal(await page.locator('.test-panel').isVisible(), true);
        assert.equal(await page.evaluate(() => getComputedStyle(document.documentElement).scrollBehavior), 'auto');
        if (width === 320 && id === 'peft') await page.screenshot({path:path.join(root, 'outputs/lab-peft-mobile.png'), fullPage:true});
      }
      await page.setViewportSize({width:1440, height:1050});
    }
    // Failed catalog loading preserves the draft, and retry restores keyboard focus.
    await page.route('**/curriculum/hoe.json', route => route.fulfill({status:503, body:'Unavailable'}));
    await open('embeddings');
    await page.locator('#code-editor').fill('preserve this draft');
    assert.match(await page.locator('#lab-execution').textContent(), /Readiness is unknown/);
    await page.unroute('**/curriculum/hoe.json');
    await page.locator('#retry-execution').focus();
    await page.keyboard.press('Enter');
    await page.waitForSelector('[data-execution-status="automated"]');
    assert.equal(await page.locator('#code-editor').inputValue(), 'preserve this draft');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'lab-execution');
    const missing = structuredClone(catalog);
    delete missing.topics.embeddings;
    const incomplete = structuredClone(catalog);
    incomplete.profiles['local-retrieval'].verify = null;
    for (const body of ['{invalid json', JSON.stringify({...catalog, schemaVersion:99}), JSON.stringify(missing), JSON.stringify(incomplete)]) {
      await page.route('**/curriculum/hoe.json', route => route.fulfill({contentType:'application/json', body}));
      await open('embeddings');
      assert.equal(await page.locator('[data-execution-status]').count(), 0);
      assert.equal(await page.locator('#retry-execution').count(), 1);
      assert.ok((await page.locator('#code-editor').inputValue()).length > 0);
      await page.unroute('**/curriculum/hoe.json');
    }
    // Catalog text and shell arguments must survive HTML safely, without executing markup.
    const escaped = structuredClone(catalog);
    const payload = '<img src=x onerror="window.injected=true">';
    escaped.profiles['local-retrieval'].artifacts = [payload];
    escaped.profiles['local-retrieval'].run = ['python3', "a file's name.py", '$(touch nope)'];
    await page.route('**/curriculum/hoe.json', route => route.fulfill({contentType:'application/json', body:JSON.stringify(escaped)}));
    await open('embeddings');
    assert.ok((await page.locator('#lab-execution').textContent()).includes(payload));
    assert.equal(await page.locator('#lab-execution img').count(), 0);
    assert.equal(await page.evaluate(() => window.injected), undefined);
    const commands = await page.locator('.execution-command code').allTextContents();
    assert.ok(commands.includes(`python3 'a file'"'"'s name.py' '$(touch nope)'`));
    assert.deepEqual(errors, []);
    assert.ok(requests.every(url => url.startsWith(base)), 'No provider or GPU requests are allowed');
    console.log('Lab browser regression passed: four profiles, catalog fidelity, prerequisites, honest review, responsive layout, keyboard, reduced motion, failure/retry and safe rendering.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
