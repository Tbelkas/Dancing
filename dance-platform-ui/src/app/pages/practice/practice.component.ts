import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { PracticeService, CreatePracticePayload } from '../../core/services/practice.service';
import { DanceService } from '../../core/services/dance.service';
import { PracticeSession } from '../../models/practice-session.model';
import { Dance } from '../../models/dance.model';

/** Calendar date in the user's timezone (toISOString would give the UTC date). */
function toLocalDateString(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

@Component({
  selector: 'app-practice',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './practice.component.html',
  styleUrls: ['./practice.component.css']
})
export class PracticeComponent implements OnInit {
  sessions = signal<PracticeSession[]>([]);
  dances = signal<Dance[]>([]);
  loading = signal(true);

  showAddForm = signal(false);
  newDanceId: number | null = null;
  newDate = '';
  newDuration: number | null = null;
  newNotes = '';
  addError = signal('');
  adding = signal(false);

  readonly streak = computed(() => {
    const sessions = this.sessions();
    if (sessions.length === 0) return 0;

    const dates = [...new Set(sessions.map(s => s.date))].sort().reverse();
    const today = toLocalDateString(new Date());
    const yesterday = toLocalDateString(new Date(Date.now() - 86400000));

    if (dates[0] !== today && dates[0] !== yesterday) return 0;

    let streak = 0;
    let current = new Date(dates[0]);
    for (const d of dates) {
      const diff = Math.round((current.getTime() - new Date(d).getTime()) / 86400000);
      if (diff > 1) break;
      streak++;
      current = new Date(d);
    }
    return streak;
  });

  readonly groupedSessions = computed(() => {
    const map = new Map<string, PracticeSession[]>();
    for (const s of this.sessions()) {
      const list = map.get(s.date) ?? [];
      list.push(s);
      map.set(s.date, list);
    }
    return [...map.entries()].sort((a, b) => b[0].localeCompare(a[0]));
  });

  constructor(
    private practiceService: PracticeService,
    private danceService: DanceService
  ) {}

  ngOnInit(): void {
    this.newDate = toLocalDateString(new Date());
    this.danceService.getAll().subscribe(d => this.dances.set(d));
    this.practiceService.getAll().subscribe({
      next: s => { this.sessions.set(s); this.loading.set(false); },
      error: () => this.loading.set(false)
    });
  }

  toggleAddForm(): void {
    this.showAddForm.update(v => !v);
    this.addError.set('');
    this.newDanceId = null;
    this.newDate = toLocalDateString(new Date());
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
        this.sessions.update(list => [session, ...list].sort((a, b) => b.date.localeCompare(a.date)));
        this.showAddForm.set(false);
        this.adding.set(false);
        this.newDanceId = null;
        this.newDuration = null;
        this.newNotes = '';
      },
      error: () => { this.addError.set('Failed to log session.'); this.adding.set(false); }
    });
  }

  deleteSession(id: number): void {
    if (!confirm('Delete this practice session?')) return;
    this.practiceService.delete(id).subscribe({
      next: () => this.sessions.update(list => list.filter(s => s.id !== id)),
      error: () => alert('Failed to delete session.')
    });
  }

  formatDate(dateStr: string): string {
    // Parse as local midnight: new Date('YYYY-MM-DD') is UTC midnight and renders a day early west of UTC
    return new Date(dateStr + 'T00:00:00').toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
  }

  totalMinutes(): number {
    return this.sessions().reduce((sum, s) => sum + (s.durationMinutes ?? 0), 0);
  }
}
