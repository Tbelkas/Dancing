/** Returns a YYYY-MM-DD string in the user's local timezone (Date.toISOString() gives UTC, which shifts the day west of UTC). */
export function toLocalDateString(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

/** A practice day runs 4 AM → 4 AM, not midnight → midnight. */
export const PRACTICE_DAY_START_HOUR = 4;

/**
 * The "practice day" a moment belongs to: anything before 4 AM counts toward the previous
 * calendar day, so a midnight session doesn't artificially split or break a streak.
 */
export function toPracticeDateString(d: Date): string {
  const shifted = new Date(d.getTime() - PRACTICE_DAY_START_HOUR * 3600000);
  return toLocalDateString(shifted);
}

export function parseVideoUrl(input: string): { platform: string; videoId: string } | null {
  const url = input.trim();
  const tiktok = url.match(/tiktok\.com\/@[^/]+\/video\/(\d+)/);
  if (tiktok) return { platform: 'tiktok', videoId: tiktok[1] };
  const ig = url.match(/instagram\.com\/(?:p|reel|reels|tv)\/([A-Za-z0-9_-]+)/);
  if (ig) return { platform: 'instagram', videoId: ig[1] };
  // Handles watch?v=, watch?…&v= (params before v), youtu.be/, embed/, shorts/, live/
  const yt = url.match(/(?:youtube\.com\/(?:watch\?(?:[^&\s]*&)*v=|embed\/|shorts\/|live\/)|youtu\.be\/)([A-Za-z0-9_-]{11})/);
  if (yt) return { platform: 'youtube', videoId: yt[1] };
  if (/^[A-Za-z0-9_-]{11}$/.test(url)) return { platform: 'youtube', videoId: url };
  return null;
}

/**
 * Fetches the video's title from the platform's public oEmbed endpoint. YouTube and
 * TikTok allow anonymous CORS requests; Instagram's oEmbed needs an access token, so
 * Instagram links resolve to null. Returns null on any failure — callers treat the
 * fetched title as a best-effort convenience, never a requirement.
 */
export async function fetchVideoTitle(input: string): Promise<string | null> {
  const parsed = parseVideoUrl(input);
  if (!parsed) return null;
  let endpoint: string;
  if (parsed.platform === 'youtube')
    endpoint = `https://www.youtube.com/oembed?format=json&url=${encodeURIComponent(`https://www.youtube.com/watch?v=${parsed.videoId}`)}`;
  else if (parsed.platform === 'tiktok')
    endpoint = `https://www.tiktok.com/oembed?url=${encodeURIComponent(input.trim())}`;
  else
    return null;
  try {
    const res = await fetch(endpoint);
    if (!res.ok) return null;
    const title = (await res.json())?.title;
    return typeof title === 'string' && title.trim() ? title.trim() : null;
  } catch {
    return null;
  }
}

export function parseTimeSecs(input: string): number | undefined {
  const s = input.trim();
  if (!s) return undefined;
  if (s.includes(':')) {
    // Accept both m:ss and h:mm:ss (formatClock emits the latter for clips >= 1 hour).
    const parts = s.split(':').map(Number);
    if (parts.some(isNaN)) return undefined;
    if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
    if (parts.length === 2) return parts[0] * 60 + parts[1];
    return undefined;
  }
  const n = Number(s);
  return isNaN(n) ? undefined : n;
}

export function formatTimeSecs(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

/** Clock-style duration: m:ss under an hour, h:mm:ss at or above it. */
export function formatClock(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return h > 0
    ? `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
    : `${m}:${s.toString().padStart(2, '0')}`;
}
