import { describe, it, expect } from 'vitest';
import {
  meaningfulSessions,
  minutesLeftInPracticeDay,
  practiceStreak,
  streakTimeLeftLabel,
  streakWarningLabel,
} from './practice.utils';

/** A logged session on a given day. Duration only matters for the sub-minute cutoff. */
const on = (date: string, totalSeconds = 600) => ({ date, totalSeconds });

/** A fixed "now" well clear of any day boundary, so tests read as calendar dates. */
const at = (dateStr: string, hour = 12) => new Date(`${dateStr}T${String(hour).padStart(2, '0')}:00:00`);

/** Neighbouring calendar day, spelled out in the test so it doesn't lean on the code under test. */
const shift = (dateStr: string, days: number) => {
  const d = new Date(dateStr + 'T12:00:00');
  d.setDate(d.getDate() + days);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

describe('meaningfulSessions', () => {
  it('drops sub-minute blips and keeps the rest', () => {
    const kept = meaningfulSessions([on('2026-08-11', 61), on('2026-08-11', 60), on('2026-08-10', 5)]);
    expect(kept).toEqual([on('2026-08-11', 61)]);
  });
});

describe('practiceStreak', () => {
  it('is empty with no sessions', () => {
    expect(practiceStreak([], at('2026-08-11'))).toEqual({ current: 0, longest: 0, atRisk: false });
  });

  it('counts consecutive days up to today', () => {
    const s = practiceStreak([on('2026-08-09'), on('2026-08-10'), on('2026-08-11')], at('2026-08-11'));
    expect(s.current).toBe(3);
    expect(s.atRisk).toBe(false);
  });

  it('counts several sessions on one day once', () => {
    expect(practiceStreak([on('2026-08-11'), on('2026-08-11')], at('2026-08-11')).current).toBe(1);
  });

  it('holds the streak through today and flags it at risk', () => {
    const s = practiceStreak([on('2026-08-09'), on('2026-08-10')], at('2026-08-11'));
    expect(s.current).toBe(2);
    expect(s.atRisk).toBe(true);
  });

  it('breaks once a whole day passes unlogged', () => {
    expect(practiceStreak([on('2026-08-09'), on('2026-08-10')], at('2026-08-12')).current).toBe(0);
  });

  it('stops at the first gap', () => {
    expect(practiceStreak([on('2026-08-07'), on('2026-08-10'), on('2026-08-11')], at('2026-08-11')).current).toBe(2);
  });

  it('ignores sub-minute blips when they would bridge a gap', () => {
    const s = practiceStreak([on('2026-08-09'), on('2026-08-10', 20), on('2026-08-11')], at('2026-08-11'));
    expect(s.current).toBe(1);
  });

  it('reports the longest run in history even after the current one breaks', () => {
    const s = practiceStreak(
      [on('2026-01-01'), on('2026-01-02'), on('2026-01-03'), on('2026-01-04'), on('2026-08-11')],
      at('2026-08-11')
    );
    expect(s.current).toBe(1);
    expect(s.longest).toBe(4);
  });

  it('counts a session after midnight toward the previous day', () => {
    // 1 AM on the 12th is still the 11th's practice day, so the 11th is "today".
    const s = practiceStreak([on('2026-08-10'), on('2026-08-11')], at('2026-08-12', 1));
    expect(s.current).toBe(2);
    expect(s.atRisk).toBe(false);
  });

  it('treats 4 AM as the start of the new practice day', () => {
    const s = practiceStreak([on('2026-08-10'), on('2026-08-11')], at('2026-08-12', 4));
    expect(s.current).toBe(2);
    expect(s.atRisk).toBe(true);
  });

  it('ignores a future-dated session instead of reading it as a break', () => {
    // A device clock ahead, or a hand-typed date: the real run still stands.
    const s = practiceStreak([on('2026-08-10'), on('2026-08-11'), on('2026-09-01')], at('2026-08-11'));
    expect(s.current).toBe(2);
    expect(s.longest).toBe(2);
  });

  // Both EU (2026-03-29 / 2026-10-25) and US (2026-03-08 / 2026-11-01) transitions, so the
  // cases are real 23- and 25-hour days whichever timezone the runner sits in.
  const springForward = ['2026-03-08', '2026-03-29'];
  const fallBack = ['2026-11-01', '2026-10-25'];

  it('spans a DST transition without dropping a day', () => {
    for (const day of [...springForward, ...fallBack]) {
      const before = shift(day, -1);
      const after = shift(day, 1);
      expect(practiceStreak([on(before), on(day), on(after)], at(after)).current, day).toBe(3);
    }
  });

  it('still grants the grace day on a fall-back day', () => {
    // The 25-hour day is why "yesterday" can't be now minus 86400000ms.
    for (const day of fallBack) {
      expect(practiceStreak([on(shift(day, -1))], at(day)).current, day).toBe(1);
    }
  });
});

/** A wall-clock moment on 2026-08-11, to the minute. */
const clock = (h: number, m = 0) => new Date(`2026-08-11T${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:00`);

describe('minutesLeftInPracticeDay', () => {
  it('runs to the next 4 AM', () => {
    expect(minutesLeftInPracticeDay(clock(12))).toBe(16 * 60);
    expect(minutesLeftInPracticeDay(clock(23, 30))).toBe(4 * 60 + 30);
  });

  it('measures against the same 4 AM after midnight, not a fresh day', () => {
    // 01:00 is still the 10th's practice day, with three hours to go.
    expect(minutesLeftInPracticeDay(clock(1))).toBe(3 * 60);
  });

  it('gives a full day just after the boundary', () => {
    expect(minutesLeftInPracticeDay(clock(4))).toBe(24 * 60);
    expect(minutesLeftInPracticeDay(clock(3, 59))).toBe(1);
  });
});

describe('streakTimeLeftLabel', () => {
  it('stays quiet while there is plenty of day left', () => {
    expect(streakTimeLeftLabel(clock(12))).toBeNull();
    expect(streakTimeLeftLabel(clock(19, 59))).toBeNull();
  });

  it('starts counting in the evening, eight hours out', () => {
    expect(streakTimeLeftLabel(clock(20))).toBe('8 hours left');
    expect(streakTimeLeftLabel(clock(22))).toBe('6 hours left');
    expect(streakTimeLeftLabel(clock(0))).toBe('4 hours left');
    expect(streakTimeLeftLabel(clock(1))).toBe('3 hours left');
    expect(streakTimeLeftLabel(clock(2, 30))).toBe('1 hour left');
  });

  it('takes a wider window when asked', () => {
    expect(streakTimeLeftLabel(clock(19, 59), 4)).toBeNull();
    expect(streakTimeLeftLabel(clock(19, 59), 12)).toBe('8 hours left');
  });

  it('rounds hours down, so it never over-promises', () => {
    expect(streakTimeLeftLabel(clock(1, 1))).toBe('2 hours left');
  });

  it('switches to minutes inside the last hour', () => {
    expect(streakTimeLeftLabel(clock(3))).toBe('1 hour left');
    expect(streakTimeLeftLabel(clock(3, 1))).toBe('59 min left');
    expect(streakTimeLeftLabel(clock(3, 48))).toBe('12 min left');
  });

  it('never counts down to zero while the day is still alive', () => {
    expect(streakTimeLeftLabel(new Date('2026-08-11T03:59:30'))).toBe('1 min left');
  });
});

describe('streakWarningLabel', () => {
  /** A run of `days` ending yesterday: at risk, with nothing logged today yet. */
  const atRisk = (days: number, today = '2026-08-11') =>
    practiceStreak(
      Array.from({ length: days }, (_, i) => on(shift(today, -(i + 1)))),
      at(today)
    );

  it('says nothing about a short streak, however late it gets', () => {
    for (const days of [1, 2, 6]) {
      expect(streakWarningLabel(atRisk(days), clock(23)), `${days}-day`).toBeNull();
    }
  });

  it('warns from seven days up, in the evening', () => {
    expect(streakWarningLabel(atRisk(7), clock(21))).toBe('7 hours left');
    expect(streakWarningLabel(atRisk(30), clock(21))).toBe('7 hours left');
  });

  it('stays quiet earlier in the day, however long the streak', () => {
    expect(streakWarningLabel(atRisk(30), clock(9))).toBeNull();
    expect(streakWarningLabel(atRisk(30), clock(19, 59))).toBeNull();
  });

  it('says nothing once today is already practiced, long streak or not', () => {
    // Ten days ending *today* — long enough and late enough, but there is nothing to save.
    const done = practiceStreak(
      Array.from({ length: 10 }, (_, i) => on(shift('2026-08-11', -i))),
      at('2026-08-11')
    );
    expect(done.current).toBe(10);
    expect(done.atRisk).toBe(false);
    expect(streakWarningLabel(done, clock(23))).toBeNull();
  });

  it('says nothing when there is no streak at all', () => {
    expect(streakWarningLabel(practiceStreak([], at('2026-08-11')), clock(23))).toBeNull();
  });
});
