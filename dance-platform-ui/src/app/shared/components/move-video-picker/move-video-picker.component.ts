import { Component, EventEmitter, Input, OnInit, Output, computed, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DanceService } from '../../../core/services/dance.service';
import { VideoService } from '../../../core/services/video.service';
import { Video } from '../../../models/video.model';

/**
 * Admin control to reassign a video to a different dance (it inherits that dance's style),
 * extracted from DanceDetailComponent. It loads the dance name list it searches over, owns
 * the move call, and emits `moved` on success so the parent can drop the video from the page.
 * `cancelled` closes the panel.
 */
@Component({
  selector: 'app-move-video-picker',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="admin-form card admin-form--inline">
      @if (error()) { <div class="error-message">{{ error() }}</div> }
      <div class="form-group">
        <label>Move to dance <span class="optional">(search by name; the video takes on that dance's style)</span></label>
        <input type="text" [ngModel]="query()" (ngModelChange)="query.set($event)" placeholder="Type a dance name..." />
      </div>
      @if (matches().length > 0) {
        <div class="move-matches">
          @for (m of matches(); track m.id) {
            <button class="btn btn--ghost btn--sm" (click)="submit(m)" [disabled]="moving()">{{ m.name }}</button>
          }
        </div>
      } @else if (query().trim()) {
        <p class="empty">No matching dances.</p>
      }
      <div class="admin-form__actions">
        <button class="btn btn--ghost btn--sm" (click)="cancelled.emit()" [disabled]="moving()">Cancel</button>
      </div>
    </div>
  `,
  styles: [`
    .admin-form { animation: slideDown 0.18s ease both; }
    .admin-form--inline { margin-bottom: 0; padding: 14px 16px; }
    .admin-form__actions {
      display: flex;
      gap: 8px;
      margin-top: 12px;
    }
    .move-matches {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      max-height: 220px;
      overflow-y: auto;
      margin-top: 4px;
    }
    .empty {
      font-family: var(--font-ui);
      font-size: 0.78rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.07em;
      color: var(--color-text-muted);
      padding: 40px 0;
    }
  `]
})
export class MoveVideoPickerComponent implements OnInit {
  @Input({ required: true }) video!: Video;
  /** The current dance — excluded from the target list (a video can't move onto itself). */
  @Input() excludeDanceId: number | null = null;

  /** Emitted after the video is successfully moved; the parent removes it from this page. */
  @Output() moved = new EventEmitter<Video>();
  /** Emitted when the admin closes the panel without moving. */
  @Output() cancelled = new EventEmitter<void>();

  query = signal('');
  moving = signal(false);
  error = signal('');
  private danceNames = signal<{ id: number; name: string }[]>([]);

  // Dances matching the search box, excluding the current one; capped for a tidy list.
  matches = computed(() => {
    const q = this.query().trim().toLowerCase();
    if (!q) return [];
    return this.danceNames()
      .filter(d => d.id !== this.excludeDanceId && d.name.toLowerCase().includes(q))
      .slice(0, 20);
  });

  constructor(
    private danceService: DanceService,
    private videoService: VideoService
  ) {}

  ngOnInit(): void {
    this.danceService.getNames().subscribe(n => this.danceNames.set(n));
  }

  submit(target: { id: number; name: string }): void {
    this.moving.set(true);
    this.error.set('');
    this.videoService.moveToDance(this.video.id, target.id).subscribe({
      next: () => { this.moving.set(false); this.moved.emit(this.video); },
      error: () => { this.error.set('Failed to move video. Please try again.'); this.moving.set(false); }
    });
  }
}
