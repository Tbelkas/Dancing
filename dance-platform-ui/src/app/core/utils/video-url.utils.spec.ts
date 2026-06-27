import { describe, it, expect } from 'vitest';
import { parseVideoUrl, parseTimeSecs, formatTimeSecs } from './video-url.utils';

describe('parseVideoUrl', () => {
  it('parses a YouTube watch URL', () => {
    expect(parseVideoUrl('https://www.youtube.com/watch?v=UTFZ9AR1gUQ'))
      .toEqual({ platform: 'youtube', videoId: 'UTFZ9AR1gUQ' });
  });

  it('parses youtu.be short links', () => {
    expect(parseVideoUrl('https://youtu.be/UTFZ9AR1gUQ'))
      .toEqual({ platform: 'youtube', videoId: 'UTFZ9AR1gUQ' });
  });

  it('parses /shorts/ links', () => {
    expect(parseVideoUrl('https://www.youtube.com/shorts/abcdefghijk')?.videoId).toBe('abcdefghijk');
  });

  it('accepts a bare 11-char id as YouTube', () => {
    expect(parseVideoUrl('UTFZ9AR1gUQ')).toEqual({ platform: 'youtube', videoId: 'UTFZ9AR1gUQ' });
  });

  it('parses TikTok video URLs', () => {
    expect(parseVideoUrl('https://www.tiktok.com/@user/video/1234567890'))
      .toEqual({ platform: 'tiktok', videoId: '1234567890' });
  });

  it('parses Instagram reels', () => {
    expect(parseVideoUrl('https://www.instagram.com/reel/AbC123/')?.platform).toBe('instagram');
  });

  it('rejects unrecognized URLs', () => {
    expect(parseVideoUrl('https://example.com/whatever')).toBeNull();
    expect(parseVideoUrl('')).toBeNull();
  });
});

describe('parseTimeSecs', () => {
  it('parses m:ss', () => expect(parseTimeSecs('2:30')).toBe(150));
  it('parses bare seconds', () => expect(parseTimeSecs('90')).toBe(90));
  it('returns undefined for blank', () => expect(parseTimeSecs('  ')).toBeUndefined());
  it('returns undefined for garbage', () => expect(parseTimeSecs('abc')).toBeUndefined());
});

describe('formatTimeSecs', () => {
  it('formats with zero-padded seconds', () => expect(formatTimeSecs(150)).toBe('2:30'));
  it('pads single-digit seconds', () => expect(formatTimeSecs(65)).toBe('1:05'));
});
