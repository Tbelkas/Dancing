import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { DancePathPipe } from '../../shared/pipes/dance-path.pipe';
import { forkJoin } from 'rxjs';
import { ProfileService } from '../../core/services/profile.service';
import { PracticeService } from '../../core/services/practice.service';
import { UserProfile } from '../../models/user.model';
import { PracticeSession } from '../../models/practice-session.model';
import { computeStreak } from '../../core/utils/practice.utils';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, DancePathPipe],
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

  readonly streak = computed(() => computeStreak(this.sessions()));

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
