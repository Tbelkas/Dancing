import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { AdminService } from '../../core/services/admin.service';
import { CatalogHealth, HealthCheck } from '../../models/catalog-health.model';

/**
 * The admin home: what needs attention, and the way in to every other admin surface.
 *
 * The checks below all existed already, as scripts somebody had to remember to run
 * (audit_labels, chip_health, verify_intake, backfill_durations). Nothing here is new knowledge —
 * what's new is that it's standing in front of you, ordered worst-first, with each finding
 * linking to the page where it gets fixed.
 */
@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './admin-dashboard.component.html',
  styleUrls: ['./admin-dashboard.component.css']
})
export class AdminDashboardComponent implements OnInit {
  health = signal<CatalogHealth | null>(null);
  loading = signal(true);
  loadError = signal(false);

  /** Which check is expanded. One at a time — the samples run to 25 rows each. */
  openCheck = signal<string | null>(null);

  constructor(private admin: AdminService) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.admin.getHealth().subscribe({
      next: health => { this.health.set(health); this.loading.set(false); this.loadError.set(false); },
      error: () => { this.loading.set(false); this.loadError.set(true); }
    });
  }

  toggle(check: HealthCheck): void {
    this.openCheck.set(this.openCheck() === check.key ? null : check.key);
  }

  /** Findings worth acting on. A check at zero is the good outcome and needs no row. */
  problems(): HealthCheck[] {
    return this.health()?.checks.filter(c => c.count > 0) ?? [];
  }

  /** Checks currently at zero, listed by name only — proof they ran, not a wall of green cards. */
  clean(): HealthCheck[] {
    return this.health()?.checks.filter(c => c.count === 0) ?? [];
  }
}
