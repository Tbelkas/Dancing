import { Component, ElementRef, HostListener, ViewChild, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
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

  constructor(public toast: ToastService, public confirmSvc: ConfirmService) {
    // Focus lands on the safe option whenever a confirm opens.
    effect(() => {
      if (this.confirmSvc.pending()) {
        setTimeout(() => this.cancelBtn?.nativeElement.focus());
      }
    });
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.confirmSvc.pending()) this.confirmSvc.answer(false);
  }
}
