import { describe, it, expect } from 'vitest';
import { isMask, hexToRgba } from '../lib/masks';
import type { Annotation } from '../types';

const a = (shape: string, transcription = ''): Annotation => ({
  points: [],
  transcription,
  difficult: false,
  shape,
});

describe('isMask', () => {
  it('detects Mask-family shapes and the ### marker', () => {
    expect(isMask(a('Mask'))).toBe(true);
    expect(isMask(a('MaskQuad'))).toBe(true);
    expect(isMask(a('MaskPolygon'))).toBe(true);
    expect(isMask(a('Quad', '###'))).toBe(true);
    expect(isMask(a('Quad', 'hello'))).toBe(false);
    expect(isMask(a('Polygon'))).toBe(false);
  });
});

describe('hexToRgba', () => {
  it('converts 6-digit hex (with/without #)', () => {
    expect(hexToRgba('#000000', 0.5)).toBe('rgba(0, 0, 0, 0.5)');
    expect(hexToRgba('#ff0000', 1)).toBe('rgba(255, 0, 0, 1)');
    expect(hexToRgba('ffffff', 0.2)).toBe('rgba(255, 255, 255, 0.2)');
  });
});
