import { Component, OnDestroy, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { DancePathPipe } from '../../shared/pipes/dance-path.pipe';
import { PracticeService, CreatePracticePayload } from '../../core/services/practice.service';
import { DanceService } from '../../core/services/dance.service';
import { ToastService } from '../../core/services/toast.service';
import { PracticeSession, PracticeSessionItem } from '../../models/practice-session.model';
import { ReviewDance } from '../../models/review-dance.model';
import { toLocalDateString, toPracticeDateString, formatClock } from '../../core/utils/video-url.utils';
import { meaningfulSessions, practiceStreak, streakWarningLabel } from '../../core/utils/practice.utils';
import { youtubeThumbUrl } from '../../core/utils/youtube-thumb.utils';
import { delayedLoading } from '../../core/utils/delayed-loading';

type Timeframe = 'week' | 'month' | 'all';

const GOAL_KEY = 'practice.weeklyGoal.v1';

/** Items shorter than this are tracking noise (a stray autoplay, a mis-click) and get folded away. */
const SLIVER_SECONDS = 30;

interface HeatmapDay {
  date: string;
  minutes: number;
  /** 0–4 intensity bucket; -1 marks days in the future (rendered blank). */
  level: number;
  title: string;
}

interface HeatmapWeek {
  monthLabel: string | null;
  days: HeatmapDay[];
}

interface TrendBar {
  /** Monday of the week, YYYY-MM-DD — the bar's identity. */
  key: string;
  /** Month label under the bar when the week starts a new month; null otherwise. */
  monthLabel: string | null;
  minutes: number;
  /** Bar height relative to the axis max, 0–100. */
  heightPct: number;
  /** The in-progress current week renders hollow — its number isn't final. */
  current: boolean;
  /** Direct label only on the peak and current week; the rest live in the tooltip. */
  labeled: boolean;
  title: string;
}

interface BreakdownRow {
  /** Dance id for dance rows; 0 for style rows (not linkable). */
  danceId: number;
  name: string;
  slug: string;
  styleSlug: string;
  minutes: number;
  /** Bar width relative to the top row, 0–100. */
  pct: number;
}

@Component({
  selector: 'app-practice',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, DancePathPipe],
  templateUrl: './practice.component.html',
  styleUrls: ['./practice.component.css']
})
export class PracticeComponent implements OnInit, OnDestroy {
  sessions = signal<PracticeSession[]>([]);
  dances = signal<{ id: number; name: string }[]>([]);
  loading = signal(true);
  showSkeleton = delayedLoading(this.loading);
  /**
   * Done waiting, and the skeleton has finished its minimum-visible hold.
   *
   * Every block above the session list keys off this rather than off `loading` alone, so the
   * page paints on one frame. Each of them reads a different signal that fills in at its own
   * time — the stats need the sessions, the review panel needs its own request — and each one
   * that rendered early pushed the rest of the page down as it arrived, or worse, landed
   * before the skeleton did and left the skeleton drawn underneath real content.
   */
  readonly ready = computed(() => !this.showSkeleton() && !this.loading());

  // Review queue: learned dances gone unpracticed for 3+ weeks (server decides the threshold).
  reviewQueue = signal<ReviewDance[]>([]);
  reviewExpanded = signal(false);
  private readonly failedReviewThumbs = signal<Set<number>>(new Set());

  showAddForm = signal(false);
  newDanceId: number | null = null;
  newDate = '';
  newDuration: number | null = null;
  newNotes = '';
  addError = signal('');
  adding = signal(false);

  // Stats can be scoped to a rolling window; streaks are inherently all-time.
  timeframe = signal<Timeframe>('all');

  // Weekly goal lives in localStorage — it's personal pacing, not shared data.
  weeklyGoal = signal<number | null>(this.readGoal());
  editingGoal = signal(false);
  goalInput: number | null = null;

  // Inline session editing
  editingId = signal<number | null>(null);
  editDate = '';
  editDuration: number | null = null;
  editNotes = '';
  savingEdit = signal(false);
  editError = signal('');

  /** Only surface sessions that lasted more than a minute — sub-minute blips (stray watches) are noise. */
  readonly visibleSessions = computed(() => meaningfulSessions(this.sessions()));

