import { signal } from '@angular/core';

/**
 * Tracks which items' thumbnails failed to load so cards can fall back to their
 * placeholder styling instead of a broken image. Signal-backed, so template
 * bindings that consult it re-render when a failure lands.
 */
export class ThumbFallback {
  private readonly failed = signal<Set<number>>(new Set());

  has(id: number): boolean {
    return this.failed().has(id);
  }

  markFailed(id: number): void {
    this.failed.update(set => new Set(set).add(id));
  }
}
