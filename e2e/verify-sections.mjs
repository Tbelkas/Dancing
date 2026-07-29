import { chromium } from 'playwright';
const b = await chromium.launch({ channel: 'chromium' });
const p = await b.newPage();
await p.addInitScript(() => localStorage.setItem('dp_beta_viewer','1'));
await p.goto('https://dance.takelord.com/dances/ballroom/waltz', { waitUntil: 'domcontentloaded' });
for (let i=0;i<10;i++){
  await p.waitForTimeout(3000);
  const s = await p.evaluate(() => ({
    max: document.querySelector('.rc__seek')?.getAttribute('max'),
    ticks: [...document.querySelectorAll('.rc__section')].map(e => e.style.left),
    current: document.querySelectorAll('.rc__section--current').length,
    label: document.querySelector('.rc__section-label')?.textContent,
    chips: document.querySelectorAll('.segment-chip').length,
  }));
  console.log((i*3)+'s', JSON.stringify(s));
  if (s.ticks.length) { await p.screenshot({path:'sections.png'}); break; }
}
await b.close();
