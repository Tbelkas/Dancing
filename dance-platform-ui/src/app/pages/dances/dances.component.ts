import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { DanceService, CreateDancePayload } from '../../core/services/dance.service';
import { StyleService } from '../../core/services/style.service';
import { MusicalStyleService } from '../../core/services/musical-style.service';
import { AuthService } from '../../core/services/auth.service';
import { RoleService } from '../../core/services/role.service';
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
  // Data
  allDances = signal<Dance[]>([]);
  styles = signal<Style[]>([]);
  musicalStyles = signal<MusicalStyle[]>([]);
  loading = signal(true);

  // Filters (client-side)
  searchQuery = signal('');
  selectedStyleId = signal<number | null>(null);

  readonly filteredDances = computed(() => {
    const q = this.searchQuery().trim().toLowerCase();
    const sid = this.selectedStyleId();
    const styleName = sid ? this.styles().find(s => s.id === sid)?.name ?? null : null;
    return this.allDances().filter(d =>
      (!q || d.name.toLowerCase().includes(q)) &&
      (!styleName || d.styles.includes(styleName))
    );
  });

  // Admin: add style form
  showAddStyle = signal(false);
  newStyleName = '';
  newStyleDesc = '';
  addingStyle = signal(false);
  addStyleError = signal('');

  // Admin: add dance form
  showAddDance = signal(false);
  newDanceName = '';
  newDanceDesc = '';
  newDanceStyleIds = signal<Set<number>>(new Set());
  newDanceMusicalStyleIds = signal<Set<number>>(new Set());
  addingDance = signal(false);
  addDanceError = signal('');

  constructor(
    private danceService: DanceService,
    private styleService: StyleService,
    private musicalStyleService: MusicalStyleService,
    public auth: AuthService,
    public role: RoleService
  ) {}

  ngOnInit(): void {
    this.styleService.getAll().subscribe(s => this.styles.set(s));
    this.musicalStyleService.getAll().subscribe(ms => this.musicalStyles.set(ms));
    this.loadDances();
  }

  loadDances(): void {
    this.loading.set(true);
    this.danceService.getAll().subscribe({
      next: d => { this.allDances.set(d); this.loading.set(false); },
      error: () => this.loading.set(false)
    });
  }

  onSearchInput(value: string): void {
    this.searchQuery.set(value);
  }

  filterByStyle(styleId: number | null): void {
    this.selectedStyleId.set(styleId);
  }

  toggleFavorite(dance: Dance, event: Event): void {
    event.stopPropagation();
    event.preventDefault();
    this.danceService.toggleFavorite(dance.id).subscribe(res => {
      this.allDances.update(list =>
        list.map(d => d.id === dance.id ? { ...d, isFavorite: res.isFavorite } : d)
      );
    });
  }

  toggleLearned(dance: Dance, event: Event): void {
    event.stopPropagation();
    event.preventDefault();
    this.danceService.toggleLearned(dance.id).subscribe(res => {
      this.allDances.update(list =>
        list.map(d => d.id === dance.id ? { ...d, isLearned: res.isLearned } : d)
      );
    });
  }

  // --- Admin: Add Style ---
  toggleAddStyle(): void {
    this.showAddStyle.update(v => !v);
    this.addStyleError.set('');
    this.newStyleName = '';
    this.newStyleDesc = '';
  }

  submitAddStyle(): void {
    if (!this.newStyleName.trim()) { this.addStyleError.set('Name is required.'); return; }
    this.addingStyle.set(true);
    this.addStyleError.set('');
    this.styleService.create(this.newStyleName.trim(), this.newStyleDesc.trim() || undefined).subscribe({
      next: style => {
        this.styles.update(list => [...list, style]);
        this.showAddStyle.set(false);
        this.addingStyle.set(false);
        this.newStyleName = '';
        this.newStyleDesc = '';
      },
      error: () => { this.addStyleError.set('Failed to create style.'); this.addingStyle.set(false); }
    });
  }

  // --- Admin: Add Dance ---
  toggleAddDance(): void {
    this.showAddDance.update(v => !v);
    this.addDanceError.set('');
    this.newDanceName = '';
    this.newDanceDesc = '';
    this.newDanceStyleIds.set(new Set());
    this.newDanceMusicalStyleIds.set(new Set());
  }

  toggleDanceStyle(id: number): void {
    this.newDanceStyleIds.update(s => {
      const next = new Set(s);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  toggleDanceMusicalStyle(id: number): void {
    this.newDanceMusicalStyleIds.update(s => {
      const next = new Set(s);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  submitAddDance(): void {
    if (!this.newDanceName.trim()) { this.addDanceError.set('Name is required.'); return; }
    const payload: CreateDancePayload = {
      name: this.newDanceName.trim(),
      description: this.newDanceDesc.trim() || undefined,
      styleIds: [...this.newDanceStyleIds()],
      musicalStyleIds: [...this.newDanceMusicalStyleIds()]
    };
    this.addingDance.set(true);
    this.addDanceError.set('');
    this.danceService.create(payload).subscribe({
      next: dance => {
        this.allDances.update(list => [dance, ...list]);
        this.showAddDance.set(false);
        this.addingDance.set(false);
        this.newDanceName = '';
        this.newDanceDesc = '';
        this.newDanceStyleIds.set(new Set());
        this.newDanceMusicalStyleIds.set(new Set());
      },
      error: () => { this.addDanceError.set('Failed to create dance.'); this.addingDance.set(false); }
    });
  }
}