  /** How many review cards show before the queue collapses behind "show all". */
  private readonly REVIEW_PREVIEW = 6;

  readonly visibleReview = computed(() =>
    this.reviewExpanded() ? this.reviewQueue() : this.reviewQueue().slice(0, this.REVIEW_PREVIEW));

  readonly hiddenReviewCount = computed(() => this.reviewQueue().length - this.visibleReview().length);

  /** Drives everything that depends on "now", so a page left open doesn't show a stale
   *  countdown — or keep yesterday's streak lit after the practice day rolls over at 4 AM. */
  private readonly clockTick = signal(Date.now());
  private clockHandle: ReturnType<typeof setInterval> | null = null;

  private readonly streakInfo = computed(() => practiceStreak(this.sessions(), new Date(this.clockTick())));

  readonly streak = computed(() => this.streakInfo().current);
  readonly longestStreak = computed(() => this.streakInfo().longest);

  /** The banner's whole condition: "3 hours left" / "12 min left" when a streak worth keeping
   *  is running out of day, null the rest of the time. */
  readonly streakWarning = computed(() =>
    streakWarningLabel(this.streakInfo(), new Date(this.clockTick())));

  readonly scopedSessions = computed(() => {
    const tf = this.timeframe();
    if (tf === 'all') return this.visibleSessions();
    const days = tf === 'week' ? 7 : 30;
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - (days - 1));
    const cutoffStr = toLocalDateString(cutoff);
    return this.visibleSessions().filter(s => s.date >= cutoffStr);
  });

  readonly scopedTotalMinutes = computed(() =>
    this.scopedSessions().reduce((sum, s) => sum + (s.durationMinutes ?? 0), 0));

  /** Minutes practiced in the current Monday-start week, for the goal ring. */
  readonly thisWeekMinutes = computed(() => {
    const monday = this.mondayOfCurrentWeek();
    const mondayStr = toLocalDateString(monday);
    return this.visibleSessions()
      .filter(s => s.date >= mondayStr)
      .reduce((sum, s) => sum + (s.durationMinutes ?? 0), 0);
  });

  readonly goalPct = computed(() => {
    const goal = this.weeklyGoal();
    if (!goal || goal <= 0) return 0;
    return Math.min(100, Math.round(this.thisWeekMinutes() / goal * 100));
  });

  /** Circumference-based dash offset for the SVG goal ring (r = 15.5). */
  readonly goalDash = computed(() => {
    const c = 2 * Math.PI * 15.5;
    return `${c * this.goalPct() / 100} ${c}`;
  });

  readonly groupedSessions = computed(() => {
    const map = new Map<string, PracticeSession[]>();
    for (const s of this.visibleSessions()) {
      const list = map.get(s.date) ?? [];
      list.push(s);
      map.set(s.date, list);
    }
    return [...map.entries()].sort((a, b) => b[0].localeCompare(a[0]));
  });

  readonly heatmapWeeks = computed<HeatmapWeek[]>(() => {
    const minutesByDate = new Map<string, number>();
    for (const s of this.visibleSessions()) {
      minutesByDate.set(s.date, (minutesByDate.get(s.date) ?? 0) + (s.durationMinutes ?? 0));
    }
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const thisMonday = this.mondayOfCurrentWeek();
    const WEEKS = 12;
    const weeks: HeatmapWeek[] = [];
    let prevMonth = -1;
    for (let w = WEEKS - 1; w >= 0; w--) {
      const monday = new Date(thisMonday);
      monday.setDate(thisMonday.getDate() - w * 7);
      const days: HeatmapDay[] = [];
      for (let i = 0; i < 7; i++) {
        const d = new Date(monday);
        d.setDate(monday.getDate() + i);
        const ds = toLocalDateString(d);
        const minutes = minutesByDate.get(ds) ?? 0;
        const future = d.getTime() > today.getTime();
        const label = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        days.push({
          date: ds,
          minutes,
          level: future ? -1 : this.heatLevel(minutes),
          title: future ? '' : `${label} — ${minutes > 0 ? this.formatDuration(minutes) : 'no practice'}`
        });
      }
      const month = monday.getMonth();
      weeks.push({
        monthLabel: month !== prevMonth ? monday.toLocaleDateString('en-US', { month: 'short' }) : null,
        days
      });
      prevMonth = month;
    }
    return weeks;
  });

  /** Minutes per Monday-start week for the last 12 weeks — the same window the heatmap shows. */
  readonly weeklyTrend = computed<TrendBar[]>(() => {
    const minutesByWeek = new Map<string, number>();
    const thisMonday = this.mondayOfCurrentWeek();
    const thisMondayStr = toLocalDateString(thisMonday);
    for (const s of this.visibleSessions()) {
      const monday = this.mondayOfDate(s.date);
      minutesByWeek.set(monday, (minutesByWeek.get(monday) ?? 0) + (s.durationMinutes ?? 0));
    }

    const WEEKS = 12;
    const raw: { key: string; monthLabel: string | null; minutes: number; current: boolean }[] = [];
    let prevMonth = -1;
    for (let w = WEEKS - 1; w >= 0; w--) {
      const monday = new Date(thisMonday);
      monday.setDate(thisMonday.getDate() - w * 7);
      const key = toLocalDateString(monday);
      const month = monday.getMonth();
      raw.push({
        key,
        monthLabel: month !== prevMonth ? monday.toLocaleDateString('en-US', { month: 'short' }) : null,
        minutes: minutesByWeek.get(key) ?? 0,
        current: key === thisMondayStr
      });
      prevMonth = month;
    }

    const axisMax = this.trendAxisMax();
    const peak = Math.max(...raw.map(r => r.minutes));
    return raw.map(r => ({
      ...r,
      heightPct: axisMax > 0 ? Math.round(r.minutes / axisMax * 100) : 0,
      labeled: r.minutes > 0 && (r.current || r.minutes === peak),
      title: `Week of ${new Date(r.key + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} — ${
        r.minutes > 0 ? this.formatDuration(r.minutes) : 'no practice'}${r.current ? ' (this week so far)' : ''}`
    }));
  });

  /** Top of the y-axis: the peak week rounded up to a clean step, so ticks land on round numbers. */
  readonly trendAxisMax = computed<number>(() => {
    const thisMonday = this.mondayOfCurrentWeek();
    const cutoff = new Date(thisMonday);
    cutoff.setDate(thisMonday.getDate() - 11 * 7);
    const cutoffStr = toLocalDateString(cutoff);
    const minutesByWeek = new Map<string, number>();
    for (const s of this.visibleSessions()) {
      if (s.date < cutoffStr) continue;
      const monday = this.mondayOfDate(s.date);
      minutesByWeek.set(monday, (minutesByWeek.get(monday) ?? 0) + (s.durationMinutes ?? 0));
    }
    const peak = Math.max(0, ...minutesByWeek.values());
    const step = this.trendStep(peak);
    return Math.max(step, Math.ceil(peak / step) * step);
  });

  /** Gridline values from the axis top down to (not including) zero. */
  readonly trendTicks = computed<number[]>(() => {
    const max = this.trendAxisMax();
    const step = this.trendStep(max);
    const ticks: number[] = [];
    for (let v = step; v <= max; v += step) ticks.push(v);
    return ticks.reverse();
  });

  readonly trendHasData = computed(() => this.weeklyTrend().some(b => b.minutes > 0));

  /** Clean tick step sized so the axis carries at most ~4 gridlines. */
  private trendStep(max: number): number {
    for (const s of [10, 15, 30, 60, 120, 180, 240, 360, 480]) {
      if (max / s <= 4) return s;
    }
    return 600;
  }

  private mondayOfDate(dateStr: string): string {
    const d = new Date(dateStr + 'T00:00:00');
    const dow = (d.getDay() + 6) % 7; // 0 = Monday
    d.setDate(d.getDate() - dow);
    return toLocalDateString(d);
  }

  /** Mean session length within the current timeframe. */
  readonly avgSessionMinutes = computed(() => {
    const sessions = this.scopedSessions();
    if (sessions.length === 0) return 0;
    return Math.round(this.scopedTotalMinutes() / sessions.length);
  });

  /** Distinct dances (and local choreos) practiced within the current timeframe. */
  readonly scopedDanceCount = computed(() => {
    const keys = new Set<string>();
    for (const s of this.scopedSessions()) {
      for (const item of s.items) {
        if (item.seconds >= SLIVER_SECONDS) keys.add(this.itemKey(item));
      }
    }
    return keys.size;
  });

  /** Whether the time breakdown aggregates per dance or per style. */
  breakdownBy = signal<'dance' | 'style'>('dance');

  readonly danceBreakdown = computed<BreakdownRow[]>(() => {
    // Choreo items all carry danceId 0, so the key must tell them apart per choreo.
    const byDance = new Map<string, BreakdownRow & { seconds: number }>();
    for (const s of this.scopedSessions()) {
      for (const item of s.items) {
        const key = this.itemKey(item);
        const row = byDance.get(key)
          ?? { danceId: item.danceId, name: item.danceName, slug: item.danceSlug, styleSlug: item.danceStyleSlug, minutes: 0, pct: 0, seconds: 0 };
        row.seconds += item.seconds;
        byDance.set(key, row);
      }
    }
    return this.toBreakdownRows([...byDance.values()]);
  });

  readonly styleBreakdown = computed<BreakdownRow[]>(() => {
    const byStyle = new Map<string, BreakdownRow & { seconds: number }>();
    for (const s of this.scopedSessions()) {
      for (const item of s.items) {
        const name = item.danceStyleName || 'Untagged';
        const row = byStyle.get(name)
          ?? { danceId: 0, name, slug: '', styleSlug: '', minutes: 0, pct: 0, seconds: 0 };
        row.seconds += item.seconds;
        byStyle.set(name, row);
      }
    }
    return this.toBreakdownRows([...byStyle.values()]);
  });

  readonly displayedBreakdown = computed<BreakdownRow[]>(() =>
    this.breakdownBy() === 'style' ? this.styleBreakdown() : this.danceBreakdown());

  private toBreakdownRows(rows: (BreakdownRow & { seconds: number })[]): BreakdownRow[] {
    const kept = rows
      .filter(r => r.seconds >= SLIVER_SECONDS)
      .sort((a, b) => b.seconds - a.seconds)
      .slice(0, 8);
    const max = kept[0]?.seconds ?? 1;
    return kept.map(r => ({ ...r, minutes: Math.round(r.seconds / 60), pct: Math.max(4, Math.round(r.seconds / max * 100)) }));
  }

  constructor(
    private practiceService: PracticeService,
    private danceService: DanceService,
    private toast: ToastService
  ) {}

  ngOnInit(): void {
    // 30s keeps the minute countdown honest without the cost of a per-second tick.
    this.clockHandle = setInterval(() => this.clockTick.set(Date.now()), 30_000);
    this.newDate = toPracticeDateString(new Date());
    this.danceService.getNames().subscribe(d => this.dances.set(d));
    // Both requests gate the same wait. The review panel renders *above* the stats and the
    // session list, so letting it land on its own pushed 175px of already-painted page down
    // whenever it answered second. Waiting for the pair costs the slower of two parallel
    // calls and paints the page once.
    let pending = 2;
    const settled = () => { if (--pending === 0) this.loading.set(false); };
    // An errored observable never completes, so each failure has to settle its own half or
    // the page would hold the skeleton forever.
    this.practiceService.getAll().subscribe({
      next: s => this.sessions.set(s),
      error: settled,
      complete: settled
    });
    // The queue is a bonus panel — if it fails, the page just renders without it.
    this.practiceService.getReviewQueue().subscribe({
      next: q => this.reviewQueue.set(q),
      error: settled,
      complete: settled
    });
  }

  ngOnDestroy(): void {
    if (this.clockHandle) clearInterval(this.clockHandle);
  }

  // --- Stats helpers ---

  setTimeframe(tf: Timeframe): void {
    this.timeframe.set(tf);
  }

  /** "45 min" under an hour, "2 h 35 min" above it. */
  formatDuration(minutes: number): string {
    if (minutes < 60) return `${minutes} min`;
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    return m > 0 ? `${h} h ${m} min` : `${h} h`;
  }

  private mondayOfCurrentWeek(): Date {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const dow = (today.getDay() + 6) % 7; // 0 = Monday
    const monday = new Date(today);
    monday.setDate(today.getDate() - dow);
    return monday;
  }

  private heatLevel(minutes: number): number {
    if (minutes <= 0) return 0;
    if (minutes < 10) return 1;
    if (minutes < 20) return 2;
    if (minutes < 40) return 3;
    return 4;
  }

  // --- Weekly goal ---

  private readGoal(): number | null {
    try {
      const raw = localStorage.getItem(GOAL_KEY);
      const n = raw === null ? NaN : Number(raw);
      return Number.isFinite(n) && n > 0 ? n : null;
    } catch { return null; }
  }

  startEditGoal(): void {
    this.goalInput = this.weeklyGoal() ?? 60;
    this.editingGoal.set(true);
  }

  saveGoal(): void {
    const n = this.goalInput;
    const goal = n && n > 0 ? Math.round(n) : null;
    this.weeklyGoal.set(goal);
    this.editingGoal.set(false);
    try {
      if (goal) localStorage.setItem(GOAL_KEY, String(goal));
      else localStorage.removeItem(GOAL_KEY);
    } catch { /* storage unavailable — the signal still applies for the session */ }
  }

  cancelEditGoal(): void {
    this.editingGoal.set(false);
  }

  // --- Manual add ---

  toggleAddForm(): void {
    this.showAddForm.update(v => !v);
    this.addError.set('');
    this.newDanceId = null;
    this.newDate = toPracticeDateString(new Date());
    this.newDuration = null;
    this.newNotes = '';
  }

  submitAdd(): void {
    if (!this.newDanceId) { this.addError.set('Please select a dance.'); return; }
    if (!this.newDate) { this.addError.set('Date is required.'); return; }

    const payload: CreatePracticePayload = {
      danceId: this.newDanceId,
      date: this.newDate,
      durationMinutes: this.newDuration ?? undefined,
      notes: this.newNotes.trim() || undefined
    };

    this.adding.set(true);
    this.addError.set('');
    this.practiceService.create(payload).subscribe({
      next: session => {
        this.sessions.update(list => this.sorted([session, ...list]));
        this.showAddForm.set(false);
        this.adding.set(false);
        this.newDanceId = null;
        this.newDuration = null;
        this.newNotes = '';
      },
      error: () => { this.addError.set('Failed to log session.'); this.adding.set(false); }
    });
  }

  // --- Inline edit ---

  startEdit(session: PracticeSession): void {
    this.editingId.set(session.id);
    this.editDate = session.date;
    this.editDuration = session.items.length === 1 ? session.durationMinutes : null;
    this.editNotes = session.notes ?? '';
    this.editError.set('');
  }

  cancelEdit(): void {
    this.editingId.set(null);
  }

  /** Duration is only editable when the session holds a single dance — matches the server rule. */
  canEditDuration(session: PracticeSession): boolean {
    return session.items.length === 1;
  }

  saveEdit(session: PracticeSession): void {
    if (!this.editDate) { this.editError.set('Date is required.'); return; }
    this.savingEdit.set(true);
    this.editError.set('');
    this.practiceService.update(session.id, {
      date: this.editDate,
      notes: this.editNotes.trim() || undefined,
      durationMinutes: this.canEditDuration(session) && this.editDuration != null ? this.editDuration : undefined
    }).subscribe({
      next: updated => {
        this.sessions.update(list => this.sorted(list.map(s => s.id === updated.id ? updated : s)));
        this.editingId.set(null);
        this.savingEdit.set(false);
      },
      error: () => { this.editError.set('Failed to save changes.'); this.savingEdit.set(false); }
    });
  }

  // --- Delete with undo ---

  deleteSession(session: PracticeSession): void {
    this.sessions.update(list => list.filter(s => s.id !== session.id));
    const restore = () => this.sessions.update(list => this.sorted([session, ...list]));
    this.toast.undoable('Session deleted.', {
      undo: restore,
      commit: () => this.practiceService.delete(session.id).subscribe({
        // If the server refuses, quietly put the session back rather than losing data.
        error: () => { restore(); this.toast.error('Failed to delete session.'); }
      })
    });
  }

  private sorted(list: PracticeSession[]): PracticeSession[] {
    return [...list].sort((a, b) => b.date.localeCompare(a.date) || b.startedAt.localeCompare(a.startedAt));
  }

  // --- Review queue ---

  reviewThumbUrl(dance: ReviewDance): string | null {
    if (this.failedReviewThumbs().has(dance.danceId)) return null;
    return youtubeThumbUrl(dance.thumbnailVideoId, dance.thumbnailPlatform);
  }

  onReviewThumbError(danceId: number): void {
    this.failedReviewThumbs.update(set => new Set(set).add(danceId));
  }

  /** "5 weeks" / "3 months" since the dance was last touched. */
  reviewAgeLabel(dance: ReviewDance): string {
    const days = dance.daysSince;
    if (days < 14) return `${days} days`;
    if (days < 61) return `${Math.floor(days / 7)} weeks`;
    const months = Math.floor(days / 30.4);
    return months === 1 ? '1 month' : `${months} months`;
  }

  /** Learned but no session ever recorded — the age counts from when it was marked learned. */
  neverPracticed(dance: ReviewDance): boolean {
    return dance.lastPracticedOn === null;
  }

  /** Six-plus weeks untouched gets the hotter accent. */
  reviewIsOverdue(dance: ReviewDance): boolean {
    return dance.daysSince >= 42;
  }

  // --- Display helpers ---

  formatDate(dateStr: string): string {
    // Parse as local midnight: new Date('YYYY-MM-DD') is UTC midnight and renders a day early west of UTC
    return new Date(dateStr + 'T00:00:00').toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
  }

  formatItemTime = formatClock;

  /** Clock time range for a session, e.g. "3:45 PM – 4:12 PM" (collapses to one time if instant). */
  formatSessionTime(session: PracticeSession): string {
    const opts: Intl.DateTimeFormatOptions = { hour: 'numeric', minute: '2-digit' };
    const start = new Date(session.startedAt).toLocaleTimeString('en-US', opts);
    const end = new Date(session.lastActivityAt).toLocaleTimeString('en-US', opts);
    return start === end ? start : `${start} – ${end}`;
  }

  /** Sessions that started deep in the night get a moon marker. */
  isNightSession(session: PracticeSession): boolean {
    const hour = new Date(session.startedAt).getHours();
    return hour >= 22 || hour < 5;
  }

  /** Explains why the duration chip can be smaller than the clock window (pauses aren't counted). */
  durationTitle(session: PracticeSession): string {
    const spanMinutes = Math.round((new Date(session.lastActivityAt).getTime() - new Date(session.startedAt).getTime()) / 60000);
    if (spanMinutes >= session.durationMinutes + 2) {
      return `${session.durationMinutes} min of practice across a ${spanMinutes}-minute window — pauses don't count`;
    }
    return `${session.durationMinutes} min of practice`;
  }

  /** Unique key per item: dances by id, local choreos (all danceId 0) by choreo id. */
  itemKey(item: PracticeSessionItem): string {
    return item.choreoId ? `choreo-${item.choreoId}` : `dance-${item.danceId}`;
  }

  /** Sub-30s items are noise in a multi-dance session; fold them into a "+n more" line. */
  visibleItems(session: PracticeSession): PracticeSessionItem[] {
    if (session.items.length <= 1) return session.items;
    const real = session.items.filter(i => i.seconds >= SLIVER_SECONDS);
    return real.length > 0 ? real : session.items;
  }

  hiddenItemCount(session: PracticeSession): number {
    return session.items.length - this.visibleItems(session).length;
  }

  dayTotalLabel(sessions: PracticeSession[]): string {
    const minutes = sessions.reduce((sum, s) => sum + (s.durationMinutes ?? 0), 0);
    return `${sessions.length} session${sessions.length !== 1 ? 's' : ''} · ${this.formatDuration(minutes)}`;
  }

  // --- CSV export ---

  exportCsv(): void {
    const esc = (v: string | number | undefined | null): string => {
      const s = String(v ?? '');
      return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    };
    const lines = ['Date,Start,End,Dance,Minutes,Seconds,Notes'];
    for (const s of this.visibleSessions()) {
      for (const item of s.items) {
        lines.push([
          s.date,
          new Date(s.startedAt).toLocaleTimeString(),
          new Date(s.lastActivityAt).toLocaleTimeString(),
          esc(item.danceName),
          Math.round(item.seconds / 60),
          item.seconds,
          esc(s.notes)
        ].join(','));
      }
    }
    const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `practice-log-${toLocalDateString(new Date())}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }
}
