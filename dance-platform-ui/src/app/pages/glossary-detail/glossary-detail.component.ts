import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { Title } from '@angular/platform-browser';
import { GlossaryService } from '../../core/services/glossary.service';
import { AuthService } from '../../core/services/auth.service';
import { ToastService } from '../../core/services/toast.service';
import { Glossary, GlossaryCategory, GlossaryTerm } from '../../models/glossary.model';
import { DancePathPipe } from '../../shared/pipes/dance-path.pipe';
import { SignInDialogComponent } from '../../shared/components/sign-in-dialog/sign-in-dialog.component';
import { youtubeThumbUrl } from '../../core/utils/youtube-thumb.utils';
import { delayedLoading } from '../../core/utils/delayed-loading';

@Component({
  selector: 'app-glossary-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, DancePathPipe, SignInDialogComponent],
  templateUrl: './glossary-detail.component.html',
  styleUrls: ['./glossary-detail.component.css']
})
export class GlossaryDetailComponent implements OnInit {
  glossary = signal<Glossary | null>(null);
  loading = signal(true);
  showSkeleton = delayedLoading(this.loading);
  notFound = signal(false);
  failed = signal(false);

  query = signal('');
  category = signal<string | null>(null);
  hideLearned = signal(false);
  expanded = signal<Set<string>>(new Set());
  signInOpen = signal(false);
  private readonly pending = new Set<number>();

  readonly learnedCount = computed(() => this.allTerms().filter(t => t.isLearnable && t.isLearned).length);
  readonly moveCount = computed(() => this.allTerms().filter(t => t.isLearnable).length);
  readonly progressPercent = computed(() =>
    this.moveCount() === 0 ? 0 : Math.round((this.learnedCount() / this.moveCount()) * 100));

  private readonly allTerms = computed(() => this.glossary()?.categories.flatMap(c => c.terms) ?? []);

  /**
   * Categories with the filters applied. A category whose terms are all filtered out is dropped,
   * so a search never leaves a stack of empty headings behind it.
   */
  readonly visible = computed<GlossaryCategory[]>(() => {
    const g = this.glossary();
    if (!g) return [];
    const q = this.query().trim().toLowerCase();
    const cat = this.category();
    const hide = this.hideLearned() && this.auth.isAuthenticated();
    return g.categories
      .filter(c => !cat || c.name === cat)
      .map(c => ({
        name: c.name,
        terms: c.terms.filter(t =>
          (!hide || !t.isLearned) &&
          (!q || this.matches(t, q)))
      }))
      .filter(c => c.terms.length > 0);
  });

  readonly visibleCount = computed(() => this.visible().reduce((n, c) => n + c.terms.length, 0));

  constructor(
    private route: ActivatedRoute,
    private glossaryService: GlossaryService,
    private title: Title,
    private toast: ToastService,
    public auth: AuthService
  ) {}

  ngOnInit(): void {
    this.route.paramMap.subscribe(p => this.load(p.get('style') ?? ''));
  }

  private load(style: string): void {
    this.loading.set(true);
    this.glossaryService.getByStyle(style).subscribe({
      next: g => {
        this.glossary.set(g);
        this.loading.set(false);
        this.title.setTitle(`${g.styleName} glossary · Dance Platform`);
        // A shared /glossary/house#jack link opens on that term.
        const fragment = this.route.snapshot.fragment;
        if (fragment) this.open(fragment);
      },
      error: err => {
        if (err?.status === 404) this.notFound.set(true); else this.failed.set(true);
        this.loading.set(false);
      }
    });
  }

  private matches(t: GlossaryTerm, q: string): boolean {
    return t.name.toLowerCase().includes(q)
      || t.aliases.some(a => a.toLowerCase().includes(q))
      || t.summary.toLowerCase().includes(q);
  }

  isExpanded(slug: string): boolean {
    return this.expanded().has(slug);
  }

  toggle(slug: string): void {
    const next = new Set(this.expanded());
    if (next.has(slug)) next.delete(slug); else next.add(slug);
    this.expanded.set(next);
  }

  /**
   * Expands a term and scrolls to it, clearing any filter that would hide it — following a
   * "related" link to a term the search has filtered out would otherwise go nowhere.
   */
  open(slug: string): void {
    const term = this.allTerms().find(t => t.slug === slug);
    if (!term) return;
    if (!this.visible().some(c => c.terms.includes(term))) {
      this.query.set('');
      this.category.set(null);
      this.hideLearned.set(false);
    }
    this.expanded.set(new Set(this.expanded()).add(slug));
    history.replaceState(null, '', `${location.pathname}#${slug}`);
    setTimeout(() => document.getElementById(slug)?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
  }

  expandAll(): void {
    this.expanded.set(new Set(this.visible().flatMap(c => c.terms.map(t => t.slug))));
  }

  collapseAll(): void {
    this.expanded.set(new Set());
  }

  onSearch(event: Event): void {
    this.query.set((event.target as HTMLInputElement).value);
  }

  setLearned(term: GlossaryTerm, learned: boolean): void {
    if (!this.auth.isAuthenticated()) {
      this.signInOpen.set(true);
      return;
    }
    if (this.pending.has(term.id)) return;
    this.pending.add(term.id);
    this.patch(term.id, learned);
    this.glossaryService.setLearned(term.id, learned).subscribe({
      next: () => this.pending.delete(term.id),
      error: () => {
        this.pending.delete(term.id);
        this.patch(term.id, !learned);
        this.toast.error('Could not save that. Check you are still signed in.');
      }
    });
  }

  /** Replaces the one term immutably so every computed downstream of the glossary re-runs. */
  private patch(termId: number, isLearned: boolean): void {
    const g = this.glossary();
    if (!g) return;
    this.glossary.set({
      ...g,
      categories: g.categories.map(c => ({
        ...c,
        terms: c.terms.map(t => t.id === termId ? { ...t, isLearned } : t)
      }))
    });
  }

  onSignedIn(): void {
    this.signInOpen.set(false);
    // Reload so the page picks up the marks this account already has.
    const g = this.glossary();
    if (g) this.load(g.styleSlug);
  }

  thumbnailUrl(t: GlossaryTerm): string | null {
    return youtubeThumbUrl(t.dance?.thumbnailVideoId, t.dance?.thumbnailPlatform);
  }
}
