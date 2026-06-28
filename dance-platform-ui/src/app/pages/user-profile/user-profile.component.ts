import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { EMPTY } from 'rxjs';
import { switchMap, catchError } from 'rxjs/operators';
import { DancePathPipe } from '../../shared/pipes/dance-path.pipe';
import { UserService, PublicProfile } from '../../core/services/user.service';

@Component({
  selector: 'app-user-profile',
  standalone: true,
  imports: [CommonModule, RouterLink, DancePathPipe],
  templateUrl: './user-profile.component.html'
})
export class UserProfileComponent implements OnInit {
  profile = signal<PublicProfile | null>(null);
  notFound = signal(false);
  loading = signal(true);

  constructor(private route: ActivatedRoute, private userService: UserService) {}

  ngOnInit(): void {
    // Subscribe to paramMap (not snapshot) so navigating directly between two /users/:username
    // pages — where Angular reuses this component instance — reloads the new profile.
    this.route.paramMap.pipe(
      switchMap(pm => {
        this.profile.set(null);
        this.notFound.set(false);
        this.loading.set(true);
        return this.userService.getPublicProfile(pm.get('username') ?? '').pipe(
          // Catch here (not in subscribe) so a 404 doesn't kill the stream and block later reloads.
          catchError(() => { this.notFound.set(true); this.loading.set(false); return EMPTY; })
        );
      })
    ).subscribe(p => { this.profile.set(p); this.loading.set(false); });
  }
}
