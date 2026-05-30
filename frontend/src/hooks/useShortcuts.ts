import { useEffect } from 'react';
import { useEditor } from '../store/editor';
import { gotoAdjacentImage, saveCurrent } from '../controller';

// Global keyboard shortcuts. All canvas/list key handling lives here so there is
// a single source of truth and no double-handling between components.
export function useShortcuts() {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const tag = target?.tagName;
      const typing = !!target && (tag === 'INPUT' || tag === 'TEXTAREA' || target.isContentEditable);
      const inTextarea = tag === 'TEXTAREA';
      const st = useEditor.getState();
      const ctrl = e.ctrlKey || e.metaKey;
      const k = e.key.toLowerCase();

      // ---- global (work even while typing) ----
      if (ctrl && k === 's') {
        e.preventDefault();
        void saveCurrent();
        return;
      }
      if (ctrl && k === 'z') {
        e.preventDefault();
        st.undo();
        return;
      }
      if (ctrl && k === 'y') {
        e.preventDefault();
        st.redo();
        return;
      }

      // Tab / Shift+Tab cycles boxes and focuses the transcription editor — works
      // while editing text so the loop is type → Tab → type → Tab.
      if (e.key === 'Tab' && st.imageKey && st.annotations.length > 0 && (!typing || inTextarea)) {
        e.preventDefault();
        st.selectAdjacent(e.shiftKey ? -1 : 1, true);
        return;
      }

      if (typing) return;

      // ---- clipboard / selection (Ctrl) ----
      if (ctrl && k === 'a') {
        e.preventDefault();
        st.selectAll();
        return;
      }
      if (ctrl && k === 'c') {
        e.preventDefault();
        st.copySelected();
        return;
      }
      if (ctrl && k === 'x') {
        e.preventDefault();
        st.cutSelected();
        return;
      }
      if (ctrl && k === 'v') {
        e.preventDefault();
        st.paste();
        return;
      }
      if (ctrl && k === 'd') {
        e.preventDefault();
        st.duplicateSelected();
        return;
      }
      if (ctrl) return; // leave other Ctrl combos to the browser

      // ---- delete ----
      if (e.key === 'Delete' || e.key === 'Backspace') {
        e.preventDefault();
        st.deleteSelected();
        return;
      }

      // ---- arrows: nudge selection if any, else navigate images ----
      if (e.key.startsWith('Arrow')) {
        const hasSel = st.selected !== null || st.marked.size > 0;
        if (hasSel) {
          e.preventDefault();
          const d = e.shiftKey ? 10 : 1;
          if (e.key === 'ArrowUp') st.nudgeSelected(0, -d);
          else if (e.key === 'ArrowDown') st.nudgeSelected(0, d);
          else if (e.key === 'ArrowLeft') st.nudgeSelected(-d, 0);
          else if (e.key === 'ArrowRight') st.nudgeSelected(d, 0);
          return;
        }
        if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
          e.preventDefault();
          void gotoAdjacentImage(e.key === 'ArrowDown' ? 1 : -1);
        }
        return;
      }
      if (e.key === 'PageDown') {
        e.preventDefault();
        void gotoAdjacentImage(1);
        return;
      }
      if (e.key === 'PageUp') {
        e.preventDefault();
        void gotoAdjacentImage(-1);
        return;
      }

      // ---- tools ----
      if (k === 'd' || k === 'q') st.setTool('quad');
      else if (k === 'p') st.setTool('polygon');
      else if (k === 'm') st.setTool('mask');
      else if (k === 'v') st.setTool('select');
      else if (e.key === 'Escape') {
        st.setTool('select');
        st.select(null);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);
}
