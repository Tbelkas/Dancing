import { describe, it, expect } from 'vitest';
import { introSkipTarget } from './intro-skip.utils';
import { VideoSegment } from '../../models/video.model';

const seg = (id: number, label: string, startTime: number, endTime?: number): VideoSegment =>
  ({ id, label, startTime, endTime } as VideoSegment);

describe('introSkipTarget', () => {
  it('opens at the end of a leading intro', () => {
    expect(introSkipTarget([seg(1, 'Intro', 0, 42), seg(2, 'Breakdown', 42, 300)])).toBe(42);
  });

  it('accepts the intro labels the chipping scripts produce', () => {
    for (const label of ['Intro', 'intro', ' Intro ', 'Intro:', 'Introduction', 'Welcome']) {
      expect(introSkipTarget([seg(1, label, 0, 30), seg(2, 'Drill', 30, 200)])).toBe(30);
    }
  });

  it('leaves a section alone when preamble is not all it holds', () => {
    // "Intro to the six-step" is the teaching; "Intro & basic step" teaches after the
    // greeting. Skipping either would drop content.
    for (const label of ['Intro to the six-step', 'Intro & basic step']) {
      expect(introSkipTarget([seg(1, label, 0, 60), seg(2, 'Drill', 60, 200)])).toBeNull();
    }
  });

  it('skips nothing when the video opens on real content', () => {
    expect(introSkipTarget([seg(1, 'Basic step', 0, 40), seg(2, 'Drill', 40, 200)])).toBeNull();
  });

  it('skips nothing when the video has no sections', () => {
    expect(introSkipTarget([])).toBeNull();
  });

  it('runs an open-ended intro to the start of the next section', () => {
    expect(introSkipTarget([seg(1, 'Intro', 0), seg(2, 'Drill', 25)])).toBe(25);
  });

  it('leaves a trailing open-ended intro alone, its end being unknown', () => {
    expect(introSkipTarget([seg(1, 'Intro', 0)])).toBeNull();
  });

  it('sorts first, so an out-of-order list still finds the opening section', () => {
    expect(introSkipTarget([seg(2, 'Drill', 30, 200), seg(1, 'Intro', 0, 30)])).toBe(30);
  });

  it('refuses a mislabelled intro that swallows most of the video', () => {
    // Real data holds a few "Intro" chips running eight minutes.
    expect(introSkipTarget([seg(1, 'Intro', 0, 495), seg(2, 'Drill', 495, 900)])).toBeNull();
  });

  it('measures the intro of a dance cut later in the source video', () => {
    // Dance starts at 5:00; the intro chip covering that point ends at 5:20.
    const segments = [seg(1, 'Intro', 0, 40), seg(2, 'First dance', 40, 300), seg(3, 'Intro', 300, 320), seg(4, 'Second dance', 320, 600)];
    expect(introSkipTarget(segments, 300, 600)).toBe(320);
  });

  it('ignores an intro at 0:00 when the dance starts after it', () => {
    expect(introSkipTarget([seg(1, 'Intro', 0, 40), seg(2, 'Drill', 40, 300)], 40, 300)).toBeNull();
  });

  it('refuses a skip that would land at or past the end of the dance', () => {
    expect(introSkipTarget([seg(1, 'Intro', 0, 58)], 0, 60)).toBeNull();
  });
});
