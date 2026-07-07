import { Component, OnInit, OnDestroy, ElementRef, ViewChild, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ChoreoService } from '../../core/services/choreo.service';
import { ConfirmService } from '../../core/services/confirm.service';
import { ToastService } from '../../core/services/toast.service';
import { Choreo } from '../../models/choreo.model';
import { VideoSegment } from '../../models/video.model';
import { LocalVideoPlayerComponent } from '../../shared/components/local-video-player/local-video-player.component';
import { formatTimeSecs } from '../../core/utils/video-url.utils';

/**
 * Choreo videos that live on the user's own computer. The server stores only each
 * file's name and the user's saved time slots; the video itself is picked from disk
 * and played via an object URL, so it never leaves the device. A session cache in
 * ChoreoService avoids re-picking while the tab stays open, but a fresh visit always
 * starts with a file prompt — browsers can't reopen local files on their own.
 */
@Component({
  selector: 'app-my-choreos',
  standalone: true,
  imports: [CommonModule, LocalVideoPlayerComponent],
  templateUrl: './my-choreos.component.html',
  styleUrls: ['./my-choreos.component.css']
})
export class MyChoreosComponent implements OnInit, OnDestroy {
  choreos = signal<Choreo[]>([]);
  loading = signal(true);
  selected = signal<Choreo | null>(null);
  videoUrl = signal<string | null>(null);
  /** Set when the re-picked file's name differs from the one saved for the choreo. */
  fileMismatch = signal<string | null>(null);
  deletingId = signal<number | null>(null);

  @ViewChild('fileInput', { static: true }) fileInput!: ElementRef<HTMLInputElement>;

  /** What the next file-pick is for: a brand-new choreo, or re-linking an existing one. */
  private pickTarget: Choreo | 'new' = 'new';

  formatTime = formatTimeSecs;

  constructor(
    private choreoService: ChoreoService,
    private confirmSvc: ConfirmService,
    private toast: ToastService
  ) {}

  ngOnInit(): void {
    this.choreoService.getMine().subscribe({
      next: list => { this.choreos.set(list); this.loading.set(false); },
      error: () => { this.choreos.set([]); this.loading.set(false); }
    });
  }

  ngOnDestroy(): void {
    this.releaseVideoUrl();
  }

  pickNewFile(): void {
    this.pickTarget = 'new';
    this.fileInput.nativeElement.click();
  }

  openChoreo(choreo: Choreo): void {
    const cached = this.choreoService.recallFile(choreo.id);
    if (cached) {
      this.playFile(choreo, cached);
      return;
    }
    this.pickTarget = choreo;
    this.fileInput.nativeElement.click();
  }

  onFilePicked(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = ''; // allow re-picking the same file later
    if (!file) return;

    if (this.pickTarget === 'new') this.createChoreo(file);
    else this.linkFile(this.pickTarget, file);
  }

  closePlayer(): void {
    this.releaseVideoUrl();
    this.selected.set(null);
    this.fileMismatch.set(null);
  }

  /** Persist the real duration the first time the browser reads the file's metadata. */
  onDurationDetected(duration: number): void {
    const choreo = this.selected();
    if (!choreo || choreo.durationSeconds === duration) return;
    this.choreoService.update(choreo.id, { durationSeconds: duration }).subscribe({
      next: updated => this.applyUpdate(updated),
      error: () => {} // display-only metadata; not worth surfacing a failure
    });
  }

  saveLoop(payload: { label: string; startTime: number; endTime: number }): void {
    const choreo = this.selected();
    if (!choreo) return;
    this.choreoService.addLoop(choreo.id, payload).subscribe({
      next: updated => { this.applyUpdate(updated); this.toast.success('Loop saved.'); },
      error: () => this.toast.error('Failed to save loop.')
    });
  }

  async deleteLoop(loop: VideoSegment): Promise<void> {
    const choreo = this.selected();
    if (!choreo) return;
    if (!await this.confirmSvc.ask(`Delete loop "${loop.label}"?`, { title: 'Delete loop' })) return;
    this.choreoService.deleteLoop(choreo.id, loop.id).subscribe({
      next: updated => this.applyUpdate(updated),
      error: () => this.toast.error('Failed to delete loop.')
    });
  }

  async deleteChoreo(choreo: Choreo, event: Event): Promise<void> {
    event.stopPropagation();
    if (!await this.confirmSvc.ask(
      `Remove "${choreo.name}" and its ${choreo.loops.length} saved loop${choreo.loops.length === 1 ? '' : 's'}? ` +
      `The video file on your computer is not touched.`,
      { title: 'Remove choreo' }
    )) return;
    this.deletingId.set(choreo.id);
    this.choreoService.delete(choreo.id).subscribe({
      next: () => {
        this.choreoService.forgetFile(choreo.id);
        this.choreos.update(list => list.filter(c => c.id !== choreo.id));
        if (this.selected()?.id === choreo.id) this.closePlayer();
        this.deletingId.set(null);
        this.toast.success('Choreo removed.');
      },
      error: () => {
        this.deletingId.set(null);
        this.toast.error('Failed to remove choreo.');
      }
    });
  }

  durationLabel(choreo: Choreo): string | null {
    return choreo.durationSeconds ? formatTimeSecs(choreo.durationSeconds) : null;
  }

  private createChoreo(file: File): void {
    const name = file.name.replace(/\.[^.]+$/, '') || file.name;
    this.choreoService.create({ name, fileName: file.name }).subscribe({
      next: choreo => {
        this.choreos.update(list => [choreo, ...list]);
        this.playFile(choreo, file);
        this.toast.success('Choreo added — only the file name was saved.');
      },
      error: () => this.toast.error('Failed to add choreo.')
    });
  }

  private linkFile(choreo: Choreo, file: File): void {
    this.playFile(choreo, file);
    if (file.name !== choreo.fileName) {
      this.fileMismatch.set(
        `This file is named "${file.name}", but "${choreo.fileName}" was saved for this choreo. ` +
        `Your loops may not line up if it's a different video.`
      );
    }
  }

  private playFile(choreo: Choreo, file: File): void {
    this.choreoService.rememberFile(choreo.id, file);
    this.releaseVideoUrl();
    this.fileMismatch.set(null);
    this.videoUrl.set(URL.createObjectURL(file));
    this.selected.set(choreo);
  }

  /** Swap the updated choreo into both the list and, if open, the player. */
  private applyUpdate(updated: Choreo): void {
    this.choreos.update(list => list.map(c => c.id === updated.id ? updated : c));
    if (this.selected()?.id === updated.id) this.selected.set(updated);
  }

  private releaseVideoUrl(): void {
    const url = this.videoUrl();
    if (url) URL.revokeObjectURL(url);
    this.videoUrl.set(null);
  }
}
