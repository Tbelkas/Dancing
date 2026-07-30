import { AfterViewInit, Component, ElementRef, EventEmitter, Input, Output, ViewChild, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../../core/services/auth.service';

/**
 * The /login form as a dialog, for pages that are readable signed out but need an account
 * before anything can be *done* with them (the roadmap tree being the first).
 *
 * It signs in in place and emits `signedIn` — deliberately not a redirect to /login. Sending a
 * visitor away from the path they were reading to a page that then dumps them on /my-dances
 * loses the thing they clicked; here the page just reloads itself with their progress on it.
 *
 * Register lives in the same dialog for the same reason: most people who hit this wall don't
 * have an account yet, and bouncing them out to /register would lose the path too.
 */
@Component({
  selector: 'app-sign-in-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './sign-in-dialog.component.html',
  styleUrls: ['./sign-in-dialog.component.css']
})
export class SignInDialogComponent implements AfterViewInit {
  /** Why the dialog opened — say what signing in unlocks, not just "Sign in". */
  @Input() heading = 'Sign in to follow this path';
  @Input() message = 'Tick moves off as you learn them and the tree unlocks as you go.';

  /** Closed without signing in (Escape, backdrop, the X). */
  @Output() dismissed = new EventEmitter<void>();
  /** Signed in or registered successfully; the token is already stored. */
  @Output() signedIn = new EventEmitter<void>();

  @ViewChild('firstField') firstField?: ElementRef<HTMLInputElement>;

  username = '';
  password = '';
  name = '';
  nickname = '';

  isRegister = signal(false);
  loading = signal(false);
  error = signal('');

  constructor(private auth: AuthService) {}

  ngAfterViewInit(): void {
    // The dialog opens in response to a click on something else, so focus has to be moved
    // explicitly or a keyboard user is left tabbing through the page behind it.
    this.firstField?.nativeElement.focus();
  }

  toggleMode(): void {
    this.isRegister.update(v => !v);
    this.error.set('');
  }

  /** Escape and backdrop clicks close; a click inside the card must not. */
  onBackdropClick(event: MouseEvent): void {
    if (event.target === event.currentTarget) this.dismiss();
  }

  dismiss(): void {
    if (this.loading()) return;
    this.dismissed.emit();
  }

  // Validation mirrors LoginComponent.submit — the two forms must not disagree about what
  // the API will accept, or one of them fails server-side where the other caught it.
  submit(): void {
    if (this.isRegister()) {
      if (!this.username || this.username.length < 3) {
        this.error.set('Username must be at least 3 characters.');
        return;
      }
      if (!this.password || this.password.length < 8) {
        this.error.set('Password must be at least 8 characters.');
        return;
      }
      if (!this.name) {
        this.error.set('Full name is required.');
        return;
      }
    } else if (!this.username.trim() || !this.password) {
      this.error.set('Please enter your username and password.');
      return;
    }

    this.loading.set(true);
    this.error.set('');

    const obs = this.isRegister()
      ? this.auth.register({ username: this.username, password: this.password, name: this.name, nickname: this.nickname })
      : this.auth.login(this.username, this.password);

    obs.subscribe({
      next: () => {
        this.loading.set(false);
        this.signedIn.emit();
      },
      error: err => {
        this.error.set(err.error?.message ?? 'An error occurred. Please try again.');
        this.loading.set(false);
      }
    });
  }
}
