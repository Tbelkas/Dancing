import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { SkeletonCount } from './skeleton-count';

/** Minimal in-memory stand-in — the node test env has no Storage of its own. */
function fakeStorage(seed: Record<string, string> = {}) {
  const map = new Map(Object.entries(seed));
  return {
    getItem: (k: string) => map.get(k) ?? null,
    setItem: (k: string, v: string) => { map.set(k, v); },
    removeItem: (k: string) => { map.delete(k); },
    clear: () => map.clear(),
    key: (i: number) => [...map.keys()][i] ?? null,
    get length() { return map.size; },
    raw: map,
  };
}

let storage: ReturnType<typeof fakeStorage>;

const install = (seed?: Record<string, string>) => {
  storage = fakeStorage(seed);
  (globalThis as any).localStorage = storage;
};

beforeEach(() => install());
afterEach(() => { delete (globalThis as any).localStorage; });

describe('SkeletonCount', () => {
  it('uses the fallback on a first visit', () => {
    expect(new SkeletonCount('a', 3).slots().length).toBe(3);
  });

  it('reserves what the list held last time', () => {
    install({ dp_skel_a: '9' });
    expect(new SkeletonCount('a', 3, { max: 12 }).slots().length).toBe(9);
  });

  it('caps the reservation at max', () => {
    install({ dp_skel_a: '200' });
    expect(new SkeletonCount('a', 5, { max: 12 }).slots().length).toBe(12);
  });

  it('defaults max to the fallback, so a paged list can only shrink', () => {
    install({ dp_skel_browse: '24' });
    expect(new SkeletonCount('browse', 6).slots().length).toBe(6);
    install({ dp_skel_browse: '2' });
    expect(new SkeletonCount('browse', 6).slots().length).toBe(2);
  });

  it('always draws at least one slot, even for an empty list', () => {
    install({ dp_skel_a: '0' });
    expect(new SkeletonCount('a', 4).slots().length).toBe(1);
  });

  it('remember() writes the raw count and updates the slots', () => {
    const s = new SkeletonCount('a', 3, { max: 12 });
    s.remember(7);
    expect(s.slots().length).toBe(7);
    expect(storage.getItem('dp_skel_a')).toBe('7');
  });

  it('stores the raw count past the cap, so raising max later takes effect', () => {
    const s = new SkeletonCount('a', 3, { max: 5 });
    s.remember(40);
    expect(s.slots().length).toBe(5);
    expect(new SkeletonCount('a', 3, { max: 20 }).slots().length).toBe(20);
  });

  it('ignores junk in storage', () => {
    install({ dp_skel_a: 'not-a-number' });
    expect(new SkeletonCount('a', 3).slots().length).toBe(3);
  });

  it('ignores a nonsense count', () => {
    const s = new SkeletonCount('a', 3, { max: 12 });
    s.remember(Number.NaN);
    s.remember(-1);
    expect(s.slots().length).toBe(3);
    expect(storage.getItem('dp_skel_a')).toBeNull();
  });

  it('falls back cleanly when storage is unavailable', () => {
    delete (globalThis as any).localStorage;
    const s = new SkeletonCount('a', 3, { max: 12 });
    expect(s.slots().length).toBe(3);
    expect(() => s.remember(7)).not.toThrow();
    expect(s.slots().length).toBe(7);
  });
});
