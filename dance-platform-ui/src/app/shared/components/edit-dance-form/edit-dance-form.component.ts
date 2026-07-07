import { Component, EventEmitter, Input, OnInit, Output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DanceService, UpdateDancePayload } from '../../../core/services/dance.service';
import { Dance } from '../../../models/dance.model';
import { Style } from '../../../models/style.model';
import { MusicalStyle } from '../../../models/musical-style.model';
import { Instructor } from '../../../models/instructor.model';
import { toggleInArray } from '../../../core/utils/set.utils';

/**
 * Admin "Edit Dance" form, extracted from DanceDetailComponent. Seeds its fields from the
 * current dance (matching its style/music/instructor names against the passed-in catalogs)
 * and owns the update call. It emits the server's updated Dance and lets the parent reconcile
 * it with the flags it already holds (favorite/learned/counts) and fix up the URL — keeping
 * that page-level concern where it belongs.
 */
@Component({
  selector: 'app-edit-dance-form',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="admin-form card">
      <h3 class="admin-form__title">Edit Dance</h3>
      @if (error()) { <div class="error-message">{{ error() }}</div> }
      <div class="admin-form__fields">
        <div class="form-group">
          <label for="edit-dance-name">Name</label>
          <input id="edit-dance-name" type="text" [(ngModel)]="name" placeholder="Dance name" />
        </div>
        <div class="form-group">
          <label for="edit-dance-desc">Description <span class="optional">(optional)</span></label>
          <input id="edit-dance-desc" type="text" [(ngModel)]="description" placeholder="Short description" />
        </div>
        <div class="form-group">
          <label for="edit-dance-difficulty">Difficulty</label>
          <select id="edit-dance-difficulty" [(ngModel)]="difficulty">
            @for (d of difficulties; track d) {
              <option [value]="d">{{ d === 'None' ? 'Not specified' : d }}</option>
            }
          </select>
        </div>
      </div>
      @if (allStyles.length > 0) {
        <div class="form-group">
          <label>Styles</label>
          <div class="checkbox-grid">
            @for (style of allStyles; track style.id) {
              <label class="checkbox-item" [class.checked]="styleIds.includes(style.id)" (click)="toggleStyle(style.id)">
                <input type="checkbox" [checked]="styleIds.includes(style.id)" />
                {{ style.name }}
              </label>
            }
          </div>
        </div>
      }
      @if (allMusicalStyles.length > 0) {
        <div class="form-group">
          <label>Musical Styles</label>
          <div class="checkbox-grid">
            @for (ms of allMusicalStyles; track ms.id) {
              <label class="checkbox-item" [class.checked]="musicalStyleIds.includes(ms.id)" (click)="toggleMusicalStyle(ms.id)">
                <input type="checkbox" [checked]="musicalStyleIds.includes(ms.id)" />
                <i class="fa-solid fa-music"></i> {{ ms.name }}
              </label>
            }
          </div>
        </div>
      }
      @if (allInstructors.length > 0) {
        <div class="form-group">
          <label>Instructors <span class="optional">(optional)</span></label>
          <div class="checkbox-grid">
            @for (inst of allInstructors; track inst.id) {
              <label class="checkbox-item" [class.checked]="instructorIds.includes(inst.id)" (click)="toggleInstructor(inst.id)">
                <input type="checkbox" [checked]="instructorIds.includes(inst.id)" />
                {{ inst.name }}
              </label>
            }
          </div>
        </div>
      }
      <button class="btn btn--primary btn--sm" (click)="submit()" [disabled]="saving()">
        {{ saving() ? 'Saving...' : 'Save Changes' }}
      </button>
    </div>
  `,
  styles: [`
    .admin-form { margin-bottom: 24px; animation: slideDown 0.18s ease both; }
    .admin-form__title {
      font-family: var(--font-ui);
      font-size: 0.7rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--color-text-muted);
      margin-bottom: 18px;
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
export class EditDanceFormComponent implements OnInit {
  @Input({ required: true }) dance!: Dance;
  @Input() allStyles: Style[] = [];
  @Input() allMusicalStyles: MusicalStyle[] = [];
  @Input() allInstructors: Instructor[] = [];
  @Input() difficulties: readonly string[] = [];

  /** Emitted with the server's updated dance; the parent reconciles flags/URL and closes. */
  @Output() updated = new EventEmitter<Dance>();

  name = '';
  description = '';
  difficulty = 'None';
  styleIds: number[] = [];
  musicalStyleIds: number[] = [];
  instructorIds: number[] = [];
  saving = signal(false);
  error = signal('');

  constructor(private danceService: DanceService) {}

  ngOnInit(): void {
    const d = this.dance;
    this.name = d.name;
    this.description = d.description ?? '';
    this.difficulty = d.difficulty;
    this.styleIds = this.allStyles.filter(s => d.styles.includes(s.name)).map(s => s.id);
    this.musicalStyleIds = this.allMusicalStyles.filter(s => d.musicalStyles.includes(s.name)).map(s => s.id);
    this.instructorIds = this.allInstructors.filter(i => d.instructors.includes(i.name)).map(i => i.id);
  }

  toggleStyle(id: number): void { this.styleIds = toggleInArray(this.styleIds, id); }
  toggleMusicalStyle(id: number): void { this.musicalStyleIds = toggleInArray(this.musicalStyleIds, id); }
  toggleInstructor(id: number): void { this.instructorIds = toggleInArray(this.instructorIds, id); }

  submit(): void {
    if (!this.name.trim()) { this.error.set('Name is required.'); return; }
    const payload: UpdateDancePayload = {
      name: this.name.trim(),
      description: this.description.trim() || undefined,
      difficulty: this.difficulty,
      styleIds: this.styleIds,
      musicalStyleIds: this.musicalStyleIds,
      instructorIds: this.instructorIds
    };
    this.saving.set(true);
    this.error.set('');
    this.danceService.update(this.dance.id, payload).subscribe({
      next: updated => { this.saving.set(false); this.updated.emit(updated); },
      error: () => { this.error.set('Failed to save changes.'); this.saving.set(false); }
    });
  }
}
