import { Injectable, signal } from '@angular/core';

/** A dance the user recently opened, remembered locally so we can offer "Continue Learning". */
export interface RecentDance {
  id: number;
  name: string;
  slug: string;
  thumbnailVideoId?: string;
  thumbnailPlatform?: string;
  /** epoch ms of the last time the dance was opened */
  viewedAt: number;
  /** snapshot of learned status — learned dances are dropped from "Continue Learning" */
  learned: boolean;
}

/**
 * Tracks the dances the user has clicked into, in this browser, so My Dances can surface a
 * "Continue Learning" row of the most recent ones they haven't learned yet. Purely client-side
 * (localStorage); learned status is kept in sync from the dance-detail page.
 */
@Injectable({ providedIn: 'root' })
export class RecentDancesService {
  private readonly STORAGE_KEY = 'dp_recent_dances';
  /** The "Continue learning" carousel scrolls through history, so keep a deeper trail. */
  private readonly MAX_ENTRIES = 30;

  private readonly _recent = signal<RecentDance[]>(this.read());
  readonly recent = this._recent.asReadonly();

  /** Records (or refreshes) a dance the user just opened, moving it to the front of the list. */
  record(dance: { id: number; name: string; slug: string; thumbnailVideoId?: string; thumbnailPlatform?: string; isLearned: boolean }): void {
    const entry: RecentDance = {
      id: dance.id,
      name: dance.name,
      slug: dance.slug,
      thumbnailVideoId: dance.thumbnailVideoId,
      thumbnailPlatform: dance.thumbnailPlatform,
      viewedAt: Date.now(),
      learned: dance.isLearned
    };
    const next = [entry, ...this._recent().filter(d => d.id !== dance.id)].slice(0, this.MAX_ENTRIES);
    this.commit(next);
  }

  /** Keeps the stored learned flag in step when status changes elsewhere on the detail page. */
  setLearned(id: number, learned: boolean): void {
    const list = this._recent();
    if (!list.some(d => d.id === id)) return;
    this.commit(list.map(d => d.id === id ? { ...d, learned } : d));
  }

  /** Lets the user dismiss a dance from the "Continue Learning" row. */
  remove(id: number): void {
    this.commit(this._recent().filter(d => d.id !== id));
  }

  private commit(list: RecentDance[]): void {
    this._recent.set(list);
    try {
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(list));
    } catch {
      // ignore quota / unavailable storage — the in-memory signal still works for the session
    }
  }

  private read(): RecentDance[] {
    try {
      const raw = localStorage.getItem(this.STORAGE_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed.filter(d => d && typeof d.id === 'number' && d.slug) : [];
    } catch {
      return [];
    }
  }
}
