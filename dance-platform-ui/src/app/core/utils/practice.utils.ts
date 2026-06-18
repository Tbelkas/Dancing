import { toLocalDateString } from './video-url.utils';

export function computeStreak(sessions: { date: string }[]): number {
  if (sessions.length === 0) return 0;
  const dates = [...new Set(sessions.map(s => s.date))].sort().reverse();
  const today = toLocalDateString(new Date());
  const yesterday = toLocalDateString(new Date(Date.now() - 86400000));
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
