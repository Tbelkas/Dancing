import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { DanceService } from '../../core/services/dance.service';
import { StyleService } from '../../core/services/style.service';
import { AuthService } from '../../core/services/auth.service';
import { Dance } from '../../models/dance.model';
import { Style } from '../../models/style.model';

@Component({
  selector: 'app-dances',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="container">
      <div class="page-header">
        <h1 class="page-title">Explore Dances</h1>
        <p class="page-subtitle">Discover, favorite, and track your dance journey</p>
      </div>

      <div class="filters">
        <input type="text" [(ngModel)]="searchQuery" (input)="onSearch()" class="search-input" placeholder="Search dances..." />
        <div class="style-filters">
          <button class="btn" [class.btn--primary]="selectedStyleId() === null" [class.btn--ghost]="selectedStyleId() !== null" (click)="filterByStyle(null)">All</button>
          @for (style of styles(); track style.id) {
            <button class="btn" [class.btn--primary]="selectedStyleId() === style.id" [class.btn--ghost]="selectedStyleId() !== style.id" (click)="filterByStyle(style.id)">
              {{ style.name }}
            </button>
          }
        </div>
      </div>

      @if (loading()) {
        <div class="loading">Loading dances...</div>
      } @else if (dances().length === 0) {
        <div class="empty">No dances found.</div>
      } @else {
        <div class="grid grid--2">
          @for (dance of dances(); track dance.id) {
            <div class="card dance-card">
              <div class="dance-card__header">
                <h3 class="dance-card__name">{{ dance.name }}</h3>
                @if (auth.isAuthenticated()) {
                  <div class="dance-card__actions">
                    <button class="icon-btn" [class.active]="dance.isFavorite" (click)="toggleFavorite(dance, $event)" title="Favorite">
                      {{ dance.isFavorite ? '\u2605' : '\u2606' }}
                    </button>
                    <button class="icon-btn" [class.active]="dance.isLearned" (click)="toggleLearned(dance, $event)" title="Mark as learned">
                      {{ dance.isLearned ? '\u2713' : '\u25CB' }}
                    </button>
                  </div>
                }
              </div>
              @if (dance.description) {
                <p class="dance-card__desc">{{ dance.description }}</p>
              }
              <div class="dance-card__meta">
                <div class="dance-card__styles">
                  @for (style of dance.styles; track style) {
                    <span class="badge">{{ style }}</span>
                  }
                </div>
                <span class="video-count">{{ dance.videoCount }} video{{ dance.videoCount !== 1 ? 's' : '' }}</span>
              </div>
              <a [routerLink]="['/dances', dance.id]" class="btn btn--ghost btn--sm">View details</a>
            </div>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    .page-header { margin-bottom: 32px; }
    .page-subtitle { color: var(--color-text-muted); }
    .filters { margin-bottom: 32px; display: flex; flex-direction: column; gap: 16px; }
    .search-input {
      background: var(--color-surface);
      border: 1px solid var(--color-surface-2);
      border-radius: var(--radius);
      color: var(--color-text);
      font-size: 1rem;
      padding: 12px 16px;
      outline: none;
      width: 100%;
      max-width: 400px;
      transition: border-color var(--transition);
      &:focus { border-color: var(--color-primary); }
    }
    .style-filters { display: flex; flex-wrap: wrap; gap: 8px; }
    .btn--sm { padding: 6px 14px; font-size: 0.85rem; margin-top: 12px; }
    .dance-card__header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
    .dance-card__name { font-size: 1.15rem; font-weight: 700; }
    .dance-card__desc { color: var(--color-text-muted); font-size: 0.9rem; margin-bottom: 12px; }
    .dance-card__meta { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
    .dance-card__styles { display: flex; flex-wrap: wrap; gap: 6px; }
    .dance-card__actions { display: flex; gap: 8px; }
    .video-count { font-size: 0.8rem; color: var(--color-text-muted); }
    .icon-btn {
      background: none; border: none; cursor: pointer;
      font-size: 1.2rem; color: var(--color-text-muted);
      transition: color var(--transition), transform var(--transition);
      &:hover, &.active { color: var(--color-accent); }
      &.active { transform: scale(1.1); }
    }
    .loading, .empty { text-align: center; padding: 60px; color: var(--color-text-muted); font-size: 1.1rem; }
  `]
})
export class DancesComponent implements OnInit {
  dances = signal<Dance[]>([]);
  styles = signal<Style[]>([]);
  loading = signal(true);
  selectedStyleId = signal<number | null>(null);
  searchQuery = '';

  constructor(
    private danceService: DanceService,
    private styleService: StyleService,
    public auth: AuthService
  ) {}

  ngOnInit(): void {
    this.styleService.getAll().subscribe(s => this.styles.set(s));
    this.loadDances();
  }

  loadDances(): void {
    this.loading.set(true);
    this.danceService.getAll().subscribe({
      next: d => { this.dances.set(d); this.loading.set(false); },
      error: () => this.loading.set(false)
    });
  }

  onSearch(): void {
    this.loading.set(true);
    this.danceService.search(this.searchQuery, this.selectedStyleId() ?? undefined).subscribe({
      next: d => { this.dances.set(d); this.loading.set(false); },
      error: () => this.loading.set(false)
    });
  }

  filterByStyle(styleId: number | null): void {
    this.selectedStyleId.set(styleId);
    this.onSearch();
  }

  toggleFavorite(dance: Dance, event: Event): void {
    event.stopPropagation();
    event.preventDefault();
    this.danceService.toggleFavorite(dance.id).subscribe(res => {
      this.dances.update(list =>
        list.map(d => d.id === dance.id ? { ...d, isFavorite: res.isFavorite } : d)
      );
    });
  }

  toggleLearned(dance: Dance, event: Event): void {
    event.stopPropagation();
    event.preventDefault();
    this.danceService.toggleLearned(dance.id).subscribe(res => {
      this.dances.update(list =>
        list.map(d => d.id === dance.id ? { ...d, isLearned: res.isLearned } : d)
      );
    });
  }
}
