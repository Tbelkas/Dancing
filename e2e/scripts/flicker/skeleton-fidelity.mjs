// Does each skeleton actually stand in for what replaces it?
//
// skeleton-timing.mjs answers "is the skeleton on screen long enough to read". This answers
// the other half: while it is up, is it the right shape? A placeholder that reserves two
// cards where three land, or two lines where a whole form lands, still jerks the page — the
// skeleton just moves the jerk to a different moment.
//
// Every page here is loaded with its own API call slowed down, because on a warm API most of
// these skeletons never render at all. The delay only forces the state; the shapes it
// measures are the ones a user on a slow connection (or a busy Pi) actually sees.
//
//   npm run flicker:fidelity
import { chromium, login, record, windows, pace, BASE_URL } from './probe-lib.mjs';

const SLOW = Number(process.env.SLOW || 900);
const creds = await login();
const browser = await chromium.launch();

const runs = [];
const report = (title, lines) => runs.push({ title, lines });

// Last row where the skeleton was up, and the final row.
const phases = (log, skelKey) => {
  const during = [...log].reverse().find(r => r[skelKey]);
  return { during, after: log[log.length - 1] };
};

// ---------------------------------------------------------------- profile: card count
{
  const { log } = await record(browser, creds, {
    url: BASE_URL + '/profile', settleMs: 4000,
    delays: [{ match: '**/api/profile', ms: SLOW }],
    probes: [
      { name: 'skelCards', sel: '.skeleton-card', mode: 'count' },
      { name: 'columnCards', sel: '.stats-column > .card', mode: 'count' },
      { name: 'skel', sel: '.skeleton-card', mode: 'exists' },
    ],
  });
  const { during, after } = phases(log, 'skel');
  report('profile — stats column', [
    `skeleton placeholders in the column: ${during ? during.columnCards : 'skeleton never rendered'}`,
    `real cards that land there:          ${after.columnCards}`,
    `page height ${during ? during.h : '?'} -> ${after.h}  (${during ? after.h - during.h : '?'}px)`,
  ]);
  await pace();
}

// ---------------------------------------------------------------- practice: the review panel
for (const slow of [0, SLOW]) {
  const { log } = await record(browser, creds, {
    url: BASE_URL + '/practice', settleMs: 4500,
    delays: slow ? [{ match: '**/api/practice', ms: slow }] : [],
    probes: [
      { name: 'skel', sel: '.skeleton-stats', mode: 'exists' },
      { name: 'review', sel: '.review-panel', mode: 'exists' },
      { name: 'bodyTop', sel: '.skeleton-stats, .stats-block', mode: 'top' },
      { name: 'sessions', sel: '.session-group, .skeleton-session-card', mode: 'count' },
    ],
  });
  const reviewIn = log.find(r => r.review);
  const beforeReview = log.filter(r => !r.review).pop();
  report(`practice — review panel (sessions ${slow ? `slowed ${slow}ms` : 'at real speed'})`, [
    `review panel appears at:     ${reviewIn ? reviewIn.t + 'ms' : 'never'}`,
    `skeleton up at that moment:  ${reviewIn ? (reviewIn.skel ? 'yes' : 'no') : '-'}`,
    `content below it moves:      ${beforeReview && reviewIn ? `${beforeReview.bodyTop}px -> ${reviewIn.bodyTop}px (+${reviewIn.bodyTop - beforeReview.bodyTop}px)` : '-'}`,
    `page height:                 ${beforeReview ? beforeReview.h : '?'} -> ${log[log.length - 1].h}`,
  ]);
  await pace();
}

// ---------------------------------------------------------------- roadmaps: card count
{
  const { log } = await record(browser, creds, {
    url: BASE_URL + '/roadmaps', settleMs: 4000,
    delays: [{ match: '**/api/roadmaps', ms: SLOW }],
    probes: [
      { name: 'skel', sel: '.roadmap-card--skeleton', mode: 'exists' },
      { name: 'skelCards', sel: '.roadmap-card--skeleton', mode: 'count' },
      { name: 'cards', sel: '[data-testid=roadmap-card]', mode: 'count' },
    ],
  });
  const { during, after } = phases(log, 'skel');
  report('roadmaps — card grid', [
    `placeholder cards: ${during ? during.skelCards : 'skeleton never rendered'}`,
    `real cards:        ${after.cards}`,
    `page height ${during ? during.h : '?'} -> ${after.h}  (${during ? after.h - during.h : '?'}px)`,
  ]);
  await pace();
}

