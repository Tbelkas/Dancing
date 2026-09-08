import { Component, Input, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { VideoService } from '../../../core/services/video.service';
import { ToastService } from '../../../core/services/toast.service';
import { REPORT_REASONS, ReportReason } from '../../../models/video-flag.model';

/**
 * "Something wrong?" on a video — the one way for anybody but an admin to say a video is broken.
 *
 * Deliberately open to anonymous viewers. A dead YouTube embed looks fine from the outside until
 * someone clicks it, and requiring a sign-in first loses most of the people who would have told
 * us. The API throttles it and collapses duplicates, which is where that risk belongs.
 *
 * Collapsed to a single quiet link until used: it sits under every video on the site and must not
 * compete with the controls people actually came for.
 */
@Component({
  selector: 'app-report-video',
  standalone: true,
  imports: [FormsModule],
  template: `
    @if (!open() && !sent()) {
      <button type="button" class="report__trigger" data-testid="report-video-open" (click)="open.set(true)">
        <i class="fa-solid fa-flag"></i> Something wrong?
      </button>
    }

    @if (sent()) {
      <p class="report__thanks" data-testid="report-video-thanks">Thanks — it's on the list.</p>
    }

    @if (open()) {
      <div class="report card">
        <p class="report__title">What's wrong with this video?</p>
        <div class="report__reasons">
          @for (option of reasons; track option.value) {
            <label class="report__reason" [class.is-picked]="reason === option.value">
              <input type="radio" name="report-reason-{{ videoId }}" [value]="option.value" [(ngModel)]="reason" />
              {{ option.label }}
            </label>
          }
        </div>
        <input type="text" class="report__detail" [(ngModel)]="detail" maxlength="500"
               placeholder="Anything else worth knowing (optional)" data-testid="report-video-detail" />
        <div class="report__actions">
          <button type="button" class="btn btn--primary btn--sm" data-testid="report-video-send"
                  [disabled]="!reason || sending()" (click)="submit()">
            {{ sending() ? 'Sending…' : 'Send' }}
          </button>
          <button type="button" class="btn btn--ghost btn--sm" (click)="cancel()">Cancel</button>
        </div>
      </div>
    }
  `,
  styles: [`
    .report__trigger {
      background: none;
      border: none;
      padding: 0;
      cursor: pointer;
      font-family: var(--font-ui);
      font-size: 0.72rem;
      font-weight: 600;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      color: var(--color-text-muted);
    }
    .report__trigger:hover { color: var(--color-primary); }

    .report__thanks {
      font-family: var(--font-ui);
      font-size: 0.72rem;
      font-weight: 600;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      color: var(--color-primary);
    }

    .report { padding: 16px; margin-top: 8px; animation: slideDown 0.18s ease both; }

    .report__title {
      font-family: var(--font-ui);
      font-size: 0.76rem;
      font-weight: 700;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      margin-bottom: 10px;
    }

    .report__reasons {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 12px;
    }

    .report__reason {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 5px 10px;
      border: 1px solid var(--color-border);
      border-radius: 999px;
      cursor: pointer;
      font-size: 0.85rem;
    }
    .report__reason.is-picked { border-color: var(--color-primary); color: var(--color-primary); }

    .report__detail { width: 100%; max-width: 460px; }

    .report__actions { display: flex; gap: 8px; margin-top: 12px; }
  `]
})
export class ReportVideoComponent {
  @Input({ required: true }) videoId!: number;

  readonly reasons = REPORT_REASONS;

  open = signal(false);
  sending = signal(false);
  sent = signal(false);
  reason: ReportReason | '' = '';
  detail = '';

  constructor(private videoService: VideoService, private toast: ToastService) {}

  cancel(): void {
    this.open.set(false);
    this.reason = '';
    this.detail = '';
  }

  submit(): void {
    if (!this.reason) return;
    this.sending.set(true);
    this.videoService.report(this.videoId, this.reason, this.detail.trim() || undefined).subscribe({
      // The API answers the same way for a fresh report and a duplicate — from the reporter's
      // side those are the same event, and saying "already reported" invites a second guess at
      // whether it went through.
      next: () => { this.sending.set(false); this.open.set(false); this.sent.set(true); },
      error: () => {
        this.sending.set(false);
        this.toast.error("That didn't send. Try again in a minute.");
      }
    });
  }
}
