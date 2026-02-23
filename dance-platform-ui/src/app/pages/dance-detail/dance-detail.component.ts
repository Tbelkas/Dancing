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
  templateUrl: './dance-detail.component.html',
  styleUrls: ['./dance-detail.component.css']
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
