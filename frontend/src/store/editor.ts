import { create } from 'zustand';
import type { Annotation, Tool } from '../types';

const MAX_HISTORY = 50;
const PASTE_OFFSET = 12;

function clone(anns: Annotation[]): Annotation[] {
  return anns.map((a) => ({ ...a, points: a.points.map((p) => [...p]) }));
}

function offsetAnn(a: Annotation, dx: number, dy: number): Annotation {
  return { ...a, points: a.points.map(([x, y]) => [x + dx, y + dy]) };
}

function topLeft(a: Annotation): [number, number] {
  let mx = Infinity;
  let my = Infinity;
  for (const p of a.points) {
    if (p[0] < mx) mx = p[0];
    if (p[1] < my) my = p[1];
  }
  return [mx, my];
}

function boxHeight(a: Annotation): number {
  let lo = Infinity;
  let hi = -Infinity;
  for (const p of a.points) {
    if (p[1] < lo) lo = p[1];
    if (p[1] > hi) hi = p[1];
  }
  return hi > lo ? hi - lo : 0;
}

interface EditorState {
  workspaceId: string | null;
  imageKey: string | null;
  imageKeys: string[]; // ordered (filtered) list for keyboard navigation
  rotation: number;

  tool: Tool;
  stickyTool: boolean; // keep the draw tool active after each shape
  annotations: Annotation[];
  selected: number | null; // primary selection (gets corner anchors)
  marked: Set<number>; // additional multi-selection (Shift-click / select-all)
  dirty: boolean;
  editSeq: number; // bump to request focusing the selected transcription editor

  clipboard: Annotation[];

  // image keys excluded from export (per workspace, session-scoped)
  excluded: Set<string>;

  // censor/mask UI prefs
  maskColor: string;
  maskMode: string;
  maskPreview: boolean;

  past: Annotation[][];
  future: Annotation[][];

  // workspace / image lifecycle
  setWorkspace: (id: string | null) => void;
  setImageKeys: (keys: string[]) => void;
  toggleExcluded: (key: string) => void;
  setExcluded: (keys: string[]) => void;
  loadImage: (key: string, annotations: Annotation[], rotation: number) => void;
  closeImage: () => void;
  markSaved: () => void;
  setRotation: (angle: number) => void;
  setMaskColor: (color: string) => void;
  setMaskMode: (mode: string) => void;
  toggleMaskPreview: () => void;

  // tools / selection
  setTool: (tool: Tool) => void;
  toggleSticky: () => void;
  select: (index: number | null) => void;
  toggleMark: (index: number) => void;
  selectAll: () => void;
  selectMany: (indices: number[]) => void;
  clearMarks: () => void;
  selectAdjacent: (delta: number, focusEditor?: boolean) => void;
  requestEdit: () => void;

  // mutations (history-aware)
  snapshot: () => void;
  resetHistory: () => void;
  setAnnotations: (next: Annotation[], recordHistory?: boolean) => void;
  addAnnotation: (a: Annotation) => void;
  updateAnnotation: (index: number, patch: Partial<Annotation>) => void;
  deleteSelected: () => void;
  nudgeSelected: (dx: number, dy: number) => void;
  sortByReadingOrder: () => void;
  insertVertex: (index: number, at: number, point: number[]) => void;
  deleteVertex: (index: number, vertex: number) => void;
  convertToMask: (index: number, color: string, mode: string) => void;
  convertToText: (index: number) => void;

  // clipboard
  copySelected: () => void;
  cutSelected: () => void;
  paste: () => void;
  duplicateSelected: () => void;

  undo: () => void;
  redo: () => void;
}

