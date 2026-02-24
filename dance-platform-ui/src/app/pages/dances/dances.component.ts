import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { DanceService } from '../../core/services/dance.service';
import { StyleService } from '../../core/services/style.service';
import { MusicalStyleService } from '../../core/services/musical-style.service';
import { AuthService } from '../../core/services/auth.service';
import { Dance } from '../../models/dance.model';
import { Style } from '../../models/style.model';
import { MusicalStyle } from '../../models/musical-style.model';

@Component({
  selector: 'app-dances',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './dances.component.html',
  styleUrls: ['./dances.component.css']
})
export class DancesComponent implements OnInit {
  dances = signal<Dance[]>([]);
  styles = signal<Style[]>([]);
  musicalStyles = signal<MusicalStyle[]>([]);
  loading = signal(true);
  selectedStyleId = signal<number | null>(null);
  searchQuery = '';

  constructor(
    private danceService: DanceService,
    private styleService: StyleService,
    private musicalStyleService: MusicalStyleService,
    public auth: AuthService
  ) {}

  ngOnInit(): void {
    this.styleService.getAll().subscribe(s => this.styles.set(s));
    this.musicalStyleService.getAll().subscribe(ms => this.musicalStyles.set(ms));
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
