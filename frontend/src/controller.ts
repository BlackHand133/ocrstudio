// Imperative orchestration shared by components — uses the Zustand store and
// the shared QueryClient outside of React render.

import { notifications } from '@mantine/notifications';
import { api } from './api/client';
import { queryClient } from './api/queryClient';
import { useEditor } from './store/editor';
import { translate, useI18n } from './i18n';

const tr = (key: string, params?: Record<string, string | number>) =>
  translate(useI18n.getState().lang, key, params);

export async function saveCurrent(): Promise<void> {
  const { workspaceId, imageKey, annotations, rotation, dirty } = useEditor.getState();
  if (!workspaceId || !imageKey || !dirty) return;
  await api.saveAnnotations(workspaceId, imageKey, annotations, rotation);
  useEditor.getState().markSaved();
  queryClient.invalidateQueries({ queryKey: ['images', workspaceId] });
}

export async function openImage(key: string): Promise<void> {
  const st = useEditor.getState();
  if (!st.workspaceId || st.imageKey === key) return;
  try {
    await saveCurrent();
  } catch (e) {
    notifications.show({ color: 'red', title: 'Save failed', message: (e as Error).message });
  }
  try {
    const data = await api.getAnnotations(st.workspaceId, key);
    useEditor.getState().loadImage(key, data.annotations, data.rotation);
  } catch (e) {
    notifications.show({ color: 'red', title: 'Load failed', message: (e as Error).message });
  }
}

// Move to the previous/next image in the (filtered) list, auto-saving first.
export async function gotoAdjacentImage(delta: number): Promise<void> {
  const { imageKeys, imageKey } = useEditor.getState();
  if (imageKeys.length === 0) return;
  const idx = imageKey ? imageKeys.indexOf(imageKey) : -1;
  const ni =
    idx < 0
      ? delta > 0
        ? 0
        : imageKeys.length - 1
      : Math.min(imageKeys.length - 1, Math.max(0, idx + delta));
  const key = imageKeys[ni];
  if (key && key !== imageKey) await openImage(key);
}

// Append a copy of the previous image's annotations onto the current image —
// handy when consecutive pages share the same layout.
export async function copyFromPrevImage(): Promise<void> {
  const { imageKeys, imageKey, workspaceId } = useEditor.getState();
  if (!workspaceId || !imageKey) return;
  const idx = imageKeys.indexOf(imageKey);
  if (idx <= 0) {
    notifications.show({ message: tr('copy.noPrev') });
    return;
  }
  const prev = imageKeys[idx - 1];
  try {
    const data = await api.getAnnotations(workspaceId, prev);
    if (!data.annotations.length) {
      notifications.show({ message: tr('copy.prevEmpty') });
      return;
    }
    const st = useEditor.getState();
    const copies = data.annotations.map((a) => ({ ...a, points: a.points.map((p) => [...p]) }));
    st.setAnnotations([...st.annotations, ...copies]);
    notifications.show({
      color: 'green',
      message: tr('copy.copied', { n: copies.length, k: prev }),
    });
  } catch (e) {
    notifications.show({ color: 'red', message: (e as Error).message });
  }
}

export async function openWorkspace(id: string): Promise<void> {
  try {
    await saveCurrent();
  } catch {
    /* ignore — switching workspace */
  }
  useEditor.getState().setWorkspace(id);
  queryClient.invalidateQueries({ queryKey: ['images', id] });
}

export async function reloadCurrentImage(): Promise<void> {
  const { workspaceId, imageKey } = useEditor.getState();
  if (!workspaceId || !imageKey) return;
  const data = await api.getAnnotations(workspaceId, imageKey);
  if (useEditor.getState().imageKey !== imageKey) return; // user navigated during fetch
  useEditor.getState().loadImage(imageKey, data.annotations, data.rotation);
}

export async function runBatchDetect(
  scope: 'empty' | 'all' | 'selected',
  overwrite = false,
): Promise<void> {
  const { workspaceId } = useEditor.getState();
  if (!workspaceId) return;

  let start: { job_id: string; total: number };
  try {
    start = await api.detectBatch(workspaceId, { scope, overwrite });
  } catch (e) {
    notifications.show({ color: 'red', title: 'OCR failed', message: (e as Error).message });
    return;
  }
  if (start.total === 0) {
    notifications.show({ message: 'No images to detect.' });
    return;
  }

  const nid = notifications.show({
    loading: true,
    title: 'Batch OCR',
    message: `0 / ${start.total}`,
    autoClose: false,
    withCloseButton: false,
  });

  const poll = async () => {
    try {
      const job = await api.getJob(start.job_id);
      if (job.status === 'running') {
        notifications.update({
          id: nid,
          loading: true,
          title: 'Batch OCR',
          message: `${job.done} / ${job.total}`,
          autoClose: false,
          withCloseButton: false,
        });
        setTimeout(poll, 800);
        return;
      }
      if (job.status === 'done') {
        notifications.update({
          id: nid,
          loading: false,
          color: 'green',
          title: 'Batch OCR complete',
          message: `Processed ${job.result?.processed ?? job.done} image(s)`,
          autoClose: 3000,
          withCloseButton: true,
        });
        queryClient.invalidateQueries({ queryKey: ['images', workspaceId] });
        if (!useEditor.getState().dirty) await reloadCurrentImage();
      } else {
        notifications.update({
          id: nid,
          loading: false,
          color: 'red',
          title: 'Batch OCR failed',
          message: job.error || 'error',
          autoClose: 6000,
          withCloseButton: true,
        });
      }
    } catch (e) {
      notifications.update({
        id: nid,
        loading: false,
        color: 'red',
        message: (e as Error).message,
        autoClose: 6000,
        withCloseButton: true,
      });
    }
  };
  setTimeout(poll, 600);
}

export async function switchToVersion(name: string): Promise<void> {
  const { workspaceId } = useEditor.getState();
  if (!workspaceId) return;
  try {
    await saveCurrent();
  } catch {
    /* ignore */
  }
  await api.switchVersion(workspaceId, name);
  queryClient.invalidateQueries({ queryKey: ['workspace', workspaceId] });
  queryClient.invalidateQueries({ queryKey: ['versions', workspaceId] });
  queryClient.invalidateQueries({ queryKey: ['images', workspaceId] });
  if (!useEditor.getState().dirty) await reloadCurrentImage();
}

export async function runDetect(): Promise<void> {
  const { workspaceId, imageKey } = useEditor.getState();
  if (!workspaceId || !imageKey) return;
  const id = notifications.show({
    loading: true,
    message: 'Running OCR…',
    autoClose: false,
    withCloseButton: false,
  });
  try {
    const res = await api.detect(workspaceId, imageKey);
    // Re-read fresh state after the await: only merge if the user is still on
    // the same image, and append to the *current* boxes (not a stale snapshot).
    const st = useEditor.getState();
    if (st.imageKey === imageKey) {
      st.setAnnotations([...st.annotations, ...res.annotations]);
    }
    notifications.update({
      id,
      loading: false,
      color: 'green',
      message: `Detected ${res.annotations.length} text region(s)`,
      autoClose: 2500,
    });
  } catch (e) {
    notifications.update({
      id,
      loading: false,
      color: 'red',
      title: 'OCR failed',
      message: (e as Error).message,
      autoClose: 5000,
    });
  }
}
