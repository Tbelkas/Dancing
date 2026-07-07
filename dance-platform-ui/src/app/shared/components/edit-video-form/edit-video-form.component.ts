import { Component, EventEmitter, Input, OnInit, Output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { VideoService, SegmentPayload } from '../../../core/services/video.service';
import { Video, VideoType } from '../../../models/video.model';
import { parseTimeSecs, formatTimeSecs } from '../../../core/utils/video-url.utils';

const DEFAULT_SEGMENT_LABELS = ['Theory', 'Steps', 'Practice'];

interface SegmentRow {
  label: string;
  start: string;
  end: string;
}

/**
 * Admin form to edit a video's start/end bounds, its Steps/Tutorial type and its tutorial
 * sections, extracted from DanceDetailComponent (it was the shared `#editVideoForm` template
 * reused by both the single- and multi-video layouts). Seeds itself from the passed-in video,
 * owns the update call, and emits the server's updated video (or a cancel) for the parent to
 * apply to its list and the open player.
 */
@Component({
  selector: 'app-edit-video-form',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="admin-form card admin-form--inline">
      @if (error()) { <div class="error-message">{{ error() }}</div> }
      <div class="admin-form__fields admin-form__fields--row">
        <div class="form-group">
          <label>Start Time <span class="optional">(m:ss or seconds, blank to clear)</span></label>
          <input type="text" [(ngModel)]="startTime" placeholder="e.g. 2:29" />
        </div>
        <div class="form-group">
          <label>End Time <span class="optional">(m:ss or seconds, blank to clear)</span></label>
          <input type="text" [(ngModel)]="endTime" placeholder="e.g. 3:06" />
        </div>
        <div class="form-group">
          <label>Type</label>
          <select [(ngModel)]="videoType" (ngModelChange)="onTypeChange()">
            <option value="steps">Steps</option>
            <option value="tutorial">Tutorial</option>
          </select>
        </div>
      </div>
      @if (videoType === 'tutorial') {
        <div class="form-group">
          <label>Sections <span class="optional">(start time as m:ss or seconds)</span></label>
          <div class="segment-rows">
            @for (row of segments; track $index) {
              <div class="segment-row">
                <input type="text" [(ngModel)]="row.label" placeholder="Label" />
                <input type="text" class="segment-row__time" [(ngModel)]="row.start" placeholder="Start" />
                <input type="text" class="segment-row__time" [(ngModel)]="row.end" placeholder="End (opt.)" />
                <button class="btn btn--danger btn--xs" (click)="removeSegmentRow($index)" title="Remove section"><i class="fa-solid fa-xmark"></i></button>
              </div>
            }
            <button class="btn btn--ghost btn--sm" (click)="addSegmentRow()"><i class="fa-solid fa-plus"></i> Add Section</button>
          </div>
        </div>
      }
      <div class="admin-form__actions">
        <button class="btn btn--primary btn--sm" (click)="submit()" [disabled]="saving()">
          {{ saving() ? 'Saving...' : 'Save' }}
        </button>
        <button class="btn btn--ghost btn--sm" (click)="cancelled.emit()">Cancel</button>
      </div>
    </div>
  `,
  styles: [`
    .admin-form { animation: slideDown 0.18s ease both; }
    .admin-form--inline { margin-bottom: 0; padding: 14px 16px; }
    .admin-form__fields--row {
      display: flex;
      flex-wrap: wrap;
      gap: 0 24px;
    }
    .admin-form__actions {
      display: flex;
      gap: 8px;
      margin-top: 12px;
    }
    .segment-rows {
      display: flex;
      flex-direction: column;
      gap: 8px;
      align-items: flex-start;
    }
    .segment-row {
      display: flex;
      gap: 8px;
      align-items: center;
      width: 100%;
      max-width: 520px;
    }
    .segment-row input { flex: 1; min-width: 0; }
    .segment-row .segment-row__time { flex: 0 0 110px; }
  `]
})
export class EditVideoFormComponent implements OnInit {
  @Input({ required: true }) video!: Video;

  /** Emitted with the server's updated video; the parent replaces it in its list/player. */
  @Output() updated = new EventEmitter<Video>();
  /** Emitted when the admin cancels; the parent closes the inline editor. */
  @Output() cancelled = new EventEmitter<void>();

  startTime = '';
  endTime = '';
  videoType: VideoType = 'steps';
  segments: SegmentRow[] = [];
  saving = signal(false);
  error = signal('');

  constructor(private videoService: VideoService) {}

  ngOnInit(): void {
    const v = this.video;
    this.startTime = v.startTime != null ? formatTimeSecs(v.startTime) : '';
    this.endTime = v.endTime != null ? formatTimeSecs(v.endTime) : '';
    this.videoType = v.videoType === 'tutorial' ? 'tutorial' : 'steps';
    this.segments = v.segments.map(s => ({
      label: s.label,
      start: formatTimeSecs(s.startTime),
      end: s.endTime != null ? formatTimeSecs(s.endTime) : ''
    }));
  }

  onTypeChange(): void {
    if (this.videoType === 'tutorial' && this.segments.length === 0)
      this.segments = DEFAULT_SEGMENT_LABELS.map(label => ({ label, start: '', end: '' }));
  }

  addSegmentRow(): void {
    this.segments.push({ label: '', start: '', end: '' });
  }

  removeSegmentRow(index: number): void {
    this.segments.splice(index, 1);
  }

  private buildSegments(): SegmentPayload[] | null {
    if (this.videoType !== 'tutorial') return [];
    const segments: SegmentPayload[] = [];
    for (const row of this.segments) {
      if (!row.label.trim() && !row.start.trim()) continue;
      const startTime = parseTimeSecs(row.start);
      if (!row.label.trim() || startTime === undefined) {
        this.error.set('Each section needs a label and a start time (m:ss or seconds).');
        return null;
      }
      segments.push({ label: row.label.trim(), startTime, endTime: parseTimeSecs(row.end) });
    }
    return segments;
  }

  submit(): void {
    const startTime = parseTimeSecs(this.startTime);
    const endTime = parseTimeSecs(this.endTime);
    const segments = this.buildSegments();
    if (segments === null) return;
    // The form only edits sections for tutorials; for other types leave segments untouched
    // so admin-saved loops aren't wiped when just changing the time.
    const updateSegments = this.videoType === 'tutorial';
    this.saving.set(true);
    this.error.set('');
    this.videoService.update(this.video.id, {
      updateTimes: true,
      startTime,
      endTime,
      videoType: this.videoType,
      updateSegments,
      segments
    }).subscribe({
      next: updated => { this.saving.set(false); this.updated.emit(updated); },
      error: () => { this.error.set('Failed to save. Please try again.'); this.saving.set(false); }
    });
  }
}
