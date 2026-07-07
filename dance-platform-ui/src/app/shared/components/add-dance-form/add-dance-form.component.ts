import { Component, EventEmitter, Input, Output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DanceService, CreateDancePayload } from '../../../core/services/dance.service';
import { Dance } from '../../../models/dance.model';
import { Style } from '../../../models/style.model';
import { MusicalStyle } from '../../../models/musical-style.model';
import { Instructor } from '../../../models/instructor.model';
import { toggleSet } from '../../../core/utils/set.utils';

/**
 * Admin "Add Dance" form (name / description / difficulty + style, musical-style and
 * instructor multi-selects), extracted from DancesComponent. The catalog lists it needs
 * are passed in as inputs; it owns the form state and the create call and emits the created
 * Dance so the parent can prepend it to the grid and close the form.
 */
@Component({
  selector: 'app-add-dance-form',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="admin-form card">
      <h3 class="admin-form__title">New Dance</h3>
      @if (error()) { <div class="error-message">{{ error() }}</div> }
      <div class="admin-form__fields">
        <div class="form-group">
          <label for="dance-name">Name</label>
          <input id="dance-name" type="text" [(ngModel)]="name" placeholder="e.g. Bachata" />
        </div>
        <div class="form-group">
          <label for="dance-desc">Description <span class="optional">(optional)</span></label>
          <textarea id="dance-desc" [(ngModel)]="description" rows="2" placeholder="Short description"></textarea>
        </div>
        <div class="form-group">
          <label for="dance-difficulty">Difficulty</label>
          <select id="dance-difficulty" [(ngModel)]="difficulty">
            <option value="None">Not specified</option>
            @for (d of difficulties; track d) {
              <option [value]="d">{{ d }}</option>
            }
          </select>
        </div>
        <div class="form-group">
          <label>Dance Styles</label>
          <div class="checkbox-grid">
            @for (style of styles; track style.id) {
              <label class="checkbox-item" [class.checked]="styleIds().has(style.id)">
                <input type="checkbox" [checked]="styleIds().has(style.id)" (change)="toggleStyle(style.id)" />
                {{ style.name }}
              </label>
            }
          </div>
        </div>
        <div class="form-group">
          <label>Musical Styles</label>
          <div class="checkbox-grid">
            @for (ms of musicalStyles; track ms.id) {
              <label class="checkbox-item" [class.checked]="musicalStyleIds().has(ms.id)">
                <input type="checkbox" [checked]="musicalStyleIds().has(ms.id)" (change)="toggleMusicalStyle(ms.id)" />
                {{ ms.name }}
              </label>
            }
          </div>
        </div>
        @if (instructors.length > 0) {
          <div class="form-group">
            <label>Instructors <span class="optional">(optional)</span></label>
            <div class="checkbox-grid">
              @for (inst of instructors; track inst.id) {
                <label class="checkbox-item" [class.checked]="instructorIds().has(inst.id)">
                  <input type="checkbox" [checked]="instructorIds().has(inst.id)" (change)="toggleInstructor(inst.id)" />
                  {{ inst.name }}
                </label>
              }
            </div>
          </div>
        }
      </div>
      <button class="btn btn--primary btn--sm" (click)="submit()" [disabled]="saving()">
        {{ saving() ? 'Creating...' : 'Create Dance' }}
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
export class AddDanceFormComponent {
  @Input() styles: Style[] = [];
  @Input() musicalStyles: MusicalStyle[] = [];
  @Input() instructors: Instructor[] = [];
  @Input() difficulties: readonly string[] = [];

  /** Emitted with the created dance so the parent can prepend it and close the form. */
  @Output() created = new EventEmitter<Dance>();

  name = '';
  description = '';
  difficulty = 'None';
  styleIds = signal<Set<number>>(new Set());
  musicalStyleIds = signal<Set<number>>(new Set());
  instructorIds = signal<Set<number>>(new Set());
  saving = signal(false);
  error = signal('');

  constructor(private danceService: DanceService) {}

  toggleStyle(id: number): void { this.styleIds.update(s => toggleSet(s, id)); }
  toggleMusicalStyle(id: number): void { this.musicalStyleIds.update(s => toggleSet(s, id)); }
  toggleInstructor(id: number): void { this.instructorIds.update(s => toggleSet(s, id)); }

  submit(): void {
    if (!this.name.trim()) { this.error.set('Name is required.'); return; }
    const payload: CreateDancePayload = {
      name: this.name.trim(),
      description: this.description.trim() || undefined,
      difficulty: this.difficulty,
      styleIds: [...this.styleIds()],
      musicalStyleIds: [...this.musicalStyleIds()],
      instructorIds: [...this.instructorIds()]
    };
    this.saving.set(true);
    this.error.set('');
    this.danceService.create(payload).subscribe({
      next: dance => { this.saving.set(false); this.created.emit(dance); },
      error: () => { this.error.set('Failed to create dance.'); this.saving.set(false); }
    });
  }
}
