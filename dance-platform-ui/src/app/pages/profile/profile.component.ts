import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { DancePathPipe } from '../../shared/pipes/dance-path.pipe';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { ProfileService } from '../../core/services/profile.service';
import { PracticeService } from '../../core/services/practice.service';
import { AuthService } from '../../core/services/auth.service';
import { UserProfile } from '../../models/user.model';
import { PracticeSession } from '../../models/practice-session.model';
import { computeStreak } from '../../core/utils/practice.utils';
import { delayedLoading } from '../../core/utils/delayed-loading';

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
  loadError = signal(false);
  // No explicit loading flag here either — "neither loaded nor failed yet" is the wait.
  private readonly loading = computed(() => !this.profile() && !this.loadError());
  showSkeleton = delayedLoading(this.loading);
  editing = signal(false);
  savingViewerPref = signal(false);
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
    private practiceService: PracticeService,
    private auth: AuthService
  ) {}

  signOut(): void {
    this.auth.logout();
  }

  ngOnInit(): void {
    forkJoin({
      profile: this.profileService.getProfile(),
      // Practice history is secondary — if it fails, still show the profile with an empty streak
      // rather than letting one failed call leave the whole page stuck on the loading skeleton.
      sessions: this.practiceService.getAll().pipe(catchError(() => of([] as PracticeSession[])))
    }).subscribe({
      next: ({ profile, sessions }) => {
        this.profile.set(profile);
        // Ignore sub-minute blips so streak/totals match the Practice Log page.
        this.sessions.set(sessions.filter(s => s.totalSeconds > 60));
      },
      error: () => this.loadError.set(true)
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

  /** Saved on click rather than through the edit form — it's a player preference, not identity. */
  setBetaViewer(value: boolean): void {
    const p = this.profile();
    if (!p || p.useBetaViewer === value || this.savingViewerPref()) return;
    this.savingViewerPref.set(true);
    this.profileService.updateProfile({ useBetaViewer: value }).subscribe({
      next: updated => {
        this.profile.set(updated);
        this.savingViewerPref.set(false);
      },
      error: () => this.savingViewerPref.set(false)
    });
  }
}
