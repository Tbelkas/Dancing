import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css']
})
export class LoginComponent {
  username = '';
  password = '';
  name = '';
  nickname = '';
  isRegister = signal(false);
  loading = signal(false);
  error = signal('');

  constructor(private auth: AuthService, private router: Router) {}

  toggleMode(): void {
    this.isRegister.update(v => !v);
    this.error.set('');
  }

  submit(): void {
    this.loading.set(true);
    this.error.set('');

    const obs = this.isRegister()
      ? this.auth.register({ username: this.username, password: this.password, name: this.name, nickname: this.nickname })
      : this.auth.login(this.username, this.password);

    obs.subscribe({
      next: () => this.router.navigate(['/dances']),
      error: (err) => {
        this.error.set(err.error?.message ?? 'An error occurred. Please try again.');
        this.loading.set(false);
      }
    });
  }
}