export const useEditor = create<EditorState>((set, get) => {
  // Indices in the current selection (primary + marked), clamped to bounds.
  const selectionIndices = (): number[] => {
    const { selected, marked, annotations } = get();
    const s = new Set<number>(marked);
    if (selected !== null) s.add(selected);
    return [...s].filter((i) => i >= 0 && i < annotations.length).sort((a, b) => a - b);
  };

  const NO_MARKS = (): Set<number> => new Set<number>();

  return {
    workspaceId: null,
    imageKey: null,
    imageKeys: [],
    rotation: 0,

    tool: 'select',
    stickyTool: false,
    annotations: [],
    selected: null,
    marked: NO_MARKS(),
    dirty: false,
    editSeq: 0,
    clipboard: [],
    excluded: new Set<string>(),
    maskColor: '#000000',
    maskMode: 'solid',
    maskPreview: false,

    past: [],
    future: [],

    setWorkspace: (id) =>
      set({
        workspaceId: id,
        imageKey: null,
        imageKeys: [],
        annotations: [],
        selected: null,
        marked: NO_MARKS(),
        dirty: false,
        excluded: new Set<string>(),
        past: [],
        future: [],
      }),

    setImageKeys: (keys) => set({ imageKeys: keys }),

    toggleExcluded: (key) =>
      set((s) => {
        const next = new Set(s.excluded);
        if (next.has(key)) next.delete(key);
        else next.add(key);
        return { excluded: next };
      }),

    setExcluded: (keys) => set({ excluded: new Set(keys) }),

    loadImage: (key, annotations, rotation) =>
      set({
        imageKey: key,
        rotation,
        annotations: clone(annotations),
        selected: null,
        marked: NO_MARKS(),
        dirty: false,
        past: [],
        future: [],
      }),

    closeImage: () =>
      set({
        imageKey: null,
        annotations: [],
        selected: null,
        marked: NO_MARKS(),
        dirty: false,
        past: [],
        future: [],
      }),

    markSaved: () => set({ dirty: false }),

    setRotation: (angle) => set({ rotation: ((Math.round(angle) % 360) + 360) % 360, dirty: true }),

    setMaskColor: (color) => set({ maskColor: color }),
    setMaskMode: (mode) => set({ maskMode: mode }),
    toggleMaskPreview: () => set((s) => ({ maskPreview: !s.maskPreview })),

    setTool: (tool) => set({ tool }),
    toggleSticky: () => set((s) => ({ stickyTool: !s.stickyTool })),

    // Selection invariant: `marked` is the full selection set and the primary
    // `selected` (which gets the corner anchors) is always a member of it, or null.
    select: (index) =>
      set({ selected: index, marked: index === null ? NO_MARKS() : new Set([index]) }),

    toggleMark: (index) =>
      set((s) => {
        const next = new Set(s.marked);
        let selected = s.selected;
        if (next.has(index)) {
          next.delete(index);
          if (selected === index) selected = next.size ? [...next][next.size - 1] : null;
        } else {
          next.add(index);
          selected = index;
        }
        return { marked: next, selected };
      }),

    selectAll: () =>
      set((s) => {
        const n = s.annotations.length;
        if (n === 0) return {};
        const all = new Set<number>();
        for (let i = 0; i < n; i++) all.add(i);
        return { marked: all, selected: n - 1 };
      }),

    selectMany: (indices) =>
      set((s) => {
        const valid = indices.filter((i) => i >= 0 && i < s.annotations.length);
        const marked = new Set<number>(valid);
        return { marked, selected: valid.length ? valid[valid.length - 1] : null };
      }),

    clearMarks: () => set({ marked: NO_MARKS() }),

    selectAdjacent: (delta, focusEditor = false) =>
      set((s) => {
        const n = s.annotations.length;
        if (n === 0) return {};
        const cur = s.selected ?? (delta > 0 ? -1 : 0);
        const next = (((cur + delta) % n) + n) % n;
        return {
          selected: next,
          marked: new Set([next]),
          editSeq: focusEditor ? s.editSeq + 1 : s.editSeq,
        };
      }),

    requestEdit: () => set((s) => ({ editSeq: s.editSeq + 1 })),

    snapshot: () => {
      const { annotations, past } = get();
      const next = [...past, clone(annotations)].slice(-MAX_HISTORY);
      set({ past: next, future: [] });
    },

    resetHistory: () => set({ past: [], future: [] }),

    setAnnotations: (next, recordHistory = true) => {
      if (recordHistory) get().snapshot();
      // Clamp selection + marks so they can never point past the end of the array
      // (e.g. after deleting an annotation that precedes the selected one).
      const sel = get().selected;
      const marked = new Set([...get().marked].filter((i) => i < next.length));
      set({
        annotations: next,
        dirty: true,
        selected: sel !== null && sel >= next.length ? null : sel,
        marked,
      });
    },

    addAnnotation: (a) => {
      get().snapshot();
      const annotations = [...get().annotations, a];
      const last = annotations.length - 1;
      set({ annotations, selected: last, marked: new Set([last]), dirty: true });
    },

    updateAnnotation: (index, patch) => {
      get().snapshot();
      const annotations = get().annotations.map((a, i) => (i === index ? { ...a, ...patch } : a));
      set({ annotations, dirty: true });
    },

    deleteSelected: () => {
      const idx = selectionIndices();
      if (idx.length === 0) return;
      get().snapshot();
      const drop = new Set(idx);
      set({
        annotations: get().annotations.filter((_, i) => !drop.has(i)),
        selected: null,
        marked: NO_MARKS(),
        dirty: true,
      });
    },

    nudgeSelected: (dx, dy) => {
      const idx = selectionIndices();
      if (idx.length === 0) return;
      get().snapshot();
      const move = new Set(idx);
      set({
        annotations: get().annotations.map((a, i) => (move.has(i) ? offsetAnn(a, dx, dy) : a)),
        dirty: true,
      });
    },

    sortByReadingOrder: () => {
      const anns = get().annotations;
      if (anns.length < 2) return;
      get().snapshot();
      const heights = anns
        .map(boxHeight)
        .filter((h) => h > 0)
        .sort((a, b) => a - b);
      const med = heights.length ? heights[Math.floor(heights.length / 2)] : 0;
      const band = Math.max(8, med * 0.6);
      const sorted = [...anns].sort((a, b) => {
        const [ax, ay] = topLeft(a);
        const [bx, by] = topLeft(b);
        const ra = Math.round(ay / band);
        const rb = Math.round(by / band);
        if (ra !== rb) return ra - rb;
        return ax - bx;
      });
      set({ annotations: sorted, selected: null, marked: NO_MARKS(), dirty: true });
    },

    insertVertex: (index, at, point) => {
      get().snapshot();
      set({
        annotations: get().annotations.map((a, i) => {
          if (i !== index) return a;
          const pts = a.points.map((p) => [...p]);
          pts.splice(at, 0, [point[0], point[1]]);
          return { ...a, points: pts };
        }),
        dirty: true,
      });
    },

    deleteVertex: (index, vertex) => {
      const a = get().annotations[index];
      if (!a || a.points.length <= 3) return;
      get().snapshot();
      set({
        annotations: get().annotations.map((it, i) =>
          i === index ? { ...it, points: it.points.filter((_, vi) => vi !== vertex) } : it,
        ),
        dirty: true,
      });
    },

    convertToMask: (index, color, mode) => {
      const a = get().annotations[index];
      if (!a) return;
      get().snapshot();
      set({
        annotations: get().annotations.map((it, i) =>
          i === index
            ? { ...it, shape: 'Mask', transcription: '###', mask_color: color, mask_mode: mode }
            : it,
        ),
        dirty: true,
      });
    },

    convertToText: (index) => {
      const a = get().annotations[index];
      if (!a) return;
      get().snapshot();
      set({
        annotations: get().annotations.map((it, i) =>
          i === index
            ? {
                ...it,
                shape: it.points.length === 4 ? 'Quad' : 'Polygon',
                transcription: it.transcription === '###' ? '' : it.transcription,
                mask_color: null,
                mask_mode: null,
              }
            : it,
        ),
        dirty: true,
      });
    },

    copySelected: () => {
      const idx = selectionIndices();
      if (idx.length === 0) return;
      const anns = get().annotations;
      set({ clipboard: clone(idx.map((i) => anns[i])) });
    },

    cutSelected: () => {
      const idx = selectionIndices();
      if (idx.length === 0) return;
      const anns = get().annotations;
      get().snapshot();
      const drop = new Set(idx);
      set({
        clipboard: clone(idx.map((i) => anns[i])),
        annotations: anns.filter((_, i) => !drop.has(i)),
        selected: null,
        marked: NO_MARKS(),
        dirty: true,
      });
    },

    paste: () => {
      const { clipboard, annotations } = get();
      if (clipboard.length === 0) return;
      get().snapshot();
      const add = clone(clipboard).map((a) => offsetAnn(a, PASTE_OFFSET, PASTE_OFFSET));
      const next = [...annotations, ...add];
      const marked = new Set<number>();
      for (let i = annotations.length; i < next.length; i++) marked.add(i);
      set({ annotations: next, selected: next.length - 1, marked, dirty: true });
    },

    duplicateSelected: () => {
      const idx = selectionIndices();
      if (idx.length === 0) return;
      const anns = get().annotations;
      get().snapshot();
      const add = clone(idx.map((i) => anns[i])).map((a) => offsetAnn(a, PASTE_OFFSET, PASTE_OFFSET));
      const next = [...anns, ...add];
      const marked = new Set<number>();
      for (let i = anns.length; i < next.length; i++) marked.add(i);
      set({ annotations: next, selected: next.length - 1, marked, dirty: true });
    },

    undo: () => {
      const { past, annotations, future } = get();
      if (past.length === 0) return;
      const prev = past[past.length - 1];
      set({
        annotations: prev,
        past: past.slice(0, -1),
        future: [...future, clone(annotations)].slice(-MAX_HISTORY),
        selected: null,
        marked: NO_MARKS(),
        dirty: true,
      });
    },

    redo: () => {
      const { future, annotations, past } = get();
      if (future.length === 0) return;
      const nxt = future[future.length - 1];
      set({
        annotations: nxt,
        future: future.slice(0, -1),
        past: [...past, clone(annotations)].slice(-MAX_HISTORY),
        selected: null,
        marked: NO_MARKS(),
        dirty: true,
      });
    },
  };
});
