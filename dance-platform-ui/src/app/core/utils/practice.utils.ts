import { toPracticeDateString } from './video-url.utils';

export function computeStreak(sessions: { date: string }[]): number {
  if (sessions.length === 0) return 0;
  const dates = [...new Set(sessions.map(s => s.date))].sort().reverse();
  // "Today" in practice-day terms: before 4 AM still counts as the previous day.
  const today = toPracticeDateString(new Date());
  const yesterday = toPracticeDateString(new Date(Date.now() - 86400000));
  if (dates[0] !== today && dates[0] !== yesterday) return 0;
  let streak = 0;
  let current = new Date(dates[0] + 'T00:00:00');
  for (const d of dates) {
    const diff = Math.round((current.getTime() - new Date(d + 'T00:00:00').getTime()) / 86400000);
    if (diff > 1) break;
    streak++;
    current = new Date(d + 'T00:00:00');
  }
  return streak;
}

/** Longest run of consecutive practice days anywhere in the history (the personal record). */
export function computeLongestStreak(sessions: { date: string }[]): number {
  if (sessions.length === 0) return 0;
  const dates = [...new Set(sessions.map(s => s.date))].sort();
  let longest = 1;
  let run = 1;
  for (let i = 1; i < dates.length; i++) {
    const diff = Math.round((new Date(dates[i] + 'T00:00:00').getTime() - new Date(dates[i - 1] + 'T00:00:00').getTime()) / 86400000);
    run = diff === 1 ? run + 1 : 1;
    if (run > longest) longest = run;
  }
  return longest;
}
