// Geometry helpers for rubber-band (marquee) multi-selection on the canvas.

export interface Rect {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

/** Normalize two corners (any order) into a rect with x0<=x1, y0<=y1. */
export function normRect(ax: number, ay: number, bx: number, by: number): Rect {
  return {
    x0: Math.min(ax, bx),
    y0: Math.min(ay, by),
    x1: Math.max(ax, bx),
    y1: Math.max(ay, by),
  };
}

/** True if a polygon's axis-aligned bounding box overlaps the rect. */
export function boxIntersectsRect(points: number[][], r: Rect): boolean {
  if (!points.length) return false;
  let bx0 = Infinity;
  let by0 = Infinity;
  let bx1 = -Infinity;
  let by1 = -Infinity;
  for (const [x, y] of points) {
    if (x < bx0) bx0 = x;
    if (y < by0) by0 = y;
    if (x > bx1) bx1 = x;
    if (y > by1) by1 = y;
  }
  return bx0 <= r.x1 && bx1 >= r.x0 && by0 <= r.y1 && by1 >= r.y0;
}
