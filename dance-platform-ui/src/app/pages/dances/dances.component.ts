import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { DanceService, CreateDancePayload, ImportResult, DanceStatus } from '../../core/services/dance.service';
import { StyleService } from '../../core/services/style.service';
import { MusicalStyleService } from '../../core/services/musical-style.service';
import { InstructorService } from '../../core/services/instructor.service';
import { AuthService } from '../../core/services/auth.service';
import { RoleService } from '../../core/services/role.service';
import { Dance } from '../../models/dance.model';
import { Style } from '../../models/style.model';
import { MusicalStyle } from '../../models/musical-style.model';
import { Instructor } from '../../models/instructor.model';

const DIFFICULTIES = ['Beginner', 'Intermediate', 'Advanced'];
const STATUS_OPTIONS = [
  { value: 'all', label: 'All' },
  { value: 'notstarted', label: 'Not Started' },
  { value: 'inprogress', label: 'In Progress' },
  { value: 'learned', label: 'Learned' },
  { value: 'favorite', label: 'Favorited' }
];

@Component({
  selector: 'app-dances',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './dances.component.html',
  styleUrls: ['./dances.component.css']
})
export class DancesComponent implements OnInit {
  readonly difficulties = DIFFICULTIES;
  readonly statusOptions = STATUS_OPTIONS;
  readonly skeletonCards = [0, 1, 2, 3, 4, 5];

  // Data
  allDances = signal<Dance[]>([]);
  styles = signal<Style[]>([]);
  musicalStyles = signal<MusicalStyle[]>([]);
  instructors = signal<Instructor[]>([]);
  loading = signal(true);

  // Filters (client-side)
  searchQuery = signal('');
  selectedStyleId = signal<number | null>(null);
  selectedMusicalStyleId = signal<number | null>(null);
  selectedDifficulty = signal<string | null>(null);
  selectedStatus = signal<string>('all');
  sortBy = signal<string>('name');

  readonly hasActiveFilters = computed(() =>
    this.searchQuery().trim() !== '' ||
    this.selectedStyleId() !== null ||
    this.selectedMusicalStyleId() !== null ||
    this.selectedDifficulty() !== null ||
    this.selectedStatus() !== 'all'
  );

  readonly filteredDances = computed(() => {
    const q = this.searchQuery().trim().toLowerCase();
    const sid = this.selectedStyleId();
    const msid = this.selectedMusicalStyleId();
    const diff = this.selectedDifficulty();
    const status = this.selectedStatus();
    const styleName = sid ? this.styles().find(s => s.id === sid)?.name ?? null : null;
    const msName = msid ? this.musicalStyles().find(ms => ms.id === msid)?.name ?? null : null;

    return this.allDances().filter(d => {
      if (q && !d.name.toLowerCase().includes(q)) return false;
      if (styleName && !d.styles.includes(styleName)) return false;
      if (msName && !d.musicalStyles.includes(msName)) return false;
      if (diff && d.difficulty !== diff) return false;
      if (status === 'notstarted' && (d.isLearned || d.isInProgress)) return false;
      if (status === 'inprogress' && !d.isInProgress) return false;
      if (status === 'learned' && !d.isLearned) return false;
      if (status === 'favorite' && !d.isFavorite) return false;
      return true;
    });
  });

  readonly sortedDances = computed(() => {
    const list = [...this.filteredDances()];
    switch (this.sortBy()) {
      case 'rating':
        return list.sort((a, b) => b.averageRating - a.averageRating || b.ratingCount - a.ratingCount);
      case 'popular':
        return list.sort((a, b) => b.favoriteCount - a.favoriteCount);
      case 'newest':
        return list.sort((a, b) => +new Date(b.dateAdded) - +new Date(a.dateAdded));
      case 'name':
      default:
        return list.sort((a, b) => a.name.localeCompare(b.name));
    }
  });

  thumbFailed = signal<Set<number>>(new Set());

  thumbnailUrl(dance: Dance): string | null {
    if (this.thumbFailed().has(dance.id)) return null;
    if (dance.thumbnailVideoId && dance.thumbnailPlatform === 'youtube') {
      return `https://i.ytimg.com/vi/${dance.thumbnailVideoId}/hqdefault.jpg`;
    }
    return null;
  }

  onThumbError(danceId: number): void {
    this.thumbFailed.update(set => {
      const next = new Set(set);
      next.add(danceId);
      return next;
    });
  }

