import { Injectable, signal } from '@angular/core';

export interface Toast {
  id: number;
  kind: 'success' | 'error';
  message: string;
}

/** App-wide, non-blocking action feedback. Rendered once by ToastsComponent in the shell. */
@Injectable({ providedIn: 'root' })
export class ToastService {
  toasts = signal<Toast[]>([]);
  private nextId = 1;

  success(message: string, durationMs = 3500): void {
    this.push('success', message, durationMs);
  }

  error(message: string, durationMs = 5000): void {
    this.push('error', message, durationMs);
  }

  dismiss(id: number): void {
    this.toasts.update(list => list.filter(t => t.id !== id));
  }

  private push(kind: Toast['kind'], message: string, durationMs: number): void {
    const id = this.nextId++;
    this.toasts.update(list => [...list, { id, kind, message }]);
    setTimeout(() => this.dismiss(id), durationMs);
  }
}
