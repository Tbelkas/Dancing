import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ProfileService } from '../../core/services/profile.service';
import { UserProfile } from '../../models/user.model';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './profile.component.html',
  styleUrls: ['./profile.component.css']
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
