#!/usr/bin/env node
/**
 * Guards the test-id contract between the Angular templates and the e2e suite.
 *
 * Every `getByTestId('x')` in e2e/tests must have a matching `data-testid="x"` somewhere in
 * dance-platform-ui/src. If a refactor drops or renames an anchor, this fails in about a
 * second — instead of the e2e run failing 20 minutes later, or (worse) at 3am on a schedule.
 *
 * It also reports orphans: anchors in the templates nothing tests anymore. Those are a
 * warning, not a failure — an anchor may be waiting for a test that isn't written yet.
 *
 * Run: npm run verify:testids   (from e2e/)
 */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve, join, relative } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, '..', '..');
const uiSrc = join(repoRoot, 'dance-platform-ui', 'src');
const testsDir = join(here, '..', 'tests');

function walk(dir, extensions) {
  const out = [];
  for (const entry of readdirSync(dir)) {
    if (entry === 'node_modules' || entry.startsWith('.')) continue;
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) out.push(...walk(full, extensions));
    else if (extensions.some(ext => entry.endsWith(ext))) out.push(full);
  }
  return out;
}

/** testid -> files that define it */
const defined = new Map();
for (const file of walk(uiSrc, ['.html', '.ts'])) {
  const source = readFileSync(file, 'utf8');
  for (const [, id] of source.matchAll(/data-testid=["']([^"']+)["']/g)) {
    if (!defined.has(id)) defined.set(id, []);
    defined.get(id).push(relative(repoRoot, file));
  }
}

/**
 * testid -> spec files that use it.
 *
 * Matches both `getByTestId('x')` and a raw `[data-testid="x"]` CSS selector. The second
 * form is easy to reach for inside a `.locator()` chain, and without it a test could depend
 * on an anchor that this guard never checks — which is exactly the failure it exists to stop.
 */
const used = new Map();
const USAGE_PATTERNS = [
  /getByTestId\(\s*["'`]([^"'`]+)["'`]\s*\)/g,
  /\[data-testid=["']([^"']+)["']\]/g,
];
for (const file of walk(testsDir, ['.ts'])) {
  const source = readFileSync(file, 'utf8');
  for (const pattern of USAGE_PATTERNS) {
    for (const [, id] of source.matchAll(pattern)) {
      if (!used.has(id)) used.set(id, []);
      used.get(id).push(relative(repoRoot, file));
    }
  }
}

const missing = [...used.keys()].filter(id => !defined.has(id)).sort();
const orphaned = [...defined.keys()].filter(id => !used.has(id)).sort();

if (orphaned.length > 0) {
  console.log(`\n  ${orphaned.length} test-id(s) defined but never asserted on:`);
  for (const id of orphaned) {
    console.log(`    ~ ${id}  (${defined.get(id).join(', ')})`);
  }
  console.log('    Not a failure — either write a test or drop the attribute.');
}

if (missing.length > 0) {
  console.error(`\n  ${missing.length} test-id(s) used by the e2e suite but MISSING from the UI:\n`);
  for (const id of missing) {
    console.error(`    x ${id}`);
    for (const spec of new Set(used.get(id))) console.error(`        used in ${spec}`);
  }
  console.error(`
  A UI change removed or renamed an anchor the tests rely on.
  Fix by either:
    - restoring data-testid="<id>" on the element that replaced it, or
    - updating the spec to match the new markup, then re-running this check.

  See e2e/README.md - "The test-id contract".
`);
  process.exit(1);
}

console.log(`\n  OK - ${used.size} test-id(s) referenced by the suite all exist in the UI.\n`);
