/**
 * Builds the CDN URL for a dance's YouTube thumbnail, shared by the browse grid/list
 * cards and the dance-detail "More like this" cards so the URL scheme lives in one place.
 *
 * `frame` drives the lightweight hover preview: 0 (the default) returns the static
 * `hqdefault` poster; 1–3 return YouTube's storyboard frames (`mq1`–`mq3`) that the
 * browse cards cycle through on hover. Returns null for non-YouTube or missing videos —
 * callers layer their own "broken thumbnail" failure set on top of this.
 */
export function youtubeThumbUrl(
  videoId: string | null | undefined,
  platform: string | null | undefined,
  frame = 0
): string | null {
  if (!videoId || platform !== 'youtube') return null;
  return frame > 0
    ? `https://i.ytimg.com/vi/${videoId}/mq${frame}.jpg`
    : `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`;
}
