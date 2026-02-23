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
  @ViewChild('playerContainer', { static: true }) playerContainer!: ElementRef;

  readonly playbackRates = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 2];
  currentRate = signal(1);
  repeating = signal(false);

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
    this.player = new window.YT.Player(this.playerContainer.nativeElement, {
      videoId: this.youTubeId,
      playerVars: { rel: 0, modestbranding: 1 },
      events: { onReady: () => this.player?.setPlaybackRate(this.currentRate()) }
    });
  }

  private clearRepeat(): void {
    if (this.repeatInterval) {
      clearInterval(this.repeatInterval);
      this.repeatInterval = null;
    }
  }
}
