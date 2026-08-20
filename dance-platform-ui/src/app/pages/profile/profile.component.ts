import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { DancePathPipe } from '../../shared/pipes/dance-path.pipe';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { ProfileService } from '../../core/services/profile.service';
import { PracticeService } from '../../core/services/practice.service';
import { AuthService } from '../../core/services/auth.service';
import { UserProfile } from '../../models/user.model';
import { ExternalProvider, LinkedAccounts } from '../../models/external-auth.model';
import { PracticeSession } from '../../models/practice-session.model';
import { meaningfulSessions, practiceStreak } from '../../core/utils/practice.utils';
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

  readonly streak = computed(() => practiceStreak(this.sessions()).current);

  readonly totalSessions = computed(() => this.sessions().length);

  readonly totalMinutes = computed(() =>
    this.sessions().reduce((sum, s) => sum + (s.durationMinutes ?? 0), 0)
  );

  linked = signal<LinkedAccounts | null>(null);
  providers = signal<ExternalProvider[]>([]);
  busyProvider = signal('');
  linkMessage = signal('');
  linkFailed = signal(false);

  /** Providers with credentials that this account hasn't connected yet. */
  readonly unlinkedProviders = computed(() => {
    const connected = new Set(this.linked()?.accounts.map(a => a.provider) ?? []);
    return this.providers().filter(p => !connected.has(p.name));
  });

  /**
   * Nothing connected and nothing left to connect means the card is a heading over an empty
   * box. That's the normal state whenever the deployment has no provider credentials
   * configured — not an edge case — so the whole section stays out of the page.
   */
  readonly showConnectedAccounts = computed(
    () => (this.linked()?.accounts.length ?? 0) > 0 || this.unlinkedProviders().length > 0
  );

  constructor(
    private profileService: ProfileService,
    private practiceService: PracticeService,
    private auth: AuthService,
    private route: ActivatedRoute
  ) {}

  /** False when a single social login is the account's only way in — disconnecting it would
   *  strand the user, so the button isn't offered. The server enforces this too; this just
   *  avoids presenting an action that can only fail. */
  readonly canUnlink = computed(() => {
    const links = this.linked();
    return !!links && (links.hasPassword || links.accounts.length > 1);
  });

  link(provider: string): void {
    this.busyProvider.set(provider);
    this.auth.startLink(provider).subscribe({
      next: ({ url }) => { window.location.href = url; },
      error: () => {
        this.busyProvider.set('');
        this.linkFailed.set(true);
        this.linkMessage.set('Could not start that connection. Please try again.');
      }
    });
  }

  unlink(provider: string): void {
    this.busyProvider.set(provider);
    this.auth.unlinkAccount(provider).subscribe({
      next: () => {
        this.busyProvider.set('');
        this.linkFailed.set(false);
        this.linkMessage.set('Disconnected.');
        this.loadLinkedAccounts();
      },
      error: err => {
        this.busyProvider.set('');
        this.linkFailed.set(true);
        this.linkMessage.set(err.error?.message ?? 'Could not disconnect that account.');
      }
    });
  }

  private loadLinkedAccounts(): void {
    this.auth.linkedAccounts().subscribe({
      next: links => this.linked.set(links),
      error: () => this.linked.set(null)
    });
  }

  signOut(): void {
    this.auth.logout();
  }

  ngOnInit(): void {
    // The link flow leaves the app entirely and comes back here via the provider's callback,
    // so the outcome arrives as a query param rather than an HTTP response.
    const params = this.route.snapshot.queryParamMap;
    if (params.get('linked')) {
      this.linkFailed.set(false);
      this.linkMessage.set('Account connected.');
    } else if (params.get('linkError')) {
      this.linkFailed.set(true);
      this.linkMessage.set('That account is already connected to a different Dance Platform user.');
    }

    this.loadLinkedAccounts();
    this.auth.externalProviders().subscribe({
      next: list => this.providers.set(list),
      error: () => this.providers.set([])
    });

    forkJoin({
      profile: this.profileService.getProfile(),
      // Practice history is secondary — if it fails, still show the profile with an empty streak
      // rather than letting one failed call leave the whole page stuck on the loading skeleton.
      sessions: this.practiceService.getAll().pipe(catchError(() => of([] as PracticeSession[])))
    }).subscribe({
      next: ({ profile, sessions }) => {
        this.profile.set(profile);
        // Ignore sub-minute blips so streak/totals match the Practice Log page.
        this.sessions.set(meaningfulSessions(sessions));
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
