import { Injectable, signal } from '@angular/core';

/** A dance the user recently opened, remembered locally to build the "Recently viewed" rows. */
export interface RecentDance {
  id: number;
  name: string;
  slug: string;
  styleSlug: string;
  /** Display name of the canonical style, shown on the card to disambiguate same-named steps. */
  styleName?: string;
  thumbnailVideoId?: string;
  thumbnailPlatform?: string;
  /** Id of the last video the user actually opened here, so history resumes that video
   *  rather than dropping them back on the dance's video list. */
  videoId?: number;
  /** epoch ms of the last time the dance was opened */
  viewedAt: number;
  /** snapshot of learned status — learned dances are dropped from "Recently viewed" */
  learned: boolean;
}

/**
 * Tracks the dances the user has clicked into, in this browser, so My Dances can surface a
 * "Recently viewed" row of the most recent ones they haven't learned yet (and so browse can
 * fall back to the same row when the user has nothing marked in progress). Purely client-side
 * (localStorage); learned status is kept in sync from the dance-detail page.
 *
 * Not to be confused with browse's "Continue learning" rail, which is a server query for
 * status=inprogress and shares nothing with this trail but the resume link params.
 */
@Injectable({ providedIn: 'root' })
export class RecentDancesService {
  private readonly STORAGE_KEY = 'dp_recent_dances';
  /** The "Recently viewed" carousel scrolls through history, so keep a deeper trail. */
  private readonly MAX_ENTRIES = 30;

  private readonly _recent = signal<RecentDance[]>(this.read());
  readonly recent = this._recent.asReadonly();

  /** Records (or refreshes) a dance the user just opened, moving it to the front of the list. */
  record(dance: { id: number; name: string; slug: string; styleSlug: string; styles?: string[]; thumbnailVideoId?: string; thumbnailPlatform?: string; isLearned: boolean }): void {
    // Opening the dance page again shouldn't forget which video was last watched — the
    // detail page overwrites it via setVideo() as soon as a video is actually opened.
    const previous = this._recent().find(d => d.id === dance.id);
    const entry: RecentDance = {
      id: dance.id,
      name: dance.name,
      slug: dance.slug,
      styleSlug: dance.styleSlug,
      styleName: dance.styles?.[0],
      thumbnailVideoId: dance.thumbnailVideoId,
      thumbnailPlatform: dance.thumbnailPlatform,
      videoId: previous?.videoId,
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

  /** Remembers the video opened within a dance so history can link straight back to it. */
  setVideo(danceId: number, videoId: number): void {
    const list = this._recent();
    if (!list.some(d => d.id === danceId && d.videoId !== videoId)) return;
    this.commit(list.map(d => d.id === danceId ? { ...d, videoId } : d));
  }

  /** Lets the user dismiss a dance from the "Recently viewed" row. */
  remove(id: number): void {
    this.commit(this._recent().filter(d => d.id !== id));
  }

  /**
   * The trail as it stands, for a caller that wants to offer an undo of a dismissal.
   * Restoring the whole list rather than re-inserting one entry keeps the recency order
   * exactly as it was — the row is sorted by viewedAt, so a re-add would jump the card
   * to wherever its timestamp lands instead of back where the user removed it from.
   */
  snapshot(): RecentDance[] {
    return this._recent();
  }

  restore(list: RecentDance[]): void {
    this.commit(list);
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