  clearFilters(): void {
    this.searchQuery.set('');
    this.selectedStyleId.set(null);
    this.selectedMusicalStyleId.set(null);
    this.selectedDifficulty.set(null);
    this.selectedStatus.set('all');
  }

  // Admin: add style form
  showAddStyle = signal(false);
  newStyleName = '';
  newStyleDesc = '';
  addingStyle = signal(false);
  addStyleError = signal('');

  // Admin: bulk import form
  showImport = signal(false);
  importText = '';
  importing = signal(false);
  importResult = signal<ImportResult | null>(null);
  importError = signal('');

  // Admin: add dance form
  showAddDance = signal(false);
  newDanceName = '';
  newDanceDesc = '';
  newDanceDifficulty = 'None';
  newDanceStyleIds = signal<Set<number>>(new Set());
  newDanceMusicalStyleIds = signal<Set<number>>(new Set());
  newDanceInstructorIds = signal<Set<number>>(new Set());
  addingDance = signal(false);
  addDanceError = signal('');

  constructor(
    private danceService: DanceService,
    private styleService: StyleService,
    private musicalStyleService: MusicalStyleService,
    private instructorService: InstructorService,
    public auth: AuthService,
    public role: RoleService
  ) {}

  ngOnInit(): void {
    this.styleService.getAll().subscribe(s => this.styles.set(s));
    this.musicalStyleService.getAll().subscribe(ms => this.musicalStyles.set(ms));
    this.instructorService.getAll().subscribe(i => this.instructors.set(i));
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

  filterByMusicalStyle(msId: number | null): void {
    this.selectedMusicalStyleId.set(msId);
  }

  filterByDifficulty(difficulty: string | null): void {
    this.selectedDifficulty.set(difficulty);
  }

  filterByStatus(status: string): void {
    this.selectedStatus.set(status);
  }

  starLabel(rating: number): string {
    return rating > 0 ? rating.toFixed(1) : '—';
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
    const snap = { isLearned: dance.isLearned, isInProgress: dance.isInProgress };
    const status: DanceStatus = dance.isLearned ? 'notstarted' : 'learned';
    const willLearn = status === 'learned';

    // Optimistic single atomic call: flip now, revert on failure. Marking learned
    // clears in-progress server-side (mutually exclusive), so mirror that here.
    this.allDances.update(list =>
      list.map(d => d.id === dance.id
        ? { ...d, isLearned: willLearn, isInProgress: willLearn ? false : d.isInProgress }
        : d)
    );

    this.danceService.setStatus(dance.id, status).subscribe({
      error: () => this.allDances.update(list =>
        list.map(d => d.id === dance.id ? { ...d, ...snap } : d)
      )
    });
  }

  // --- Admin: Bulk Import ---
  toggleImport(): void {
    this.showImport.update(v => !v);
    this.importText = '';
    this.importResult.set(null);
    this.importError.set('');
  }

  submitImport(): void {
    if (!this.importText.trim()) { this.importError.set('Paste some text to import.'); return; }
    this.importing.set(true);
    this.importError.set('');
    this.importResult.set(null);
    this.danceService.importDances(this.importText).subscribe({
      next: result => {
        this.importResult.set(result);
        this.importing.set(false);
        if (result.created.length > 0) {
          this.allDances.update(list => [...result.created, ...list]);
          this.importText = '';
        }
      },
      error: () => { this.importError.set('Import failed. Make sure you are logged in as admin.'); this.importing.set(false); }
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
    this.newDanceDifficulty = 'None';
    this.newDanceStyleIds.set(new Set());
    this.newDanceMusicalStyleIds.set(new Set());
    this.newDanceInstructorIds.set(new Set());
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

  toggleDanceInstructor(id: number): void {
    this.newDanceInstructorIds.update(s => {
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
      difficulty: this.newDanceDifficulty,
      styleIds: [...this.newDanceStyleIds()],
      musicalStyleIds: [...this.newDanceMusicalStyleIds()],
      instructorIds: [...this.newDanceInstructorIds()]
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
        this.newDanceDifficulty = 'None';
        this.newDanceStyleIds.set(new Set());
        this.newDanceMusicalStyleIds.set(new Set());
        this.newDanceInstructorIds.set(new Set());
      },
      error: () => { this.addDanceError.set('Failed to create dance.'); this.addingDance.set(false); }
    });
  }
}
