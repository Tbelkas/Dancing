import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { DanceService } from '../../core/services/dance.service';
import { VideoService } from '../../core/services/video.service';
import { AuthService } from '../../core/services/auth.service';
import { Dance } from '../../models/dance.model';
import { Video } from '../../models/video.model';
import { VideoPlayerComponent } from '../../shared/components/video-player/video-player.component';

@Component({
  selector: 'app-dance-detail',
  standalone: true,
  imports: [CommonModule, VideoPlayerComponent],
  template: `
    @if (dance()) {
      <div class="container">
        <div class="detail-header">
          <div>
            <h1 class="page-title">{{ dance()!.name }}</h1>
            <div class="styles-row">
              @for (style of dance()!.styles; track style) {
                <span class="badge">{{ style }}</span>
              }
            </div>
            @if (dance()!.description) {
              <p class="description">{{ dance()!.description }}</p>
            }
          </div>
          @if (auth.isAuthenticated()) {
            <div class="detail-actions">
              <button class="btn" [class.btn--accent]="dance()!.isFavorite" [class.btn--ghost]="!dance()!.isFavorite" (click)="toggleFavorite()">
                {{ dance()!.isFavorite ? 'Favorited' : 'Add to Favorites' }}
              </button>
              <button class="btn" [class.btn--primary]="dance()!.isLearned" [class.btn--ghost]="!dance()!.isLearned" (click)="toggleLearned()">
                {{ dance()!.isLearned ? 'Learned' : 'Mark as Learned' }}
              </button>
            </div>
          }
        </div>

        <section class="videos-section">
          <h2>Videos</h2>
          @if (videos().length === 0) {
            <p class="empty">No videos available for this dance yet.</p>
          } @else {
            <div class="videos-grid">
              @for (video of videos(); track video.id) {
                <div class="video-item">
                  <h3 class="video-title">{{ video.title }}</h3>
                  @if (video.description) {
                    <p class="video-desc">{{ video.description }}</p>
                  }
                  <app-video-player [youTubeId]="video.youTubeId" />
                </div>
              }
            </div>
          }
        </section>
      </div>
    } @else {
      <div class="container loading">Loading...</div>
    }
  `,
  styles: [`
    .detail-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 40px; flex-wrap: wrap; gap: 20px; }
    .styles-row { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0; }
    .description { color: var(--color-text-muted); max-width: 600px; line-height: 1.7; }
    .detail-actions { display: flex; gap: 12px; flex-wrap: wrap; align-items: flex-start; }
    .videos-section h2 { font-size: 1.5rem; margin-bottom: 24px; }
    .videos-grid { display: grid; gap: 32px; }
    .video-title { font-size: 1.1rem; font-weight: 600; margin-bottom: 6px; }
    .video-desc { color: var(--color-text-muted); font-size: 0.9rem; margin-bottom: 12px; }
    .empty { color: var(--color-text-muted); }
    .loading { padding: 60px; text-align: center; color: var(--color-text-muted); }
  `]
})
export class DanceDetailComponent implements OnInit {
  dance = signal<Dance | null>(null);
  videos = signal<Video[]>([]);

  constructor(
    private route: ActivatedRoute,
    private danceService: DanceService,
    private videoService: VideoService,
    public auth: AuthService
  ) {}

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.danceService.getById(id).subscribe(d => {
      this.dance.set(d);
      this.videoService.getByDance(id).subscribe(v => this.videos.set(v));
    });
  }

  toggleFavorite(): void {
    const d = this.dance();
    if (!d) return;
    this.danceService.toggleFavorite(d.id).subscribe(res =>
      this.dance.update(cur => cur ? { ...cur, isFavorite: res.isFavorite } : cur)
    );
  }

  toggleLearned(): void {
    const d = this.dance();
    if (!d) return;
    this.danceService.toggleLearned(d.id).subscribe(res =>
      this.dance.update(cur => cur ? { ...cur, isLearned: res.isLearned } : cur)
    );
  }
}
