import { Component, OnInit, signal, WritableSignal } from '@angular/core';
import { CommonModule, Location } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { DanceService, UpdateDancePayload } from '../../core/services/dance.service';
import { VideoService, CreateVideoPayload, SegmentPayload } from '../../core/services/video.service';
import { StyleService } from '../../core/services/style.service';
import { MusicalStyleService } from '../../core/services/musical-style.service';
import { InstructorService } from '../../core/services/instructor.service';
import { AuthService } from '../../core/services/auth.service';
import { RoleService } from '../../core/services/role.service';
import { Dance } from '../../models/dance.model';
import { Video, VideoType, viewCountBucket } from '../../models/video.model';
import { Style } from '../../models/style.model';
import { MusicalStyle } from '../../models/musical-style.model';
import { Instructor } from '../../models/instructor.model';
import { VideoPlayerComponent } from '../../shared/components/video-player/video-player.component';

const DIFFICULTIES = ['None', 'Beginner', 'Intermediate', 'Advanced'];
const DEFAULT_SEGMENT_LABELS = ['Theory', 'Steps', 'Practice'];

interface SegmentRow {
  label: string;
  start: string;
  end: string;
}

@Component({
  selector: 'app-dance-detail',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, VideoPlayerComponent],
  templateUrl: './dance-detail.component.html',
  styleUrls: ['./dance-detail.component.css']
})
export class DanceDetailComponent implements OnInit {
  readonly difficulties = DIFFICULTIES;
  readonly stars = [1, 2, 3, 4, 5];

  dance = signal<Dance | null>(null);
  notFound = signal(false);
  videos = signal<Video[]>([]);
  selectedVideo = signal<Video | null>(null);
  readonly viewCountBucket = viewCountBucket;

  // Feedback
  actionError = signal('');

  // Admin: add video form
  showAddVideo = signal(false);
  newVideoTitle = '';
  newVideoUrl = '';
  newVideoDesc = '';
  newVideoType: VideoType = 'steps';
  newVideoSegments: SegmentRow[] = [];
  addingVideo = signal(false);
  addVideoError = signal('');

  // Admin: edit dance form
  showEditDance = signal(false);
  editName = '';
  editDescription = '';
  editDifficulty = 'None';
  editStyleIds: number[] = [];
  editMusicalStyleIds: number[] = [];
  editInstructorIds: number[] = [];
  allStyles = signal<Style[]>([]);
  allMusicalStyles = signal<MusicalStyle[]>([]);
  allInstructors = signal<Instructor[]>([]);
  savingDance = signal(false);
  editDanceError = signal('');

  // Admin: edit video time/type/segments
  editingVideoId = signal<number | null>(null);
  editVideoStartTime = '';
  editVideoEndTime = '';
  editVideoType: VideoType = 'steps';
  editVideoSegments: SegmentRow[] = [];
  savingVideoTime = signal(false);
  editVideoTimeError = signal('');

  // Admin: delete dance
  deletingDance = signal(false);

