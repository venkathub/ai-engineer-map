// Serve ./run.sh first; use an existing Playwright installation and Chrome.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const { readFile, mkdir } = require('node:fs/promises');
const path = require('node:path');

(async () => {
  const root = path.join(__dirname, '..');
  const catalog = JSON.parse(await readFile(path.join(root, 'content/tutorials.json'), 'utf8'));
  const baseline = await readFile(path.join(root, 'labs/rag_path.py'), 'utf8');
  const base = process.env.BASE_URL || 'http://127.0.0.1:8000';
  const browser = await chromium.launch({executablePath:process.env.CHROME_PATH || '/usr/bin/google-chrome', headless:true, args:['--no-sandbox']});
  try {
    const page = await browser.newPage({viewport:{width:1440, height:1000}, reducedMotion:'reduce'});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    for (const id of catalog.path) {
      await page.goto(`${base}/lesson.html?id=${id}`);
      await page.waitForSelector('[data-content-status="authored"]');
      const text = await page.locator('#lesson-article').textContent();
      assert.match(text, /Independent challenge/);
      assert.match(text, /Knowledge check/);
      assert.ok(text.includes(`./run.sh hoe run ${id}`));
      assert.ok(text.includes(`./run.sh hoe verify ${id}`));
      assert.equal(await page.locator('#lesson-article section h2').count(), 8);
      assert.equal(await page.locator('.tutorial-path li').count(), 11);
      assert.equal(await page.locator('#lesson-article pre code').count() >= 1, true);
      const source = await page.locator('.lesson-meta a').getAttribute('href');
      assert.equal(source, catalog.lessons[id].path);
      const sourceLink = page.locator('#lesson-article a').filter({hasText:/Runnable/}).first();
      assert.ok((await sourceLink.getAttribute('href')).endsWith('/labs/rag_path.py'));
      await page.locator('#lesson-complete').focus();
      await page.keyboard.press('Enter');
      assert.equal(await page.evaluate(() => document.activeElement.id), 'lesson-complete');
      for (const width of [320, 720, 1440]) {
        await page.setViewportSize({width, height:900});
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `${id} overflow at ${width}`);
      }
    }
    await page.goto(`${base}/lesson.html?id=mcp`);
    await page.waitForSelector('[data-content-status="outline"]');
    assert.equal(await page.locator('#lesson-complete').count(), 0);
    assert.match(await page.locator('#lesson-article').textContent(), /full tutorial not yet authored/);
    // No generic success page if authored content or its catalog fails.
    await page.route('**/content/rag/embeddings.md', route => route.fulfill({status:404, body:'Missing'}));
    await page.goto(`${base}/lesson.html?id=embeddings`);
    await page.getByRole('heading', {name:'Tutorial unavailable', exact:true}).waitFor();
    assert.equal(await page.locator('[data-content-status]').count(), 0);
    await page.unroute('**/content/rag/embeddings.md');
    // Raw HTML, script URLs, and command text are rendered as data.
    await page.route('**/content/rag/embeddings.md', route => route.fulfill({body:'# Fixture\n\n## Safety\n\n<img src=x onerror="window.injected=true">\n\n[bad](javascript:alert)\n\n~~~python\nprint("<script>")\n~~~'}));
    await page.goto(`${base}/lesson.html?id=embeddings`);
    await page.waitForSelector('[data-content-status="authored"]');
    assert.equal(await page.locator('#lesson-article img, #lesson-article script, a[href^="javascript:"]').count(), 0);
    assert.equal(await page.evaluate(() => window.injected), undefined);
    assert.match(await page.locator('#lesson-article pre').textContent(), /<script>/);
    await page.unroute('**/content/rag/embeddings.md');
    // A delayed baseline must not replace work typed while loading.
    let release;
    const gate = new Promise(resolve => { release = resolve; });
    await page.route('**/labs/rag_path.py', async route => { await gate; await route.fulfill({body:baseline}); });
    await page.goto(`${base}/lab.html?id=embeddings`, {waitUntil:'domcontentloaded'});
    await page.waitForSelector('#lab-content-status');
    await page.locator('#code-editor').fill('my draft');
    release();
    await page.getByText('Your draft was preserved.', {exact:false}).waitFor();
    assert.equal(await page.locator('#code-editor').inputValue(), 'my draft');
    await page.unroute('**/labs/rag_path.py');
    await page.goto(`${base}/lab.html?id=embeddings`);
    await page.getByText('Working baseline loaded.', {exact:false}).waitFor();
    assert.equal(await page.locator('#code-editor').inputValue(), baseline);
    assert.equal(await page.locator('#editor-filename').textContent(), 'rag_path.py');
    await page.locator('#code-editor').fill('edited artifact');
    const downloadPromise = page.waitForEvent('download');
    await page.locator('#download-artifact').click();
    const download = await downloadPromise;
    assert.equal(download.suggestedFilename(), 'rag_path.py');
    await mkdir(path.join(root, 'outputs'), {recursive:true});
    await download.saveAs(path.join(root, 'outputs/test-download.py'));
    assert.equal(await readFile(path.join(root, 'outputs/test-download.py'), 'utf8'), 'edited artifact');
    await page.goto(`${base}/lesson.html?id=grounded-generation`);
    await page.waitForSelector('[data-content-status="authored"]');
    await page.screenshot({path:path.join(root, 'outputs/tutorial-desktop.png')});
    await page.locator('#tutorial-section-3').scrollIntoViewIfNeeded();
    await page.screenshot({path:path.join(root, 'outputs/tutorial-example-desktop.png')});
    await page.setViewportSize({width:320, height:900});
    await page.locator('#tutorial-section-3').scrollIntoViewIfNeeded();
    await page.screenshot({path:path.join(root, 'outputs/tutorial-mobile.png')});
    assert.equal(await page.evaluate(() => getComputedStyle(document.documentElement).scrollBehavior), 'auto');
    assert.deepEqual(errors, []);
    console.log('Tutorial browser regression passed: 11 authored lessons, mobile layouts, outline/error states, safe Markdown, focus, baseline race and artifact download.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
