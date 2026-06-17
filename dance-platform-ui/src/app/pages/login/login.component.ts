import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink, ActivatedRoute } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css']
})
export class LoginComponent implements OnInit {
  username = '';
  password = '';
  name = '';
  nickname = '';
  isRegister = signal(false);
  loading = signal(false);
  error = signal('');

  constructor(private auth: AuthService, private router: Router, private route: ActivatedRoute) {}

  ngOnInit(): void {
    if (this.route.snapshot.url[0]?.path === 'register') {
      this.isRegister.set(true);
    }
  }

  toggleMode(): void {
    this.isRegister.update(v => !v);
    this.error.set('');
  }

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
      next: () => this.router.navigate(['/dances']),
      error: (err) => {
        this.error.set(err.error?.message ?? 'An error occurred. Please try again.');
        this.loading.set(false);
      }
    });
  }
}
