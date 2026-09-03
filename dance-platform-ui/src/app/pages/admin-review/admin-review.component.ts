import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { DanceService } from '../../core/services/dance.service';
import { Dance } from '../../models/dance.model';
import { DancePathPipe } from '../../shared/pipes/dance-path.pipe';

/**
 * The review queue. POST /dances is open to any signed-in user, so their submissions land as
 * "pending" — visible to the person who added them and to nobody else — and wait here. Without
 * this page that queue would be invisible and nothing would ever leave it.
 */
@Component({
  selector: 'app-admin-review',
  standalone: true,
  imports: [CommonModule, RouterLink, DancePathPipe],
  templateUrl: './admin-review.component.html',
  styleUrls: ['./admin-review.component.css']
})
export class AdminReviewComponent implements OnInit {
  pending = signal<Dance[]>([]);
  loading = signal(true);
  loadError = signal(false);
  busyId = signal<number | null>(null);
  message = signal('');

  constructor(private danceService: DanceService) {}

  ngOnInit(): void {
    this.load();
  }

  private load(): void {
    this.loading.set(true);
    this.danceService.pending().subscribe({
      next: list => { this.pending.set(list); this.loading.set(false); this.loadError.set(false); },
      error: () => { this.loading.set(false); this.loadError.set(true); }
    });
  }

  approve(dance: Dance): void {
    this.busyId.set(dance.id);
    this.danceService.review(dance.id, 'approved').subscribe({
      next: () => {
        this.pending.update(list => list.filter(d => d.id !== dance.id));
        this.busyId.set(null);
        this.message.set(`"${dance.name}" is now in the catalogue.`);
      },
      error: () => { this.busyId.set(null); this.message.set('Could not approve that one.'); }
    });
  }

  reject(dance: Dance): void {
    // Deletion, not a state change: a rejected submission has no reason to stay in the table,
    // and the confirm is here because it takes the dance's videos with it.
    if (!confirm(`Delete "${dance.name}" and everything attached to it?`)) return;
    this.busyId.set(dance.id);
    this.danceService.delete(dance.id).subscribe({
      next: () => {
        this.pending.update(list => list.filter(d => d.id !== dance.id));
        this.busyId.set(null);
        this.message.set(`"${dance.name}" deleted.`);
      },
      error: () => { this.busyId.set(null); this.message.set('Could not delete that one.'); }
    });
  }
}
