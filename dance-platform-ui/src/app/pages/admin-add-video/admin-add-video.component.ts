import { Component, OnInit, computed, signal, WritableSignal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Title } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { DanceService } from '../../core/services/dance.service';
import { VideoService, CreateVideoPayload, SegmentPayload } from '../../core/services/video.service';
import { VideoType } from '../../models/video.model';
import { parseVideoUrl, parseTimeSecs } from '../../core/utils/video-url.utils';

const DEFAULT_SEGMENT_LABELS = ['Theory', 'Steps', 'Practice'];

interface SegmentRow {
  label: string;
  start: string;
  end: string;
}

@Component({
  selector: 'app-admin-add-video',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './admin-add-video.component.html',
  styleUrls: ['./admin-add-video.component.css']
})
export class AdminAddVideoComponent implements OnInit {
  // Dance picker — search the full name list client-side (same source the move-video flow uses).
  private danceNames = signal<{ id: number; name: string }[]>([]);
  danceQuery = signal('');
  selectedDance = signal<{ id: number; name: string } | null>(null);
  danceMatches = computed(() => {
    const q = this.danceQuery().trim().toLowerCase();
    if (!q) return [];
    return this.danceNames()
      .filter(d => d.name.toLowerCase().includes(q))
      .slice(0, 20);
  });

  // Video form
  title = '';
  url = '';
  description = '';
  videoType: VideoType = 'steps';
  segments: SegmentRow[] = [];

  submitting = signal(false);
  error = signal('');
  // The just-created video's dance, so we can offer a link straight to it.
  created = signal<{ danceId: number; danceName: string; title: string } | null>(null);

  constructor(
    private title$: Title,
    private danceService: DanceService,
    private videoService: VideoService
  ) {}

  ngOnInit(): void {
    this.title$.setTitle('Add Video · Dance Platform');
    this.danceService.getNames().subscribe(n => this.danceNames.set(n));
  }

  pickDance(d: { id: number; name: string }): void {
    this.selectedDance.set(d);
    this.danceQuery.set('');
  }

  clearDance(): void {
    this.selectedDance.set(null);
  }

  // Inline dance creation: when the search finds nothing, let the user create the dance
  // right here (name only) and select it. Style/music can be filled in later on the dance page.
  creatingDance = signal(false);

  createDanceFromQuery(): void {
    const name = this.danceQuery().trim();
    if (!name || this.creatingDance()) return;
    this.creatingDance.set(true);
    this.error.set('');
    this.danceService.create({ name, styleIds: [], musicalStyleIds: [] }).subscribe({
      next: dance => {
        const created = { id: dance.id, name: dance.name };
        this.danceNames.update(list => [...list, created]);
        this.selectedDance.set(created);
        this.danceQuery.set('');
        this.creatingDance.set(false);
      },
      error: () => { this.error.set('Failed to create dance. Please try again.'); this.creatingDance.set(false); }
    });
  }

  onVideoTypeChange(): void {
    if (this.videoType === 'tutorial' && this.segments.length === 0)
      this.segments = DEFAULT_SEGMENT_LABELS.map(label => ({ label, start: '', end: '' }));
  }

  addSegmentRow(): void {
    this.segments.push({ label: '', start: '', end: '' });
  }

  removeSegmentRow(index: number): void {
    this.segments.splice(index, 1);
  }

  /** Converts editor rows to API payload; returns null (and sets the error) on invalid input. */
  private buildSegments(error: WritableSignal<string>): SegmentPayload[] | null {
    if (this.videoType !== 'tutorial') return [];
    const out: SegmentPayload[] = [];
    for (const row of this.segments) {
      if (!row.label.trim() && !row.start.trim()) continue; // skip empty rows
      const startTime = parseTimeSecs(row.start);
      if (!row.label.trim() || startTime === undefined) {
        error.set('Each section needs a label and a start time (m:ss or seconds).');
        return null;
      }
      out.push({ label: row.label.trim(), startTime, endTime: parseTimeSecs(row.end) });
    }
    return out;
  }

  submit(): void {
    const dance = this.selectedDance();
    if (!dance) { this.error.set('Pick a dance to attach this video to.'); return; }
    if (!this.title.trim()) { this.error.set('Title is required.'); return; }
    if (!this.url.trim()) { this.error.set('Video URL or ID is required.'); return; }

    const parsed = parseVideoUrl(this.url);
    if (!parsed) { this.error.set('Unrecognized URL. Paste a YouTube, TikTok, or Instagram link.'); return; }

    const segments = this.buildSegments(this.error);
    if (segments === null) return;

    const payload: CreateVideoPayload = {
      title: this.title.trim(),
      videoId: parsed.videoId,
      platform: parsed.platform,
      videoType: this.videoType,
      description: this.description.trim() || undefined,
      danceId: dance.id,
      segments
    };

    this.submitting.set(true);
    this.error.set('');
    this.videoService.create(payload).subscribe({
      next: video => {
        this.created.set({ danceId: video.danceId, danceName: video.danceName, title: video.title });
        this.submitting.set(false);
        // Reset for adding another, keeping the chosen dance for convenience.
        this.title = '';
        this.url = '';
        this.description = '';
        this.videoType = 'steps';
        this.segments = [];
      },
      error: () => { this.error.set('Failed to add video. Please try again.'); this.submitting.set(false); }
    });
  }
}
