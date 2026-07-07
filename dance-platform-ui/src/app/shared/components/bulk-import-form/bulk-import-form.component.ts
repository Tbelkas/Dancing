import { Component, EventEmitter, Output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DanceService, ImportResult } from '../../../core/services/dance.service';

/**
 * Admin bulk-import form (paste a YouTube description / timestamp list), extracted from
 * DancesComponent. Owns the paste text, the in-flight/result/error state and the import call;
 * it keeps rendering its own result summary after a run. On a successful import it emits the
 * ImportResult so the parent can prepend the created dances to the catalog grid.
 */
@Component({
  selector: 'app-bulk-import-form',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="admin-form card">
      <h3 class="admin-form__title">Import Dances from YouTube</h3>
      <p class="admin-form__hint">Paste text containing a YouTube URL and dance entries in the format <code>Dance Name [MM:SS]</code>. One Dance + Video will be created per entry.</p>
      @if (error()) { <div class="error-message">{{ error() }}</div> }
      <div class="admin-form__fields">
        <div class="form-group">
          <label for="import-text">Paste text</label>
          <textarea id="import-text" [(ngModel)]="importText" rows="8" placeholder="Paste the YouTube description or timestamps here...&#10;&#10;Example:&#10;The Wu-Tang [00:29]&#10;The Roger Rabbit [01:26]"></textarea>
        </div>
      </div>
      <button class="btn btn--primary btn--sm" (click)="submit()" [disabled]="importing()">
        {{ importing() ? 'Importing...' : 'Import' }}
      </button>

      @if (result()) {
        <div class="import-result">
          @if (result()!.videoId) {
            <p class="import-result__video">Linked to YouTube video: <code>{{ result()!.videoId }}</code></p>
          }
          @if (result()!.created.length > 0) {
            <p class="import-result__success">Created {{ result()!.created.length }} dance{{ result()!.created.length !== 1 ? 's' : '' }}:</p>
            <ul class="import-result__list">
              @for (d of result()!.created; track d.id) {
                <li>{{ d.name }}</li>
              }
            </ul>
          }
          @if (result()!.errors.length > 0) {
            <p class="import-result__errors-label">Errors:</p>
            <ul class="import-result__list import-result__list--error">
              @for (e of result()!.errors; track e) {
                <li>{{ e }}</li>
              }
            </ul>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    .admin-form { margin-bottom: 28px; animation: slideDown 0.18s ease both; }
    .admin-form__title {
      font-family: var(--font-ui);
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--color-text-muted);
      margin-bottom: 20px;
      padding-bottom: 10px;
      border-bottom: 1px solid var(--color-border);
    }
    .admin-form__fields {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
      gap: 0 24px;
    }
    @media (max-width: 640px) { .admin-form__fields { grid-template-columns: 1fr; } }

    .admin-form__hint {
      font-size: 0.78rem;
      color: var(--color-text-muted);
      margin-bottom: 16px;
      line-height: 1.5;
    }
    .admin-form__hint code {
      font-family: var(--font-mono);
      font-size: 0.75rem;
      background: var(--color-surface-alt, rgba(255,255,255,0.05));
      padding: 1px 5px;
      border-radius: 3px;
    }

    .import-result {
      margin-top: 20px;
      padding-top: 16px;
      border-top: 1px solid var(--color-border);
      font-size: 0.82rem;
    }
    .import-result__video { color: var(--color-text-muted); margin-bottom: 10px; }
    .import-result__video code { font-family: var(--font-mono); font-size: 0.75rem; }
    .import-result__success { color: var(--color-text); font-weight: 600; margin-bottom: 6px; }
    .import-result__errors-label {
      color: var(--color-error, #e05252);
      font-weight: 600;
      margin-top: 10px;
      margin-bottom: 6px;
    }
    .import-result__list {
      margin: 0;
      padding-left: 18px;
      line-height: 1.7;
      color: var(--color-text-muted);
    }
    .import-result__list--error { color: var(--color-error, #e05252); }
  `]
})
export class BulkImportFormComponent {
  /** Emitted after a successful import so the parent can splice the created dances into its grid. */
  @Output() imported = new EventEmitter<ImportResult>();

  importText = '';
  importing = signal(false);
  result = signal<ImportResult | null>(null);
  error = signal('');

  constructor(private danceService: DanceService) {}

  submit(): void {
    if (!this.importText.trim()) { this.error.set('Paste some text to import.'); return; }
    this.importing.set(true);
    this.error.set('');
    this.result.set(null);
    this.danceService.importDances(this.importText).subscribe({
      next: result => {
        this.result.set(result);
        this.importing.set(false);
        if (result.created.length > 0) {
          this.importText = '';
          this.imported.emit(result);
        }
      },
      error: () => { this.error.set('Import failed. Make sure you are logged in as admin.'); this.importing.set(false); }
    });
  }
}
