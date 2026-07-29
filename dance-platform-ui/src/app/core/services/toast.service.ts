import { Injectable, signal } from '@angular/core';

export interface Toast {
  id: number;
  kind: 'success' | 'error' | 'undo';
  message: string;
  /** 'undo' only — puts back what the caller optimistically removed. */
  undo?: () => void;
  /** 'undo' only — length of the undo window, drives the countdown bar. */
  durationMs?: number;
}

/** Registered alongside an 'undo' toast: the real deletion, still un-fired. */
interface PendingCommit {
  commit: () => void;
  timer: ReturnType<typeof setTimeout>;
}

/** App-wide, non-blocking action feedback. Rendered once by ToastsComponent in the shell. */
@Injectable({ providedIn: 'root' })
export class ToastService {
  toasts = signal<Toast[]>([]);
  private nextId = 1;
  private pending = new Map<number, PendingCommit>();

  success(message: string, durationMs = 3500): void {
    this.push('success', message, durationMs);
  }

  error(message: string, durationMs = 5000): void {
    this.push('error', message, durationMs);
  }

  /**
   * Announces a deletion the user can still take back.
   *
   * The caller removes the item from its own view *first* (so the UI reacts instantly),
   * then hands us two closures: `commit` performs the real deletion — typically the HTTP
   * call — and only runs once the window closes; `undo` puts the item back in the view.
   * Nothing is destroyed while the toast is on screen, so undo costs nothing and can't
   * half-fail. That matters for videos and choreos, where the server-side delete cascades
   * to segments, ratings and notes that a delete-then-recreate could never restore.
   *
   * The window ends when the timer expires, when the user dismisses the toast (dismissing
   * accepts the deletion), or when they navigate away — see flush().
   */
  undoable(message: string, handlers: { commit: () => void; undo: () => void; durationMs?: number }): void {
    const { commit, undo, durationMs = 6000 } = handlers;
    const id = this.nextId++;
    this.toasts.update(list => [...list, {
      id, kind: 'undo', message, durationMs, undo: () => this.runUndo(id, undo)
    }]);
    this.pending.set(id, { commit, timer: setTimeout(() => this.dismiss(id), durationMs) });
  }

  dismiss(id: number): void {
    // Dismissing an undo toast means "yes, delete it" — commit now rather than leaving
    // the request hanging on a timer the user thinks they've closed.
    this.commitPending(id);
    this.toasts.update(list => list.filter(t => t.id !== id));
  }

  /**
   * Commits every still-open deletion at once. The shell calls this on navigation and on
   * pagehide: an undo window is tied to the screen the user is looking at, and a deferred
   * delete must not outlive it, or the item silently returns on the next load.
   */
  flush(): void {
    for (const id of [...this.pending.keys()]) this.dismiss(id);
  }

  /** True while a deletion is still take-back-able — lets a page hold off on refetching. */
  hasPending(): boolean {
    return this.pending.size > 0;
  }

  private runUndo(id: number, undo: () => void): void {
    const p = this.pending.get(id);
    if (!p) return; // already committed; the undo button is gone by now anyway
    clearTimeout(p.timer);
    this.pending.delete(id);
    this.toasts.update(list => list.filter(t => t.id !== id));
    undo();
  }

  private commitPending(id: number): void {
    const p = this.pending.get(id);
    if (!p) return;
    clearTimeout(p.timer);
    this.pending.delete(id);
    p.commit();
  }

  private push(kind: 'success' | 'error', message: string, durationMs: number): void {
    const id = this.nextId++;
    this.toasts.update(list => [...list, { id, kind, message }]);
    setTimeout(() => this.dismiss(id), durationMs);
  }
}
