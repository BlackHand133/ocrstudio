import type { DatasetFormat } from '../../../api/client';

/**
 * Augmentation catalogue and export-format constants for the export wizard.
 *
 * Kept apart from the wizard component because this is data, not UI: the
 * backend contract lives here, and both the controls and the preview read from
 * the same definitions.
 */

// Per-effect tunable parameters. `fixed` carries non-UI params the backend
// needs; each `params` entry becomes a labelled NumberInput the user can adjust.
export type ParamSpec = {
  key: string;
  label: string;
  min: number;
  max: number;
  step: number;
  def: number;
};

export type AugDef = {
  type: string;
  label: string;
  params: ParamSpec[];
  fixed?: Record<string, unknown>;
};

export const AUG_DEFS: AugDef[] = [
  { type: 'blur', label: 'Blur', params: [{ key: 'kernel_size', label: 'Kernel', min: 3, max: 25, step: 2, def: 5 }] },
  {
    type: 'noise',
    label: 'Noise',
    fixed: { noise_type: 'gaussian' },
    params: [{ key: 'intensity', label: 'Intensity', min: 5, max: 80, step: 5, def: 20 }],
  },
  {
    type: 'brightness_contrast',
    label: 'Brightness',
    params: [
      { key: 'brightness', label: 'Brightness', min: -80, max: 80, step: 5, def: 15 },
      { key: 'contrast', label: 'Contrast', min: 0.5, max: 2, step: 0.05, def: 1.2 },
    ],
  },
  { type: 'grayscale', label: 'Grayscale', params: [] },
  { type: 'sharpen', label: 'Sharpen', params: [{ key: 'strength', label: 'Strength', min: 0.2, max: 3, step: 0.1, def: 1 }] },
  { type: 'rotation', label: 'Rotate', params: [{ key: 'angle', label: 'Max angle°', min: 1, max: 30, step: 1, def: 3 }] },
  { type: 'perspective', label: 'Perspective', params: [{ key: 'strength', label: 'Strength', min: 0.02, max: 0.3, step: 0.01, def: 0.08 }] },
  {
    type: 'color_jitter',
    label: 'Color',
    params: [
      { key: 'saturation', label: 'Saturation', min: 0.3, max: 2, step: 0.05, def: 1.3 },
      { key: 'hue', label: 'Hue', min: -0.5, max: 0.5, step: 0.02, def: 0.05 },
    ],
  },
  {
    type: 'shear',
    label: 'Shear',
    params: [
      { key: 'shear_x', label: 'Shear X', min: 0, max: 0.4, step: 0.02, def: 0.1 },
      { key: 'shear_y', label: 'Shear Y', min: 0, max: 0.4, step: 0.02, def: 0 },
    ],
  },
  {
    type: 'random_erasing',
    label: 'Random erase',
    fixed: { prob: 1 },
    params: [{ key: 'area_ratio', label: 'Area', min: 0.02, max: 0.4, step: 0.02, def: 0.06 }],
  },
];

export const defaultAugParams = (): Record<string, Record<string, number>> =>
  Object.fromEntries(
    AUG_DEFS.map((d) => [d.type, Object.fromEntries(d.params.map((p) => [p.key, p.def]))]),
  );

export const FORMATS: { value: DatasetFormat; label: string }[] = [
  { value: 'paddleocr', label: 'PaddleOCR (det + rec)' },
  { value: 'icdar', label: 'ICDAR-2015 (det)' },
  { value: 'coco', label: 'COCO (det)' },
  { value: 'yolo', label: 'YOLO (det)' },
  { value: 'csv', label: 'CSV manifest' },
  { value: 'jsonl', label: 'JSONL manifest' },
];

/** Formats that carry detection boxes only — recognition crops make no sense. */
export const DET_ONLY: DatasetFormat[] = ['icdar', 'coco', 'yolo'];

export const SPLIT_COLORS: Record<string, string> = {
  train: 'blue',
  valid: 'teal',
  test: 'orange',
};
