import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { UserService, PublicProfile } from '../../core/services/user.service';

@Component({
  selector: 'app-user-profile',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './user-profile.component.html'
})
export class UserProfileComponent implements OnInit {
  profile = signal<PublicProfile | null>(null);
  notFound = signal(false);
  loading = signal(true);

  constructor(private route: ActivatedRoute, private userService: UserService) {}

  ngOnInit(): void {
    const username = this.route.snapshot.paramMap.get('username')!;
    this.userService.getPublicProfile(username).subscribe({
      next: p => { this.profile.set(p); this.loading.set(false); },
      error: () => { this.notFound.set(true); this.loading.set(false); }
    });
  }
}
