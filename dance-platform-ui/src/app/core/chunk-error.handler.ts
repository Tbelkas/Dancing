import { ErrorHandler, Injectable } from '@angular/core';

/**
 * Recovers from stale-deploy chunk load failures.
 *
 * After a new deploy, a browser still running the old main bundle may request a
 * lazy chunk hash that no longer exists on the server. The SPA fallback then
 * returns index.html (text/html) for the missing .js, the browser refuses to
 * execute it, and lazy routes throw. We detect that class of error and reload
 * the page once to pull a fresh index.html + chunk manifest.
 *
 * A sessionStorage flag prevents a reload loop if the failure is not actually a
 * stale-deploy (e.g. a genuinely broken chunk or offline).
 */
@Injectable()
export class ChunkErrorHandler implements ErrorHandler {
  private static readonly RELOAD_FLAG = 'dp_chunk_reloaded';

  handleError(error: unknown): void {
    if (this.isChunkLoadError(error) && !sessionStorage.getItem(ChunkErrorHandler.RELOAD_FLAG)) {
      sessionStorage.setItem(ChunkErrorHandler.RELOAD_FLAG, '1');
      window.location.reload();
      return;
    }

    // Not a recoverable chunk error (or we already tried) — clear the flag on a
    // successful, unrelated error so a future real stale-deploy can recover too.
    console.error(error);
  }

  private isChunkLoadError(error: unknown): boolean {
    const message = this.messageOf(error);
    return (
      /ChunkLoadError/i.test(message) ||
      /Loading chunk \S+ failed/i.test(message) ||
      /error loading dynamically imported module/i.test(message) ||
      /Failed to fetch dynamically imported module/i.test(message) ||
      /disallowed MIME type/i.test(message)
    );
  }

  private messageOf(error: unknown): string {
    if (!error) return '';
    if (typeof error === 'string') return error;
    const e = error as { message?: string; name?: string; rejection?: unknown };
    if (e.rejection) return this.messageOf(e.rejection); // unhandled promise rejections
    return `${e.name ?? ''} ${e.message ?? ''}`.trim() || String(error);
  }
}
