import { describe, it, expect } from 'vitest';
import { sectionMarkers } from './section-markers.utils';
import { VideoSegment } from '../../models/video.model';

const seg = (id: number, label: string, startTime: number, endTime?: number): VideoSegment =>
  ({ id, label, startTime, endTime } as VideoSegment);

describe('sectionMarkers', () => {
  it('places each section at its share of the duration', () => {
    const markers = sectionMarkers([seg(1, 'Intro', 0), seg(2, 'Drill', 50)], 100, 0);
    expect(markers.map(m => m.startPct)).toEqual([0, 50]);
    expect(markers.map(m => m.label)).toEqual(['Intro', 'Drill']);
  });

  it('returns nothing until the player reports a duration', () => {
    expect(sectionMarkers([seg(1, 'Intro', 10)], 0, 0)).toEqual([]);
  });

  it('returns nothing when the video has no sections', () => {
    expect(sectionMarkers([], 120, 5)).toEqual([]);
  });

  it('marks the section containing the playhead as current', () => {
    const markers = sectionMarkers([seg(1, 'A', 0, 30), seg(2, 'B', 30, 60)], 60, 42);
    expect(markers.map(m => m.current)).toEqual([false, true]);
  });

  it('treats a section as running up to, but not including, its end', () => {
    const markers = sectionMarkers([seg(1, 'A', 0, 30), seg(2, 'B', 30, 60)], 60, 30);
    expect(markers.map(m => m.current)).toEqual([false, true]);
  });

  it('runs an open-ended section to the start of the next one', () => {
    const markers = sectionMarkers([seg(1, 'A', 0), seg(2, 'B', 40)], 100, 39);
    expect(markers[0].current).toBe(true);
    expect(markers[1].current).toBe(false);
  });

  it('runs a trailing open-ended section to the end of the video', () => {
    const markers = sectionMarkers([seg(1, 'A', 0, 40), seg(2, 'Last', 40)], 100, 95);
    expect(markers[1].current).toBe(true);
  });

  it('sorts before filling gaps, so an out-of-order list still spans correctly', () => {
    // Unsorted input: 'B' is listed first but starts later. Without the sort, 'A' would
    // take B's start as its end and never be current.
    const markers = sectionMarkers([seg(2, 'B', 40), seg(1, 'A', 0)], 100, 10);
    expect(markers.map(m => m.label)).toEqual(['A', 'B']);
    expect(markers[0].current).toBe(true);
  });

  it('clamps a section that starts past the end of the video', () => {
    // Stale segment on a video whose bounds were later shortened.
    expect(sectionMarkers([seg(1, 'Stray', 500)], 100, 0)[0].startPct).toBe(100);
  });

  it('leaves the playhead in no section when it sits in a gap', () => {
    const markers = sectionMarkers([seg(1, 'A', 0, 10), seg(2, 'B', 50, 60)], 100, 30);
    expect(markers.every(m => !m.current)).toBe(true);
  });
});
