import { useState } from 'react';
import {
  Alert,
  Button,
  Checkbox,
  Group,
  Modal,
  NumberInput,
  Progress,
  Select,
  SegmentedControl,
  Stack,
  Switch,
  Text,
} from '@mantine/core';
import { IconDownload } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import {
  api,
  type DatasetFormat,
  type ExportParams,
  type SplitMode,
  type SplitPreview,
} from '../../api/client';
import { useEditor } from '../../store/editor';
import { useImages } from '../../hooks/queries';
import { saveCurrent } from '../../controller';
import { useT } from '../../i18n';
import type { ExportResult } from '../../types';

const AUGS: { type: string; label: string; params: Record<string, unknown> }[] = [
  { type: 'blur', label: 'Blur', params: { kernel_size: 5 } },
  { type: 'noise', label: 'Noise', params: { noise_type: 'gaussian', intensity: 20 } },
  { type: 'brightness_contrast', label: 'Brightness', params: { brightness: 15, contrast: 1.2 } },
  { type: 'grayscale', label: 'Grayscale', params: {} },
  { type: 'sharpen', label: 'Sharpen', params: { strength: 1 } },
  { type: 'rotation', label: 'Rotate ±3°', params: { angle: 3 } },
  { type: 'perspective', label: 'Perspective', params: { strength: 0.08 } },
  { type: 'random_erasing', label: 'Random erase', params: { prob: 1, area_ratio: 0.06 } },
];

const FORMATS: { value: DatasetFormat; label: string }[] = [
  { value: 'paddleocr', label: 'PaddleOCR (det + rec)' },
  { value: 'icdar', label: 'ICDAR-2015 (det)' },
  { value: 'coco', label: 'COCO (det)' },
  { value: 'yolo', label: 'YOLO (det)' },
  { value: 'csv', label: 'CSV manifest' },
  { value: 'jsonl', label: 'JSONL manifest' },
];
const DET_ONLY: DatasetFormat[] = ['icdar', 'coco', 'yolo'];