// ---------------------------------------------------------------- roadmap builder
// A full editor can't be reserved honestly — the loaded page runs past 8000px. What matters
// is that the placeholder clears the fold instead of leaving the viewport nearly empty.
{
  const { log } = await record(browser, creds, {
    url: BASE_URL + '/roadmaps/house-my-copy/edit', settleMs: 5000,
    delays: [{ match: '**/api/roadmaps/**', ms: SLOW }],
    probes: [
      { name: 'skel', sel: '.builder__card--skeleton', mode: 'exists' },
      { name: 'skelCards', sel: '.builder__card--skeleton', mode: 'count' },
      { name: 'crumb', sel: '.crumb', mode: 'text' },
      { name: 'form', sel: '.builder__card:not(.builder__card--skeleton)', mode: 'count' },
    ],
  });
  const { during, after } = phases(log, 'skel');
  report('roadmap builder — /roadmaps/:slug/edit', [
    `placeholder cards: ${during ? during.skelCards : 'skeleton never rendered'}`,
    `real form cards:   ${after.form}`,
    `breadcrumb while loading: ${during ? JSON.stringify(during.crumb) : '-'}   loaded: ${JSON.stringify(after.crumb)}`,
    `page height ${during ? during.h : '?'} -> ${after.h}  (fold is 900px)`,
  ]);
  await pace();
}

// ---------------------------------------------------------------- roadmap detail: right view?
// view() defaults to 'tree' and is forced to 'tree' when signed out, so a list-shaped
// placeholder here is one almost nobody sees the payoff of.
{
  const { log } = await record(browser, creds, {
    url: BASE_URL + '/roadmaps/house', settleMs: 5000,
    delays: [{ match: '**/api/roadmaps/house', ms: SLOW }],
    probes: [
      { name: 'skel', sel: '.roadmap-skeleton__canvas, .step--skeleton', mode: 'exists' },
      { name: 'canvas', sel: '.roadmap-skeleton__canvas', mode: 'count' },
      { name: 'steps', sel: '.step--skeleton', mode: 'count' },
      { name: 'tree', sel: '.tree__svg', mode: 'count' },
    ],
  });
  const { during, after } = phases(log, 'skel');
  report('roadmap detail — does the skeleton match the view that loads?', [
    `placeholder: ${during ? (during.canvas ? 'tree canvas' : `${during.steps} list steps`) : 'skeleton never rendered'}`,
    `what loads:  ${after.tree ? 'tree (svg)' : 'list'}`,
    `page height ${during ? during.h : '?'} -> ${after.h}`,
  ]);
  await pace();
}

// ---------------------------------------------------------------- page-title placeholder height
for (const vp of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
  const { log } = await record(browser, creds, {
    url: BASE_URL + '/dances/swing/20s-charleston', settleMs: 4000, viewport: vp,
    delays: [{ match: '**/api/dances/**', ms: SLOW }],
    probes: [
      { name: 'skel', sel: '.skeleton-line--page-title', mode: 'exists' },
      { name: 'skelTitleH', sel: '.skeleton-line--page-title', mode: 'height' },
      { name: 'realTitleH', sel: '.page-title', mode: 'height' },
    ],
  });
  const { during, after } = phases(log, 'skel');
  report(`page-title placeholder @ ${vp.width}px`, [
    `placeholder: ${during ? during.skelTitleH + 'px' : 'skeleton never rendered'}`,
    `real title:  ${after.realTitleH}px`,
  ]);
  await pace();
}

await browser.close();
for (const r of runs) {
  console.log(`\n### ${r.title}`);
  for (const l of r.lines) console.log('    ' + l);
}
