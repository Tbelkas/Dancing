import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { switchMap } from 'rxjs';
import { ProfileService } from '../../core/services/profile.service';
import { StyleService } from '../../core/services/style.service';
import { DanceService, CreateDancePayload } from '../../core/services/dance.service';
import { VideoService, CreateVideoPayload } from '../../core/services/video.service';
import { MyStyleWithDances } from '../../models/user.model';
import { Style } from '../../models/style.model';

@Component({
  selector: 'app-my-dances',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './my-dances.component.html',
  styleUrls: ['./my-dances.component.css']
})
export class MyDancesComponent implements OnInit {
  myStyles = signal<MyStyleWithDances[]>([]);
  allStyles = signal<Style[]>([]);
  selectedStyleId = signal<number | null>(null);
  loading = signal(true);
  showStylePicker = signal(false);

  // Add style form
  showAddStyle = signal(false);
  newStyleName = '';
  newStyleDesc = '';
  addingStyle = signal(false);
  addStyleError = signal('');

  // Add dance form
  showAddDance = signal(false);
  newDanceName = '';
  newDanceDesc = '';
  newDanceStyleIds = signal<Set<number>>(new Set());
  newVideoTitle = '';
  newVideoUrl = '';
  setVideoTime = false;
  newVideoStartTime = '';
  newVideoEndTime = '';
  addingDance = signal(false);
  addDanceError = signal('');

  readonly myStyleIds = computed(() => new Set(this.myStyles().map(ms => ms.styleId)));

  readonly selectedStyle = computed(() => {
    const id = this.selectedStyleId();
    return id ? this.myStyles().find(ms => ms.styleId === id) ?? null : null;
  });

  readonly learnedDances = computed(() =>
    this.selectedStyle()?.dances.filter(d => d.status === 'learned') ?? []
  );

  readonly inProgressDances = computed(() =>
    this.selectedStyle()?.dances.filter(d => d.status === 'inProgress') ?? []
  );

  constructor(
    private profileService: ProfileService,
    private styleService: StyleService,
    private danceService: DanceService,
    private videoService: VideoService
  ) {}

  ngOnInit(): void {
    this.load();
    this.styleService.getAll().subscribe(s => this.allStyles.set(s));
  }

  load(): void {
    this.loading.set(true);
    this.profileService.getMyDances().subscribe({
      next: data => {
        this.myStyles.set(data);
        if (data.length > 0 && !this.selectedStyleId()) {
          this.selectedStyleId.set(data[0].styleId);
        }
        this.loading.set(false);
      },
      error: () => this.loading.set(false)
    });
  }

  selectStyle(id: number): void {
    this.selectedStyleId.set(id);
    this.showAddDance.set(false);
  }

  toggleMyStyle(style: Style): void {
    this.styleService.toggleMyStyle(style.id).subscribe(res => {
      if (res.isMyStyle) {
        this.myStyles.update(list => [...list, { styleId: style.id, styleName: style.name, dances: [] }]);
        if (this.myStyles().length === 1) this.selectedStyleId.set(style.id);
      } else {
        const prevId = this.selectedStyleId();
        this.myStyles.update(list => list.filter(ms => ms.styleId !== style.id));
        if (prevId === style.id) {
          const remaining = this.myStyles();
          this.selectedStyleId.set(remaining.length > 0 ? remaining[0].styleId : null);
        }
      }
    });
  }

  // --- Add Style ---
  toggleAddStyle(): void {
    this.showAddStyle.set(!this.showAddStyle());
    this.addStyleError.set('');
    this.newStyleName = '';
    this.newStyleDesc = '';
  }

  submitAddStyle(): void {
    if (!this.newStyleName.trim()) { this.addStyleError.set('Name is required.'); return; }
    this.addingStyle.set(true);
    this.addStyleError.set('');
    this.styleService.create(this.newStyleName.trim(), this.newStyleDesc.trim() || undefined).subscribe({
      next: style => {
        this.allStyles.update(list => [...list, style]);
        this.showAddStyle.set(false);
        this.addingStyle.set(false);
        this.newStyleName = '';
        this.newStyleDesc = '';
      },
      error: () => { this.addStyleError.set('Failed to create style.'); this.addingStyle.set(false); }
    });
  }

  // --- Add Dance ---
  toggleAddDance(): void {
    const open = !this.showAddDance();
    this.showAddDance.set(open);
    if (open) {
      const sid = this.selectedStyleId();
      this.newDanceStyleIds.set(sid ? new Set([sid]) : new Set());
    }
    this.addDanceError.set('');
    this.newDanceName = '';
    this.newDanceDesc = '';
    this.newVideoTitle = '';
    this.newVideoUrl = '';
    this.setVideoTime = false;
    this.newVideoStartTime = '';
    this.newVideoEndTime = '';
  }

  toggleNewDanceStyle(id: number): void {
    this.newDanceStyleIds.update(s => {
      const next = new Set(s);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  private extractYouTubeId(input: string): string {
    const match = input.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([A-Za-z0-9_-]{11})/);
    return match ? match[1] : input.trim();
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

  submitAddDance(): void {
    if (!this.newDanceName.trim()) { this.addDanceError.set('Dance name is required.'); return; }
    const videoTitle = this.newVideoTitle.trim();
    const videoUrl = this.newVideoUrl.trim();
    if (videoTitle && !videoUrl) { this.addDanceError.set('YouTube URL is required when adding a video.'); return; }

    this.addingDance.set(true);
    this.addDanceError.set('');

    const dancePayload: CreateDancePayload = {
      name: this.newDanceName.trim(),
      description: this.newDanceDesc.trim() || undefined,
      styleIds: [...this.newDanceStyleIds()],
      musicalStyleIds: []
    };

    this.danceService.create(dancePayload).pipe(
      switchMap(dance => {
        if (videoTitle && videoUrl) {
          const videoPayload: CreateVideoPayload = {
            title: videoTitle,
            youTubeId: this.extractYouTubeId(videoUrl),
            danceId: dance.id,
            ...(this.setVideoTime ? {
              startTime: this.parseTimeSecs(this.newVideoStartTime),
              endTime: this.parseTimeSecs(this.newVideoEndTime)
            } : {})
          };
          return this.videoService.create(videoPayload).pipe(
            switchMap(() => this.danceService.toggleInProgress(dance.id))
          );
        }
        return this.danceService.toggleInProgress(dance.id);
      })
    ).subscribe({
      next: () => {
        this.addingDance.set(false);
        this.showAddDance.set(false);
        this.newDanceName = '';
        this.newDanceDesc = '';
        this.newVideoTitle = '';
        this.newVideoUrl = '';
        this.setVideoTime = false;
        this.newVideoStartTime = '';
        this.newVideoEndTime = '';
        this.load();
      },
      error: () => {
        this.addDanceError.set('Failed to create dance. Please try again.');
        this.addingDance.set(false);
      }
    });
  }
}
