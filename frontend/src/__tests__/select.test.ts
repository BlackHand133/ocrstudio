import { describe, it, expect } from 'vitest';
import { normRect, boxIntersectsRect } from '../lib/select';

const quad = (x0: number, y0: number, x1: number, y1: number): number[][] => [
  [x0, y0],
  [x1, y0],
  [x1, y1],
  [x0, y1],
];

describe('normRect', () => {
  it('normalizes corners regardless of drag direction', () => {
    expect(normRect(50, 60, 10, 20)).toEqual({ x0: 10, y0: 20, x1: 50, y1: 60 });
    expect(normRect(0, 0, 5, 5)).toEqual({ x0: 0, y0: 0, x1: 5, y1: 5 });
  });
});

describe('boxIntersectsRect', () => {
  const r = { x0: 0, y0: 0, x1: 100, y1: 100 };
  it('detects inside / partial / outside', () => {
    expect(boxIntersectsRect(quad(10, 10, 50, 50), r)).toBe(true); // fully inside
    expect(boxIntersectsRect(quad(90, 90, 150, 150), r)).toBe(true); // partial overlap
    expect(boxIntersectsRect(quad(200, 200, 250, 250), r)).toBe(false); // outside
    expect(boxIntersectsRect([], r)).toBe(false); // empty
  });
});
