import type { Annotation } from '../types';

// Matches the backend is_mask_item(): a "Mask"-family shape OR the ### marker.
// Desktop masks use shapes like "MaskQuad"/"MaskPolygon", so check substring.
export function isMask(a: Annotation): boolean {
  return (a.shape || '').toLowerCase().includes('mask') || a.transcription === '###';
}

export const MASK_COLORS = ['#000000', '#ffffff', '#808080', '#212529', '#fa5252', '#fab005'];

export const MASK_MODES = ['solid', 'blur', 'pixelate'] as const;
export type MaskMode = (typeof MASK_MODES)[number];

export function hexToRgba(hex: string, alpha: number): string {
  const h = (hex || '#000000').replace('#', '');
  const r = parseInt(h.slice(0, 2), 16) || 0;
  const g = parseInt(h.slice(2, 4), 16) || 0;
  const b = parseInt(h.slice(4, 6), 16) || 0;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
