import { useEffect } from 'react';
import { useEditor } from '../store/editor';
import { saveCurrent } from '../controller';

const AUTOSAVE_MS = 60_000;

// Periodic auto-save + a browser warning when closing/reloading with unsaved edits.
export function useAutosave() {
  useEffect(() => {
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      if (useEditor.getState().dirty) {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', onBeforeUnload);

    const timer = window.setInterval(() => {
      if (useEditor.getState().dirty) void saveCurrent();
    }, AUTOSAVE_MS);

    return () => {
      window.removeEventListener('beforeunload', onBeforeUnload);
      window.clearInterval(timer);
    };
  }, []);
}