export function ExportModal({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const t = useT();
  const workspaceId = useEditor((s) => s.workspaceId);
  const excluded = useEditor((s) => s.excluded);
  const { data: images } = useImages(workspaceId);
  const [kind, setKind] = useState<'detection' | 'recognition'>('detection');
  const [datasetFormat, setDatasetFormat] = useState<DatasetFormat>('paddleocr');
  const [splitMode, setSplitMode] = useState<SplitMode>('percentage');
  const [train, setTrain] = useState<number>(80);
  const [valid, setValid] = useState<number>(10);
  const [test, setTest] = useState<number>(10);
  const [trainCount, setTrainCount] = useState<number>(0);
  const [validCount, setValidCount] = useState<number>(0);
  const [testCount, setTestCount] = useState<number>(0);
  const [nBins, setNBins] = useState<number>(3);
  const [groupByImage, setGroupByImage] = useState<boolean>(true);
  const [format, setFormat] = useState<'png' | 'jpg'>('png');
  const [crop, setCrop] = useState<'bbox' | 'rotated'>('bbox');
  const [autoOrient, setAutoOrient] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ExportResult | null>(null);
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null);
  const [preview, setPreview] = useState<SplitPreview | null>(null);
  const [augment, setAugment] = useState(false);
  const [augMode, setAugMode] = useState<'combinatorial' | 'sequential'>('combinatorial');
  const [augCopies, setAugCopies] = useState<number>(1);
  const [selAugs, setSelAugs] = useState<string[]>(['blur', 'brightness_contrast']);

  const sum = train + valid + test;

  const buildParams = (): ExportParams => {
    const params: ExportParams = {
      kind,
      dataset_format: datasetFormat,
      split_mode: splitMode,
      train,
      valid,
      test,
      train_count: trainCount,
      valid_count: validCount,
      test_count: testCount,
      n_bins: nBins,
      group_by_image: groupByImage,
      image_format: format,
      crop_method: crop,
      auto_orient: autoOrient,
    };
    if (excluded.size && images?.length) {
      params.selected_keys = images.filter((i) => !excluded.has(i.key)).map((i) => i.key);
    }
    if (augment && selAugs.length) {
      params.augment = true;
      params.aug_mode = augMode;
      params.aug_copies = augCopies;
      params.augmentations = AUGS.filter((a) => selAugs.includes(a.type)).map((a) => ({
        type: a.type,
        params: a.params,
      }));
      params.aug_targets = ['train'];
    }
    return params;
  };

  const doPreview = async () => {
    if (!workspaceId) return;
    try {
      await saveCurrent();
      setPreview(await api.previewSplit(workspaceId, buildParams()));
    } catch (e) {
      notifications.show({ color: 'red', message: (e as Error).message });
    }
  };

  const run = async () => {
    if (!workspaceId) return;
    setBusy(true);
    setResult(null);
    try {
      await saveCurrent(); // persist unsaved edits — export reads from disk
      const { job_id } = await api.exportDataset(workspaceId, buildParams());
      let job = await api.getJob(job_id);
      while (job.status === 'running') {
        setProgress({ done: job.done, total: job.total });
        await new Promise((r) => setTimeout(r, 500));
        job = await api.getJob(job_id);
      }
      if (job.status === 'done') {
        const res = job.result as unknown as ExportResult;
        setResult(res);
        notifications.show({ color: 'green', message: t('exp.exported', { n: res.total }) });
      } else {
        notifications.show({ color: 'red', title: t('exp.failed'), message: job.error || 'error' });
      }
    } catch (e) {
      notifications.show({ color: 'red', title: t('exp.failed'), message: (e as Error).message });
    } finally {
      setBusy(false);
      setProgress(null);
    }
  };

  return (
    <Modal opened={opened} onClose={onClose} title={t('exp.title')} size="md">
      <Stack gap="sm">
        <Select
          label={t('exp.format')}
          value={datasetFormat}
          onChange={(v) => {
            const f = (v as DatasetFormat) || 'paddleocr';
            setDatasetFormat(f);
            setPreview(null);
            if (DET_ONLY.includes(f)) setKind('detection');
          }}
          data={FORMATS}
          allowDeselect={false}
          comboboxProps={{ withinPortal: true }}
        />

        <div>
          <Text size="sm" fw={500} mb={4}>
            {t('exp.dsType')}
          </Text>
          <SegmentedControl
            fullWidth
            value={kind}
            onChange={(v) => {
              setKind(v as 'detection' | 'recognition');
              setPreview(null);
            }}
            data={[
              { label: t('exp.detection'), value: 'detection' },
              {
                label: t('exp.recognition'),
                value: 'recognition',
                disabled: DET_ONLY.includes(datasetFormat),
              },
            ]}
          />
          {DET_ONLY.includes(datasetFormat) && (
            <Text size="xs" c="dimmed" mt={4}>
              {t('exp.formatDetOnly')}
            </Text>
          )}
        </div>

        <div>
          <Text size="sm" fw={500} mb={4}>
            {t('exp.splitMode')}
          </Text>
          <SegmentedControl
            fullWidth
            size="xs"
            value={splitMode}
            onChange={(v) => {
              setSplitMode(v as SplitMode);
              setPreview(null);
            }}
            data={[
              { label: t('exp.byPct'), value: 'percentage' },
              { label: t('exp.byCount'), value: 'count' },
              { label: t('exp.byStrat'), value: 'stratified' },
            ]}
          />
          {splitMode === 'count' ? (
            <Group grow mt={6}>
              <NumberInput label={t('exp.train')} min={0} value={trainCount} onChange={(v) => setTrainCount(Number(v) || 0)} />
              <NumberInput label={t('exp.valid')} min={0} value={validCount} onChange={(v) => setValidCount(Number(v) || 0)} />
              <NumberInput label={t('exp.test')} min={0} value={testCount} onChange={(v) => setTestCount(Number(v) || 0)} />
            </Group>
          ) : (
            <>
              <Group grow mt={6}>
                <NumberInput label={t('exp.train')} min={0} max={100} value={train} onChange={(v) => setTrain(Number(v) || 0)} />
                <NumberInput label={t('exp.valid')} min={0} max={100} value={valid} onChange={(v) => setValid(Number(v) || 0)} />
                <NumberInput label={t('exp.test')} min={0} max={100} value={test} onChange={(v) => setTest(Number(v) || 0)} />
              </Group>
              {sum !== 100 && (
                <Text size="xs" c="orange" mt={4}>
                  {t('exp.splitSum', { s: sum })}
                </Text>
              )}
            </>
          )}
          {splitMode === 'stratified' && (
            <>
              <NumberInput
                mt={6}
                size="xs"
                w={140}
                label={t('exp.nbins')}
                min={2}
                max={10}
                value={nBins}
                onChange={(v) => setNBins(Number(v) || 3)}
              />
              <Text size="xs" c="dimmed" mt={4}>
                {t('exp.stratNote')}
              </Text>
            </>
          )}

          <Group mt={8} gap="xs" align="center">
            <Button size="compact-xs" variant="light" onClick={doPreview}>
              {t('exp.preview')}
            </Button>
            {preview && (
              <Text size="xs" c="dimmed">
                {Object.entries(preview.splits)
                  .map(([k, v]) => `${k}: ${v}`)
                  .join(' · ')}{' '}
                ({preview.total} {preview.unit})
              </Text>
            )}
          </Group>
        </div>

        <Group grow>
          <div>
            <Text size="sm" fw={500} mb={4}>
              {t('exp.imageFormat')}
            </Text>
            <SegmentedControl
              fullWidth
              value={format}
              onChange={(v) => setFormat(v as 'png' | 'jpg')}
              data={['png', 'jpg']}
            />
          </div>
          {kind === 'recognition' && (
            <div>
              <Text size="sm" fw={500} mb={4}>
                {t('exp.cropMethod')}
              </Text>
              <SegmentedControl
                fullWidth
                value={crop}
                onChange={(v) => setCrop(v as 'bbox' | 'rotated')}
                data={[
                  { label: t('exp.bbox'), value: 'bbox' },
                  { label: t('exp.rotated'), value: 'rotated' },
                ]}
              />
            </div>
          )}
        </Group>

        {kind === 'recognition' && (
          <>
            <Switch
              label={t('exp.autoOrient')}
              checked={autoOrient}
              onChange={(e) => setAutoOrient(e.currentTarget.checked)}
            />
            <Switch
              label={t('exp.groupByImage')}
              checked={groupByImage}
              onChange={(e) => {
                setGroupByImage(e.currentTarget.checked);
                setPreview(null);
              }}
            />
          </>
        )}

        <Switch
          label={t('exp.augment')}
          checked={augment}
          onChange={(e) => setAugment(e.currentTarget.checked)}
        />
        {augment && (
          <Stack gap="xs" pl="xs">
            <Checkbox.Group value={selAugs} onChange={setSelAugs}>
              <Group gap="xs">
                {AUGS.map((a) => (
                  <Checkbox key={a.type} value={a.type} label={a.label} size="xs" />
                ))}
              </Group>
            </Checkbox.Group>
            <Group gap="sm" align="flex-end">
              <SegmentedControl
                size="xs"
                value={augMode}
                onChange={(v) => setAugMode(v as 'combinatorial' | 'sequential')}
                data={[
                  { label: t('exp.augSeparate'), value: 'combinatorial' },
                  { label: t('exp.augCombined'), value: 'sequential' },
                ]}
              />
              <NumberInput
                size="xs"
                w={130}
                label={t('exp.copies')}
                min={1}
                max={10}
                value={augCopies}
                onChange={(v) => setAugCopies(Number(v) || 1)}
              />
            </Group>
            <Text size="xs" c="dimmed">
              {t('exp.augNote')}
            </Text>
          </Stack>
        )}

        <Button onClick={run} loading={busy}>
          {t('exp.export')}
        </Button>

        {busy && progress && (
          <div>
            <Progress
              value={progress.total ? (progress.done / progress.total) * 100 : 0}
              striped
              animated
            />
            <Text size="xs" c="dimmed" ta="center" mt={4}>
              {progress.done} / {progress.total}
            </Text>
          </div>
        )}

        {result && (
          <Alert color="green" title={t('exp.exportedTitle', { n: result.total, kind: result.kind })}>
            <Stack gap="xs">
              <Text size="sm">
                {Object.entries(result.splits)
                  .map(([k, v]) => `${k}: ${v}`)
                  .join(' · ')}
              </Text>
              <Text size="xs" c="dimmed">
                {t('exp.savedTo', {
                  dir: `${result.kind === 'detection' ? 'output_det' : 'output_rec'}/${result.folder}`,
                })}
              </Text>
              <Button
                component="a"
                href={result.download_url}
                leftSection={<IconDownload size={16} />}
                variant="light"
                size="xs"
              >
                {t('exp.download')}
              </Button>
            </Stack>
          </Alert>
        )}
      </Stack>
    </Modal>
  );
}
