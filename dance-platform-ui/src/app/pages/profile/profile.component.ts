import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import { ProfileService } from '../../core/services/profile.service';
import { PracticeService } from '../../core/services/practice.service';
import { UserProfile } from '../../models/user.model';
import { PracticeSession } from '../../models/practice-session.model';

function toLocalDateString(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './profile.component.html',
  styleUrls: ['./profile.component.css']
})
export class ProfileComponent implements OnInit {
  profile = signal<UserProfile | null>(null);
  sessions = signal<PracticeSession[]>([]);
  editing = signal(false);
  editName = '';
  editNickname = '';
  editAvatarUrl = '';
  editVisibility: 'Public' | 'Private' = 'Private';

  readonly streak = computed(() => {
    const s = this.sessions();
    if (s.length === 0) return 0;
    const dates = [...new Set(s.map(x => x.date))].sort().reverse();
    const today = toLocalDateString(new Date());
    const yesterday = toLocalDateString(new Date(Date.now() - 86400000));
    if (dates[0] !== today && dates[0] !== yesterday) return 0;
    let streak = 0;
    let current = new Date(dates[0]);
    for (const d of dates) {
      const diff = Math.round((current.getTime() - new Date(d).getTime()) / 86400000);
      if (diff > 1) break;
      streak++;
      current = new Date(d);
    }
    return streak;
  });

  readonly totalSessions = computed(() => this.sessions().length);

  readonly totalMinutes = computed(() =>
    this.sessions().reduce((sum, s) => sum + (s.durationMinutes ?? 0), 0)
  );

  constructor(
    private profileService: ProfileService,
    private practiceService: PracticeService
  ) {}

  ngOnInit(): void {
    forkJoin({
      profile: this.profileService.getProfile(),
      sessions: this.practiceService.getAll()
    }).subscribe(({ profile, sessions }) => {
      this.profile.set(profile);
      this.sessions.set(sessions);
    });
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
