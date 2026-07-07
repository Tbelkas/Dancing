/**
 * Client-side mirror of the server's slug format: lowercase, runs of non-alphanumerics
 * collapsed to single hyphens, and leading/trailing hyphens trimmed. This is the one place
 * the rule lives so the pipe and any future caller stay in lock-step with the backend.
 *
 * It is idempotent on values already in slug form (the server-provided slugs the app routes
 * on), so passing those through it does not change the produced URL.
 */
export function slugify(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
}
