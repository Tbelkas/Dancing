import { Injectable, signal } from '@angular/core';

export interface ConfirmRequest {
  title: string;
  message: string;
  confirmLabel: string;
  danger: boolean;
}

/**
 * Styled replacement for window.confirm(). ConfirmDialogComponent (rendered once
 * in the shell) shows the pending request; ask() resolves with the user's answer.
 */
@Injectable({ providedIn: 'root' })
export class ConfirmService {
  pending = signal<ConfirmRequest | null>(null);
  private resolver: ((value: boolean) => void) | null = null;

  ask(message: string, opts?: Partial<Omit<ConfirmRequest, 'message'>>): Promise<boolean> {
    // A second request while one is open cancels the first.
    this.resolver?.(false);
    return new Promise<boolean>(resolve => {
      this.resolver = resolve;
      this.pending.set({
        message,
        title: opts?.title ?? 'Are you sure?',
        confirmLabel: opts?.confirmLabel ?? 'Delete',
        danger: opts?.danger ?? true
      });
    });
  }

  answer(value: boolean): void {
    this.pending.set(null);
    this.resolver?.(value);
    this.resolver = null;
  }
}
