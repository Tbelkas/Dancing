// Does a page show an empty state ("no videos", "no results") while the request that would
// fill it is still in flight?
//
// A loading skeleton only helps if it covers every request the page needs. Where a second
// request fires after the first one lands, the template can render its empty branch in the
// gap — the user is told there is nothing, then handed something. This measures that gap.
//
//   npm run flicker:empty-state
//   DANCES='["/dances/hip-hop/6-step"]' node scripts/flicker/empty-state-flash.mjs
import { chromium, login, record, windows, pace, BASE_URL, API_URL } from './probe-lib.mjs';

const RUNS = Number(process.env.RUNS || 2);

const creds = await login();

// Pick real dances off the catalog: ones that do have videos, so "no videos" is always a lie.
const res = await fetch(`${API_URL}/search/dances?sort=popular&pageSize=40`, {
  headers: { authorization: `Bearer ${creds.token}` },
});
const withVideos = (await res.json()).items.filter(d => d.videoCount > 0);
const dances = process.env.DANCES
  ? JSON.parse(process.env.DANCES)
  : withVideos.slice(0, 4).map(d => (d.styleSlug ? `/dances/${d.styleSlug}/${d.slug}` : `/dances/${d.slug}`));

const probes = [
  { name: 'skel', sel: '.detail-skeleton', mode: 'exists' },
  { name: 'title', sel: '[data-testid=dance-title]', mode: 'exists' },
  { name: 'noVideos', sel: '.videos-section p.empty', mode: 'exists' },
  { name: 'videos', sel: '.video-item, .video-list-item, .video-grid', mode: 'count' },
];

console.log(`base: ${BASE_URL}`);
console.log(`\ndance                                  skeleton   "No videos available" on screen   videos`);
const browser = await chromium.launch();
for (const url of dances) {
  for (let i = 0; i < RUNS; i++) {
    const { log, api } = await record(browser, creds, { url: BASE_URL + url, probes, settleMs: 5000 });
    const skel = windows(log, 'skel').map(w => w[2]);
    const lie = windows(log, 'noVideos');
    const videos = log.length ? log[log.length - 1].videos : 0;
    const danceReq = api.find(a => a.path.startsWith('dances/'));
    const videoReq = api.find(a => a.path.startsWith('videos/dance/'));
    const gap = danceReq && videoReq ? `dance@${danceReq.t}ms → videos@${videoReq.t}ms` : '';
    console.log(
      `${url.padEnd(38)} ${(skel.length ? skel.join(',') + 'ms' : 'none').padEnd(10)} ` +
      `${(lie.length ? lie.map(w => `${w[2]}ms (from ${w[0]})`).join(', ') : 'never shown').padEnd(33)} ${videos}`
    );
    if (gap) console.log(`${' '.repeat(38)} ${gap}`);
    await pace();
  }
}
await browser.close();
