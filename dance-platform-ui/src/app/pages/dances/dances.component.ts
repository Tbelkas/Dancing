import { Component, OnInit, OnDestroy, computed, signal } from '@angular/core';
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
const PAGE_SIZE = 24;

const SEED_STYLES: Style[] = [
  { id: 1, name: 'Latin', dateAdded: '', danceCount: 0 },
  { id: 2, name: 'Ballroom', dateAdded: '', danceCount: 0 },
  { id: 3, name: 'Street / Urban', dateAdded: '', danceCount: 0 },
  { id: 4, name: 'Classical / Ballet', dateAdded: '', danceCount: 0 },
  { id: 5, name: 'Folk / Traditional', dateAdded: '', danceCount: 0 },
  { id: 6, name: 'Swing', dateAdded: '', danceCount: 0 },
  { id: 7, name: 'Contemporary', dateAdded: '', danceCount: 0 },
  { id: 8, name: 'Waacking', dateAdded: '', danceCount: 0 },
  { id: 9, name: 'Tektonik', dateAdded: '', danceCount: 0 },
  { id: 10, name: 'Hip-hop', dateAdded: '', danceCount: 0 },
  { id: 11, name: 'House', dateAdded: '', danceCount: 0 }
];
const SEED_MUSICAL_STYLES: MusicalStyle[] = [
  { id: 1, name: 'Salsa', dateAdded: '', danceCount: 0 },
  { id: 2, name: 'Classical / Orchestral', dateAdded: '', danceCount: 0 },
  { id: 3, name: 'Hip-Hop', dateAdded: '', danceCount: 0 },
  { id: 4, name: 'Jazz', dateAdded: '', danceCount: 0 },
  { id: 5, name: 'Tango', dateAdded: '', danceCount: 0 },
  { id: 6, name: 'Electronic / EDM', dateAdded: '', danceCount: 0 },
  { id: 7, name: 'Blues', dateAdded: '', danceCount: 0 },
  { id: 8, name: 'Reggaeton', dateAdded: '', danceCount: 0 },
  { id: 9, name: 'Cumbia', dateAdded: '', danceCount: 0 },
  { id: 10, name: 'Flamenco', dateAdded: '', danceCount: 0 }
];

@Component({
  selector: 'app-dances',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './dances.component.html',
  styleUrls: ['./dances.component.css']
})
export class DancesComponent implements OnInit, OnDestroy {
  readonly difficulties = DIFFICULTIES;
  readonly statusOptions = STATUS_OPTIONS;
  readonly skeletonCards = [0, 1, 2, 3, 4, 5];
  readonly PAGE_SIZE = PAGE_SIZE;

  // Data
  searchResults = signal<Dance[]>([]);
  searchTotal = signal(0);
  currentPage = signal(1);
  styles = signal<Style[]>(SEED_STYLES);
  musicalStyles = signal<MusicalStyle[]>(SEED_MUSICAL_STYLES);
  instructors = signal<Instructor[]>([]);
  loading = signal(true);

  // Filters
  searchQuery = signal('');
  selectedStyleId = signal<number | null>(null);
  selectedMusicalStyleId = signal<number | null>(null);
  selectedDifficulty = signal<string | null>(null);
  selectedStatus = signal<string>('all');
  sortBy = signal<string>('name');

  styleQuery = signal('');
  musicQuery = signal('');

  readonly visibleStyles = computed(() => {
    const q = this.styleQuery().trim().toLowerCase();
    if (!q) return this.styles();
    const sel = this.selectedStyleId();
    return this.styles().filter(s => s.id === sel || s.name.toLowerCase().includes(q));
  });

  readonly visibleMusicalStyles = computed(() => {
    const q = this.musicQuery().trim().toLowerCase();
    if (!q) return this.musicalStyles();
    const sel = this.selectedMusicalStyleId();
    return this.musicalStyles().filter(ms => ms.id === sel || ms.name.toLowerCase().includes(q));
  });

  readonly hasActiveFilters = computed(() =>
    this.searchQuery().trim() !== '' ||
    this.selectedStyleId() !== null ||
    this.selectedMusicalStyleId() !== null ||
    this.selectedDifficulty() !== null ||
    this.selectedStatus() !== 'all'
  );

