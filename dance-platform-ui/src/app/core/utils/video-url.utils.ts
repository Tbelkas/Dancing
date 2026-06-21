/** Returns a YYYY-MM-DD string in the user's local timezone (Date.toISOString() gives UTC, which shifts the day west of UTC). */
export function toLocalDateString(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
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

export function parseTimeSecs(input: string): number | undefined {
  const s = input.trim();
  if (!s) return undefined;
  if (s.includes(':')) {
    const [m, sec] = s.split(':').map(Number);
    return isNaN(m) || isNaN(sec) ? undefined : m * 60 + sec;
  }
  const n = Number(s);
  return isNaN(n) ? undefined : n;
}

export function formatTimeSecs(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}
