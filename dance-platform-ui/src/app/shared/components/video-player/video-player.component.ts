import { Component, Input, OnInit, OnDestroy, ElementRef, ViewChild, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

declare global {
  interface Window { YT: typeof YT; onYouTubeIframeAPIReady: () => void; }
}

@Component({
  selector: 'app-video-player',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="player-wrapper">
      <div #playerContainer class="yt-player"></div>

      <div class="controls">
        <div class="control-row">
          <label>Speed</label>
          <div class="speed-buttons">
            @for (rate of playbackRates; track rate) {
              <button class="speed-btn" [class.active]="currentRate() === rate" (click)="setRate(rate)">{{ rate }}x</button>
            }
          </div>
        </div>

        <div class="control-row">
          <label>Repeat Region (seconds)</label>
          <div class="repeat-inputs">
            <input type="number" [(ngModel)]="repeatStart" min="0" placeholder="Start" class="time-input" />
            <span>to</span>
            <input type="number" [(ngModel)]="repeatEnd" min="0" placeholder="End" class="time-input" />
            <button class="btn btn--accent btn--sm" (click)="toggleRepeat()">{{ repeating() ? 'Stop Repeat' : 'Repeat Region' }}</button>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .player-wrapper { background: var(--color-surface); border-radius: var(--radius-lg); overflow: hidden; }
    .yt-player { width: 100%; aspect-ratio: 16/9; }
    .controls { padding: 16px; display: flex; flex-direction: column; gap: 12px; }
    .control-row { display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
      label { font-size: 0.8rem; font-weight: 600; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.05em; width: 80px; flex-shrink: 0; }
    }
    .speed-buttons { display: flex; gap: 6px; flex-wrap: wrap; }
    .speed-btn {
      background: var(--color-surface-2); border: none; border-radius: 4px;
      color: var(--color-text); font-size: 0.8rem; font-weight: 600;
      padding: 4px 10px; cursor: pointer; transition: all var(--transition);
      &:hover { background: var(--color-primary); color: #fff; }
      &.active { background: var(--color-primary); color: #fff; }
    }
    .repeat-inputs { display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
      span { color: var(--color-text-muted); font-size: 0.9rem; }
    }
    .time-input {
      width: 70px; background: var(--color-surface-2); border: 1px solid transparent;
      border-radius: 4px; color: var(--color-text); font-size: 0.9rem; padding: 4px 8px;
      outline: none; transition: border-color var(--transition);
      &:focus { border-color: var(--color-primary); }
    }
    .btn--sm { padding: 6px 12px; font-size: 0.8rem; }
  `]
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
        window.onYouTubeIframeAPIReady = () => this.createPlayer();
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
