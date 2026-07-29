import { chromium } from 'playwright';
const b = await chromium.launch({ channel: 'chromium' });
const p = await b.newPage();
p.on('console', m => { const t=m.text(); if(/error|blocked|refus|denied/i.test(t)) console.log('CONSOLE:', t.slice(0,160)); });
await p.addInitScript(() => localStorage.setItem('dp_beta_viewer','1'));
await p.goto('https://dance.takelord.com/dances/ballroom/waltz', { waitUntil: 'domcontentloaded' });
await p.waitForTimeout(12000);
console.log(await p.evaluate(() => {
  const f = document.querySelector('iframe');
  return { iframeSrc: f?.src?.slice(0,90), ytLoaded: typeof window.YT, hasPlayerCtor: typeof window.YT?.Player };
}));
await b.close();
