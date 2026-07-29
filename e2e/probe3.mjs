import { chromium } from 'playwright';
const b = await chromium.launch();
const p = await b.newPage();
await p.addInitScript(() => {
  localStorage.setItem('dp_beta_viewer','1');
  let t = 0;
  window.YT = {
    PlayerState: { UNSTARTED:-1, ENDED:0, PLAYING:1, PAUSED:2, BUFFERING:3, CUED:5 },
    Player: function (el, opts) {
      const self = this;
      window.__fake = this;
      this.getDuration = () => 600;
      this.getCurrentTime = () => t;
      this.getPlayerState = () => 2;
      this.setPlaybackRate = () => {};
      this.seekTo = s => { t = s; };
      this.playVideo = () => {}; this.pauseVideo = () => {};
      this.mute = () => {}; this.unMute = () => {}; this.isMuted = () => false;
      this.setVolume = () => {}; this.getVolume = () => 100;
      this.destroy = () => {};
      setTimeout(() => opts.events.onReady({ target: self }), 50);
    }
  };
});
await p.goto('https://dance.takelord.com/dances/ballroom/waltz', { waitUntil: 'domcontentloaded' });
await p.waitForTimeout(6000);
console.log(JSON.stringify(await p.evaluate(() => ({
  max: document.querySelector('.rc__seek')?.getAttribute('max'),
  ticks: [...document.querySelectorAll('.rc__section')].map(e => e.style.left),
  chips: [...document.querySelectorAll('.segment-chip__label, .segment-chip')].slice(0,6).map(e=>e.textContent.trim().slice(0,28)),
  label: document.querySelector('.rc__section-label')?.textContent,
})), null, 1));
// seek into a later section and re-read the label
await p.locator('.rc__seek').fill('300');
await p.waitForTimeout(500);
console.log('after seek to 300s:', JSON.stringify(await p.evaluate(() => ({
  label: document.querySelector('.rc__section-label')?.textContent,
  current: [...document.querySelectorAll('.rc__section--current')].map(e=>e.style.left),
}))));
await p.screenshot({ path: 'sections.png' });
await b.close();
