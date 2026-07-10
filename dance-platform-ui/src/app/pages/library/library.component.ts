import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { DancePathPipe } from '../../shared/pipes/dance-path.pipe';
import { VideoService } from '../../core/services/video.service';
import { AuthService } from '../../core/services/auth.service';
import { RoleService } from '../../core/services/role.service';
import { ConfirmService } from '../../core/services/confirm.service';
import { ToastService } from '../../core/services/toast.service';
import { VideoLibraryItem } from '../../models/video.model';
import { youtubeThumbUrl } from '../../core/utils/youtube-thumb.utils';
import { ThumbFallback } from '../../core/utils/thumb-fallback';

type LibraryScope = 'mine' | 'global';

@Component({
  selector: 'app-library',
  standalone: true,
  imports: [CommonModule, RouterLink, DancePathPipe],
  templateUrl: './library.component.html',
  styleUrls: ['./library.component.css']
})
export class LibraryComponent implements OnInit {
  scope = signal<LibraryScope>('mine');
  items = signal<VideoLibraryItem[]>([]);
  loading = signal(true);
  deletingId = signal<number | null>(null);
  private readonly thumbs = new ThumbFallback();

  constructor(
    private videoService: VideoService,
    private confirmSvc: ConfirmService,
    private toast: ToastService,
    public auth: AuthService,
    public role: RoleService
  ) {}

  ngOnInit(): void {
    this.load();
  }

  setScope(scope: LibraryScope): void {
    if (this.scope() === scope) return;
    this.scope.set(scope);
    this.load();
  }

  private load(): void {
    this.loading.set(true);
    const req = this.scope() === 'global' ? this.videoService.getGlobal() : this.videoService.getMine();
    req.subscribe({
      next: items => { this.items.set(items); this.loading.set(false); },
      error: () => { this.items.set([]); this.loading.set(false); }
    });
  }

  thumbnailUrl(item: VideoLibraryItem): string | null {
    if (this.thumbs.has(item.id)) return null;
    return youtubeThumbUrl(item.videoId, item.platform);
  }

  onThumbError(id: number): void {
    this.thumbs.markFailed(id);
  }

  platformLabel(platform: string): string {
    switch (platform) {
      case 'youtube': return 'YouTube';
      case 'tiktok': return 'TikTok';
      case 'instagram': return 'Instagram';
      default: return platform;
    }
  }

  // A regular user may delete their own personal video; admins may delete anything.
  canDelete(item: VideoLibraryItem): boolean {
    return this.role.isAdmin() || item.ownerUserId === this.auth.currentUserId();
  }

  async deleteVideo(item: VideoLibraryItem, event: Event): Promise<void> {
    event.stopPropagation();
    event.preventDefault();
    if (!await this.confirmSvc.ask(`Delete video "${item.title}"? This can't be undone.`, { title: 'Delete video' })) return;
    this.deletingId.set(item.id);
    this.videoService.delete(item.id).subscribe({
      next: () => {
        this.items.update(list => list.filter(v => v.id !== item.id));
        this.deletingId.set(null);
        this.toast.success('Video deleted.');
      },
      error: () => {
        this.deletingId.set(null);
        this.toast.error('Failed to delete video.');
      }
    });
  }
}
