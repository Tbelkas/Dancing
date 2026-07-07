import { Component, EventEmitter, Input, OnInit, Output, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { DanceService } from '../../../core/services/dance.service';
import { VideoService, CreateVideoPayload, SegmentPayload } from '../../../core/services/video.service';
import { RoleService } from '../../../core/services/role.service';
import { parseVideoUrl, parseTimeSecs, fetchVideoTitle } from '../../../core/utils/video-url.utils';
import { Dance } from '../../../models/dance.model';
import { Video, VideoType } from '../../../models/video.model';

const DEFAULT_SEGMENT_LABELS = ['Theory', 'Steps', 'Practice'];

interface SegmentRow {
  label: string;
  start: string;
  end: string;
}

/**
 * "Add Video" form shared by the Browse page (DancesComponent) and the dance detail page.
 * The two contexts differ in one axis — how the target dance is chosen:
 *   - Browse ({@link fixedDance} null): a searchable dance picker, with an inline
 *     "create this dance" path, plus a success banner so the admin can add several in a row.
 *   - Detail ({@link fixedDance} set): the dance is fixed, and admins additionally get a
 *     description, a Steps/Tutorial type toggle and the tutorial section editor.
 * Both share the URL parsing, scope handling (admin-only) and VideoService.create call, so
 * that logic lives here once; the template keeps each context's exact field layout.
 *
 * Available to any authenticated user — the Global/Local scope selector is the only part
 * gated to admins (via the injected RoleService).
 */
@Component({
  selector: 'app-add-video-form',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './add-video-form.component.html',
  styleUrls: ['./add-video-form.component.css']
})
export class AddVideoFormComponent implements OnInit {
  /** When set, the video is attached to this fixed dance (detail page). Null → searchable picker (Browse). */
  @Input() fixedDance: { id: number; name: string } | null = null;

  /** Emitted with the created video so the parent can update its lists/counts (and close, on detail). */
  @Output() created = new EventEmitter<Video>();
  /** Picker mode only: a dance created inline via "create from query", so the Browse grid can show it. */
  @Output() danceCreated = new EventEmitter<Dance>();

  // Shared inputs
  title = '';
  url = '';
  scope: 'global' | 'local' = 'global';
  saving = signal(false);
  error = signal('');

  // Title autofill from the pasted URL (oEmbed). Tracks the last fetched video so we
  // don't refetch on every keystroke, and the last auto-set title so we never clobber
  // a title the user typed or edited themselves.
  private lastTitleFetchKey = '';
  private autoTitle = '';

  // Detail-only inputs (admin: type + segments; everyone: description)
  description = '';
  videoType: VideoType = 'steps';
  segments: SegmentRow[] = [];

  // Picker-mode (Browse) state: search a dance by name, or create one inline.
  private danceNames = signal<{ id: number; name: string }[]>([]);
  danceQuery = signal('');
  selectedDance = signal<{ id: number; name: string } | null>(null);
  creatingDance = signal(false);
  /** Last successfully-added video, for the "Added X to Y" confirmation banner (picker mode). */
  lastCreated = signal<{ danceId: number; danceName: string; title: string } | null>(null);
  danceMatches = computed(() => {
    const q = this.danceQuery().trim().toLowerCase();
    if (!q) return [];
    return this.danceNames()
      .filter(d => d.name.toLowerCase().includes(q))
      .slice(0, 20);
  });

  constructor(
    private danceService: DanceService,
    private videoService: VideoService,
    public role: RoleService
  ) {}

  ngOnInit(): void {
    // Lazy-load the dance name list the picker searches over, once — only in picker mode.
    if (!this.fixedDance) {
      this.danceService.getNames().subscribe(n => this.danceNames.set(n));
    }
  }

  pickDance(d: { id: number; name: string }): void {
    this.selectedDance.set(d);
    this.danceQuery.set('');
  }

  clearDance(): void {
    this.selectedDance.set(null);
  }

  // Inline dance creation: when the search finds no dance, create one (name only) and select it.
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
        this.danceCreated.emit(dance);
      },
      error: () => { this.error.set('Failed to create dance. Please try again.'); this.creatingDance.set(false); }
    });
  }

  onUrlChange(value: string): void {
    this.url = value;
    const parsed = parseVideoUrl(value);
    if (!parsed) return;
    const key = `${parsed.platform}:${parsed.videoId}`;
    if (key === this.lastTitleFetchKey) return;
    this.lastTitleFetchKey = key;
    fetchVideoTitle(value).then(title => {
      if (!title || key !== this.lastTitleFetchKey) return;
      if (!this.title.trim() || this.title === this.autoTitle) {
        this.title = title;
        this.autoTitle = title;
      }
    });
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

  /** Converts section editor rows to API payload; returns null (and sets the error) on invalid input. */
  private buildSegments(): SegmentPayload[] | null {
    if (this.videoType !== 'tutorial') return [];
    const segments: SegmentPayload[] = [];
    for (const row of this.segments) {
      if (!row.label.trim() && !row.start.trim()) continue; // skip empty rows
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
    const dance = this.fixedDance ?? this.selectedDance();
    if (!dance) { this.error.set('Pick a dance to attach this video to.'); return; }
    // Detail requires an explicit title; the Browse picker defaults it to the dance name.
    if (this.fixedDance && !this.title.trim()) { this.error.set('Title is required.'); return; }
    if (!this.url.trim()) { this.error.set('Video URL or ID is required.'); return; }

    const parsed = parseVideoUrl(this.url);
    if (!parsed) { this.error.set('Unrecognized URL. Paste a YouTube, TikTok, or Instagram link.'); return; }

    const payload: CreateVideoPayload = {
      title: this.fixedDance ? this.title.trim() : (this.title.trim() || dance.name),
      videoId: parsed.videoId,
      platform: parsed.platform,
      danceId: dance.id,
      // Scope only matters for admins; the server forces personal for everyone else.
      ...(this.role.isAdmin() ? { scope: this.scope } : {})
    };

    // The detail form also carries a type, description and tutorial sections.
    if (this.fixedDance) {
      const segments = this.buildSegments();
      if (segments === null) return;
      payload.videoType = this.videoType;
      payload.description = this.description.trim() || undefined;
      payload.segments = segments;
    }

    this.saving.set(true);
    this.error.set('');
    this.videoService.create(payload).subscribe({
      next: video => {
        this.saving.set(false);
        if (!this.fixedDance) {
          // Browse: keep the dance selected for adding another; clear the per-video inputs
          // and surface a confirmation banner.
          this.lastCreated.set({ danceId: video.danceId, danceName: video.danceName, title: video.title });
          this.title = '';
          this.url = '';
          this.lastTitleFetchKey = '';
          this.autoTitle = '';
        }
        this.created.emit(video);
      },
      error: () => { this.error.set(this.fixedDance ? 'Failed to add video.' : 'Failed to add video. Please try again.'); this.saving.set(false); }
    });
  }
}
