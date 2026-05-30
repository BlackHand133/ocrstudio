import { describe, it, expect, beforeEach } from 'vitest';
import { useEditor } from '../store/editor';
import { isMask } from '../lib/masks';
import type { Annotation } from '../types';

const box = (x: number): Annotation => ({
  points: [
    [x, x],
    [x + 1, x],
    [x + 1, x + 1],
    [x, x + 1],
  ],
  transcription: '',
  difficult: false,
  shape: 'Quad',
});

const at = (x: number, y: number, text: string): Annotation => ({
  points: [
    [x, y],
    [x + 10, y],
    [x + 10, y + 10],
    [x, y + 10],
  ],
  transcription: text,
  difficult: false,
  shape: 'Quad',
});

beforeEach(() => {
  useEditor.getState().loadImage('k', [], 0);
});

describe('editor store', () => {
  it('adds an annotation and selects it', () => {
    useEditor.getState().addAnnotation(box(0));
    expect(useEditor.getState().annotations).toHaveLength(1);
    expect(useEditor.getState().selected).toBe(0);
  });

  it('undo / redo round-trips', () => {
    useEditor.getState().addAnnotation(box(0));
    useEditor.getState().addAnnotation(box(1));
    expect(useEditor.getState().annotations).toHaveLength(2);
    useEditor.getState().undo();
    expect(useEditor.getState().annotations).toHaveLength(1);
    useEditor.getState().redo();
    expect(useEditor.getState().annotations).toHaveLength(2);
  });

  it('clamps selection when the array shrinks below it', () => {
    const s = useEditor.getState();
    s.addAnnotation(box(0));
    s.addAnnotation(box(1));
    s.addAnnotation(box(2));
    s.select(2);
    s.setAnnotations(useEditor.getState().annotations.slice(1)); // drop index 0 -> len 2
    expect(useEditor.getState().selected).toBeNull();
  });

  it('normalizes rotation to [0,360)', () => {
    useEditor.getState().setRotation(450);
    expect(useEditor.getState().rotation).toBe(90);
    useEditor.getState().setRotation(-90);
    expect(useEditor.getState().rotation).toBe(270);
  });
});

describe('editor store — labeling ops', () => {
  it('nudges the selected box', () => {
    useEditor.getState().addAnnotation(box(0));
    useEditor.getState().select(0);
    useEditor.getState().nudgeSelected(5, -3);
    expect(useEditor.getState().annotations[0].points[0]).toEqual([5, -3]);
  });

  it('copies and pastes with an offset', () => {
    useEditor.getState().addAnnotation(box(0));
    useEditor.getState().select(0);
    useEditor.getState().copySelected();
    useEditor.getState().paste();
    const anns = useEditor.getState().annotations;
    expect(anns).toHaveLength(2);
    expect(anns[1].points[0][0]).toBe(anns[0].points[0][0] + 12);
    expect(useEditor.getState().selected).toBe(1);
  });

  it('duplicates the selection', () => {
    useEditor.getState().addAnnotation(box(0));
    useEditor.getState().select(0);
    useEditor.getState().duplicateSelected();
    expect(useEditor.getState().annotations).toHaveLength(2);
  });

  it('cycles the selection with wrap-around', () => {
    useEditor.getState().addAnnotation(box(0));
    useEditor.getState().addAnnotation(box(1));
    useEditor.getState().addAnnotation(box(2)); // selected = 2
    useEditor.getState().selectAdjacent(1); // wraps to 0
    expect(useEditor.getState().selected).toBe(0);
    useEditor.getState().selectAdjacent(-1); // wraps to 2
    expect(useEditor.getState().selected).toBe(2);
  });

  it('multi-selects with marks and deletes the union', () => {
    useEditor.getState().addAnnotation(box(0));
    useEditor.getState().addAnnotation(box(1));
    useEditor.getState().addAnnotation(box(2));
    useEditor.getState().select(0);
    useEditor.getState().toggleMark(2);
    useEditor.getState().deleteSelected();
    expect(useEditor.getState().annotations).toHaveLength(1); // index 1 survives
  });

  it('selects all', () => {
    useEditor.getState().addAnnotation(box(0));
    useEditor.getState().addAnnotation(box(1));
    useEditor.getState().selectAll();
    expect(useEditor.getState().marked.size).toBe(2);
    expect(useEditor.getState().selected).toBe(1);
  });

  it('selects many by index (marquee), clamping out-of-range', () => {
    useEditor.getState().addAnnotation(box(0));
    useEditor.getState().addAnnotation(box(1));
    useEditor.getState().addAnnotation(box(2));
    useEditor.getState().selectMany([0, 2]);
    expect(useEditor.getState().marked.size).toBe(2);
    expect(useEditor.getState().selected).toBe(2);
    useEditor.getState().selectMany([1, 99]); // 99 dropped
    expect(useEditor.getState().marked.size).toBe(1);
    expect(useEditor.getState().selected).toBe(1);
  });

  it('converts a box to censor and back to text', () => {
    useEditor.getState().addAnnotation(box(0));
    useEditor.getState().convertToMask(0, '#000000', 'solid');
    expect(isMask(useEditor.getState().annotations[0])).toBe(true);
    useEditor.getState().convertToText(0);
    const a = useEditor.getState().annotations[0];
    expect(isMask(a)).toBe(false);
    expect(a.shape).toBe('Quad');
  });

  it('sorts boxes by reading order (top→bottom, left→right)', () => {
    useEditor.getState().addAnnotation(at(100, 100, 'c'));
    useEditor.getState().addAnnotation(at(0, 0, 'a'));
    useEditor.getState().addAnnotation(at(50, 0, 'b'));
    useEditor.getState().sortByReadingOrder();
    expect(useEditor.getState().annotations.map((x) => x.transcription)).toEqual(['a', 'b', 'c']);
  });

  it('inserts and deletes polygon vertices', () => {
    useEditor.getState().addAnnotation({
      points: [
        [0, 0],
        [10, 0],
        [10, 10],
        [0, 10],
      ],
      transcription: '',
      difficult: false,
      shape: 'Polygon',
    });
    useEditor.getState().insertVertex(0, 1, [5, 0]);
    expect(useEditor.getState().annotations[0].points).toHaveLength(5);
    useEditor.getState().deleteVertex(0, 1);
    expect(useEditor.getState().annotations[0].points).toHaveLength(4);
    // refuses to drop below 3 points
    useEditor.getState().deleteVertex(0, 0);
    useEditor.getState().deleteVertex(0, 0);
    expect(useEditor.getState().annotations[0].points).toHaveLength(3);
  });
});
