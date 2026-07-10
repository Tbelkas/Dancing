import { WritableSignal } from '@angular/core';
import { ActivatedRoute, ParamMap, Router } from '@angular/router';

/**
 * One filter's wiring: the signal that holds it, how it travels as a URL query
 * param, and how it round-trips through the persisted localStorage snapshot.
 */
export interface FilterFieldSpec<T = unknown> {
  /** URL query-param name (e.g. 'q', 'style'). */
  param: string;
  /** Property name in the persisted snapshot (kept distinct so legacy snapshots stay readable). */
  storageKey: string;
  signal: WritableSignal<T>;
  /** Parse the raw query param (null when absent) into a value; must yield the default for null. */
  fromParam: (raw: string | null) => T;
  /** Value → query param; return null to omit the param when the value is the default. */
  toParam: (value: T) => string | number | null;
  /** Validate a value coming out of the stored snapshot; return undefined to leave the signal alone. */
  fromStored: (raw: unknown) => T | undefined;
  /** Custom "URL value matches current state" check (defaults to ===). */
  equals?: (fromUrl: T, current: T) => boolean;
  /** Applied to URL-sourced values before they land in the signal (e.g. auth-gating). */
  sanitize?: (value: T) => T;
}

/**
 * Keeps a set of filter signals in sync with the URL and localStorage, so any
 * filtered view is shareable/back-button-safe and a plain revisit lands where
 * the user left off. Adding a filter is one spec entry instead of touching
 * four hand-written restore/persist/sync/diff methods.
 */
export class UrlFilterSync {
  constructor(
    private readonly storageKey: string,
    private readonly router: Router,
    private readonly route: ActivatedRoute,
    private readonly fields: FilterFieldSpec<any>[]
  ) {}

  /**
   * Restore filters: an explicit URL (shared link, back button) wins; otherwise
   * fall back to the last-used snapshot in localStorage.
   */
  restore(): void {
    const qp = this.route.snapshot.queryParamMap;
    if (this.fields.some(f => qp.has(f.param))) {
      for (const f of this.fields) {
        const value = f.fromParam(qp.get(f.param));
        f.signal.set(f.sanitize ? f.sanitize(value) : value);
      }
      return;
    }
    try {
      const raw = localStorage.getItem(this.storageKey);
      if (!raw) return;
      const snapshot = JSON.parse(raw);
      for (const f of this.fields) {
        const value = f.fromStored(snapshot[f.storageKey]);
        if (value !== undefined) f.signal.set(f.sanitize ? f.sanitize(value) : value);
      }
    } catch { /* ignore malformed/unavailable storage */ }
  }

  /** Snapshot current values to localStorage and mirror them into the URL. */
  persist(): void {
    try {
      const snapshot: Record<string, unknown> = {};
      for (const f of this.fields) snapshot[f.storageKey] = f.signal();
      localStorage.setItem(this.storageKey, JSON.stringify(snapshot));
    } catch { /* storage unavailable (private mode, quota) — non-fatal */ }
    this.router.navigate([], {
      relativeTo: this.route,
      replaceUrl: true,
      queryParams: Object.fromEntries(this.fields.map(f => [f.param, f.toParam(f.signal())]))
    });
  }

  /**
   * Adopt filters arriving via the URL (header search, back button) when they
   * differ from current state; identical params (our own persist() echoes)
   * no-op. Returns true when state changed and the caller should re-query.
   */
  applyIfChanged(qp: ParamMap): boolean {
    const parsed = this.fields.map(f => f.fromParam(qp.get(f.param)));
    const unchanged = this.fields.every((f, i) =>
      f.equals ? f.equals(parsed[i], f.signal()) : parsed[i] === f.signal());
    if (unchanged) return false;
    this.fields.forEach((f, i) => f.signal.set(f.sanitize ? f.sanitize(parsed[i]) : parsed[i]));
    return true;
  }
}

/** Positive-integer id from a query param, else null (absent/invalid). */
export function idFromParam(raw: string | null): number | null {
  const n = Number(raw);
  return Number.isInteger(n) && n > 0 ? n : null;
}

/** 1-based page number from a query param, else 1. */
export function pageFromParam(raw: string | null): number {
  const n = Number(raw);
  return Number.isInteger(n) && n >= 1 ? n : 1;
}
