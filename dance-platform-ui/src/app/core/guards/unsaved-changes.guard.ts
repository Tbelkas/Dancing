import { CanDeactivateFn } from '@angular/router';

/**
 * Implemented by a page that holds edits worth warning about before they're lost.
 */
export interface HasUnsavedChanges {
  /** True while there are edits the server hasn't been told about. */
  hasUnsavedChanges(): boolean;
  /** What to warn with — named so the message can say what is about to be lost. */
  unsavedChangesMessage(): string;
}

/**
 * Blocks an in-app navigation away from a page with unsaved edits until the user confirms.
 *
 * `confirm()` rather than a styled modal on purpose: a router guard has to answer synchronously
 * with a boolean, and the app has no blocking dialog primitive. A custom modal here would mean
 * either a promise-based guard that can't cancel a back-button navigation cleanly, or building
 * one — neither is worth it for a confirmation the user should rarely see.
 *
 * This covers router navigation only. A tab close or reload never reaches the router, so a page
 * using this must also register its own `beforeunload` listener — the browser will not let a
 * script customise or await that one either way.
 */
export const unsavedChangesGuard: CanDeactivateFn<HasUnsavedChanges> = component => {
  if (!component?.hasUnsavedChanges()) return true;
  return confirm(component.unsavedChangesMessage());
};
