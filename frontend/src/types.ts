// Mirror of server/schemas.py — keep in sync.

export type Point = [number, number];

export interface Annotation {
  points: number[][];
  transcription: string;
  difficult: boolean;
  shape: string; // "Quad" | "Polygon" | "Mask"
  score?: number | null;
  mask_color?: string | null;
  mask_mode?: string | null; // "solid" | "blur" | "pixelate"
}

export interface WorkspaceSummary {
  id: string;
  name: string;
  description: string;
  source_folder: string;
  created_at: string;
  modified_at: string;
  current_version: string;
  available_versions: string[];
}

export interface WorkspaceDetail extends WorkspaceSummary {
  image_count: number;
  annotated_count: number;
}

export interface ImageInfo {
  key: string;
  has_annotations: boolean;
  annotation_count: number;
}

export interface AnnotationsResponse {
  key: string;
  rotation: number;
  annotations: Annotation[];
}

export interface ConfigResponse {
  profiles: string[];
  current_profile: string;
  languages: string[];
}

export interface ExportResult {
  kind: string;
  folder: string;
  splits: Record<string, number>;
  total: number;
  download_url: string;
}

export interface JobStatus {
  id: string;
  type: string;
  status: 'running' | 'done' | 'error';
  total: number;
  done: number;
  message: string;
  result: { processed?: number; failed?: number } | null;
  error: string | null;
}

export interface VersionInfo {
  name: string;
  is_current: boolean;
  description: string;
  created_at: string;
  modified_at: string;
  metadata: Record<string, unknown>;
}

export type Tool = 'select' | 'quad' | 'polygon' | 'mask';
