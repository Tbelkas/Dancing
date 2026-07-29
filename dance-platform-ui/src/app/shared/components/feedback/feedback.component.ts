import { Component, ElementRef, HostListener, ViewChild, effect } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';
import { NavigationStart, Router } from '@angular/router';
import { filter } from 'rxjs/operators';
import { ToastService } from '../../../core/services/toast.service';
import { ConfirmService } from '../../../core/services/confirm.service';

/** Shell-level overlay: the toast stack and the styled confirm dialog. */
@Component({
  selector: 'app-feedback',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './feedback.component.html',
  styleUrls: ['./feedback.component.css']
})
export class FeedbackComponent {
  @ViewChild('cancelBtn') cancelBtn?: ElementRef<HTMLButtonElement>;

  constructor(public toast: ToastService, public confirmSvc: ConfirmService, router: Router) {
    // Focus lands on the safe option whenever a confirm opens.
    effect(() => {
      if (this.confirmSvc.pending()) {
        setTimeout(() => this.cancelBtn?.nativeElement.focus());
      }
    });

    // An undo window belongs to the screen it was opened on. Leaving forfeits it, so the
    // deferred delete fires now — otherwise the page it came from is gone and the item
    // would quietly reappear on the next load.
    router.events.pipe(filter(e => e instanceof NavigationStart), takeUntilDestroyed())
      .subscribe(() => this.toast.flush());
  }

  // Best effort on tab close. If the request doesn't survive the unload the delete simply
  // didn't happen, which is the safe way for this to fail.
  @HostListener('window:pagehide')
  onPageHide(): void {
    this.toast.flush();
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.confirmSvc.pending()) this.confirmSvc.answer(false);
  }
}
