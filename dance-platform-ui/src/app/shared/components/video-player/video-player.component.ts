import { Component, Input, OnInit, OnDestroy, ElementRef, ViewChild, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';


@Component({
  selector: 'app-video-player',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './video-player.component.html',
  styleUrls: ['./video-player.component.css']
})
export class VideoPlayerComponent implements OnInit, OnDestroy {
  @Input({ required: true }) youTubeId!: string;
  @Input() startTime?: number;
  @Input() endTime?: number;
  @ViewChild('playerContainer', { static: true }) playerContainer!: ElementRef;

  readonly playbackRates = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 2];
  currentRate = signal(1);
  repeating = signal(false);
  videoDuration = signal(0);

  repeatStart = 0;
  repeatEnd = 0;

  private player: YT.Player | null = null;
  private repeatInterval: ReturnType<typeof setInterval> | null = null;

  ngOnInit(): void {
    if (typeof window !== 'undefined') {
      if (!window.YT) {
        const tag = document.createElement('script');
        tag.src = 'https://www.youtube.com/iframe_api';
        document.body.appendChild(tag);
        (window as any).onYouTubeIframeAPIReady = () => this.createPlayer();
      } else {
        this.createPlayer();
      }
    }
  }

  ngOnDestroy(): void {
    this.clearRepeat();
    this.player?.destroy();
  }

  setRate(rate: number): void {
    this.currentRate.set(rate);
    this.player?.setPlaybackRate(rate);
  }

  onStartSliderChange(value: number): void {
    this.repeatStart = Math.min(value, this.repeatEnd > 0 ? this.repeatEnd - 1 : value);
  }

  onEndSliderChange(value: number): void {
    this.repeatEnd = Math.max(value, this.repeatStart + 1);
  }

  formatTime(seconds: number): string {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  }

  toggleRepeat(): void {
    if (this.repeating()) {
      this.clearRepeat();
      this.repeating.set(false);
    } else if (this.repeatEnd > this.repeatStart) {
      this.repeating.set(true);
      this.player?.seekTo(this.repeatStart, true);
      this.player?.playVideo();
      this.repeatInterval = setInterval(() => {
        const current = this.player?.getCurrentTime() ?? 0;
        if (current >= this.repeatEnd) {
          this.player?.seekTo(this.repeatStart, true);
        }
      }, 250);
    }
  }

  private createPlayer(): void {
    const playerVars: YT.PlayerVars = { rel: 0, modestbranding: 1 };
    if (this.startTime != null) playerVars['start'] = this.startTime;
    if (this.endTime != null) playerVars['end'] = this.endTime;

    this.player = new window.YT.Player(this.playerContainer.nativeElement, {
      videoId: this.youTubeId,
      playerVars,
      events: {
        onReady: () => {
          this.player?.setPlaybackRate(this.currentRate());
          const dur = this.player?.getDuration() ?? 0;
          this.videoDuration.set(Math.floor(dur));
          this.repeatStart = this.startTime ?? 0;
          this.repeatEnd = this.endTime ?? Math.floor(dur);
        }
      }
    });
  }

  private clearRepeat(): void {
    if (this.repeatInterval) {
      clearInterval(this.repeatInterval);
      this.repeatInterval = null;
    }
  }
}
