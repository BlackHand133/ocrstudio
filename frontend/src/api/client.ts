import type {
  AnnotationsResponse,
  ConfigResponse,
  ExportResult,
  ImageInfo,
  JobStatus,
  VersionInfo,
  WorkspaceDetail,
  WorkspaceSummary,
  Annotation,
} from '../types';

export interface ExportParams {
  kind: 'detection' | 'recognition';
  train: number;
  valid: number;
  test: number;
  seed?: number | null;
  image_format: 'png' | 'jpg';
  crop_method: 'bbox' | 'rotated';
  auto_orient?: boolean;
  selected_keys?: string[];
  augment?: boolean;
  aug_mode?: 'combinatorial' | 'sequential';
  augmentations?: { type: string; params: Record<string, unknown> }[];
  aug_targets?: string[];
}

async function jget<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error((await safeDetail(r)) || `GET ${url} failed (${r.status})`);
  return r.json() as Promise<T>;
}

async function jsend<T>(method: string, url: string, body?: unknown): Promise<T> {
  const r = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!r.ok) throw new Error((await safeDetail(r)) || `${method} ${url} failed (${r.status})`);
  return r.json() as Promise<T>;
}

async function safeDetail(r: Response): Promise<string | null> {
  try {
    const data = await r.clone().json();
    return (data && (data.detail || data.message)) ?? null;
  } catch {
    return null;
  }
}

export const api = {
  // ---- config ----
  getConfig: () => jget<ConfigResponse>('/api/config'),
  setProfile: (profile: string) =>
    jsend<ConfigResponse>('PUT', '/api/config/profile', { profile }),
  getProfileParams: (name: string) =>
    jget<{ name: string; params: Record<string, unknown> }>(
      `/api/config/profiles/${encodeURIComponent(name)}`,
    ),
  updateProfileParams: (name: string, params: Record<string, unknown>) =>
    jsend<{ name: string; params: Record<string, unknown> }>(
      'PUT',
      `/api/config/profiles/${encodeURIComponent(name)}`,
      params,
    ),

  // ---- workspaces ----
  listWorkspaces: () => jget<WorkspaceSummary[]>('/api/workspaces'),
  getWorkspace: (id: string) => jget<WorkspaceDetail>(`/api/workspaces/${encodeURIComponent(id)}`),
  createWorkspace: (name: string, description = '', source_folder?: string) =>
    jsend<{ id: string }>('POST', '/api/workspaces', { name, description, source_folder }),
  deleteWorkspace: (id: string) =>
    jsend<{ ok: boolean }>('DELETE', `/api/workspaces/${encodeURIComponent(id)}`),

  // ---- images ----
  listImages: (ws: string) =>
    jget<ImageInfo[]>(`/api/workspaces/${encodeURIComponent(ws)}/images`),
  missingImages: (ws: string) =>
    jget<{ missing: string[]; missing_count: number; annotated: number; present: number }>(
      `/api/workspaces/${encodeURIComponent(ws)}/images/missing`,
    ),
  imageFileUrl: (ws: string, key: string) =>
    `/api/workspaces/${encodeURIComponent(ws)}/images/${encodeURIComponent(key)}/file`,
  imageThumbUrl: (ws: string, key: string, size = 72) =>
    `/api/workspaces/${encodeURIComponent(ws)}/images/${encodeURIComponent(key)}/thumb?size=${size}`,
  uploadImages: async (ws: string, files: File[]) => {
    const fd = new FormData();
    files.forEach((f) => fd.append('files', f));
    const r = await fetch(`/api/workspaces/${encodeURIComponent(ws)}/images/upload`, {
      method: 'POST',
      body: fd,
    });
    if (!r.ok) throw new Error((await safeDetail(r)) || 'upload failed');
    return r.json() as Promise<{ ok: boolean; message: string }>;
  },

  // ---- annotations ----
  getAnnotations: (ws: string, key: string) =>
    jget<AnnotationsResponse>(
      `/api/workspaces/${encodeURIComponent(ws)}/annotations/${encodeURIComponent(key)}`,
    ),
  saveAnnotations: (ws: string, key: string, annotations: Annotation[], rotation = 0) =>
    jsend<AnnotationsResponse>(
      'PUT',
      `/api/workspaces/${encodeURIComponent(ws)}/annotations/${encodeURIComponent(key)}`,
      { annotations, rotation },
    ),

  // ---- detect ----
  detect: (ws: string, key: string) =>
    jsend<{ key: string; annotations: Annotation[] }>(
      'POST',
      `/api/workspaces/${encodeURIComponent(ws)}/detect/${encodeURIComponent(key)}`,
    ),

  // ---- batch detect + jobs ----
  detectBatch: (ws: string, body: { scope: 'empty' | 'all' | 'selected'; keys?: string[]; overwrite?: boolean }) =>
    jsend<{ job_id: string; total: number }>(
      'POST',
      `/api/workspaces/${encodeURIComponent(ws)}/detect`,
      body,
    ),
  getJob: (jobId: string) => jget<JobStatus>(`/api/jobs/${encodeURIComponent(jobId)}`),

  // ---- versions ----
  listVersions: (ws: string) =>
    jget<VersionInfo[]>(`/api/workspaces/${encodeURIComponent(ws)}/versions`),
  createVersion: (ws: string, name: string, base?: string, description = '') =>
    jsend('POST', `/api/workspaces/${encodeURIComponent(ws)}/versions`, { name, base, description }),
  switchVersion: (ws: string, name: string) =>
    jsend('POST', `/api/workspaces/${encodeURIComponent(ws)}/versions/${encodeURIComponent(name)}/switch`),
  deleteVersion: (ws: string, name: string) =>
    jsend('DELETE', `/api/workspaces/${encodeURIComponent(ws)}/versions/${encodeURIComponent(name)}`),

  // ---- export (returns a job id; poll getJob for progress + result) ----
  exportDataset: (ws: string, params: ExportParams) =>
    jsend<{ job_id: string }>('POST', `/api/workspaces/${encodeURIComponent(ws)}/export`, params),
};
