import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ProfileService } from '../../core/services/profile.service';
import { UserProfile } from '../../models/user.model';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="container">
      <h1 class="page-title">My Profile</h1>

      @if (profile()) {
        <div class="profile-layout">
          <div class="card profile-card">
            <div class="avatar-section">
              @if (profile()!.avatarUrl) {
                <img [src]="profile()!.avatarUrl" alt="Avatar" class="avatar" />
              } @else {
                <div class="avatar-placeholder">{{ profile()!.name.charAt(0).toUpperCase() }}</div>
              }
              <div>
                <h2>{{ profile()!.name }}</h2>
                @if (profile()!.nickname) {
                  <p class="nickname">{{ profile()!.nickname }}</p>
                }
                <p class="username">&#64;{{ profile()!.username }}</p>
              </div>
            </div>

            @if (editing()) {
              <form (ngSubmit)="saveProfile()" class="edit-form">
                <div class="form-group">
                  <label>Full Name</label>
                  <input type="text" [(ngModel)]="editName" name="name" />
                </div>
                <div class="form-group">
                  <label>Nickname</label>
                  <input type="text" [(ngModel)]="editNickname" name="nickname" />
                </div>
                <div class="form-group">
                  <label>Avatar URL</label>
                  <input type="url" [(ngModel)]="editAvatarUrl" name="avatarUrl" placeholder="https://..." />
                </div>
                <div class="form-group">
                  <label>Visibility</label>
                  <select [(ngModel)]="editVisibility" name="visibility">
                    <option value="Public">Public</option>
                    <option value="Private">Private</option>
                  </select>
                </div>
                <div class="form-actions">
                  <button type="submit" class="btn btn--primary">Save</button>
                  <button type="button" class="btn btn--ghost" (click)="editing.set(false)">Cancel</button>
                </div>
              </form>
            } @else {
              <div class="profile-info">
                <span class="badge">{{ profile()!.visibility }}</span>
              </div>
              <button class="btn btn--ghost" (click)="startEdit()">Edit Profile</button>
            }
          </div>

          <div class="stats-column">
            <div class="card">
              <h3>Favorite Dances</h3>
              @if (profile()!.favoriteDances.length === 0) {
                <p class="empty">No favorites yet.</p>
              } @else {
                <ul class="dance-list">
                  @for (d of profile()!.favoriteDances; track d) {
                    <li>{{ d }}</li>
                  }
                </ul>
              }
            </div>

            <div class="card">
              <h3>Dances Learned</h3>
              @if (profile()!.learnedDances.length === 0) {
                <p class="empty">No dances learned yet.</p>
              } @else {
                <ul class="dance-list">
                  @for (d of profile()!.learnedDances; track d) {
                    <li>{{ d }}</li>
                  }
                </ul>
              }
            </div>
          </div>
        </div>
      } @else {
        <div class="loading">Loading profile...</div>
      }
    </div>
  `,
  styles: [`
    .profile-layout { display: grid; grid-template-columns: 360px 1fr; gap: 24px; align-items: start; }
    @media (max-width: 768px) { .profile-layout { grid-template-columns: 1fr; } }
    .avatar-section { display: flex; align-items: center; gap: 16px; margin-bottom: 20px; }
    .avatar { width: 72px; height: 72px; border-radius: 50%; object-fit: cover; border: 3px solid var(--color-primary); }
    .avatar-placeholder {
      width: 72px; height: 72px; border-radius: 50%;
      background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
      display: flex; align-items: center; justify-content: center;
      font-size: 1.8rem; font-weight: 800; color: #fff; flex-shrink: 0;
    }
    h2 { font-size: 1.3rem; font-weight: 700; }
    .nickname { color: var(--color-accent); font-size: 0.9rem; }
    .username { color: var(--color-text-muted); font-size: 0.85rem; }
    .profile-info { margin: 12px 0; }
    .edit-form { margin-top: 16px; }
    .form-actions { display: flex; gap: 12px; }
    .stats-column { display: flex; flex-direction: column; gap: 20px; }
    .stats-column .card h3 { font-size: 1rem; font-weight: 700; margin-bottom: 12px; }
    .dance-list { list-style: none; display: flex; flex-direction: column; gap: 6px;
      li { color: var(--color-text-muted); font-size: 0.9rem; padding: 6px 0; border-bottom: 1px solid var(--color-surface-2);
        &:last-child { border-bottom: none; }
      }
    }
    .empty { color: var(--color-text-muted); font-size: 0.9rem; }
    .loading { padding: 60px; text-align: center; color: var(--color-text-muted); }
  `]
})
export class ProfileComponent implements OnInit {
  profile = signal<UserProfile | null>(null);
  editing = signal(false);
  editName = '';
  editNickname = '';
  editAvatarUrl = '';
  editVisibility: 'Public' | 'Private' = 'Public';

  constructor(private profileService: ProfileService) {}

  ngOnInit(): void {
    this.profileService.getProfile().subscribe(p => this.profile.set(p));
  }

  startEdit(): void {
    const p = this.profile();
    if (!p) return;
    this.editName = p.name;
    this.editNickname = p.nickname;
    this.editAvatarUrl = p.avatarUrl ?? '';
    this.editVisibility = p.visibility;
    this.editing.set(true);
  }

  saveProfile(): void {
    this.profileService.updateProfile({
      name: this.editName,
      nickname: this.editNickname,
      avatarUrl: this.editAvatarUrl || undefined,
      visibility: this.editVisibility
    }).subscribe(p => {
      this.profile.set(p);
      this.editing.set(false);
    });
  }
}
