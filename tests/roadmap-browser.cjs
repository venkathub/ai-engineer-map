// Optional browser regression: NODE_PATH=<playwright modules> node tests/roadmap-browser.cjs
// Start ./run.sh first. No browser dependency is needed to run the site.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const { mkdir } = require('node:fs/promises');

(async () => {
  const browser = await chromium.launch({executablePath: process.env.CHROME_PATH || '/usr/bin/google-chrome', headless: true, args: ['--no-sandbox']});
  try {
    const page = await browser.newPage({viewport: {width: 1440, height: 1000}, reducedMotion: 'reduce'});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(`${process.env.BASE_URL || 'http://127.0.0.1:8000'}/roadmap.html?id=embeddings`);
    await page.waitForSelector('[data-column="1"]');
    const selected = () => page.locator('[data-column="1"]');
    const focusId = () => page.evaluate(() => document.activeElement.dataset.dependency);
    assert.equal(await selected().getAttribute('data-dependency'), 'embeddings');
    const data = await page.evaluate(() => fetch('curriculum/concepts.json').then(r => r.json()));
    const item = data.concepts.find(c => c.id === 'embeddings');
    const dependents = data.concepts.filter(c => c.prerequisites.includes(item.id));
    assert.equal(await page.locator('.dependency-edges g path').count(), item.prerequisites.length + dependents.length);
    await selected().focus();
    await page.keyboard.press('ArrowLeft');
    assert.equal(await focusId(), item.prerequisites[0]);
    await page.keyboard.press('ArrowRight');
    assert.equal(await focusId(), item.id);
    await page.keyboard.press('ArrowRight');
    assert.equal(await focusId(), dependents[0].id);
    await page.keyboard.press('ArrowDown');
    assert.equal(await focusId(), dependents[Math.min(1, dependents.length - 1)].id);
    await page.keyboard.press('Home');
    assert.equal(await focusId(), item.prerequisites[0]);
    await page.keyboard.press('End');
    assert.equal(await focusId(), dependents.at(-1).id);
    await page.keyboard.press('Enter');
    assert.equal(await selected().getAttribute('data-dependency'), dependents.at(-1).id);
    assert.equal(await focusId(), dependents.at(-1).id);
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => !!document.activeElement.closest('#dependency-graph')), false);
    await page.locator('[data-topic="embeddings"]').click();
    assert.equal(await page.evaluate(() => document.activeElement.dataset.topic), 'embeddings');
    await page.locator('#search').fill('embeddings');
    const related = page.locator('[data-column="0"]').first();
    const relatedId = await related.getAttribute('data-dependency');
    await related.focus();
    await page.keyboard.press('Space');
    assert.equal(await selected().getAttribute('data-dependency'), relatedId);
    assert.equal(await page.locator('#search').inputValue(), '');
    assert.match(await page.locator('#roadmap-status').textContent(), /Filters cleared/);
    await page.locator('#search').fill('no-such-topic-xyz');
    assert.equal(await page.locator('[data-dependency]').count(), 0);
    assert.match(await page.locator('#concept-inspector').textContent(), /No topic selected/);
    assert.equal(await page.evaluate(() => document.activeElement.id), 'search');
    await page.locator('#search').fill('');
    await page.locator('#hide-complete').check();
    const completing = await selected().getAttribute('data-dependency');
    await page.locator('#toggle-complete').click();
    assert.notEqual(await selected().getAttribute('data-dependency'), completing);
    assert.equal(await page.evaluate(() => document.activeElement.id), 'toggle-complete');
    await page.locator('[data-track="rag"]').click();
    const currentId = await selected().getAttribute('data-dependency');
    assert.equal(data.concepts.find(c => c.id === currentId).track, 'rag');
    assert.equal(await page.locator('.topic-card[aria-pressed="true"]').count(), 1);
    await page.locator('[data-track="all"]').click();
    await page.locator('[data-topic="embeddings"]').click();
    await page.locator('.dependency-panel').scrollIntoViewIfNeeded();
    await mkdir('outputs', {recursive:true});
    await page.screenshot({path:'outputs/roadmap-desktop.png'});
    for (const width of [320, 720, 1050, 1440]) {
      await page.setViewportSize({width, height:900});
      await selected().focus();
      await page.keyboard.press('End');
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `Page overflow at ${width}`);
      assert.equal(await page.evaluate(() => getComputedStyle(document.documentElement).scrollBehavior), 'auto');
      const edgesValid = await page.locator('.dependency-edges g path').evaluateAll(paths => paths.every(p => !/NaN/.test(p.getAttribute('d'))));
      assert.equal(edgesValid, true);
      if (width === 320) await page.screenshot({path:'outputs/roadmap-mobile.png'});
    }
    assert.deepEqual(errors, []);
    console.log('Roadmap browser regression passed: relationships, keyboard, filters, focus, completion, responsive layout and reduced motion.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