  // Rating hover state
  hoverRating = signal(0);

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private location: Location,
    private danceService: DanceService,
    private videoService: VideoService,
    private styleService: StyleService,
    private musicalStyleService: MusicalStyleService,
    private instructorService: InstructorService,
    public auth: AuthService,
    public role: RoleService
  ) {}

  ngOnInit(): void {
    const slug = this.route.snapshot.paramMap.get('slug') ?? '';
    this.danceService.getByIdOrSlug(slug).subscribe({
      next: d => {
        this.dance.set(d);
        // Rewrite legacy numeric URLs (/dances/22) to the slug form without reloading
        if (slug !== d.slug) {
          this.location.replaceState(`/dances/${d.slug}`);
        }
        this.videoService.getByDance(d.id).subscribe(v => {
          this.videos.set(v);
          if (v.length === 1) {
            this.selectedVideo.set(v[0]);
            this.videoService.recordView(v[0].id).subscribe();
          }
        });
      },
      error: err => {
        if (err?.status === 404) this.notFound.set(true);
        else this.router.navigate(['/dances']);
      }
    });
    if (this.role.isAdmin()) {
      this.styleService.getAll().subscribe(s => this.allStyles.set(s));
      this.musicalStyleService.getAll().subscribe(s => this.allMusicalStyles.set(s));
      this.instructorService.getAll().subscribe(i => this.allInstructors.set(i));
    }
  }

  selectVideo(video: Video): void {
    const alreadySelected = this.selectedVideo()?.id === video.id;
    this.selectedVideo.set(alreadySelected ? null : video);
    if (!alreadySelected) {
      this.videoService.recordView(video.id).subscribe();
    }
  }

  toggleFavorite(): void {
    const d = this.dance();
    if (!d) return;
    this.actionError.set('');
    this.danceService.toggleFavorite(d.id).subscribe({
      next: res => this.dance.update(cur => cur ? {
        ...cur,
        isFavorite: res.isFavorite,
        favoriteCount: cur.favoriteCount + (res.isFavorite ? 1 : -1)
      } : cur),
      error: () => this.actionError.set('Action failed. Please log in again.')
    });
  }

  toggleLearned(): void {
    const d = this.dance();
    if (!d) return;
    this.actionError.set('');
    this.danceService.toggleLearned(d.id).subscribe({
      next: res => this.dance.update(cur => cur ? {
        ...cur,
        isLearned: res.isLearned,
        learnedCount: cur.learnedCount + (res.isLearned ? 1 : -1)
      } : cur),
      error: () => this.actionError.set('Action failed. Please log in again.')
    });
  }

  toggleInProgress(): void {
    const d = this.dance();
    if (!d) return;
    this.actionError.set('');
    this.danceService.toggleInProgress(d.id).subscribe({
      next: res => this.dance.update(cur => cur ? { ...cur, isInProgress: res.isInProgress } : cur),
      error: () => this.actionError.set('Action failed. Please log in again.')
    });
  }

  // Rating
  rateDance(rating: number): void {
    const d = this.dance();
    if (!d) return;
    this.danceService.rate(d.id, rating).subscribe({
      next: updated => this.dance.update(cur => cur ? {
        ...cur,
        userRating: updated.userRating,
        averageRating: updated.averageRating,
        ratingCount: updated.ratingCount
      } : cur),
      error: () => this.actionError.set('Rating failed. Please log in again.')
    });
  }

  // Admin: add video
  toggleAddVideo(): void {
    this.showAddVideo.update(v => !v);
    this.addVideoError.set('');
    this.newVideoTitle = '';
    this.newVideoUrl = '';
    this.newVideoDesc = '';
    this.newVideoType = 'steps';
    this.newVideoSegments = [];
  }

  onNewVideoTypeChange(): void {
    if (this.newVideoType === 'tutorial' && this.newVideoSegments.length === 0) {
      this.newVideoSegments = DEFAULT_SEGMENT_LABELS.map(label => ({ label, start: '', end: '' }));
    }
  }

  onEditVideoTypeChange(): void {
    if (this.editVideoType === 'tutorial' && this.editVideoSegments.length === 0) {
      this.editVideoSegments = DEFAULT_SEGMENT_LABELS.map(label => ({ label, start: '', end: '' }));
    }
  }

  addSegmentRow(rows: SegmentRow[]): void {
    rows.push({ label: '', start: '', end: '' });
  }

  removeSegmentRow(rows: SegmentRow[], index: number): void {
    rows.splice(index, 1);
  }

  /** Converts editor rows to API payload; returns null (and sets the given error) on invalid input. */
  private buildSegments(videoType: VideoType, rows: SegmentRow[], error: WritableSignal<string>): SegmentPayload[] | null {
    if (videoType !== 'tutorial') return [];
    const segments: SegmentPayload[] = [];
    for (const row of rows) {
      if (!row.label.trim() && !row.start.trim()) continue; // skip empty rows
      const startTime = this.parseTimeSecs(row.start);
      if (!row.label.trim() || startTime === undefined) {
        error.set('Each section needs a label and a start time (m:ss or seconds).');
        return null;
      }
      segments.push({ label: row.label.trim(), startTime, endTime: this.parseTimeSecs(row.end) });
    }
    return segments;
  }

  private parseVideoUrl(input: string): { platform: string; videoId: string } | null {
    const url = input.trim();

    const tiktok = url.match(/tiktok\.com\/@[^/]+\/video\/(\d+)/);
    if (tiktok) return { platform: 'tiktok', videoId: tiktok[1] };

    const ig = url.match(/instagram\.com\/(?:p|reel)\/([A-Za-z0-9_-]+)/);
    if (ig) return { platform: 'instagram', videoId: ig[1] };

    const yt = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([A-Za-z0-9_-]{11})/);
    if (yt) return { platform: 'youtube', videoId: yt[1] };

    if (/^[A-Za-z0-9_-]{11}$/.test(url)) return { platform: 'youtube', videoId: url };

    return null;
  }

  submitAddVideo(): void {
    const danceId = this.dance()?.id;
    if (!danceId) return;
    if (!this.newVideoTitle.trim()) { this.addVideoError.set('Title is required.'); return; }
    if (!this.newVideoUrl.trim()) { this.addVideoError.set('Video URL or ID is required.'); return; }

    const parsed = this.parseVideoUrl(this.newVideoUrl);
    if (!parsed) { this.addVideoError.set('Unrecognized URL. Paste a YouTube, TikTok, or Instagram link.'); return; }

    const segments = this.buildSegments(this.newVideoType, this.newVideoSegments, this.addVideoError);
    if (segments === null) return;

    const payload: CreateVideoPayload = {
      title: this.newVideoTitle.trim(),
      videoId: parsed.videoId,
      platform: parsed.platform,
      videoType: this.newVideoType,
      description: this.newVideoDesc.trim() || undefined,
      danceId,
      segments
    };

    this.addingVideo.set(true);
    this.addVideoError.set('');
    this.videoService.create(payload).subscribe({
      next: video => {
        this.videos.update(list => [...list, video]);
        this.dance.update(d => d ? { ...d, videoCount: d.videoCount + 1 } : d);
        this.showAddVideo.set(false);
        this.addingVideo.set(false);
        this.newVideoTitle = '';
        this.newVideoUrl = '';
        this.newVideoDesc = '';
        this.newVideoType = 'steps';
        this.newVideoSegments = [];
      },
      error: () => { this.addVideoError.set('Failed to add video.'); this.addingVideo.set(false); }
    });
  }

  // Admin: edit video time/type/segments
  toggleEditVideoTime(video: Video): void {
    if (this.editingVideoId() === video.id) {
      this.editingVideoId.set(null);
      return;
    }
    this.editVideoStartTime = video.startTime != null ? this.formatTimeSecs(video.startTime) : '';
    this.editVideoEndTime = video.endTime != null ? this.formatTimeSecs(video.endTime) : '';
    this.editVideoType = video.videoType === 'tutorial' ? 'tutorial' : 'steps';
    this.editVideoSegments = video.segments.map(s => ({
      label: s.label,
      start: this.formatTimeSecs(s.startTime),
      end: s.endTime != null ? this.formatTimeSecs(s.endTime) : ''
    }));
    this.editVideoTimeError.set('');
    this.editingVideoId.set(video.id);
  }

  private formatTimeSecs(seconds: number): string {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  }

  private parseTimeSecs(input: string): number | undefined {
    const s = input.trim();
    if (!s) return undefined;
    if (s.includes(':')) {
      const [m, sec] = s.split(':').map(Number);
      return isNaN(m) || isNaN(sec) ? undefined : m * 60 + sec;
    }
    const n = Number(s);
    return isNaN(n) ? undefined : n;
  }

  submitEditVideoTime(video: Video): void {
    const startTime = this.parseTimeSecs(this.editVideoStartTime);
    const endTime = this.parseTimeSecs(this.editVideoEndTime);
    const segments = this.buildSegments(this.editVideoType, this.editVideoSegments, this.editVideoTimeError);
    if (segments === null) return;
    this.savingVideoTime.set(true);
    this.editVideoTimeError.set('');
    this.videoService.update(video.id, {
      updateTimes: true,
      startTime,
      endTime,
      videoType: this.editVideoType,
      updateSegments: true,
      segments
    }).subscribe({
      next: updated => {
        this.videos.update(list => list.map(v => v.id === updated.id ? updated : v));
        if (this.selectedVideo()?.id === updated.id) this.selectedVideo.set(updated);
        this.editingVideoId.set(null);
        this.savingVideoTime.set(false);
      },
      error: () => { this.editVideoTimeError.set('Failed to save. Please try again.'); this.savingVideoTime.set(false); }
    });
  }

  deleteVideo(video: Video): void {
    if (!confirm(`Delete video "${video.title}"?`)) return;
    this.videoService.delete(video.id).subscribe({
      next: () => {
        this.videos.update(list => list.filter(v => v.id !== video.id));
        this.dance.update(d => d ? { ...d, videoCount: d.videoCount - 1 } : d);
        if (this.selectedVideo()?.id === video.id) this.selectedVideo.set(null);
      },
      error: () => alert('Failed to delete video.')
    });
  }

  // Admin: edit dance
  toggleEditDance(): void {
    const d = this.dance();
    if (!d) return;
    if (this.showEditDance()) {
      this.showEditDance.set(false);
      return;
    }
    this.editName = d.name;
    this.editDescription = d.description ?? '';
    this.editDifficulty = d.difficulty;
    this.editStyleIds = this.allStyles()
      .filter(s => d.styles.includes(s.name))
      .map(s => s.id);
    this.editMusicalStyleIds = this.allMusicalStyles()
      .filter(s => d.musicalStyles.includes(s.name))
      .map(s => s.id);
    this.editInstructorIds = this.allInstructors()
      .filter(i => d.instructors.includes(i.name))
      .map(i => i.id);
    this.editDanceError.set('');
    this.showEditDance.set(true);
  }

  toggleEditStyleId(id: number): void {
    this.editStyleIds = this.editStyleIds.includes(id)
      ? this.editStyleIds.filter(x => x !== id)
      : [...this.editStyleIds, id];
  }

  toggleEditMusicalStyleId(id: number): void {
    this.editMusicalStyleIds = this.editMusicalStyleIds.includes(id)
      ? this.editMusicalStyleIds.filter(x => x !== id)
      : [...this.editMusicalStyleIds, id];
  }

  toggleEditInstructorId(id: number): void {
    this.editInstructorIds = this.editInstructorIds.includes(id)
      ? this.editInstructorIds.filter(x => x !== id)
      : [...this.editInstructorIds, id];
  }

  submitEditDance(): void {
    if (!this.editName.trim()) { this.editDanceError.set('Name is required.'); return; }
    const d = this.dance();
    if (!d) return;
    const payload: UpdateDancePayload = {
      name: this.editName.trim(),
      description: this.editDescription.trim() || undefined,
      difficulty: this.editDifficulty,
      styleIds: this.editStyleIds,
      musicalStyleIds: this.editMusicalStyleIds,
      instructorIds: this.editInstructorIds
    };
    this.savingDance.set(true);
    this.editDanceError.set('');
    this.danceService.update(d.id, payload).subscribe({
      next: updated => {
        this.dance.set({
          ...updated,
          isFavorite: d.isFavorite,
          isLearned: d.isLearned,
          isInProgress: d.isInProgress,
          favoriteCount: d.favoriteCount,
          learnedCount: d.learnedCount,
          userRating: d.userRating
        });
        if (updated.slug !== d.slug) {
          this.location.replaceState(`/dances/${updated.slug}`);
        }
        this.showEditDance.set(false);
        this.savingDance.set(false);
      },
      error: () => { this.editDanceError.set('Failed to save changes.'); this.savingDance.set(false); }
    });
  }

  deleteDance(): void {
    const d = this.dance();
    if (!d || !confirm(`Permanently delete "${d.name}"? This cannot be undone.`)) return;
    this.deletingDance.set(true);
    this.danceService.delete(d.id).subscribe({
      next: () => this.router.navigate(['/dances']),
      error: () => { alert('Failed to delete dance.'); this.deletingDance.set(false); }
    });
  }
}