  readonly totalPages = computed(() => Math.ceil(this.searchTotal() / PAGE_SIZE));

  readonly pageNumbers = computed(() => {
    const total = this.totalPages();
    const cur = this.currentPage();
    if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
    const pages: (number | null)[] = [];
    pages.push(1);
    if (cur > 3) pages.push(null);
    for (let p = Math.max(2, cur - 1); p <= Math.min(total - 1, cur + 1); p++) pages.push(p);
    if (cur < total - 2) pages.push(null);
    pages.push(total);
    return pages;
  });

  thumbFailed = signal<Set<number>>(new Set());

  private searchDebounce: ReturnType<typeof setTimeout> | null = null;

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
    this.runSearch();
  }

  ngOnDestroy(): void {
    if (this.searchDebounce) clearTimeout(this.searchDebounce);
  }

  private runSearch(): void {
    this.loading.set(true);
    this.danceService.searchDances({
      q: this.searchQuery().trim() || undefined,
      styleId: this.selectedStyleId(),
      musicalStyleId: this.selectedMusicalStyleId(),
      difficulty: this.selectedDifficulty() ?? undefined,
      status: this.selectedStatus(),
      sortBy: this.sortBy(),
      page: this.currentPage(),
      pageSize: PAGE_SIZE
    }).subscribe({
      next: result => {
        this.searchResults.set(result.items);
        this.searchTotal.set(result.total);
        this.loading.set(false);
      },
      error: () => this.loading.set(false)
    });
  }

  onSearchInput(value: string): void {
    this.searchQuery.set(value);
    this.currentPage.set(1);
    if (this.searchDebounce) clearTimeout(this.searchDebounce);
    this.searchDebounce = setTimeout(() => this.runSearch(), 300);
  }

  filterByStyle(styleId: number | null): void {
    this.selectedStyleId.set(styleId);
    this.currentPage.set(1);
    this.runSearch();
  }

  filterByMusicalStyle(msId: number | null): void {
    this.selectedMusicalStyleId.set(msId);
    this.currentPage.set(1);
    this.runSearch();
  }

  filterByDifficulty(difficulty: string | null): void {
    this.selectedDifficulty.set(difficulty);
    this.currentPage.set(1);
    this.runSearch();
  }

  filterByStatus(status: string): void {
    this.selectedStatus.set(status);
    this.currentPage.set(1);
    this.runSearch();
  }

  onSortChange(value: string): void {
    this.sortBy.set(value);
    this.currentPage.set(1);
    this.runSearch();
  }

  goToPage(page: number | null): void {
    if (page === null || page < 1 || page > this.totalPages()) return;
    this.currentPage.set(page);
    this.runSearch();
  }

  clearFilters(): void {
    this.searchQuery.set('');
    this.selectedStyleId.set(null);
    this.selectedMusicalStyleId.set(null);
    this.selectedDifficulty.set(null);
    this.selectedStatus.set('all');
    this.currentPage.set(1);
    this.runSearch();
  }

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

  onThumbLoad(danceId: number, event: Event): void {
    const img = event.target as HTMLImageElement;
    if (img.naturalHeight > 0 && img.naturalHeight <= 90) {
      this.onThumbError(danceId);
    }
  }

  starLabel(rating: number): string {
    return rating > 0 ? rating.toFixed(1) : '—';
  }

  toggleFavorite(dance: Dance, event: Event): void {
    event.stopPropagation();
    event.preventDefault();
    this.danceService.toggleFavorite(dance.id).subscribe(res => {
      this.searchResults.update(list =>
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

    this.searchResults.update(list =>
      list.map(d => d.id === dance.id
        ? { ...d, isLearned: willLearn, isInProgress: willLearn ? false : d.isInProgress }
        : d)
    );

    this.danceService.setStatus(dance.id, status).subscribe({
      error: () => this.searchResults.update(list =>
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
          this.searchResults.update(list => [...result.created, ...list]);
          this.searchTotal.update(t => t + result.created.length);
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
        this.searchResults.update(list => [dance, ...list]);
        this.searchTotal.update(t => t + 1);
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
