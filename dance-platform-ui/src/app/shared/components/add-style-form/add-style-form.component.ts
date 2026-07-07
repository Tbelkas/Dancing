import { Component, EventEmitter, Output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { StyleService } from '../../../core/services/style.service';
import { Style } from '../../../models/style.model';

/**
 * Admin "Add Style" form, extracted from DancesComponent. Owns its own field state, its
 * validation/submit and the StyleService call; on success it emits the created Style and
 * lets the parent splice it into the catalog list and close the form. Kept in a standalone
 * component so it can be @defer-loaded — anonymous visitors never download this authoring code.
 */
@Component({
  selector: 'app-add-style-form',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="admin-form card">
      <h3 class="admin-form__title">New Dance Style</h3>
      @if (error()) { <div class="error-message">{{ error() }}</div> }
      <div class="admin-form__fields">
        <div class="form-group">
          <label for="style-name">Name</label>
          <input id="style-name" type="text" [(ngModel)]="name" placeholder="e.g. Salsa" />
        </div>
        <div class="form-group">
          <label for="style-desc">Description <span class="optional">(optional)</span></label>
          <input id="style-desc" type="text" [(ngModel)]="description" placeholder="Brief description" />
        </div>
      </div>
      <button class="btn btn--primary btn--sm" (click)="submit()" [disabled]="saving()">
        {{ saving() ? 'Creating...' : 'Create Style' }}
      </button>
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
  `]
})
export class AddStyleFormComponent {
  /** Emitted with the freshly-created style so the parent can add it to its list and close. */
  @Output() created = new EventEmitter<Style>();

  name = '';
  description = '';
  saving = signal(false);
  error = signal('');

  constructor(private styleService: StyleService) {}

  submit(): void {
    if (!this.name.trim()) { this.error.set('Name is required.'); return; }
    this.saving.set(true);
    this.error.set('');
    this.styleService.create(this.name.trim(), this.description.trim() || undefined).subscribe({
      next: style => { this.saving.set(false); this.created.emit(style); },
      error: () => { this.error.set('Failed to create style.'); this.saving.set(false); }
    });
  }
}
