import { Component, OnInit, OnDestroy, ElementRef, ViewChild, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChoreoService } from '../../core/services/choreo.service';
import { ConfirmService } from '../../core/services/confirm.service';
import { PracticeTimerService } from '../../core/services/practice-timer.service';
import { ToastService } from '../../core/services/toast.service';
import { Choreo } from '../../models/choreo.model';
import { VideoSegment } from '../../models/video.model';
import { LocalVideoPlayerComponent } from '../../shared/components/local-video-player/local-video-player.component';
import { formatTimeSecs } from '../../core/utils/video-url.utils';
import { delayedLoading } from '../../core/utils/delayed-loading';
import { SkeletonCount } from '../../core/utils/skeleton-count';

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
  imports: [CommonModule, FormsModule, LocalVideoPlayerComponent],
  templateUrl: './my-choreos.component.html',
  styleUrls: ['./my-choreos.component.css']
})
export class MyChoreosComponent implements OnInit, OnDestroy {
  choreos = signal<Choreo[]>([]);
  loading = signal(true);
  showSkeleton = delayedLoading(this.loading);
  readonly skeleton = new SkeletonCount('choreos', 3, { max: 10 });
  selected = signal<Choreo | null>(null);
  videoUrl = signal<string | null>(null);
  /** Set when the re-picked file's name differs from the one saved for the choreo. */
  fileMismatch = signal<string | null>(null);
  /** Choreo whose title is currently an inline rename input. */
  renamingId = signal<number | null>(null);
  renameValue = '';

  @ViewChild('fileInput', { static: true }) fileInput!: ElementRef<HTMLInputElement>;
  @ViewChild('renameInput') renameInput?: ElementRef<HTMLInputElement>;

  /** What the next file-pick is for: a brand-new choreo, or re-linking an existing one. */
  private pickTarget: Choreo | 'new' = 'new';

  formatTime = formatTimeSecs;

  constructor(
    private choreoService: ChoreoService,
    private confirmSvc: ConfirmService,
    private toast: ToastService,
    private practiceTimer: PracticeTimerService
  ) {}

  ngOnInit(): void {
    this.choreoService.getMine().subscribe({
      next: list => { this.choreos.set(list); this.skeleton.remember(list.length); this.loading.set(false); },
      error: () => { this.choreos.set([]); this.loading.set(false); }
    });
  }

  ngOnDestroy(): void {
    this.releaseVideoUrl();
    // Flush any accrued practice time; the session buffer decides whether it stays live.
    this.practiceTimer.stop();
  }

  /** Choreo playback counts as practice, same as watching a dance video. */
  onPlayingChange(playing: boolean): void {
    const choreo = this.selected();
    if (playing && choreo) this.practiceTimer.setActiveChoreo(choreo.id);
    this.practiceTimer.setPlaying(playing);
  }

  pickNewFile(): void {
    this.pickTarget = 'new';
    this.fileInput.nativeElement.click();
  }

  /** Re-pick the file for an open choreo — swaps what's playing (and the session
   *  cache) even when a cached file exists, e.g. after re-exporting the video. */
  changeVideo(choreo: Choreo): void {
    this.pickTarget = choreo;
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

  /** Persist the rotation the user picked in the player. */
  onRotationChange(degrees: number): void {
    const choreo = this.selected();
    if (!choreo || choreo.rotationDegrees === degrees) return;
    this.choreoService.update(choreo.id, { rotationDegrees: degrees }).subscribe({
      next: updated => this.applyUpdate(updated),
      error: () => this.toast.error('Failed to save rotation.')
    });
  }

  startRename(choreo: Choreo, event: Event): void {
    event.stopPropagation();
    this.renameValue = choreo.name;
    this.renamingId.set(choreo.id);
    setTimeout(() => this.renameInput?.nativeElement.select());
  }

  cancelRename(): void {
    this.renamingId.set(null);
  }

  commitRename(choreo: Choreo): void {
    if (this.renamingId() !== choreo.id) return; // Enter already committed; ignore the blur
    this.renamingId.set(null);
    const name = this.renameValue.trim();
    if (!name || name === choreo.name) return;
    this.choreoService.update(choreo.id, { name }).subscribe({
      next: updated => this.applyUpdate(updated),
      error: () => this.toast.error('Failed to rename choreo.')
    });
  }

  /** The re-picked file has a different name; make it the saved one going forward. */
  adoptPickedFileName(): void {
    const choreo = this.selected();
    const file = choreo ? this.choreoService.recallFile(choreo.id) : undefined;
    if (!choreo || !file) return;
    this.choreoService.update(choreo.id, { fileName: file.name }).subscribe({
      next: updated => {
        this.applyUpdate(updated);
        this.fileMismatch.set(null);
        this.toast.success('File name updated.');
      },
      error: () => this.toast.error('Failed to update file name.')
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
    this.applyUpdate({ ...choreo, loops: choreo.loops.filter(l => l.id !== loop.id) });
    this.toast.undoable(`Loop "${loop.label}" deleted.`, {
      undo: () => this.applyUpdate(choreo),
      commit: () => this.choreoService.deleteLoop(choreo.id, loop.id).subscribe({
        next: updated => this.applyUpdate(updated),
        error: () => { this.applyUpdate(choreo); this.toast.error('Failed to delete loop.'); }
      })
    });
  }

  async deleteChoreo(choreo: Choreo, event: Event): Promise<void> {
    event.stopPropagation();
    if (!await this.confirmSvc.ask(
      `Remove "${choreo.name}" and its ${choreo.loops.length} saved loop${choreo.loops.length === 1 ? '' : 's'}? ` +
      `The video file on your computer is not touched.`,
      { title: 'Remove choreo' }
    )) return;
    const index = this.choreos().findIndex(c => c.id === choreo.id);
    this.choreos.update(list => list.filter(c => c.id !== choreo.id));
    if (this.selected()?.id === choreo.id) this.closePlayer();

    // forgetFile drops the handle to the file on disk, so it waits for the commit too —
    // undoing has to give back a choreo the user can still play without re-picking it.
    const restore = () => this.choreos.update(list => {
      const next = [...list];
      next.splice(index, 0, choreo);
      return next;
    });
    this.toast.undoable(`"${choreo.name}" removed.`, {
      undo: restore,
      commit: () => this.choreoService.delete(choreo.id).subscribe({
        next: () => this.choreoService.forgetFile(choreo.id),
        error: () => { restore(); this.toast.error('Failed to remove choreo.'); }
      })
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
    // Swapping src doesn't reliably fire pause — stop the practice clock explicitly;
    // it resumes (on the new choreo) when the user presses play.
    this.practiceTimer.setPlaying(false);
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
